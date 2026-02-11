VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

.PHONY: setup menu products products-sample test lint check

setup:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

menu:
	$(PYTHON) src/retailer_catalog_pipeline.py --mode menu --log-level INFO

products:
	$(PYTHON) src/retailer_catalog_pipeline.py --mode products --menu-file output/menu_structure.xlsx --products-file output/retailer_products.xlsx --summary-markdown output/retailer_summary.md --log-level INFO

products-sample:
	$(PYTHON) src/retailer_catalog_pipeline.py --mode all --max-categories 2 --max-pages-per-category 2 --products-file output/retailer_products_sample.xlsx --summary-markdown output/retailer_summary_sample.md --log-level INFO

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m py_compile src/retailer_catalog_pipeline.py tests/test_pipeline.py

check: lint test
