# ShopSense AI

![CI](https://github.com/veduhh/shopsense-ai/actions/workflows/ci.yml/badge.svg)

ShopSense AI is an intelligent ethical price comparison platform. It ranks products by value, credibility, and ethics using a Flask backend and a responsive UI.

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

3) Production (Render)

This project includes a `render.yaml` manifest. Basic Render steps:

- Create a Render account and connect your GitHub repo.
- Create a new Web Service (Python).
- Build command: `pip install -r requirements.txt`.
- Start command: `gunicorn -b 0.0.0.0:$PORT app:app`.

Tip: For Windows hosts use `waitress` instead of `gunicorn`.

API

Search via JSON API:

GET `/api/search?product=<query>`

Response: JSON object with `query` and `results` (each result includes `score_breakdown`).

Error handling & loading

- The UI shows a clear message when no results are found.
- A small loading indicator appears while searches run.

Testing

```powershell
python -m pytest -q
```

Notes for maintainers

- The scoring logic lives in `scoring.py` and is easy to test.
- CSV processing is streamed in `app.py` to support large datasets.
- The app exposes `create_app()` for WSGI servers that prefer a factory function.

Deploying (advanced)

- Use the included `render.yaml` or a Procfile to deploy to Render or other PaaS.
- For Docker deploys, build and run the included `Dockerfile`.

Example: call the API and render a small bar chart (Chart.js)

1) Simple curl call:

```bash
curl -s "http://localhost:5000/api/search?product=iPhone" | jq .
```

2) Tiny browser example (after loading Chart.js):

```html
<!-- assume `data` is the JSON response's `results` array -->
<canvas id="chart"></canvas>
<script>
	const top = data.slice(0,5);
	const labels = top.map(r => (r.name||'').slice(0,30));
	const scores = top.map(r => Number(r['ShopSense Score'])||0);
	new Chart(document.getElementById('chart').getContext('2d'), {
		type:'bar', data:{ labels, datasets:[{data:scores, backgroundColor:'rgba(37,99,235,0.85)'}] },
		options:{scales:{y:{beginAtZero:true,max:10}},plugins:{legend:{display:false}}}
	});
</script>
```
