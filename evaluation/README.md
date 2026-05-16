# Evaluation

This folder contains lightweight evaluation scripts for the eGov RAG assistant.

Typical flow:

```bash
python evaluation/build_testset.py
python evaluation/eval_retrieval.py
python evaluation/run_all.py
```

`run_all.py` always writes a report. API-based generation and latency checks are skipped when the local server is not running.

