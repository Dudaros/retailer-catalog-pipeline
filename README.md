# Kotsovolos Catalog Pipeline

Production-style Python pipeline for:
- extracting category tree from Kotsovolos navigation JSON
- scraping product catalog pages by category
- exporting analysis-ready datasets and non-technical summaries

## Why this project matters
- Replaces manual category/product collection workflows.
- Handles pagination, retries, and resilient parsing.
- Produces stakeholder-friendly outputs (Excel + markdown summary).

## Project structure
```text
kotsovolos-catalog-pipeline/
├── src/kotsovolos_pipeline.py
├── tests/test_pipeline.py
├── docs/automation.md
├── .github/workflows/
│   ├── ci.yml
│   └── scheduled-catalog.yml
├── output/
├── requirements.txt
├── Makefile
└── README.md
```

## Setup
```bash
cd /Users/chatzigrigorioug.a/myproject/kotsovolos-catalog-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
### Full sample run (menu + limited products)
```bash
python3 src/kotsovolos_pipeline.py \
  --mode all \
  --max-categories 2 \
  --max-pages-per-category 2 \
  --products-file output/kotsovolos_products_sample.xlsx \
  --summary-markdown output/kotsovolos_summary_sample.md
```

### Menu only
```bash
python3 src/kotsovolos_pipeline.py --mode menu --menu-file output/menu_structure.xlsx
```

### Products only (from existing menu)
```bash
python3 src/kotsovolos_pipeline.py \
  --mode products \
  --menu-file output/menu_structure.xlsx \
  --level 3 \
  --products-file output/kotsovolos_products.xlsx \
  --summary-markdown output/kotsovolos_summary.md
```

## Makefile shortcuts
```bash
make setup
make menu
make products-sample
make products
make test
make lint
make check
```

## Output
`products` output includes:
- product-level dataset (`products`)
- category aggregation (`category_summary`)
- manufacturer aggregation (`brand_summary`)

Optional markdown summary:
- `output/kotsovolos_summary*.md`

## Scheduling
- GitHub Actions weekly snapshot: `.github/workflows/scheduled-catalog.yml`
- See automation options in `docs/automation.md` (cron, Airflow, n8n)

## Legal and Responsible Use
- Respect target website/API terms of use and fair-use limits.
- Keep request rates moderate (use `--delay-seconds`).
- Do not use this pipeline for unauthorized data extraction.
- Do not publish sensitive or internal-only datasets.

## Testing
```bash
pytest -q
```
