PY ?= python3

.PHONY: setup test harness train app demo

setup:
	$(PY) -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

test:
	$(PY) -m pytest -q

harness:
	$(PY) -m failover.core.harness --out outputs

train:
	$(PY) -m failover.ml.train_all

app:
	$(PY) -m failover.app.server

demo: harness train app
