# ARGUS Demo 1 — Code Snapshot

This folder contains the Demo 1 code snapshot for ARGUS, a team project exploring governance for AI-generated Linux shell commands. It is included to provide technical context for the research, benchmark and interface work documented in the parent repository.

**Contribution and scope note:** Demo 1 was developed as part of the shared project. I participated in the project during this phase, but I did not independently build or complete the entire application. The source is therefore presented as a project code snapshot, not as a claim of sole authorship. My individual work samples and documented tasks are described in the parent `README.md`.

## What the demo contains

- `llm_backend.py` — requests structured command output from Ollama and includes an offline mock fallback.
- `governance.py` — rule-based and model-assisted risk classification.
- `core.py` — shared proposal, execution and logging pipeline.
- `app.py` — FastAPI endpoints for the browser interface.
- `main.py` — command-line front end.
- `logger.py` — action logging.
- `static/index.html` — self-contained browser interface.
- `test_prompts.py`, `Benchmark.xlsx`, `baseline_results.csv`, `run_baseline.py` — test and evaluation support files from this snapshot.

## Run locally

Requires Python 3.11+ and Ollama for live model responses. The backend includes an offline mock fallback for supported demo prompts.

```bash
pip install -r requirements.txt
ollama pull llama3.1:8b
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` in your browser. Keep the interface in **DRY-RUN** mode when exploring. Do not use `--execute` on your everyday machine; use an isolated VM or disposable test environment if you need to test actual command execution.

CLI mode:

```bash
python main.py
python main.py --show-log
```

Run the included prompt tests with:

```bash
python test_prompts.py
```

This is a historical project snapshot, not a claim that the application is production-ready or that every planned feature is complete.
