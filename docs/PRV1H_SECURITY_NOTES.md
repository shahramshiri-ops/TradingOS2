# PRV1H Security Notes

- Store `LFB_TWELVE_DATA_API_KEY` only as a GitHub Actions repository secret.
- Do not commit `.env`, API keys, tokens, or credential files.
- The public/mobile site should contain display-only outputs only.
- The workflow redacts the provider key and relies on the existing PRV1 secret-redaction proofs.
- The mobile panel is not an action surface. It must not contain broker status, execution queue, action buttons, buy/sell/hold, entry/stop/target, PnL, optimizer, validation verdict, or production-readiness claims.
- Prefer a private repository for the full runtime package. If you later want a public panel, publish only the generated static `site/` artifact, not the full working repository.
