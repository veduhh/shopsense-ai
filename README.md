# ShopSense AI

![CI](https://github.com/veduhh/shopsense-ai/actions/workflows/ci.yml/badge.svg)

Simple Flask app that ranks products by value, credibility and ethics.

Getting started

1) Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

2) Run locally (development):

```powershell
python app.py
# then open http://127.0.0.1:5000
```

3) Production

- For Unix hosts, use gunicorn (already in `requirements.txt`):

```bash
gunicorn -b 0.0.0.0:5000 app:app
```

- For Windows production hosts, use `waitress`:

```powershell
python -m waitress --listen=*:5000 app:app
```

4) Container (Docker):

```bash
docker build -t shopsense-ai:latest .
docker run -p 5000:5000 shopsense-ai:latest
```

Testing

```powershell
python -m pytest -q
```

Files changed

- `app.py` — made robust CSV/JSON loading and safe scoring.
- `templates/index.html` — template loop fixed.
- `requirements.txt` — added production servers and test deps.
- `Dockerfile`, `Procfile` — deployment artifacts.

Next steps

- Add CI (GitHub Actions) to run tests and build the Docker image.
- Add more unit tests for edge cases.

Deploying the dynamic app (recommended) — Render
-----------------------------------------------

Render is a simple PaaS for deploying dynamic apps (Flask) directly from GitHub. To deploy:

1. Create a Render account and connect your GitHub repository: https://render.com
2. Create a new Web Service and point it to this repo and branch `main`.
	- Choose Python environment.
	- Build command: `pip install -r requirements.txt` (the `render.yaml` includes this already).
	- Start command: `gunicorn -b 0.0.0.0:5000 app:app` (Procfile also available).
3. In the repo, add two GitHub Secrets: `RENDER_SERVICE_ID` and `RENDER_API_KEY` (the Render service id and an API key). The repository already includes a workflow `.github/workflows/deploy_render.yml` which will run tests then trigger a render deploy on push to `main`.

Notes:
- The included `render.yaml` is a convenience manifest that Render can use to create/update the service with the right settings.
- If you prefer automatic surface-level setup, you can skip `render.yaml` and configure the service through the Render UI.

