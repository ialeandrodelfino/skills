.DEFAULT_GOAL := help

PYTHON ?= python3
SKILL ?=
BUCKET ?=

FILTERS = $(if $(SKILL),--skill "$(SKILL)") $(if $(BUCKET),--bucket "$(BUCKET)")

.PHONY: help status check update test

help:
	@printf '%s\n' \
	  'make update                  Update verified upstream skills' \
	  'make check                   Check upstreams without changing the catalogue' \
	  'make status                  Show the offline inventory and local edits' \
	  'make update SKILL=firecrawl   Update one skill and its dependencies' \
	  'make check BUCKET=curated     Check one bucket' \
	  'make test                    Run the updater tests'

status check update:
	@$(PYTHON) scripts/upstream-skills.py $@ $(FILTERS)

test:
	@$(PYTHON) -m unittest discover -s tests/upstream_skills -v
