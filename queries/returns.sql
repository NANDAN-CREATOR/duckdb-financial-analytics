-- ============================================================
-- returns.sql
-- Daily returns, cumulative returns, and rolling performance
-- per ticker across the full price history.
-- ============================================================

-- ── 1. Daily Returns ─────────────────────────────────────────
CREATE OR REPLACE TABLE daily_returns AS
SELECT
    price_date,
    ticker,
    sector,
    close_price,
    LAG(close_price) OVER (
        PARTITION BY ticker
        ORDER BY price_date
    )                                                       AS prev_close,

    ROUND(
        (close_price
            - LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date))
        / LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date)
        * 100
    , 4)                                                    AS daily_return_pct

FROM read_parquet('data/processed/prices.parquet')
ORDER BY ticker, price_date;


-- ── 2. Cumulative Returns (compound) ─────────────────────────
CREATE OR REPLACE TABLE cumulative_returns AS
SELECT
    price_date,
    ticker,
    sector,
    close_price,
    daily_return_pct,

    ROUND(
        (EXP(
            SUM(LN(1 + daily_return_pct / 100))
            OVER (PARTITION BY ticker ORDER BY price_date)
        ) - 1) * 100
    , 4)                                                    AS cumulative_return_pct

FROM daily_returns
WHERE daily_return_pct IS NOT NULL
ORDER BY ticker, price_date;


-- ── 3. Monthly Return Summary ─────────────────────────────────
CREATE OR REPLACE TABLE monthly_returns AS
SELECT
    DATE_TRUNC('month', price_date)                         AS month,
    ticker,
    sector,
    FIRST(close_price ORDER BY price_date)                  AS month_open,
    LAST(close_price  ORDER BY price_date)                  AS month_close,
    ROUND(
        (LAST(close_price ORDER BY price_date)
            - FIRST(close_price ORDER BY price_date))
        / FIRST(close_price ORDER BY price_date) * 100
    , 4)                                                    AS monthly_return_pct,
    COUNT(*)                                                AS trading_days

FROM read_parquet('data/processed/prices.parquet')
GROUP BY DATE_TRUNC('month', price_date), ticker, sector
ORDER BY ticker, month;


-- ── 4. Best / Worst Single-Day Returns per Ticker ────────────
SELECT
    ticker,
    sector,

    -- Best day
    MAX(daily_return_pct)                                   AS best_day_pct,
    ARGMAX(price_date, daily_return_pct)                    AS best_day_date,

    -- Worst day
    MIN(daily_return_pct)                                   AS worst_day_pct,
    ARGMIN(price_date, daily_return_pct)                    AS worst_day_date,

    -- Average
    ROUND(AVG(daily_return_pct), 4)                         AS avg_daily_return_pct,
    COUNT(*)                                                AS trading_days

FROM daily_returns
WHERE daily_return_pct IS NOT NULL
GROUP BY ticker, sector
ORDER BY avg_daily_return_pct DESC;
