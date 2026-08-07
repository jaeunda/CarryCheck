# Contributing

Keep each change focused on one responsibility. A regulation change must include an official source URL, effective or verification date, dependency notes, and boundary regression tests. Do not add guessed rules or treat blogs and search-result snippets as source data.

## Local Checks

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/test.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check src api tests
node --check public/app.js
```

## Pull Requests

Describe why the change is needed, which countries, airlines, routes, and items are affected, and the exact commands and results used for verification. Do not commit real API keys, passenger information, a local `.env`, virtual environments, or generated caches.
