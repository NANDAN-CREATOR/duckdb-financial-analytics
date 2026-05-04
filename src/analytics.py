"""
analytics.py
------------
High-level analytics functions — all powered by DuckDB.
Reads from tables built by transform.py.
"""

import duckdb
import pandas as pd


def get_connection(db_path: str = "data/portfolio.duckdb") -> duckdb.DuckDBPyConnection:
    return duckdb.connect(db_path)


def max_drawdown(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute("""
        WITH running_peak AS (
            SELECT ticker, sector, price_date, close_price,
                   MAX(close_price) OVER (
                       PARTITION BY ticker ORDER BY price_date
                       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                   ) AS peak_price
            FROM read_parquet('data/processed/prices.parquet')
        )
        SELECT
            ticker, sector,
            ROUND(MIN((close_price - peak_price) / peak_price * 100), 2) AS max_drawdown_pct,
            ARGMIN(price_date, (close_price - peak_price) / peak_price)  AS max_drawdown_date
        FROM running_peak
        GROUP BY ticker, sector
        ORDER BY max_drawdown_pct ASC
    """).df()


def sharpe_and_var(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute("""
        SELECT
            ticker, sector,
            ROUND(AVG(daily_return_pct / 100) * 252 * 100, 2)          AS ann_return_pct,
            ROUND(STDDEV(daily_return_pct / 100) * SQRT(252) * 100, 2) AS ann_vol_pct,
            ROUND(
                (AVG(daily_return_pct / 100) - (0.05 / 252))
                / NULLIF(STDDEV(daily_return_pct / 100), 0)
                * SQRT(252)
            , 3)                                                        AS sharpe_ratio,
            ROUND(AVG(daily_return_pct) - 1.645 * STDDEV(daily_return_pct), 4)
                                                                        AS var_95_pct,
            ROUND(AVG(daily_return_pct) - 2.326 * STDDEV(daily_return_pct), 4)
                                                                        AS var_99_pct
        FROM daily_returns
        WHERE daily_return_pct IS NOT NULL
        GROUP BY ticker, sector
        ORDER BY sharpe_ratio DESC
    """).df()


def sector_allocation(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute("""
        WITH latest AS (
            SELECT ticker, close_price
            FROM read_parquet('data/processed/prices.parquet')
            WHERE price_date = (SELECT MAX(price_date)
                                FROM read_parquet('data/processed/prices.parquet'))
        ),
        sv AS (
            SELECT h.sector,
                   SUM(h.shares * lp.close_price) AS sector_value,
                   COUNT(*) AS positions
            FROM read_parquet('data/processed/holdings.parquet') h
            JOIN latest lp ON h.ticker = lp.ticker
            GROUP BY h.sector
        ),
        total AS (SELECT SUM(sector_value) AS nav FROM sv)
        SELECT
            sv.sector, sv.positions,
            ROUND(sv.sector_value, 2)                        AS sector_value,
            ROUND(sv.sector_value / t.nav * 100, 2)          AS actual_pct,
            CASE sv.sector
                WHEN 'Technology' THEN 40.0
                WHEN 'Financials' THEN 60.0 ELSE 0.0
            END                                              AS target_pct,
            ROUND(sv.sector_value / t.nav * 100
                  - CASE sv.sector WHEN 'Technology' THEN 40.0
                                   WHEN 'Financials' THEN 60.0
                                   ELSE 0.0 END, 2)          AS drift_pct
        FROM sv, total t
        ORDER BY actual_pct DESC
    """).df()


def portfolio_summary(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute("""
        WITH latest AS (
            SELECT ticker, close_price AS current_price
            FROM read_parquet('data/processed/prices.parquet')
            WHERE price_date = (SELECT MAX(price_date)
                                FROM read_parquet('data/processed/prices.parquet'))
        ),
        valued AS (
            SELECT h.ticker, h.sector, h.shares, h.cost_basis,
                   lp.current_price,
                   ROUND(h.shares * lp.current_price, 2) AS market_value,
                   ROUND(h.shares * (lp.current_price - h.cost_basis), 2) AS unrealised_pnl,
                   ROUND((lp.current_price - h.cost_basis) / h.cost_basis * 100, 2)
                                                          AS return_pct
            FROM read_parquet('data/processed/holdings.parquet') h
            JOIN latest lp ON h.ticker = lp.ticker
        ),
        totals AS (SELECT SUM(market_value) AS nav FROM valued)
        SELECT v.*, ROUND(v.market_value / t.nav * 100, 2) AS weight_pct
        FROM valued v, totals t
        ORDER BY unrealised_pnl DESC
    """).df()


if __name__ == "__main__":
    con = get_connection()

    print("\n=== MAX DRAWDOWN ===")
    print(max_drawdown(con).to_string(index=False))

    print("\n=== SHARPE & VaR ===")
    print(sharpe_and_var(con).to_string(index=False))

    print("\n=== SECTOR ALLOCATION ===")
    print(sector_allocation(con).to_string(index=False))

    print("\n=== PORTFOLIO SUMMARY ===")
    print(portfolio_summary(con).to_string(index=False))

    con.close()