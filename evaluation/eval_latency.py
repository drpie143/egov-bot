from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:7860")
    parser.add_argument("--output", default="evaluation/reports/latency_metrics.json")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--question", default="Đăng ký khai sinh cần giấy tờ gì?")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    latencies: list[int] = []
    for index in range(args.repeats):
        start = time.perf_counter()
        response = requests.post(
            f"{base_url}/chat",
            json={"question": args.question, "session_id": f"eval-latency-{index}"},
            timeout=180,
        )
        response.raise_for_status()
        latencies.append(int((time.perf_counter() - start) * 1000))

    metrics = {
        "count": len(latencies),
        "latency_p50_ms": int(statistics.median(latencies)) if latencies else 0,
        "latency_p95_ms": int(sorted(latencies)[int(0.95 * (len(latencies) - 1))]) if latencies else 0,
        "latency_max_ms": max(latencies) if latencies else 0,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

