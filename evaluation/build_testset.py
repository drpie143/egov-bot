from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

QUESTION_TEMPLATES = [
    "Thủ tục {title} cần hồ sơ gì?",
    "Cơ quan nào thực hiện {title}?",
    "Trình tự thực hiện {title} như thế nào?",
    "Điều kiện thực hiện {title} là gì?",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="static/data/toan_bo_du_lieu_final.json")
    parser.add_argument("--output", default="evaluation/testsets/single_turn_200.jsonl")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records = [record for record in records if record.get("ten_thu_tuc") and record.get("nguon")]
    random.seed(args.seed)
    sample = random.sample(records, min(args.limit, len(records)))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        for record in sample:
            title = record["ten_thu_tuc"]
            template = random.choice(QUESTION_TEMPLATES)
            item = {
                "question": template.format(title=title),
                "expected_title": title,
                "expected_url": record["nguon"],
            }
            file.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(sample)} questions to {output}")


if __name__ == "__main__":
    main()

