from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import requests


def load_jsonl(path: Path, limit: int) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[:limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:7860")
    parser.add_argument("--testset", default="evaluation/testsets/single_turn_200.jsonl")
    parser.add_argument("--output", default="evaluation/reports/generation_metrics.json")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    rows = load_jsonl(Path(args.testset), args.limit)
    results = []
    for index, item in enumerate(rows):
        start = time.perf_counter()
        response = requests.post(
            f"{base_url}/chat",
            json={"question": item["question"], "session_id": f"eval-generation-{index}"},
            timeout=180,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        source_urls = [source.get("url") for source in data.get("sources", [])]
        results.append(
            {
                "question": item["question"],
                "expected_url": item["expected_url"],
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "source_url_match": item["expected_url"] in source_urls,
                "answer_chars": len(data.get("answer", "")),
            }
        )

    latencies = [item["latency_ms"] for item in results]
    metrics = {
        "count": len(results),
        "success_rate": sum(1 for item in results if item["status_code"] == 200) / max(1, len(results)),
        "source_url_match": sum(1 for item in results if item["source_url_match"]) / max(1, len(results)),
        "latency_p50_ms": int(statistics.median(latencies)) if latencies else 0,
        "latency_p95_ms": int(sorted(latencies)[int(0.95 * (len(latencies) - 1))]) if latencies else 0,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"metrics": metrics, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

