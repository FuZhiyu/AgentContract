---
name: wrds-data
description: Search and download financial data from WRDS (Wharton Research Data Services). Use when asked to "download from WRDS", "search WRDS", "get CRSP data", "download Compustat", "find WRDS table", "get stock returns", "download IBES", or any WRDS/financial database task involving CRSP, Compustat, IBES, TAQ, OptionMetrics, Fama-French, BoardEx, DealScan, or other WRDS datasets.
user-invocable: true
---

# WRDS Data

Download and query data from WRDS (Wharton Research Data Services) using the `wrds` Python package.

## Step 0: Check Credentials

Before any WRDS operation, verify the environment is set up:

```bash
uv run python ${CLAUDE_SKILL_DIR}/scripts/wrds_setup.py --check
```

If any check fails, guide the user through setup:

1. **No WRDS account**: Direct to https://wrds-www.wharton.upenn.edu/register/ — requires institutional affiliation.
2. **wrds package missing**: Run `uv pip install wrds`.
3. **No .pgpass credentials**: Either run the interactive setup:
   ```bash
   uv run python ${CLAUDE_SKILL_DIR}/scripts/wrds_setup.py --setup
   ```
   Or manually create `~/.pgpass` with:
   ```
   wrds-pgdata.wharton.upenn.edu:9737:wrds:USERNAME:PASSWORD
   ```
   Then `chmod 600 ~/.pgpass` on Unix/macOS.

Do NOT proceed with queries until `--check` passes.

## Step 1: Identify the Dataset

If the user specifies a library/table, proceed directly. Otherwise, help them find it.

### Browse libraries and tables

```python
import wrds
db = wrds.Connection()

# List all accessible libraries
libs = db.list_libraries()

# List tables in a library
tables = db.list_tables(library='crsp')

# Describe a table (columns, types)
schema = db.describe_table(library='crsp', table='dsf')

# Approximate row count
count = db.get_row_count('crsp', 'dsf')

# Preview data
sample = db.get_table('crsp', 'dsf', rows=5)
```

For common datasets (CRSP, Compustat, IBES, etc.), consult the reference:
- **[Common datasets and query recipes](references/common_datasets.md)** — libraries, tables, standard filters, and variable glossary

## Step 2: Build and Execute the Query

Use `db.raw_sql()` for all queries — it is the most flexible method.

```python
data = db.raw_sql(
    "SELECT permno, date, ret FROM crsp.dsf WHERE date >= '2020-01-01'",
    date_cols=['date']
)
```

### Key parameters

| Parameter | Usage |
|-----------|-------|
| `date_cols` | List of columns to parse as dates — always specify |
| `params` | Dict for parameterized queries: `%(name)s` syntax |
| `chunksize` | Process in chunks (default 500k rows); set `None` to disable |
| `return_iter` | `True` to get an iterator for very large downloads |
| `dtype_backend` | `"pyarrow"` for memory-efficient Arrow-backed DataFrames |

### Parameterized queries (prevent SQL injection)

```python
params = {'tickers': ('AAPL', 'MSFT'), 'start': '2023-01-01'}
data = db.raw_sql("""
    SELECT a.permno, a.date, a.ret, b.ticker
    FROM crsp.dsf a
    JOIN crsp.stocknames b ON a.permno = b.permno
        AND a.date >= b.namedt AND a.date <= b.nameendt
    WHERE b.ticker IN %(tickers)s
        AND a.date >= %(start)s
""", params=params, date_cols=['date'])
```

### Large downloads

For datasets exceeding ~1M rows, use chunked iteration:

```python
chunks = db.raw_sql(
    "SELECT * FROM crsp.dsf WHERE date >= '2000-01-01'",
    chunksize=500000, return_iter=True
)
for i, chunk in enumerate(chunks):
    chunk.to_parquet(f'data/crsp_dsf_{i}.parquet')
```

Or download in one shot and save:

```python
data = db.raw_sql("...", date_cols=['date'])
data.to_parquet('data/output.parquet')
# or
data.to_csv('data/output.csv', index=False)
```

## Step 3: Save Output

Default conventions:
- Save to `Data/` directory in the project root (create if needed)
- Prefer **Parquet** for large datasets (faster, smaller, typed)
- Use **CSV** if the user requests it or for small datasets
- Name files descriptively: `crsp_daily_2020_2023.parquet`, `compustat_annual.csv`

Always close the connection when done:

```python
db.close()
```

## Error Handling

- **`NotSubscribedError`** — user lacks subscription to this library. Inform them to request access via their institution's WRDS coordinator.
- **`SchemaNotFoundError`** — library name is wrong. Use `db.list_libraries()` to find the correct name.
- **Timeout on large queries** — add date filters or use chunked downloads.

## Notes

- WRDS uses PostgreSQL under the hood; any valid PostgreSQL SQL works in `raw_sql()`.
- Always include date filters to avoid accidentally downloading entire multi-decade datasets.
- The `wrds` package connects to `wrds-pgdata.wharton.upenn.edu:9737` over SSL.
- Credentials in `~/.pgpass` are never exposed to the LLM — the wrds package reads them directly.

## Resources

### scripts/
- `wrds_setup.py` — Check environment and interactively configure WRDS credentials

### references/
- `common_datasets.md` — Common WRDS libraries, tables, query recipes, and variable glossary
