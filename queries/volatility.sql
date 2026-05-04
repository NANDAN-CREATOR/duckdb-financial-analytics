-- ============================================================
-- volatility.sql
-- Rolling volatility, annualised vol, max drawdown,
-- Sharpe approximation, and Value-at-Risk (VaR) estimates.
-- ============================================================

-- ── 1. Rolling 30-Day Annualised Volatility ───────────────────
CREATE OR REPLACE TABLE rolling_volatility AS
SELECT
    price_date,
    ticker,
    sector,
    close_price,

    -- 30-day rolling annualised volatility (SQRT(252) annualisation)
    ROUND(
        STDDEV(daily_return_pct / 100)
            OVER (
                PARTITION BY ticker
                ORDER BY price_date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) * SQRT(252) * 100
    , 4)                                                    AS vol_30d_ann_pct,

    -- 90-day rolling annualised volatility
    ROUND(
        STDDEV(daily_return_pct / 100)
            OVER (
                PARTITION BY ticker
                ORDER BY price_date
                ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
            ) * SQRT(252) * 100
    , 4)                                                    AS vol_90d_ann_pct,

    -- 252-day (1-year) rolling annualised volatility
    ROUND(
        STDDEV(daily_return_pct / 100)
            OVER (
                PARTITION BY ticker
                ORDER BY price_date
                ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
            ) * SQRT(252) * 100
    , 4)                                                    AS vol_252d_ann_pct

FROM daily_returns
WHERE daily_return_pct IS NOT NULL
ORDER BY ticker, price_date;


-- ── 2. Maximum Drawdown per Ticker ───────────────────────────
CREATE OR REPLACE TABLE max_drawdown AS
WITH running_peak AS (
    SELECT
        ticker,
        sector,
        price_date,
        close_price,
        MAX(close_price) OVER (
            PARTITION BY ticker
            ORDER BY price_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                                   AS peak_price
    FROM read_parquet('data/processed/prices.parquet')
),
drawdown AS (
    SELECT
        ticker,
        sector,
        price_date,
        close_price,
        peak_price,
        ROUND((close_price - peak_price) / peak_price * 100, 4) AS drawdown_pct
    FROM running_peak
)
SELECT
    ticker,
    sector,
    MIN(drawdown_pct)                                       AS max_drawdown_pct,
    ARGMIN(price_date, drawdown_pct)                        AS max_drawdown_date,
    ARGMIN(close_price, drawdown_pct)                       AS price_at_drawdown
FROM drawdown
GROUP BY ticker, sector
ORDER BY max_drawdown_pct ASC;


-- ── 3. Sharpe Ratio Approximation (annualised) ───────────────
--    Sharpe = (mean daily return - risk free rate) / daily vol * sqrt(252)
--    Using 5% annual risk-free rate → 5/252 per day
SELECT
    ticker,
    sector,
    COUNT(*)                                                AS trading_days,
    ROUND(AVG(daily_return_pct / 100) * 252 * 100, 4)      AS ann_return_pct,
    ROUND(STDDEV(daily_return_pct / 100) * SQRT(252) * 100, 4) AS ann_vol_pct,
    ROUND(
        (AVG(daily_return_pct / 100) - (0.05 / 252))
        / NULLIF(STDDEV(daily_return_pct / 100), 0)
        * SQRT(252)
    , 4)                                                    AS sharpe_ratio

FROM daily_returns
WHERE daily_return_pct IS NOT NULL
GROUP BY ticker, sector
ORDER BY sharpe_ratio DESC;


-- ── 4. Parametric Value-at-Risk (95% and 99% confidence) ─────
--    VaR = mean - Z * stddev (parametric normal approximation)
--    Z(95%) = 1.645, Z(99%) = 2.326
SELECT
    ticker,
    sector,
    ROUND(AVG(daily_return_pct),    4)                      AS mean_daily_return_pct,
    ROUND(STDDEV(daily_return_pct), 4)                      AS stddev_daily_return_pct,

    -- 95% 1-day VaR
    ROUND(AVG(daily_return_pct) - 1.645 * STDDEV(daily_return_pct), 4)
                                                            AS var_95_1day_pct,

    -- 99% 1-day VaR
    ROUND(AVG(daily_return_pct) - 2.326 * STDDEV(daily_return_pct), 4)
                                                            AS var_99_1day_pct,

    -- 95% 10-day VaR (scale by sqrt(10))
    ROUND(
        (AVG(daily_return_pct) - 1.645 * STDDEV(daily_return_pct))
        * SQRT(10)
    , 4)                                                    AS var_95_10day_pct

FROM daily_returns
WHERE daily_return_pct IS NOT NULL
GROUP BY ticker, sector
ORDER BY var_99_1day_pct ASC;
