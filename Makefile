PYTHON := venv/bin/python

.PHONY: fetch-historical test backtest

fetch-historical:
	$(PYTHON) -m src.fetch_historical

test:
	$(PYTHON) -m pytest tests/ -q

backtest:
	$(PYTHON) eval/backtest.py
