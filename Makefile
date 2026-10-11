# Fiecare țintă e un înveliș subțire peste o comandă `python -m ...`.
# Fără make (Windows): rulați direct comanda din dreapta, listată și în README.md.
PY ?= python

.PHONY: help setup test demo eval eval-report watch serve schema validate data acoustic pipeline record live

help:
	@$(PY) -c "print('targets: setup test demo eval eval-report watch serve schema validate data acoustic pipeline record live')"

setup:        ## pip install -r requirements.txt + core.hooksPath=.githooks
	$(PY) -m devtools.bootstrap

test:
	$(PY) -m pytest

demo:         ## traffic (fixed seed) + scenario + acoustic + pipeline -> out/timeline.json
	$(PY) -m core.demo

eval:         ## metrics on the tuning seed
	$(PY) -m eval.evaluate --seed-set tuning --run

eval-report:  ## tuning + held-out; writes pitch/metrics.md
	$(PY) -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md

watch:        ## micro-batches on a simulated clock (after make demo)
	$(PY) -m core.pipeline --watch

serve:        ## then open http://localhost:8000/web/
	$(PY) -m http.server 8000

schema:
	$(PY) -m contracts.export_schema

validate:
	$(PY) -m contracts.validate out/timeline.json --model Timeline

data:
	$(PY) -m data.generate
	$(PY) -m data.inject

acoustic:
	$(PY) -m acoustic.analyze

pipeline:
	$(PY) -m core.pipeline

record:       ## real AIS from aisstream.io -> data/raw/ais/<area>/ (needs AISSTREAM_API_KEY in .env)
	$(PY) -m data.aisstream

live:         ## pipeline on the real AIS recording, wall clock -> out/timeline.json (mode live)
	$(PY) -m core.live
