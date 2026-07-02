PYTHON := venv/bin/python

.PHONY: fetch-historical test backtest baselines lockdown unlock

fetch-historical:
	$(PYTHON) -m src.fetch_historical

test:
	$(PYTHON) -m pytest tests/ -q

backtest:
	$(PYTHON) eval/backtest.py

baselines:
	$(PYTHON) eval/baselines.py

# Freeze the data + eval layers against the autonomous loop.
lockdown:
	chmod -R a-w data/ eval/

unlock:
	chmod -R u+w data/ eval/
