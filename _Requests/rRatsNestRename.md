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

## Still to do — Brad

@@@ --- Action --- @@@

1. Set the Pi's hostname to BdRPiSrvRatsNest (on the Pi)

"Rename the host, fix /etc/hosts, re-announce the mDNS name, rename the tailnet node"
ssh BdRPiDungeon
sudo hostnamectl set-hostname BdRPiSrvRatsNest
sudo sed -i 's/\bBdRpi\b/BdRPiSrvRatsNest/g' /etc/hosts
sudo systemctl restart avahi-daemon
sudo tailscale set --hostname=bdrpisrvratsnest

2. Check it took

"Should print BdRPiSrvRatsNest, and the tailnet should list bdrpisrvratsnest"
hostname
tailscale status | grep 100.73.131.60

If `tailscale status` still shows `bdrpisrvdungeon`, the machine name was
set by hand in the Tailscale admin console. Rename it there too
(Machines → … → Edit machine name).

@@@ --- End Action --- @@@

Flip this file back to `READY` when that's done. The next session then:
- verifies over SSH (read-only) and sets Supabase `ts_url` to
  `https://bdrpisrvratsnest.tail0ed3f6.ts.net`, then updates the
  hostname/tailnet cells in FLEET.md + Naming.md;
- fixes the remaining old-name prose in `_Instructions/SSH.md`
  (line ~110 says "box hostname `BdRPiSrvDungeon`") and `HTTPS.md`. This
  pass skipped them because SSH.md had another session's uncommitted
  edits in it;
- notes that the box's TLS cert SANs still say `bdrpisrvdungeon`. That's
  handled in the `BdRPiSrvDungeon` repo's `rHTTPSStandardAdopt.md`, not
  here;
- flags that `~/projects/CLAUDE.md` on DEV still lists
  `DUNGEON`/`BdRPiSrvDungeon` as "not provisioned yet" (it's outside this
  repo, so it needs Brad's OK to edit);
- archives this file.

Optional, later: tell the `BdRatsNest` and `BdRDungeon` projects about the
box rename (their own docs say `DUNGEON`). That work belongs in those
repos, not here.
