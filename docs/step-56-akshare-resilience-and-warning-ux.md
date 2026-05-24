# Step 56 - AKShare Resilience and Warning UX

## Goal
Reduce user-perceived failures when AKShare is temporarily unstable, and make fallback behavior understandable on the UI.

## What Changed
1. Backend retry strategy upgraded in `src/data_service.py`.
2. Frontend warning text optimized in `app.py` for fallback scenarios.

## Backend Details
- Updated:
  - `_fetch_akshare_metrics_with_retry`
  - `_fetch_akshare_daily_prices_with_retry`
- New behavior:
  - Retry up to 3 times for transient errors.
  - Exponential backoff delays: `0.8s`, `1.6s`, `3.2s`.
  - Keep existing proxy-fallback logic (`temporary_disable_proxy`) during retries.
  - Add transient error detector `_is_transient_akshare_error(...)`:
    - timeout / timed out
    - 502 / 503 / 504
    - connection reset / aborted
    - max retries exceeded
    - rate limit / too many requests

## Frontend Details
- Updated warning display in `_render_analysis`:
  - raw warning -> `_friendly_data_warning(raw)`
- User-facing improvements:
  - If AKShare live data fails, clearly state fallback is active and page can continue.
  - If K-line fetch fails, state chart is skipped but text analysis remains available.

## Scope Control
- No changes to core agent routing.
- No changes to financial logic output structure.
- No UI layout refactor.

## Validation
- `python -m py_compile app.py src/data_service.py` passed.
- Local AKShare probes passed:
  - `stock_info_a_code_name()`
  - `stock_financial_abstract('600519')`
  - K-line fallback chain (`hist_tx`, `daily`, `hist`)
- Snapshot smoke test:
  - input `600519` -> recognized, with daily prices available.

## Known Note
- In current local environment, direct Chinese-name identification has encoding instability in some paths; stock code path remains reliable.

## Test Checklist
1. Start app and query `600519`.
2. Confirm normal analysis output.
3. (Optional) Temporarily simulate network instability and verify:
   - app still returns fallback-based output;
   - warning copy explains fallback clearly.
