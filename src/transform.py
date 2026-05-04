"""
transform.py
------------
Runs all SQL transformations using DuckDB.
Reads Parquet files from data/processed/ and builds
analytical tables: daily_returns, cumulative_returns,
rolling_volatility, monthly_returns.
"""

import duckdb


def get_connection(db_path: str = "data/portfolio.duckdb") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(db_path)
    con.execute("SET memory_limit='4GB'")
    con.execute(f"SET threads={4}")
    return con


def register_views(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE OR REPLACE VIEW vw_prices AS
        SELECT * FROM read_parquet('data/processed/prices.parquet')
    """)
    con.execute("""
        CREATE OR REPLACE VIEW vw_holdings AS
        SELECT * FROM read_parquet('data/processed/holdings.parquet')
    """)
    con.execute("""
        CREATE OR REPLACE VIEW vw_trades AS
        SELECT * FROM read_parquet('data/processed/trades.parquet')
    """)
    print("  Views registered: vw_prices, vw_holdings, vw_trades")


def build_daily_returns(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("""
        CREATE OR REPLACE TABLE daily_returns AS
        SELECT
            price_date, ticker, sector, close_price,
            LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date) AS prev_close,
            ROUND(
                (close_price - LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date))
                / LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date) * 100
            , 4) AS daily_return_pct
        FROM vw_prices
        ORDER BY ticker, price_date
    """)
    return con.execute("SELECT COUNT(*) FROM daily_returns WHERE daily_return_pct IS NOT NULL").fetchone()[0]


def build_cumulative_returns(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("""
        CREATE OR REPLACE TABLE cumulative_returns AS
        SELECT
            price_date, ticker, sector, close_price, daily_return_pct,
            ROUND(
                (EXP(SUM(LN(1 + daily_return_pct / 100))
                    OVER (PARTITION BY ticker ORDER BY price_date)) - 1) * 100
            , 4) AS cumulative_return_pct
        FROM daily_returns
        WHERE daily_return_pct IS NOT NULL
        ORDER BY ticker, price_date
    """)
    return con.execute("SELECT COUNT(*) FROM cumulative_returns").fetchone()[0]


def build_rolling_volatility(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("""
        CREATE OR REPLACE TABLE rolling_volatility AS
        SELECT
            price_date, ticker, sector,
            ROUND(
                STDDEV(daily_return_pct / 100)
                    OVER (PARTITION BY ticker ORDER BY price_date
                          ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
                * SQRT(252) * 100
            , 4) AS vol_30d_ann_pct,
            ROUND(
                STDDEV(daily_return_pct / 100)
                    OVER (PARTITION BY ticker ORDER BY price_date
                          ROWS BETWEEN 89 PRECEDING AND CURRENT ROW)
                * SQRT(252) * 100
            , 4) AS vol_90d_ann_pct,
            ROUND(
                STDDEV(daily_return_pct / 100)
                    OVER (PARTITION BY ticker ORDER BY price_date
                          ROWS BETWEEN 251 PRECEDING AND CURRENT ROW)
                * SQRT(252) * 100
            , 4) AS vol_252d_ann_pct
        FROM daily_returns
        WHERE daily_return_pct IS NOT NULL
        ORDER BY ticker, price_date
    """)
    return con.execute("SELECT COUNT(*) FROM rolling_volatility").fetchone()[0]


def build_monthly_returns(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("""
        CREATE OR REPLACE TABLE monthly_returns AS
        SELECT
            DATE_TRUNC('month', price_date) AS month,
            ticker, sector,
            FIRST(close_price ORDER BY price_date) AS month_open,
            LAST(close_price  ORDER BY price_date) AS month_close,
            ROUND(
                (LAST(close_price ORDER BY price_date)
                 - FIRST(close_price ORDER BY price_date))
                / FIRST(close_price ORDER BY price_date) * 100
            , 4) AS monthly_return_pct,
            COUNT(*) AS trading_days
        FROM vw_prices
        GROUP BY DATE_TRUNC('month', price_date), ticker, sector
        ORDER BY ticker, month
    """)
    return con.execute("SELECT COUNT(*) FROM monthly_returns").fetchone()[0]


if __name__ == "__main__":
    print("Running transformations...")
    con = get_connection()
    register_views(con)

    n = build_daily_returns(con)
    print(f"  daily_returns:       {n:,} rows")

    n = build_cumulative_returns(con)
    print(f"  cumulative_returns:  {n:,} rows")

    n = build_rolling_volatility(con)
    print(f"  rolling_volatility:  {n:,} rows")

    n = build_monthly_returns(con)
    print(f"  monthly_returns:     {n:,} rows")

    con.close()
    print("Transformations complete → data/portfolio.duckdb")