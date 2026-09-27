WAITING RESPONSE

# Rename the DUNGEON Pi to BdRPiSrvRatsNest

## Original request (Brad, 2026-09-27)

> im changing the dungeon pi to RatsNest. I think its called BdRPi at the
> moment
>
> So step 1. Rename the Pi to BdRatsNest
>
> Under that will be a project BdRDungeon for the circuits and testing in
> the Dungeon.
>
> Then a project BdRatsNestAutomation — This is the new home automation.
>
> The existing Home Automation on the Green module will be made redundant
> and given to my parents

Clarified with Brad in the same session:
- Box canonical name **`BdRPiSrvRatsNest`** (fleet `BdRPiSrv<X>` pattern),
  handle **`RATSNEST`**.
- Home-automation project stays **`BdRatsNest`** (no
  `BdRatsNestAutomation` rename, no new repo).
- `BdRDungeon` already exists; it stays and lives on this box.

## Done (2026-09-27, interactive session on DEV)

- Read-only check over `ssh BdRPiDungeon`: OS hostname is still
  **`BdRpi`**. It was never actually set to `BdRPiSrvDungeon`, although
  FLEET.md/Naming.md said it had been. Checkouts on the box are
  `BdRatsNest`, `BdRDungeon` and `BdRPiSrvDungeon`.
- Fleet Supabase `servers` row id 59 renamed in place
  `BdRPiSrvDungeon` → `BdRPiSrvRatsNest` (nickname, tag and `local_url`
  updated; `ts_url` kept on the still-working
  `bdrpisrvdungeon.tail0ed3f6.ts.net`). Projects `BdRDungeon`,
  `BdRatsNest` and `BdRPiSrvDungeon` follow through the FK. The `HA` row
  was re-tagged as being retired.
- `_Instructions/FLEET.md` + `_Instructions/Naming.md`: box is now
  `RATSNEST` / `BdRPiSrvRatsNest`, the HA Green's handle is now `HA`
  (was `RatsNest`), the old "two RatsNests" note was replaced, and the
  project rows were repointed.
- Kept their old names on purpose (repo/key renames are deferred per
  Naming.md): SSH alias `BdRPiDungeon`, key
  `bdrdev_to_bdrpidungeonserver`, config repo `BdRPiSrvDungeon`, deploy
  keys `*bdrpisrvdungeon*`.

## Hostname rename — done, verified 2026-09-27

Brad ran the rename. The first attempt was undone at boot by cloud-init
(Imager's `/boot/firmware/user-data` still said `hostname: BdRpi`, and
`preserve_hostname: false` re-applies it every boot). Fixed by changing
that line and adding `/etc/cloud/cloud.cfg.d/99-keep-hostname.cfg` with
`preserve_hostname: true`. Read-only check after the 10:27 reboot:
`hostname`, `/etc/hostname`, user-data, tailnet (`bdrpisrvratsnest`) and
`bdrpisrvratsnest.local` are all correct. Supabase `ts_url` is set to
`https://bdrpisrvratsnest.tail0ed3f6.ts.net`; FLEET.md + Naming.md are
updated.

## Still to do — Brad: the web front doors broke

Since the reboot, nothing on the box is reachable over HTTPS. The
backends are fine (`srvhome` on `:8610` and `bdratsnest.service` on
`:8440` both return 200 locally).

- **`tailscale serve`** still has its config under the old name
  `bdrpisrvdungeon.tail0ed3f6.ts.net`, so every TLS handshake to the new
  name fails. This is a direct consequence of the rename, so it's fixed
  here:

@@@ --- Action --- @@@

1. Re-create tailscale serve under the new name (on the Pi)

"Clear the old-name serve config and re-add the same mappings"
ssh BdRPiDungeon
sudo tailscale serve reset
sudo tailscale serve --bg --https=443  http://127.0.0.1:8610
sudo tailscale serve --bg --https=8441 http://127.0.0.1:8440
sudo tailscale serve status

2. Check from any tailnet browser

"srvhome and BdRatsNest should both load"
https://bdrpisrvratsnest.tail0ed3f6.ts.net/
https://bdrpisrvratsnest.tail0ed3f6.ts.net:8441/

@@@ --- End Action --- @@@

  The old `:8445 → 127.0.0.1:8085` mapping was left out on purpose.
  Nothing listens on `:8085`. Re-add it if you know what it was for.

- **nginx** is `failed` (`bind() to 0.0.0.0:443 … Address already in
  use`), because `tailscale serve` took the tailnet IP's `:443` first
  this boot. That's a latent fault in the box's nginx config, not caused
  by the rename. Per `HTTPS.md`, nginx should `listen` on
  `10.10.10.30:443` + `127.0.0.1` only. The fix belongs in the
  `BdRPiSrvDungeon` repo (`_Requests/rHTTPSStandardAdopt.md`), not here.
  Until it's fixed there's no LAN HTTPS (`https://bdrpisrvratsnest.local`).

When step 1 is done, flip this back to `READY`. The next session then:
- verifies both tailnet URLs from DEV and archives this file;
- fixes the remaining old-name prose in `_Instructions/SSH.md` (line ~110
  says "box hostname `BdRPiSrvDungeon`") and `HTTPS.md`. These were
  skipped because SSH.md had another session's uncommitted edits;
- flags that `~/projects/CLAUDE.md` on DEV still lists
  `DUNGEON`/`BdRPiSrvDungeon` as "not provisioned yet" (outside this repo,
  so it needs Brad's OK to edit).

Optional, later: tell the `BdRatsNest`, `BdRDungeon` and
`BdRPiSrvDungeon` projects about the box rename (their docs say
`DUNGEON`, and the box's TLS cert SANs still say `bdrpisrvdungeon`).
That work belongs in those repos.
