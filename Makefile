PY ?= .venv/bin/python
VOICE_URL = https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx
VIDEOS = $(basename $(notdir $(filter-out videos/00-test.yaml,$(wildcard videos/*.yaml))))
JOBS ?= 3

.PHONY: setup all videos thumbs branding video preview qa clean

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	mkdir -p voices
	test -f voices/es_ES-davefx-medium.onnx || curl -L -o voices/es_ES-davefx-medium.onnx $(VOICE_URL)
	test -f voices/es_ES-davefx-medium.onnx.json || curl -L -o voices/es_ES-davefx-medium.onnx.json $(VOICE_URL).json

all: thumbs branding videos

videos:
	mkdir -p output/logs
	printf '%s\n' $(VIDEOS) | xargs -P $(JOBS) -I{} sh -c '$(PY) -m engine.render videos/{}.yaml > output/logs/{}.log 2>&1 && echo "listo: {}"'

thumbs:
	$(PY) -m engine.thumbnail $(addprefix videos/,$(addsuffix .yaml,$(VIDEOS)))

branding:
	$(PY) -m engine.branding

video:
	$(PY) -m engine.render videos/$(V).yaml

preview:
	$(PY) -m engine.render videos/$(V).yaml --fast

qa:
	$(PY) tools/voice_qa.py $(addprefix videos/,$(addsuffix .yaml,$(VIDEOS)))

clean:
	rm -rf output .cache
