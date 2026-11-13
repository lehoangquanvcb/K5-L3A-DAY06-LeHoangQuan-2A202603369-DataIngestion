"""Run the VIC corpus with local multilingual embeddings and Qdrant."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from statistics import median
from time import perf_counter

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from .chunking import by_paragraph, fixed_size
from .evaluation import evaluate_query, summarize
from .ingestion import corpus_digest, evidence_text, load_ocr

ROOT = Path(__file__).resolve().parents[2]
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSIONS = 384
STRATEGIES = ("A", "B", "C")
FIXED_SIZE = 500
FIXED_OVERLAP = 50
PARAGRAPH_SIZE = 500


def write_json(path: Path, value: object) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def build_index(client, embedder, name, chunks):
    started = perf_counter()
    if not client.collection_exists(name):
        vectors = list(embedder.embed([chunk.text for chunk in chunks], batch_size=32))
        if len(vectors) != len(chunks):
            raise ValueError("Embedding count differs from chunk count.")
        client.create_collection(name, vectors_config=models.VectorParams(
            size=DIMENSIONS, distance=models.Distance.COSINE))
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            payload = vars(chunk).copy()
            payload["note_topic"] = chunk.metadata["note_topic"]
            points.append(models.PointStruct(id=chunk.chunk_id, vector=vector.tolist(), payload=payload))
        client.upsert(name, points, wait=True)
        reused = False
    else:
        reused = True
    count = client.count(name, exact=True).count
    if count != len(chunks):
        raise ValueError(f"Incomplete collection {name}: {count}/{len(chunks)}. Use a fresh --work-dir.")
    lengths = [len(chunk.text) for chunk in chunks]
    return {
        "collection": name, "chunk_count": count, "characters": sum(lengths),
        "length_min": min(lengths), "length_median": median(lengths), "length_max": max(lengths),
        "index_seconds": round(perf_counter() - started, 4), "reused": reused,
        "service_cost_usd": 0,
    }


def search(client, collection, vector, scope):
    if scope and set(scope) != {"note_topic"}:
        raise ValueError(f"Unsupported filter: {scope}")
    query_filter = models.Filter(must=[
        models.FieldCondition(key=key, match=models.MatchValue(value=value))
        for key, value in scope.items()
    ]) if scope else None
    started = perf_counter()
    result = client.query_points(
        collection, query=vector.tolist(), query_filter=query_filter,
        limit=3, with_payload=True,
    ).points
    elapsed = round((perf_counter() - started) * 1000, 3)
    return [{**point.payload, "score": point.score} for point in result], elapsed


def run(args):
    pages = load_ocr(args.ocr_dir, ROOT / "data/manifest.json")
    benchmark_path = ROOT / "benchmark/vic_fy2025.json"
    benchmark_bytes = benchmark_path.read_bytes()
    benchmark = json.loads(benchmark_bytes)
    if benchmark["status"] != "frozen_before_retrieval":
        raise ValueError("Freeze benchmark before retrieval.")
    source_pages = {(page.document_id, page.page): evidence_text(page.text) for page in pages}
    for question in benchmark["questions"]:
        key = (question["gold_source_id"], question["gold_page"])
        if evidence_text(question["evidence_quote"]) not in source_pages.get(key, ""):
            raise ValueError(f"Gold evidence absent from OCR: {question['id']}")
    configs = {"fixed_size": FIXED_SIZE, "fixed_overlap": FIXED_OVERLAP,
               "paragraph_max": PARAGRAPH_SIZE, "long_paragraph_overlap": 80}
    model = {"name": MODEL, "dimensions": DIMENSIONS, "fastembed_version": version("fastembed"),
             "onnxruntime_version": version("onnxruntime")}
    signature = {
        "corpus_sha256": corpus_digest(pages), "benchmark_sha256": hashlib.sha256(benchmark_bytes).hexdigest(),
        "pipeline_sha256": hashlib.sha256(b"".join(
            (Path(__file__).parent / name).read_bytes()
            for name in ("run.py", "chunking.py", "evaluation.py", "ingestion.py")
        )).hexdigest(),
        "configs": configs, "model": model,
    }
    snapshot = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:20]
    args.work_dir.mkdir(parents=True, exist_ok=True)
    dev_path = args.work_dir / "dev.json"
    dev = None
    if args.split == "test":
        if not dev_path.exists():
            raise ValueError("Run dev and record the strategy before running test.")
        dev = json.loads(dev_path.read_text(encoding="utf-8"))
        if dev["signature"] != signature:
            raise ValueError("Inputs changed since dev. Run dev again before opening test.")
    questions = [q for q in benchmark["questions"] if q["split"] == args.split]
    started = perf_counter()
    embedder = TextEmbedding(MODEL, threads=2)
    model_load_seconds = round(perf_counter() - started, 4)
    started = perf_counter()
    query_vectors = list(embedder.embed([q["question"] for q in questions], batch_size=32))
    query_embedding_seconds = round(perf_counter() - started, 4)
    all_chunks = {
        "A": [chunk for page in pages for chunk in fixed_size(page, FIXED_SIZE, FIXED_OVERLAP)],
        "B": [chunk for page in pages for chunk in by_paragraph(page, PARAGRAPH_SIZE)],
    }
    all_chunks["C"] = all_chunks["B"]
    collections = {"A": f"vic_{snapshot}_a", "B": f"vic_{snapshot}_b", "C": f"vic_{snapshot}_b"}
    traces = {}
    with_client = QdrantClient(path=str(args.work_dir / "qdrant"))
    try:
        index = {key: build_index(with_client, embedder, collections[key], all_chunks[key]) for key in ("A", "B")}
        index["C"] = {**index["B"], "shares_index_with": "B"}
        for key in STRATEGIES:
            traces[key] = []
            for question, vector in zip(questions, query_vectors, strict=True):
                scope = question.get("filter", {}) if key == "C" else {}
                hits, elapsed = search(with_client, collections[key], vector, scope)
                trace = evaluate_query(question, hits)
                trace.update({"applied_filter": scope, "search_ms": elapsed})
                traces[key].append(trace)
    finally:
        with_client.close()
    metrics = {key: summarize(rows) for key, rows in traces.items()}
    # With equal dev scores and service cost, retain the first strategy in A, B, C order.
    selected = dev["selected"] if dev else max(STRATEGIES, key=lambda key: (
        metrics[key]["evidence_hit_at_3"], metrics[key]["hit_at_1"], -index[key]["service_cost_usd"]
    ))
    result = {"signature": signature, "split": args.split, "selected": selected,
              "store": {"name": "Qdrant local", "version": version("qdrant-client"), "metric": "cosine", "exact": True},
              "model_load_seconds": model_load_seconds, "query_embedding_seconds": query_embedding_seconds,
              "index": index, "metrics": metrics, "traces": traces}
    write_json(args.work_dir / f"{args.split}.json", result)
    if args.split == "dev":
        sample = [{"page": page.page, "anchor": evidence_text(page.text)[len(evidence_text(page.text)) // 2:][:30],
                   "coherence": {key: None for key in STRATEGIES}} for page in pages[:10]]
        for row in sample:
            row["chunks"] = {key: [vars(c) for c in all_chunks[key] if c.page == row["page"]
                                   and row["anchor"] in evidence_text(c.text)] for key in STRATEGIES}
        write_json(args.work_dir / "coherence_samples.json", sample)
    print(json.dumps({"split": args.split, "selected": selected, "metrics": metrics}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, default=ROOT / ".day06-vic")
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    args = parser.parse_args()
    try:
        run(args)
    except ValueError as exc:
        parser.exit(1, f"Day 06: {exc}\n")


if __name__ == "__main__":
    main()
