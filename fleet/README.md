# fleet/

Fleet-wide helper scripts that get deployed onto other boxes.

## Moved out

- **`srvhome/`** — the per-box status page served at `/` on `AMI`.
  Canonical source is now the **`BdRPiSrvAMI` repo, `srvhome/`**
  (moved 2026-09-11). The AMI box runs it from its own config-repo
  checkout, so it no longer needs a `BdRDev` checkout. `BdRDev` still
  owns the fleet WebUI standard (`_Instructions/WebUI.md`) it follows.
- **`update.sh`** — the "pull + migrate + rebuild an app" script the
  `srvhome` Pull button drives on `AMI`. Moved to `BdRPiSrvAMI`
  alongside `srvhome/`.
