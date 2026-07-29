# DevCrew AI Backend

This backend now implements the Stage 2 multi-agent workflow:

- Supervisor
- Architect
- Researcher
- Coder
- Reviewer
- Documentation

It exposes an asynchronous `POST /generate` endpoint that returns a `job_id`, plus `GET /status/{job_id}` for live progress polling.

Quick start:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

Generate a project:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/generate `
	-ContentType "application/json" `
	-Body '{"prompt":"Build a FastAPI Todo API with JWT authentication"}'
```

Poll status:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/status/<job_id>
```
