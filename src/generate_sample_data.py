"""
generate_sample_data.py
-----------------------
Generates realistic synthetic financial data:
- prices.csv / prices.parquet   (daily OHLCV, 2022-2024)
- holdings.csv / holdings.parquet
- trades.csv / trades.parquet
Uses real-world-like price paths via geometric Brownian motion.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date

np.random.seed(42)

# ── Realistic starting prices & annual drift/vol (approximate 2022 values) ─
TICKER_PARAMS = {
    "AAPL": {"start": 182.0, "mu": 0.18,  "sigma": 0.28, "sector": "Technology"},
    "MSFT": {"start": 310.0, "mu": 0.22,  "sigma": 0.26, "sector": "Technology"},
    "JPM":  {"start": 135.0, "mu": 0.10,  "sigma": 0.22, "sector": "Financials"},
    "GS":   {"start": 350.0, "mu": 0.08,  "sigma": 0.24, "sector": "Financials"},
    "BLK":  {"start": 690.0, "mu": 0.09,  "sigma": 0.23, "sector": "Financials"},
    "BAC":  {"start": 38.0,  "mu": 0.07,  "sigma": 0.25, "sector": "Financials"},
    "SCHW": {"start": 75.0,  "mu": 0.06,  "sigma": 0.27, "sector": "Financials"},
    "WFC":  {"start": 46.0,  "mu": 0.09,  "sigma": 0.26, "sector": "Financials"},
}

HOLDINGS = {
    "AAPL": {"shares": 150, "cost_basis": 145.00},
    "MSFT": {"shares": 120, "cost_basis": 310.00},
    "JPM":  {"shares": 200, "cost_basis": 130.00},
    "GS":   {"shares": 80,  "cost_basis": 340.00},
    "BLK":  {"shares": 60,  "cost_basis": 680.00},
    "BAC":  {"shares": 300, "cost_basis": 36.00},
    "SCHW": {"shares": 250, "cost_basis": 72.00},
    "WFC":  {"shares": 220, "cost_basis": 44.00},
}


def simulate_prices(trading_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Simulate daily close prices using Geometric Brownian Motion."""
    T   = len(trading_dates)
    dt  = 1 / 252
    rows = []

    for ticker, p in TICKER_PARAMS.items():
        S    = p["start"]
        mu   = p["mu"]
        sig  = p["sigma"]
        prices_arr = [S]

        for _ in range(T - 1):
            Z    = np.random.standard_normal()
            S    = S * np.exp((mu - 0.5 * sig**2) * dt + sig * np.sqrt(dt) * Z)
            prices_arr.append(round(S, 4))

        # Add realistic volume (log-normal)
        base_vol = 25_000_000 if ticker in ("AAPL", "MSFT") else 8_000_000
        volumes  = (np.random.lognormal(mean=np.log(base_vol), sigma=0.4, size=T)
                    .astype(int))

        for i, d in enumerate(trading_dates):
            rows.append({
                "price_date":  d.date(),
                "ticker":      ticker,
                "sector":      p["sector"],
                "close_price": prices_arr[i],
                "volume":      int(volumes[i]),
            })

    return pd.DataFrame(rows).sort_values(["ticker", "price_date"]).reset_index(drop=True)


def build_holdings(as_of_date: date) -> pd.DataFrame:
    rows = []
    for ticker, h in HOLDINGS.items():
        rows.append({
            "portfolio_id":   "WAM-001",
            "portfolio_name": "Global Equity Growth Fund",
            "ticker":         ticker,
            "sector":         TICKER_PARAMS[ticker]["sector"],
            "shares":         h["shares"],
            "cost_basis":     h["cost_basis"],
            "currency":       "USD",
            "as_of_date":     as_of_date,
        })
    return pd.DataFrame(rows)


def build_trades(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Generate synthetic trade history — buy/sell every 5 business days."""
    trading_dates = prices_df["price_date"].unique()
    sample_dates  = trading_dates[::5]
    records       = []
    trade_counter = 1

    for trade_date in sample_dates:
        for ticker in TICKER_PARAMS:
            row = prices_df[(prices_df["ticker"] == ticker) &
                            (prices_df["price_date"] == trade_date)]
            if row.empty:
                continue
            price = float(row["close_price"].values[0])
            qty   = int(np.random.choice([-100, -50, 50, 100, 200]))
            records.append({
                "trade_id":     f"TRD-{str(trade_counter).zfill(6)}",
                "trade_date":   trade_date,
                "portfolio_id": "WAM-001",
                "ticker":       ticker,
                "sector":       TICKER_PARAMS[ticker]["sector"],
                "quantity":     qty,
                "price":        round(price, 4),
                "currency":     "USD",
                "gross_value":  round(abs(qty) * price, 2),
                "trade_type":   "BUY" if qty > 0 else "SELL",
            })
            trade_counter += 1

    return pd.DataFrame(records).sort_values("trade_date").reset_index(drop=True)


if __name__ == "__main__":
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    trading_dates = pd.bdate_range("2022-01-03", "2024-12-31")

    print("Generating prices...")
    prices = simulate_prices(trading_dates)
    prices.to_csv("data/raw/prices.csv", index=False)
    prices.to_parquet("data/processed/prices.parquet", index=False)
    print(f"  {len(prices):,} rows → data/raw/prices.csv + data/processed/prices.parquet")

    print("Generating holdings...")
    holdings = build_holdings(date(2024, 12, 31))
    holdings.to_csv("data/raw/holdings.csv", index=False)
    holdings.to_parquet("data/processed/holdings.parquet", index=False)
    print(f"  {len(holdings)} rows → data/raw/holdings.csv + data/processed/holdings.parquet")

    print("Generating trades...")
    trades = build_trades(prices)
    trades.to_csv("data/raw/trades.csv", index=False)
    trades.to_parquet("data/processed/trades.parquet", index=False)
    print(f"  {len(trades):,} rows → data/raw/trades.csv + data/processed/trades.parquet")

    print("\nSample data generation complete.")