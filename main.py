"""
main.py
-------
Entry point — runs the full DuckDB Financial Analytics pipeline.
Step 1: Generate sample data
Step 2: Run DuckDB transformations
Step 3: Print analytics output
"""

import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date

# ── Windows-compatible path fix ───────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
SRC  = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from src.generate_sample_data import simulate_prices, build_holdings, build_trades
from src.transform import get_connection, register_views, build_daily_returns, \
    build_cumulative_returns, build_rolling_volatility, build_monthly_returns
from src.analytics import max_drawdown, sharpe_and_var, sector_allocation, portfolio_summary

print("=" * 60)
print("  DuckDB Financial Analytics Engine")
print("  Wealth & Asset Management Portfolio")
print("=" * 60)

# ── Step 1: Generate data ─────────────────────────────────────
print("\n[1/3] Generating financial data...")
(ROOT / "data" / "raw").mkdir(parents=True, exist_ok=True)
(ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)

t0 = time.time()
np.random.seed(42)
trading_dates = pd.bdate_range("2022-01-03", "2024-12-31")
prices   = simulate_prices(trading_dates)
holdings = build_holdings(date(2024, 12, 31))
trades   = build_trades(prices)

prices.to_parquet(ROOT / "data/processed/prices.parquet",     index=False)
holdings.to_parquet(ROOT / "data/processed/holdings.parquet", index=False)
trades.to_parquet(ROOT / "data/processed/trades.parquet",     index=False)
prices.to_csv(ROOT / "data/raw/prices.csv",     index=False)
holdings.to_csv(ROOT / "data/raw/holdings.csv", index=False)
trades.to_csv(ROOT / "data/raw/trades.csv",     index=False)

print(f"  Prices:   {len(prices):,} rows")
print(f"  Holdings: {len(holdings)} positions")
print(f"  Trades:   {len(trades):,} records")
print(f"  Done in {time.time()-t0:.2f}s")

# ── Step 2: Transform ─────────────────────────────────────────
print("\n[2/3] Running DuckDB transformations...")
t0  = time.time()
con = get_connection(str(ROOT / "data/portfolio.duckdb"))
register_views(con)
build_daily_returns(con)
build_cumulative_returns(con)
build_rolling_volatility(con)
build_monthly_returns(con)
print(f"  All tables built in {time.time()-t0:.2f}s")

# ── Step 3: Analytics output ──────────────────────────────────
print("\n[3/3] Analytics results")

print("\n--- Maximum Drawdown ---")
print(max_drawdown(con).to_string(index=False))

print("\n--- Sharpe Ratio & Value at Risk (95% / 99%) ---")
print(sharpe_and_var(con).to_string(index=False))

print("\n--- Sector Allocation vs Target ---")
print(sector_allocation(con).to_string(index=False))

print("\n--- Portfolio P&L Summary ---")
print(portfolio_summary(con).to_string(index=False))

con.close()
print("\n" + "=" * 60)
print("  Complete. DuckDB file: data/portfolio.duckdb")
print("  Open notebooks/exploration.ipynb for charts.")
print("=" * 60)