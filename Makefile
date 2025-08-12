SHELL := /usr/bin/bash

.PHONY: setup run

setup:
	python -m venv .venv && . .venv/bin/activate || .venv\Scripts\activate && pip install -r requirements.txt && python -m playwright install

run:
	python extract_maui_deals.py --headed