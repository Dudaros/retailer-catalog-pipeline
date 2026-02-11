# Retail Catalog Pipeline

A Python data pipeline that extracts category hierarchies and product catalog data from an e-commerce API, then produces analysis-ready outputs and stakeholder-friendly summaries.

## Project Overview
This project demonstrates an end-to-end data engineering workflow:
- ingest hierarchical category data
- crawl paginated product endpoints
- normalize and enrich records
- generate business-facing reports
- support scheduled execution (CI, cron, Airflow, n8n)

## Tech Stack
- Python 3
- Requests
- Pandas
- OpenPyXL
- Pytest
- GitHub Actions

## Key Features
- Menu/category extraction with recursive traversal
- Product scraping by category and page
- Retry strategy with exponential backoff
- Deduplication for product-level records
- Multi-sheet Excel export (`products`, `category_summary`, `brand_summary`)
- Markdown summary generation for non-technical stakeholders
- Configurable endpoint templates via CLI args or environment variables

## Installation
```bash
git clone https://github.com/your-username/retailer-catalog-pipeline.git
cd retailer-catalog-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
### 1) Sample run (safe limits)
```bash
python3 src/retailer_catalog_pipeline.py \
  --mode all \
  --max-categories 2 \
  --max-pages-per-category 2 \
  --products-file output/retailer_products_sample.xlsx \
  --summary-markdown output/retailer_summary_sample.md
```

### 2) Menu only
```bash
python3 src/retailer_catalog_pipeline.py \
  --mode menu \
  --menu-file output/menu_structure.xlsx
```

### 3) Products only
```bash
python3 src/retailer_catalog_pipeline.py \
  --mode products \
  --menu-file output/menu_structure.xlsx \
  --level 3 \
  --products-file output/retailer_products.xlsx \
  --summary-markdown output/retailer_summary.md
```

## Endpoint Configuration
The repository is anonymized. Provide your own endpoints using arguments or env vars:

- `--menu-url` / `RETAILER_MENU_URL`
- `--model-url-template` / `RETAILER_MODEL_URL_TEMPLATE`
- `--catalog-url-template` / `RETAILER_CATALOG_URL_TEMPLATE`

Required placeholders in templates:
- model template: `{path}`
- catalog template: `{category_key}`, `{page}`, `{page_size}`


Optional starter files:
- `.env.example`
- `config/endpoints.sample.json`

Example:
```bash
python3 src/retailer_catalog_pipeline.py \
  --mode all \
  --menu-url "https://your-domain/content/store/navigation.json" \
  --model-url-template "https://your-domain/content/store/products/{path}.model.json" \
  --catalog-url-template "https://your-domain/api/search/byCategory/{category_key}?pageNumber={page}&pageSize={page_size}"
```

## Sample Output
`output/retailer_summary_sample.md` includes sections like:

```md
# Retail Catalog Summary
- Categories processed: 2
- Products captured: 30

## Top Categories
| Category | Products |
|---|---:|
| Smartphones | 15 |
| Tablets | 15 |
```

## Developer Commands
```bash
make setup
make menu
make products-sample
make products
make test
make lint
make check
```

## Scheduling
- GitHub Actions: `.github/workflows/scheduled-catalog.yml`
- Additional orchestration patterns: `docs/automation.md`

## Professional Disclaimer
This repository is provided for educational and portfolio purposes. Brand-specific details have been anonymized. Use only with data sources and endpoints you are authorized to access, and always comply with applicable terms of service, privacy requirements, and legal constraints.
