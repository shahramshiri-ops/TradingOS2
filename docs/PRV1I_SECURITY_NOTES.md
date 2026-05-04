# PRV1I Security Notes

Public: GitHub Pages panel and Worker URL.

Secret: GitHub dispatch token, refresh PIN, Twelve Data API key, `.env`.

The Worker only triggers GitHub Actions workflow_dispatch and optionally reads latest run status. It does not run provider fetch, broker, order, execution, signals, PnL, validation verdict, or production-readiness logic.
