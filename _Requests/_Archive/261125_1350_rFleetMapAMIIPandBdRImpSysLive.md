DONE 2026-11-25

## Outcome (2026-11-25, scheduler session)

All verified live before writing: DEV `eth0` = 10.10.11.10; `ssh BdRPiAMI` lands on
BdRPiSrvAMI at 10.10.11.11; `ssh BdRPiSrvRatsNest` works (10.10.10.10);
`https://bdotrad-makegood.web.app` returns 200; `impsys` on AMI is `inactive` (install pending).

- **Supabase (ecosystem, DEV):** `servers` BdRPiSrvDev address → 10.10.11.10,
  BdRPiSrvAMI → 10.10.11.11 (tag notes the reservation), BdRIS → BdRImpSys in both
  git_notes. `projects` id 4 renamed `BdRIS` → `BdRImpSys`, exists_flag true,
  runs_on AMI, local_url `https://makegood.bdotrad.me`, database SQLite on AMI +
  Firestore bdotrad-for-me, status `building`.
- **FLEET.md:** box table IPs, AMI app row, `bdotrad-for-me` row, Firebase sites row
  (MakeGood), SSH matrix, projects row, BdRIS drift note removed.
- **Naming.md:** DEV/AMI IPs, ImpSys description.
- **SSH.md:** current-address lines for DEV/AMI/RATSNEST (historical rows left).
- **AppServerSync.md:** one-line note that AMI is now 10.10.11.11; rest left as history.
- **app/common.py:** fallback seed addresses for DEV/AMI (only used when Supabase is down).
- **~/projects/CLAUDE.md:** DEV 10.10.11.10, AMI 10.10.11.11, RATSNEST 10.10.10.10.
- **Rotation:** added `BdRImpSys` to `state/selected_projects.json`.
- The other session's uncommitted 2026-11-23 edits to FLEET.md / Naming.md /
  RatDevApp.md (RNA, Firebase split, HIW, BdRNotes) were kept and committed with these.

Left for Brad:
- GoDaddy CNAME `makegood` → `bdotrad-makegood.web.app`; AMI cert + nginx + impsys
  install per `BdRImpSys/_Requests/rGo live.md`.
- DEV's LAN cert SAN (`tls/gen-cert.sh`) still lists IP 10.10.8.11, not 10.10.11.10.
  Only matters if you browse DEV by bare IP; `bdrpisrvdev.local` is unaffected.

---


# Fleet map: AMI's new IP, BdRImpSys/MakeGood is live, DEV's and RatsNest's IPs

**From:** the AMI-cfg / BdRImpSys session on DEV, 2026-11-25. These are
deployment facts that changed today. I didn't edit `FLEET.md` here because it
already had uncommitted edits from another session.

## What changed (all verified 2026-11-25)

1. **AMI's LAN IP is now `10.10.11.11`**, a DHCP reservation for MAC
   `88:a2:9e:f1:36:5c`. It was `10.10.10.20`, then temporarily `10.10.8.19`
   and `10.10.11.97`. DEV's `~/.ssh/config` `BdRPiAMI` alias now points there
   (`HostKeyAlias 10.10.10.20` kept). AMI-cfg commit `f69939d` moved the cert SAN
   and the sslip name to `ami.10.10.11.11.sslip.io`. The cert regenerate + nginx
   deploy on AMI is still with Brad (`BdRImpSys/_Requests/rGo live.md`, step 5).
2. **DEV's LAN IP is `10.10.11.10`** (`ip -br addr` on `eth0`), not
   `10.10.8.11` as in `FLEET.md` line ~28 and `~/projects/CLAUDE.md`.
3. **RATSNEST answers on `10.10.10.10`** (the `BdRPiSrvRatsNest` SSH alias
   works). `~/projects/CLAUDE.md` still says `10.10.10.30`; `FLEET.md` is already right.
4. **BdRImpSys is built.** Repo `bDotRad/BdRImpSys` (private, commit `99d38ff`).
   - Online interface **MakeGood**: Firebase Hosting site `bdotrad-makegood` in
     `bdotrad-for-me`, `https://bdotrad-makegood.web.app`, live. Custom domain
     `makegood.bdotrad.me` was added in Firebase and is waiting on a GoDaddy CNAME
     `makegood` → `bdotrad-makegood.web.app` (Brad).
   - Worker `impsys.service` on `AMI`: keeps the master copy (SQLite
     `~/impsys`), Claude triage, daily review, backups. Its service-account
     key (`impsys-ami@bdotrad-for-me`, role Cloud Datastore User) and env file are
     in place on AMI. The pull + `setup.sh` + `systemctl enable` is with Brad.
   - Firestore `improvements/` + `impsys_meta/`, rules in `BdRNotes/firestore.rules`
     (commit `12d87e1`, deployed).
   - Side effect: the **IAM API was enabled** on `bdotrad-for-me` so the service account could be created.

## Changes to make

- `FLEET.md`:
  - box table: `DEV` → `10.10.11.10`; `AMI` → `10.10.11.11`.
  - AMI app table: the `BdRImpSys` row → `ImpSys` | worker `impsys.service` (master copy, triage) + `https://makegood.bdotrad.me` | building (page live, worker install pending).
  - `bdotrad-for-me` row: add "ImpSys (MakeGood)".
  - Firebase sites table: add `| BdRImpSys — MakeGood improvement tracker | ImpSys | https://makegood.bdotrad.me (site bdotrad-makegood in bdotrad-for-me) | live on web.app; custom domain waiting on DNS |`.
  - SSH matrix: `DEV → AMI` → `bdr@10.10.11.11`.
  - projects table: the `BdRImpSys` row → hosted `AMI` (worker, pull) + Firebase Hosting `bdotrad-makegood`; data: SQLite on AMI (master copy) + Firestore `bdotrad-for-me` (rules in BdRNotes).
  - remove the `projects.BdRIS` drift note once it's fixed in Supabase.
- Ecosystem Supabase on DEV: `servers` (AMI and DEV LAN IPs), and in `projects`
  rename `BdRIS` → `BdRImpSys` with `exists_flag = true` and the deployment above.
- `~/projects/CLAUDE.md` on DEV: DEV LAN `10.10.11.10`; AMI `10.10.11.11`; RATSNEST `10.10.10.10`.
- `AppServerSync.md` mentions AMI at `10.10.10.20`. Update it, or leave it as history.
- Optional: add `BdRImpSys` to the scheduler rotation so its `_Requests/` get picked up.
