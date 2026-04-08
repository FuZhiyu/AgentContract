---
name: econ-data-analysis
description: >
  Guide for rigorous economic data analysis. Use PROACTIVELY whenever performing
  data analysis on economic or financial datasets — importing, cleaning, merging,
  constructing variables, or producing summary statistics. Three core principles:
  (1) describe before and after every transformation, (2) document in jupytext
  percent format with interleaved code/narrative/outputs, (3) validate against
  economic intuition, literature, and cross-variable relationships. Includes
  pitfall checklists for merges, aggregations, filtering, and variable construction.
  Language-agnostic (Python, Julia). Trigger: any data analysis task involving
  economic, financial, or panel data.
user-invocable: true
---

# Economic Data Analysis

Three concurrent principles for rigorous data work. These are not sequential
stages — apply all three at every point in the analysis.

## Principle 1: Description Before Analysis

The most common analytical error is transforming data you do not understand.
**Describe thoroughly and often.**

### After loading any dataset

- **Dimensions**: row × column counts match expectations (N units × T periods)?
- **Column types**: dates as dates, numerics as numerics (not strings)
- **ID uniqueness**: panel ID + time uniquely identifies each row? Check for duplicates
- **Date coverage**: min/max dates; gaps in time series within each unit?
- **Distribution** for key variables: mean, median, std, min, max, and tail
  percentiles (p1, p5, p95, p99) — tails are critical for detecting outliers
- **Missing values**: count and share per variable; is missingness random or
  systematic (concentrated in certain periods, countries, or correlated with
  other variables)?
- **Compare to source**: if documentation states expected sample size, verify

When data was already imported and validated upstream, read existing diagnostics
rather than re-running full validation.

### After every major transformation

Re-run descriptive statistics on affected variables. Compare before/after.
Major transformations include: merges, filters, variable construction,
aggregations, reshaping, deduplication.

**Rule: if something looks unexpected, investigate before proceeding.**
Do not use a variable downstream until its distribution is understood.

### Outlier decisions

- Flag observations beyond p1/p99 — are they data errors or genuine extremes?
- For naturally skewed variables (firm size, wealth, trade volumes), extreme
  values may be real — document the decision to keep, winsorize, or trim
- If winsorizing, document cutoff and consider robustness with alternatives
  (see `references/data-robustness-checklist.md`)

## Principle 2: Logs and Documentation

Analysis scripts should be human-readable documents that interleave code,
narrative, and outputs. Use **jupytext percent format** as the default.

### Script format

Write `.py` or `.jl` files in percent format — `# %%` separates code cells,
`# %% [markdown]` starts narrative cells. For full syntax and rendering
instructions, see `references/jupytext-guide.md`.

Brief example:

```python
# %% [markdown]
"""
## Load Holdings Data
Source: CRSP mutual fund holdings, 2000-2020.
Expect ~4.7M rows across ~12K funds.
"""

# %%
df = pd.read_parquet("Data/holdings.parquet")
print(f"Shape: {df.shape}")
df.describe(percentiles=[.01, .05, .25, .5, .75, .95, .99])

# %% [markdown]
"""
## Merge with Fund Characteristics
Left join on fund_id × date. Expect same row count (fund_chars is m:1).
"""

# %%
n_before = len(df)
df = df.merge(chars, on=["fund_id", "date"], how="left")
print(f"Rows: {n_before} → {len(df)} (delta: {len(df) - n_before})")
```

### Row count tracking

Report before/after row counts for **every** sample-changing operation:
merges, filters, drops, deduplication, sample restrictions. Each gets its own
code cell so the count is visible in the rendered notebook.

### Decision documentation

- **Minor** decisions (winsorization percentile, filter threshold): inline comment
- **Major** decisions (excluding countries, choosing sample period, variable
  definition): markdown cell with reasoning

### Output rendering

Pair the `.py`/`.jl` script with a `.ipynb` notebook:
- The script goes in version control (git-friendly diffs)
- The `.ipynb` holds rendered outputs for human review
- Render with: `jupytext --set-kernel <name> --to notebook --execute script.py`
- See `references/jupytext-guide.md` for details

## Principle 3: Multi-Source Validation

Numbers must make economic sense. Validate against intuition, literature, and
cross-variable relationships.

### Scale check

Does the magnitude match economic intuition? GDP growth of 300% is wrong;
stock returns of -99% need investigation. Compare summary statistics to
published benchmarks (IMF WEO, World Bank, central bank data, prior literature).

### Property check

Is the variable's behavior consistent with priors or what the literature has
found? For constructed variables, spot-check a few observations by hand.
For growth rates, verify against published figures for well-known cases.

### Relationship check

- Compute correlations between new variables and known related measures
- Signs and magnitudes consistent with published stylized facts?
  (e.g., GDP growth positively correlated with employment growth)
- Conditional means across subgroups behave as expected?
  (e.g., developed vs. emerging, pre/post crisis)

### Reference verification

For key variables, find at least one external reference to verify alignment.
If a relationship looks surprising, investigate before proceeding — it may
indicate a data or construction error.

### Missing data as validation signal

- Systematic missingness (concentrated in time/geography) is informative —
  investigate whether it reflects true data absence or a construction error
- Ask: what does "missing" mean here? No position (→ zero) vs didn't report
  (→ truly missing) — the correct treatment depends on the data source and
  research question
- Missing returns treated as zero is almost always wrong

## Pitfalls

Concise checklists for common data manipulation errors. Consult when performing
the relevant operation.

### Merges and joins

- **Before**: check row counts and unique join-key values in both tables
- **Join type**: 1:1, m:1, or 1:m. Many-to-many is almost always a bug —
  it creates a Cartesian product that silently inflates row counts
- **After**: row count should match left table for left join (unless right
  has dupes on the join key — the many-to-many trap)
- **Unmatched**: log how many rows from each side did not match; assess whether
  non-matching is random or systematic

### Sorting

- **Mandatory** before time-series operations: sort by panel ID + time before
  any lag, lead, diff, cumsum, or time-fill
- **Joins destroy sort order** — always re-sort after any merge, even if data
  was sorted before

### Reshaping

- After pivot: unique IDs × unique time periods should match original shape
- Check for unintended NAs from unbalanced panels going wide

### Aggregations

- **Function**: sum dollar amounts, average rates — never the reverse.
  Averaging dollars or summing rates are common silent errors
- **Group-by keys**: verify they match intended level (country-year, not
  country-month)
- **Weights**: if weighted average, verify weights sum to expected values
- **Duplicates**: handle before aggregating — dupes cause double-counting

### Deduplication

- Check uniqueness before operations that assume it (merges, index-setting)
- Document which duplicate kept and why (first, last, highest value, etc.)

### Filtering

- Log rows dropped: count, reason, before/after
- Check non-randomness: are drops concentrated in certain countries, periods,
  or variable ranges? This may introduce sample selection bias
- Verify boolean logic: `&` vs `|` errors are a common silent bug
- Watch chained filters for unintended cumulative effects

### Variable construction

- **Transformation order**: log → winsorize → standardize
  (log after standardize fails because standardized values can be negative)
- **Ratio denominators**: check for zero/near-zero; extreme ratios often come
  from small denominators
- **Growth rates**: compare to published benchmarks for spot checks; first
  differences amplify measurement error — inspect for implausible spikes
- **Standardization**: verify mean ≈ 0, std ≈ 1 within the relevant sample;
  be clear about cross-sectional vs time-series vs pooled

### Missing data handling

- **Explicit** handling (`.fillna(0)`, `.dropna()`, filters) is visible and auditable
- **Implicit** handling (package defaults silently ignoring NaN in aggregations)
  is easy to miss — check alignment with analytical objective
- Ask: what does "missing" mean in this specific context?
- Prefer passing missing through the pipeline over filling silently;
  use fill/coalesce only with explicit justification

## Key References

- `references/jupytext-guide.md` — percent format syntax, rendering, pairing
- `references/data-robustness-checklist.md` — sensitivity analysis: outlier
  alternatives, alternative definitions, sample restrictions, leave-one-out
- Gentzkow & Shapiro (2014), "Code and Data for the Social Sciences"
- AEA Data Editor, "Guidance for Replication Packages"
