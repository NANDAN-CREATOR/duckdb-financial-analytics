# duckdb-financial-analytics

> A local portfolio analytics engine built entirely on DuckDB.
> No Spark. No cloud warehouse. No infrastructure.
> Just DuckDB + Python + Parquet.

---

## What This Project Does

Simulates a **Asset Management (AM)** data engineering pipeline:

1. **Ingests** daily price data and portfolio holdings as Parquet files
2. **Transforms** with pure DuckDB SQL — daily returns, cumulative returns, rolling volatility, monthly summaries
3. **Analyses** — max drawdown, Sharpe ratio, VaR, sector allocation drift, unrealised P&L
4. **Visualises** in a Jupyter notebook with Plotly charts

---

## Project Structure

```
duckdb-financial-analytics/
├── data/
│   ├── raw/              ← CSV files (human-readable)
│   └── processed/        ← Parquet files (DuckDB reads directly)
├── src/
│   ├── generate_sample_data.py   ← Synthetic data generator (GBM price simulation)
│   ├── ingest.py                 ← Real data ingestion via yfinance
│   ├── transform.py              ← DuckDB SQL transformations
│   ├── analytics.py              ← Analytics functions (drawdown, Sharpe, VaR)
│   └── report.py                 ← Output to CSV/HTML
├── queries/
│   ├── returns.sql       ← Daily, cumulative, monthly returns
│   ├── volatility.sql    ← Rolling vol, drawdown, Sharpe, VaR
│   └── allocation.sql    ← Portfolio valuation, sector allocation, trade summary
├── notebooks/
│   └── exploration.ipynb ← Full analysis with Plotly charts
├── main.py               ← Entry point — runs full pipeline
└── requirements.txt
```

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/duckdb-financial-analytics
cd duckdb-financial-analytics
pip install -r requirements.txt

# 2. Run full pipeline
python main.py

# 3. Open notebook for charts
jupyter notebook notebooks/exploration.ipynb
```

---

## Analytics Included

| Analysis | Description |
|---|---|
| Daily Returns | Price-to-price daily % return per ticker |
| Cumulative Returns | Compound cumulative return from inception |
| Monthly Returns | Month-open to month-close % return |
| Rolling Volatility | 30d / 90d / 252d annualised vol (√252 scaled) |
| Maximum Drawdown | Peak-to-trough % decline per ticker |
| Sharpe Ratio | (Ann. return - 5% RFR) / Ann. vol |
| Value at Risk | Parametric 95% and 99% 1-day VaR |
| Portfolio P&L | Unrealised gain/loss per position |
| Sector Allocation | Actual vs target % with drift flag |
| Trade Summary | Monthly buy/sell activity by ticker |

---

## Why DuckDB?

```python
# This runs on your laptop. No cluster. No credentials. No waiting.
import duckdb
duckdb.sql("SELECT * FROM read_parquet('data/processed/prices.parquet')").df()
```

- `pip install duckdb` — entire setup
- Reads Parquet, CSV, Delta Lake natively
- Full SQL: window functions, CTEs, MERGE — everything
- 6,000 row dataset processed in **0.08 seconds**
- Same files your Databricks/Snowflake pipeline uses in production

Use DuckDB during development. Graduate to Databricks or Snowflake for production scale.

---

## Sample Output

```
--- Maximum Drawdown ---
ticker     sector  max_drawdown_pct
   BLK Financials            -47.35
  SCHW Financials            -42.11
  AAPL Technology            -32.21
  MSFT Technology            -22.08

--- Sharpe Ratio ---
ticker  ann_return_pct  ann_vol_pct  sharpe_ratio
  MSFT           32.14        25.33         1.071
   BAC           18.89        26.08         0.533
  AAPL           13.65        27.71         0.312

--- Sector Allocation vs Target ---
    sector  actual_pct  target_pct  drift_pct
Financials       51.25        60.0      -8.75
Technology       48.75        40.0      +8.75
```

---

## Author

**Aman Kumar** — Senior Data Engineer, EY GDS

- Medium: [Data engineering Use Cases Decoded](https://medium.com/@aman)
- LinkedIn: [linkedin.com/in/aman-nandan-7b184b143](https://linkedin.com/in/aman-nandan-7b184b143)
- GitHub: [github.com/aman-nandan](https://github.com/aman-nandan)

---

*Part of the **Data engineering Use Cases Decoded** series — real-world data engineering patterns for financial services.*
