# Generated Reports

This directory contains reproducible outputs created by project pipelines. The
generated files are intentionally excluded from Git because they can be rebuilt
from the source data. The two standalone notebook HTML exports in
`reports/notebooks/` are the exception: they are committed as recruiter-friendly
previews that do not require Jupyter.

Run the data-quality audit from the repository root:

```powershell
python scripts\run_data_quality_audit.py
```

The resulting audit files will be written to `reports/data_quality/`.

Run the cleaning pipeline with:

```powershell
python scripts\run_data_cleaning.py
```

Its lineage manifest and post-cleaning validation files will be written to
`reports/data_cleaning/`.

Run the PostgreSQL analytical queries with:

```powershell
python scripts\run_analytics.py
```

Validated KPI and exploratory extracts will be written to `reports/analytics/`.
