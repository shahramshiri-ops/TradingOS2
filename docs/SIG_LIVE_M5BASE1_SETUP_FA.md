# SIG-LIVE-M5BASE1 — M5 Canonical Intake + Internal Resampling Engine

Created: 2026-05-09T07:43:27Z

## Final status

ACCEPTED_WITH_CAVEATS_M5_CANONICAL_SEED_AND_INTERNAL_RESAMPLER_BUILT

## What this pack does

```text
manual M5 seed, one time
        ↓
canonical M5 store
        ↓
Twelve Data M5 incremental fetch, overlap
        ↓
M5 merge / dedupe
        ↓
internal resampling
        ↓
M15 / H1 / H4 / D1
        ↓
inputs/sig_brain5_raw_bars_latest.json
        ↓
Brain5 / Brain4 / mobile brain panel
```

## Uploaded seed files consumed

```text
EURUSD5.csv
USDJPY5.csv
XAUUSD5 (1).csv
```

## Seed audit summary

```text
instrument     source_file  rows_raw  rows_canonical                 start_utc                   end_utc  duplicate_rows  non_5min_timestamp_rows  gap_count_gt_5min         max_gap  weekend_utc_rows  null_bar_open_ts  null_open  null_high  null_low  null_close                    assumed_timezone                                  canonical_output
    EURUSD     EURUSD5.csv      6354            6354 2026-04-08T19:15:00+00:00 2026-05-08T20:55:00+00:00               0                        0                  5 2 days 00:05:00               144                 0          0          0         0           0 UTC_from_source_timestamp_no_offset data/live_m5/canonical/EURUSD_M5_canonical.csv.gz
    USDJPY     USDJPY5.csv      6463            6463 2026-04-08T10:10:00+00:00 2026-05-08T20:55:00+00:00               0                        0                  5 2 days 00:05:00               144                 0          0          0         0           0 UTC_from_source_timestamp_no_offset data/live_m5/canonical/USDJPY_M5_canonical.csv.gz
    XAUUSD XAUUSD5 (1).csv      6315            6315 2026-04-08T00:45:00+00:00 2026-05-08T20:55:00+00:00               0                        0                 22 2 days 01:05:00                96                 0          0          0         0           0 UTC_from_source_timestamp_no_offset data/live_m5/canonical/XAUUSD_M5_canonical.csv.gz
```

## Resampled summary

```text
instrument timeframe  rows  complete_rows  incomplete_rows                 start_utc                   end_utc last_complete_bar_open_utc  expected_m5_count                                   output_file
    EURUSD       M15  2118           2118                0 2026-04-08T19:15:00+00:00 2026-05-08T20:45:00+00:00  2026-05-08T20:45:00+00:00                  3 data/live_resampled/EURUSD_M15_from_M5.csv.gz
    EURUSD        H1   530            528                2 2026-04-08T19:00:00+00:00 2026-05-08T20:00:00+00:00  2026-05-08T20:00:00+00:00                 12  data/live_resampled/EURUSD_H1_from_M5.csv.gz
    EURUSD        H4   138            127               11 2026-04-08T16:00:00+00:00 2026-05-08T20:00:00+00:00  2026-05-08T16:00:00+00:00                 48  data/live_resampled/EURUSD_H4_from_M5.csv.gz
    EURUSD        D1    27             16               11 2026-04-08T00:00:00+00:00 2026-05-08T00:00:00+00:00  2026-05-07T00:00:00+00:00                288  data/live_resampled/EURUSD_D1_from_M5.csv.gz
    USDJPY       M15  2155           2154                1 2026-04-08T10:00:00+00:00 2026-05-08T20:45:00+00:00  2026-05-08T20:45:00+00:00                  3 data/live_resampled/USDJPY_M15_from_M5.csv.gz
    USDJPY        H1   539            537                2 2026-04-08T10:00:00+00:00 2026-05-08T20:00:00+00:00  2026-05-08T20:00:00+00:00                 12  data/live_resampled/USDJPY_H1_from_M5.csv.gz
    USDJPY        H4   140            129               11 2026-04-08T08:00:00+00:00 2026-05-08T20:00:00+00:00  2026-05-08T16:00:00+00:00                 48  data/live_resampled/USDJPY_H4_from_M5.csv.gz
    USDJPY        D1    27             16               11 2026-04-08T00:00:00+00:00 2026-05-08T00:00:00+00:00  2026-05-07T00:00:00+00:00                288  data/live_resampled/USDJPY_D1_from_M5.csv.gz
    XAUUSD       M15  2105           2105                0 2026-04-08T00:45:00+00:00 2026-05-08T20:45:00+00:00  2026-05-08T20:45:00+00:00                  3 data/live_resampled/XAUUSD_M15_from_M5.csv.gz
    XAUUSD        H1   527            526                1 2026-04-08T00:00:00+00:00 2026-05-08T20:00:00+00:00  2026-05-08T20:00:00+00:00                 12  data/live_resampled/XAUUSD_H1_from_M5.csv.gz
    XAUUSD        H4   142            114               28 2026-04-08T00:00:00+00:00 2026-05-08T20:00:00+00:00  2026-05-08T16:00:00+00:00                 48  data/live_resampled/XAUUSD_H4_from_M5.csv.gz
    XAUUSD        D1    27             17               10 2026-04-08T00:00:00+00:00 2026-05-08T00:00:00+00:00  2026-05-07T00:00:00+00:00                276  data/live_resampled/XAUUSD_D1_from_M5.csv.gz
```

## Important timezone caveat

The seed files did not include an explicit timezone offset. They are imported as UTC-compatible timestamps.

```text
assumed_timezone = UTC_from_source_timestamp_no_offset
```

If the source export was not GMT/UTC, stop and tell me before using this live.

## Local install

Copy `github_overlay_product_root/*` into your repo root:

```powershell
C:\Users\shahr\OneDrive\Documents\TradingOS\GitHub\TradingOS2\TradingOS2
```

## Local test

```powershell
py scripts\validate_sig_live_m5base1_outputs.py
py scripts\resample_m5_to_higher_timeframes.py
py scripts\build_brain5_raw_bars_from_resampled.py
py scripts\run_live_m5_refresh_pipeline.py
```

For real API live refresh after setting the API key:

```powershell
$env:LFB_TWELVE_DATA_API_KEY = "<your-api-key>"
py scripts\run_live_m5_refresh_pipeline.py --fetch-live
```

## GitHub secret

Add one of these in GitHub repo secrets:

```text
LFB_TWELVE_DATA_API_KEY
TWELVE_DATA_API_KEY
```

## Workflow

```text
.github/workflows/sig_live_m5_refresh_resample_brain.yml
```

Default schedule:

```text
every 10 minutes Monday-Friday UTC
```

Estimated API use for 3 symbols:

```text
3 credits/run × 144 runs/day ≈ 432 credits/day
```

## Boundary

Read-only OHLC only. Not signal. No buy/sell/hold. No entry/stop/target. No broker/execution. No profitability/tradability.
