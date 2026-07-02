PYTHON := venv/bin/python

.PHONY: fetch-historical test

fetch-historical:
	$(PYTHON) -m src.fetch_historical

test:
	$(PYTHON) -m pytest tests/ -q
