# Automation Patterns

## 1) GitHub Actions (quick orchestration)
- Use `.github/workflows/scheduled-catalog.yml`.
- Weekly snapshot run with safe limits (`max-categories`, `max-pages-per-category`).
- Artifacts are uploaded per run.

## 2) Cron (local/server)
```bash
0 9 * * 1 cd /path/to/kotsovolos-catalog-pipeline && .venv/bin/python3 src/kotsovolos_pipeline.py --mode all --products-file output/kotsovolos_products.xlsx --summary-markdown output/kotsovolos_summary.md
```

## 3) Airflow
Use a DAG with `BashOperator` calling the CLI command.

## 4) n8n
Suggested flow:
1. `Cron` node
2. `Execute Command` node (run the CLI)
3. `Read Binary File` + `Email`/`Slack` node to deliver outputs to non-tech users
