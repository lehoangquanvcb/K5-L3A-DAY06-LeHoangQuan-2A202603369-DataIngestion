"""Score exact OCR evidence and retain top-three traces for manual review."""
from .ingestion import evidence_text


def evaluate_query(question: dict, hits: list[dict]) -> dict:
    gold = [question, *question.get("alternative_gold", [])]
    for hit in hits:
        hit["evidence_hit"] = any(
            hit["document_id"] == item["gold_source_id"]
            and hit["page"] == item["gold_page"]
            and evidence_text(item["evidence_quote"]) in evidence_text(hit["text"])
            for item in gold
        )
    return {
        "question": question,
        "top3": hits,
        "hit_at_1": bool(hits and hits[0]["evidence_hit"]),
        "evidence_hit_at_3": any(hit["evidence_hit"] for hit in hits),
    }


def summarize(traces: list[dict]) -> dict:
    filtered = [row for row in traces if row["question"].get("filter")]
    compliant = sum(bool(row["top3"]) and all(
        all(hit["metadata"].get(key) == value for key, value in row["question"]["filter"].items())
        for hit in row["top3"]
    ) for row in filtered)
    return {
        "questions": len(traces),
        "hit_at_1": sum(row["hit_at_1"] for row in traces),
        "evidence_hit_at_3": sum(row["evidence_hit_at_3"] for row in traces),
        "filter_compliance": {"correct": compliant, "total": len(filtered)} if filtered else None,
    }
