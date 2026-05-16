from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "evaluation" / "reports"
TESTSET = ROOT / "evaluation" / "testsets" / "single_turn_200.jsonl"


def run(command: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return completed.returncode == 0, output


def api_available(base_url: str) -> bool:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []

    if not TESTSET.exists():
        ok, output = run([sys.executable, "evaluation/build_testset.py"])
        steps.append({"name": "build_testset", "ok": ok, "output": output[-1200:]})

    ok, output = run([sys.executable, "evaluation/eval_retrieval.py"])
    steps.append({"name": "eval_retrieval", "ok": ok, "output": output[-1200:]})

    base_url = "http://localhost:7860"
    if api_available(base_url):
        ok, output = run([sys.executable, "evaluation/eval_generation.py", "--base-url", base_url])
        steps.append({"name": "eval_generation", "ok": ok, "output": output[-1200:]})
        ok, output = run([sys.executable, "evaluation/eval_latency.py", "--base-url", base_url])
        steps.append({"name": "eval_latency", "ok": ok, "output": output[-1200:]})
    else:
        steps.append({"name": "api_checks", "ok": False, "output": "Skipped: local API server is not running."})

    metrics = {
        "retrieval": read_json(REPORT_DIR / "retrieval_metrics.json"),
        "generation": read_json(REPORT_DIR / "generation_metrics.json").get("metrics", {}),
        "latency": read_json(REPORT_DIR / "latency_metrics.json"),
        "steps": steps,
    }
    (REPORT_DIR / "latest_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# eGov RAG Evaluation Report",
        "",
        "## Retrieval",
        f"- Metrics: `{json.dumps(metrics['retrieval'], ensure_ascii=False)}`",
        "",
        "## Generation",
        f"- Metrics: `{json.dumps(metrics['generation'], ensure_ascii=False)}`",
        "",
        "## Latency",
        f"- Metrics: `{json.dumps(metrics['latency'], ensure_ascii=False)}`",
        "",
        "## Steps",
    ]
    for step in steps:
        lines.append(f"- {step['name']}: {'pass' if step['ok'] else 'skip/fail'}")
    (REPORT_DIR / "latest_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

