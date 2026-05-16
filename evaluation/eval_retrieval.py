from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from egov_bot.config import load_settings  # noqa: E402
from egov_bot.data.resource_loader import load_resources  # noqa: E402
from egov_bot.retrieval.hybrid_retriever import HybridRetriever  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(items: list[dict], retriever: HybridRetriever, k: int) -> dict:
    hits = 0
    reciprocal = 0.0
    ndcg = 0.0
    for item in items:
        results = retriever.search(item["question"], limit=k)
        urls = [result.url for result in results]
        expected = item["expected_url"]
        if expected in urls:
            hits += 1
            rank = urls.index(expected) + 1
            reciprocal += 1.0 / rank
            ndcg += 1.0 / math.log2(rank + 1)
    total = max(1, len(items))
    return {
        f"recall@{k}": hits / total,
        f"mrr@{k}": reciprocal / total,
        f"ndcg@{k}": ndcg / total,
        "count": len(items),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--testset", default="evaluation/testsets/single_turn_200.jsonl")
    parser.add_argument("--output", default="evaluation/reports/retrieval_metrics.json")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    settings = load_settings()
    resources = load_resources(settings, load_models=True)
    retriever = HybridRetriever(
        settings,
        resources.procedure_store,
        metadatas=resources.metadatas,
        faiss_index=resources.faiss_index,
        bm25=resources.bm25,
        embedding_model=resources.embedding_model,
    )
    metrics = score(load_jsonl(Path(args.testset)), retriever, args.k)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

