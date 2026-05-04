-- ============================================================
-- allocation.sql
-- Portfolio allocation, P&L, drift analysis, and trade summary.
-- Run AFTER daily_returns and rolling_volatility tables exist.
-- ============================================================

-- ── 1. Current Portfolio Valuation & Unrealised P&L ──────────
CREATE OR REPLACE TABLE portfolio_valuation AS
WITH latest_prices AS (
    SELECT ticker, close_price AS current_price
    FROM read_parquet('data/processed/prices.parquet')
    WHERE price_date = (
        SELECT MAX(price_date)
        FROM read_parquet('data/processed/prices.parquet')
    )
),
valued AS (
    SELECT
        h.portfolio_id,
        h.portfolio_name,
        h.ticker,
        h.sector,
        h.shares,
        h.cost_basis,
        h.currency,
        lp.current_price,
        ROUND(h.shares * h.cost_basis,    2)                AS book_value,
        ROUND(h.shares * lp.current_price, 2)               AS market_value,
        ROUND(h.shares * (lp.current_price - h.cost_basis), 2)
                                                            AS unrealised_pnl,
        ROUND(
            (lp.current_price - h.cost_basis) / h.cost_basis * 100
        , 4)                                                AS unrealised_return_pct
    FROM read_parquet('data/processed/holdings.parquet') h
    JOIN latest_prices lp ON h.ticker = lp.ticker
),
totals AS (
    SELECT SUM(market_value) AS portfolio_nav FROM valued
)
SELECT
    v.*,
    ROUND(v.market_value / t.portfolio_nav * 100, 4)        AS weight_pct,
    t.portfolio_nav                                          AS total_portfolio_nav
FROM valued v, totals t
ORDER BY weight_pct DESC;


-- ── 2. Sector Allocation ──────────────────────────────────────
CREATE OR REPLACE TABLE sector_allocation AS
WITH latest_prices AS (
    SELECT ticker, close_price
    FROM read_parquet('data/processed/prices.parquet')
    WHERE price_date = (
        SELECT MAX(price_date)
        FROM read_parquet('data/processed/prices.parquet')
    )
),
sector_values AS (
    SELECT
        h.sector,
        SUM(h.shares * lp.close_price)                      AS sector_market_value,
        COUNT(*)                                             AS position_count
    FROM read_parquet('data/processed/holdings.parquet') h
    JOIN latest_prices lp ON h.ticker = lp.ticker
    GROUP BY h.sector
),
total AS (
    SELECT SUM(sector_market_value) AS portfolio_total FROM sector_values
)
SELECT
    sv.sector,
    sv.position_count,
    ROUND(sv.sector_market_value, 2)                         AS sector_market_value,
    ROUND(sv.sector_market_value / t.portfolio_total * 100, 4)
                                                            AS actual_allocation_pct,

    -- Target allocations (hardcoded for this fund mandate)
    CASE sv.sector
        WHEN 'Technology'  THEN 40.0
        WHEN 'Financials'  THEN 60.0
        ELSE 0.0
    END                                                     AS target_allocation_pct,

    -- Drift from target
    ROUND(
        sv.sector_market_value / t.portfolio_total * 100
        - CASE sv.sector
            WHEN 'Technology' THEN 40.0
            WHEN 'Financials' THEN 60.0
            ELSE 0.0
          END
    , 4)                                                    AS drift_pct,

    CASE
        WHEN sv.sector_market_value / t.portfolio_total * 100
             > (CASE sv.sector WHEN 'Technology' THEN 40.0
                               WHEN 'Financials' THEN 60.0
                               ELSE 0.0 END) + 2
        THEN 'OVERWEIGHT'
        WHEN sv.sector_market_value / t.portfolio_total * 100
             < (CASE sv.sector WHEN 'Technology' THEN 40.0
                               WHEN 'Financials' THEN 60.0
                               ELSE 0.0 END) - 2
        THEN 'UNDERWEIGHT'
        ELSE 'IN RANGE'
    END                                                     AS drift_status

FROM sector_values sv, total t
ORDER BY actual_allocation_pct DESC;


-- ── 3. Trade Activity Summary ─────────────────────────────────
CREATE OR REPLACE TABLE trade_summary AS
SELECT
    DATE_TRUNC('month', trade_date)                         AS trade_month,
    ticker,
    sector,
    trade_type,
    COUNT(*)                                                AS trade_count,
    SUM(ABS(quantity))                                      AS total_quantity,
    ROUND(AVG(price), 4)                                    AS avg_execution_price,
    ROUND(SUM(gross_value), 2)                              AS total_gross_value,
    ROUND(MIN(price), 4)                                    AS min_price,
    ROUND(MAX(price), 4)                                    AS max_price

FROM read_parquet('data/processed/trades.parquet')
GROUP BY DATE_TRUNC('month', trade_date), ticker, sector, trade_type
ORDER BY trade_month, ticker, trade_type;


-- ── 4. Portfolio Performance — Weighted Return ────────────────
SELECT
    pv.portfolio_id,
    pv.portfolio_name,
    ROUND(SUM(pv.weight_pct / 100 * dr.avg_daily_return_pct * 252), 4)
                                                            AS weighted_ann_return_pct,
    ROUND(SUM(pv.weight_pct / 100 * rv.avg_vol), 4)        AS weighted_ann_vol_pct,
    ROUND(SUM(pv.unrealised_pnl), 2)                        AS total_unrealised_pnl,
    ROUND(SUM(pv.market_value), 2)                          AS total_nav
FROM portfolio_valuation pv
JOIN (
    SELECT ticker, AVG(daily_return_pct) AS avg_daily_return_pct
    FROM daily_returns WHERE daily_return_pct IS NOT NULL
    GROUP BY ticker
) dr ON pv.ticker = dr.ticker
JOIN (
    SELECT ticker, AVG(vol_30d_ann_pct) AS avg_vol
    FROM rolling_volatility WHERE vol_30d_ann_pct IS NOT NULL
    GROUP BY ticker
) rv ON pv.ticker = rv.ticker
GROUP BY pv.portfolio_id, pv.portfolio_name;
