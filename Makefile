# Uses the project virtualenv when it exists, else the system python3.
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
HOST ?= 127.0.0.1
PORT ?= 5000

.PHONY: setup test harness train app serve docker demo

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	$(PY) -m pytest -q

harness:
	$(PY) -m failover.core.harness --out outputs

train:
	$(PY) -m failover.ml.train_all

app:
	HOST=$(HOST) PORT=$(PORT) $(PY) -m failover.app.server

serve:
	$(PY) -m gunicorn --workers 2 --timeout 120 --bind $(HOST):$(PORT) failover.app.server:app

docker:
	docker build -t failover-guardian .

demo: harness train app
