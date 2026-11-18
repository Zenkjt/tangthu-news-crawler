# Checkpoint — Post-merge cleanup

Date: 2026-11-18

## Changes
- Update README from obsolete Phase 0 skeleton description.
- Run VnExpress live smoke workflow from `main`, with path filters and manual dispatch.
- Ignore Python bytecode, test caches, virtual environments, build output and runtime crawler data.
- Remove tracked Python bytecode.
- Normalize `www.` aliases only for local source-host matching; preserve registered URLs.

## Validation
- Maintainer's previous Hà Nội live smoke test: 4 discovered, 4 extracted, 0 failed.
- After applying this cleanup, confirm the pytest and live smoke GitHub Actions runs.
