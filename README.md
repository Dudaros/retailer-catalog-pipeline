# Retail Catalog Pipeline

## What This Project Does

This project is a configurable pipeline that:
- extracts a category/menu hierarchy,
- scrapes paginated product data by category,
- and exports analysis-ready Excel outputs plus summaries.

## Why It Was Built

It was built to standardize catalog data collection into a repeatable process with retries, parsing safeguards, and structured exports for reporting.

## Tech Stack

- Python 3
- requests
- pandas
- openpyxl
- urllib3
- pytest

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## How To Run

```bash
python src/retailer_catalog_pipeline.py --mode all
```

Common modes:
- `--mode menu`
- `--mode products`
- `--mode all`

## Configuration

This project does not require a mandatory config file.

Source endpoints are provided through CLI arguments or environment variables:
- `RETAILER_MENU_URL`
- `RETAILER_MODEL_URL_TEMPLATE`
- `RETAILER_CATALOG_URL_TEMPLATE`

CLI options also control page size, retries, timeout, delay, output paths, and processing limits.
