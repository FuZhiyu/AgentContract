# Common WRDS Datasets

## Quick Reference: Libraries and Key Tables

| Library | Full Name | Key Tables | Description |
|---------|-----------|------------|-------------|
| `crsp` | CRSP | `dsf`, `msf`, `dsenames`, `stocknames`, `dsi`, `msi`, `ccmxpf_lnkhist` | US equity prices, returns, volumes, CCM link |
| `comp` / `comp_na` | Compustat NA | `funda`, `fundq`, `secd`, `secm`, `company` | Financial statements (North America) |
| `comp_global` | Compustat Global | `g_funda`, `g_fundq`, `g_secd`, `g_company` | International financial statements |
| `ibes` | I/B/E/S | `statsum_epsus`, `det_epsus`, `actu_epsus`, `recddet` | Analyst forecasts and recommendations |
| `tfn` | Thomson Reuters | `s34` (13F), `s12` (mutual fund) | Institutional holdings |
| `optionm` | OptionMetrics | `opprcd`, `secprd`, `vsurfd` | Options data |
| `ff` | Fama-French | `factors_daily`, `factors_monthly`, `fivefactors_daily` | Fama-French factors |
| `taq` / `taqmsec` | TAQ | `ctm_*`, `cqm_*` | High-frequency tick data |
| `boardex` | BoardEx | `na_wrds_company_profile`, `na_wrds_org_composition` | Board of directors |
| `dealscan` | DealScan | `facility`, `package`, `borrower` | Syndicated loans |
| `bank` | Bank Regulatory | `call_*` | Bank call reports |
| `audit` | Audit Analytics | Various | Audit and governance |
| `wrdsapps` | WRDS Apps | `ccmxpf_lnkhist` | Pre-built linking tables |

---

## Query Recipes

### CRSP Daily Stock Returns

```python
data = db.raw_sql("""
    SELECT a.permno, a.date, a.ret, a.retx, a.prc, a.vol, a.shrout,
           b.ticker, b.comnam, b.siccd, b.shrcd, b.exchcd
    FROM crsp.dsf AS a
    LEFT JOIN crsp.dsenames AS b
        ON a.permno = b.permno
        AND a.date >= b.namedt
        AND a.date <= b.nameendt
    WHERE a.date BETWEEN '2020-01-01' AND '2023-12-31'
        AND b.shrcd IN (10, 11)
""", date_cols=['date'])
```

Key filters:
- `shrcd IN (10, 11)` — common shares only
- `exchcd IN (1, 2, 3)` — NYSE, AMEX, NASDAQ

### CRSP Monthly Stock Returns

```python
data = db.raw_sql("""
    SELECT a.permno, a.date, a.ret, a.retx, a.prc, a.vol, a.shrout,
           b.ticker, b.comnam, b.siccd, b.shrcd, b.exchcd
    FROM crsp.msf AS a
    LEFT JOIN crsp.msenames AS b
        ON a.permno = b.permno
        AND a.date >= b.namedt
        AND a.date <= b.nameendt
    WHERE a.date BETWEEN '2000-01-01' AND '2023-12-31'
        AND b.shrcd IN (10, 11)
""", date_cols=['date'])
```

### CRSP Index Returns

```python
# Daily
data = db.raw_sql("""
    SELECT date, vwretd, ewretd, sprtrn
    FROM crsp.dsi
    WHERE date BETWEEN '2020-01-01' AND '2023-12-31'
""", date_cols=['date'])

# Monthly
data = db.raw_sql("""
    SELECT date, vwretd, ewretd, sprtrn
    FROM crsp.msi
    WHERE date BETWEEN '2000-01-01' AND '2023-12-31'
""", date_cols=['date'])
```

### Compustat Annual Fundamentals

```python
data = db.raw_sql("""
    SELECT gvkey, datadate, fyear, conm,
           at, lt, sale, revt, ni, ceq, csho, prcc_f,
           ebitda, oibdp, dp, xint, txt, xrd, capx
    FROM comp.funda
    WHERE indfmt = 'INDL'
        AND datafmt = 'STD'
        AND popsrc = 'D'
        AND consol = 'C'
        AND datadate >= '2015-01-01'
""", date_cols=['datadate'])
```

Standard Compustat filters (almost always needed):
- `indfmt = 'INDL'` — industrial format
- `datafmt = 'STD'` — standardized
- `popsrc = 'D'` — domestic population
- `consol = 'C'` — consolidated statements

### Compustat Quarterly Fundamentals

```python
data = db.raw_sql("""
    SELECT gvkey, datadate, fyearq, fqtr, conm,
           atq, ltq, saleq, revtq, niq, ceqq, cshoq, prccq
    FROM comp.fundq
    WHERE indfmt = 'INDL'
        AND datafmt = 'STD'
        AND popsrc = 'D'
        AND consol = 'C'
        AND datadate >= '2015-01-01'
""", date_cols=['datadate'])
```

### CRSP-Compustat Link (CCM)

```python
ccm = db.raw_sql("""
    SELECT gvkey, lpermno AS permno, linkdt, linkenddt, linktype, linkprim
    FROM crsp.ccmxpf_lnkhist
    WHERE linktype IN ('LU', 'LC')
        AND linkprim IN ('P', 'C')
""", date_cols=['linkdt', 'linkenddt'])
```

Link type filters:
- `linktype IN ('LU', 'LC')` — primary link types
- `linkprim IN ('P', 'C')` — primary security

### IBES Analyst Consensus

```python
data = db.raw_sql("""
    SELECT ticker, cusip, cname, fpedats, statpers,
           meanest, medest, stdev, numest, actual
    FROM ibes.statsum_epsus
    WHERE fpi = '1'
        AND statpers >= '2020-01-01'
        AND measure = 'EPS'
""", date_cols=['fpedats', 'statpers'])
```

`fpi` values: `'1'` = annual, `'6'` = quarterly

### Fama-French Factors

```python
data = db.raw_sql("""
    SELECT date, mktrf, smb, hml, rf, umd
    FROM ff.fivefactors_daily
    WHERE date >= '2000-01-01'
""", date_cols=['date'])
```

### Institutional Holdings (13F)

```python
data = db.raw_sql("""
    SELECT mgrno, rdate, fdate, cusip, shares, prc, shrout1
    FROM tfn.s34
    WHERE fdate >= '2020-01-01'
""", date_cols=['rdate', 'fdate'])
```

---

## Variable Glossary

### CRSP Daily/Monthly (`dsf`/`msf`)
| Variable | Description |
|----------|-------------|
| `permno` | Permanent security identifier |
| `date` | Trading date |
| `ret` | Holding-period return (dividends included) |
| `retx` | Return excluding dividends |
| `prc` | Closing price (negative = bid/ask average) |
| `vol` | Trading volume (shares) |
| `shrout` | Shares outstanding (thousands) |
| `cfacpr` | Cumulative factor to adjust price |
| `cfacshr` | Cumulative factor to adjust shares |

### Compustat Annual (`funda`)
| Variable | Description |
|----------|-------------|
| `gvkey` | Global company key |
| `datadate` | Data date (fiscal year end) |
| `fyear` | Fiscal year |
| `at` | Total assets |
| `lt` | Total liabilities |
| `sale` | Net sales/revenue |
| `ni` | Net income |
| `ceq` | Common equity |
| `csho` | Common shares outstanding |
| `prcc_f` | Price close (fiscal year end) |
| `ebitda` | EBITDA |
| `capx` | Capital expenditures |
| `xrd` | R&D expense |
| `dp` | Depreciation and amortization |

### CRSP Name History (`dsenames`/`stocknames`)
| Variable | Description |
|----------|-------------|
| `ticker` | Ticker symbol |
| `comnam` | Company name |
| `siccd` | SIC code |
| `shrcd` | Share code (10/11 = common) |
| `exchcd` | Exchange code (1=NYSE, 2=AMEX, 3=NASDAQ) |
| `namedt` | Name start date |
| `nameendt` | Name end date |
