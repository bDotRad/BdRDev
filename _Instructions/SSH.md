# SSH Key Convention

Standard for every SSH deploy key generated on BdRDev (this host) for
reaching another machine or a git remote. Applies fleet-wide — any project
under `~/projects/` that needs a new key should follow this rather than
inventing its own naming.

## Naming

- **Filename**: `<source>_to_<target>`, snake_case, no file extension for
  the private half (`.pub` suffix for the public half). `source` is
  almost always `bdrdev` (this host) unless the key is generated
  elsewhere and copied in. **2026-09-06 note**: this host is now a
  physical Raspberry Pi with machine hostname `bdrpisrvdev` (tailnet
  node `bdrpisrvdev`, `bdrpisrvdev.tail0ed3f6.ts.net`, LAN `10.10.8.11`
  on `wlan0`/DHCP). `BdRDev` remains the *project/app* name. The earlier
  planned `BdRSrvDev` VM-style hostname never happened — the box was
  replaced by a Pi instead. Existing keys below keep the `bdrdev_`
  prefix; new keys generated here may use `bdrpisrvdev_` if you want the
  filename to track the real hostname, but consistency with the existing
  `bdrdev_` set is fine too.
- **Comment** (the trailing field in the `.pub` line): `<Source>-to-<Target>`,
  same pairing as the filename but PascalCase, no separating punctuation
  inside `<Target>`. Append the target's *kind* directly onto its name,
  no hyphen: `...Server` for a VM/box you SSH into, `...GIT` for a git
  remote/deploy key. Examples:
  - `bdrdev_to_planbdradserver` / comment `BdRDev-to-PlanBdRadServer`
  - `bdrdev_to_planbdradgit` / comment `BdRDev-to-PlanBdRadGIT`
  - `bdrdev_to_bdrdevgit` / comment `BdRDev-to-BdRDevGIT`

## Rules

- **One key per (source, target) pair.** Never reuse a key across
  unrelated targets, and never leave a generic/unlabeled key
  (`id_ed25519` with no comment or doc reference) sitting around — if you
  can't say in one line what it's for, it shouldn't exist.
- **Document it in the owning project's setup doc** (e.g. `VM_SETUP.md`,
  `CLAUDE.md`) — purpose, where the public half was installed (target's
  `authorized_keys`, or a git host's deploy-key UI), and the date
  generated.
- **Never trust an existing `.pub` file blindly.** Before writing a key
  into any doc or handing it to Brad to paste somewhere, derive it fresh
  from the private key and diff:
  ```
  ssh-keygen -y -f ~/.ssh/<name>
  ```
  A `.pub` file can silently drift from its private key (wrong content
  pasted over it, stale copy, etc.) — this already happened once
  (2026-08-24, the PlanBdRad VM key) and cost several rounds of back-and-forth
  before anyone thought to check. Confirm the current file matches the
  ssh-keygen -y output before treating it as ground truth.
- **"Pi" in names/comments is fine now — the whole fleet is Pis.** This
  host (`bdrpisrvdev`) and the AMI box (`bdrpisrvami` / on-box hostname
  `BdRPiSrvAMI`, LAN `10.10.10.20`) are both physical Raspberry Pis, as
  is `BdRadBirdDetector` at `192.168.1.187` (BdRBirdDetector project).
  The old rule against "Pi" in names dated from when this host was a
  VM/box; it no longer applies.

## Asking Brad to run SSH commands

The unattended session can `ssh` to fleet boxes for read-only checks and
file copies, but auto-mode blocks it from starting/restarting daemons on
a remote host or running any `sudo`. When a request needs one of those,
hand the commands back in the **Action block** format from
[`Requests.md`](Requests.md#how-to-write-actions-and-questions-back-into-a-request-file)
-- a quoted description above each command, numbered steps, `# on <box>`
where it runs -- and set the request to `WAITING RESPONSE`. Don't
paraphrase the command ("restart srvhome on the Pi"); write the exact
line Brad will paste.

## Tailscale SSH vs. key-based SSH — which path works

The fleet has two ways to SSH between boxes and they fail differently:

- **Key-based SSH over the LAN** (e.g. `ssh BdRPiAMI` → `bdr@10.10.10.20`
  with `bdrdev_to_bdrpiamiserver`): works headless, no prompt. This is
  the path unattended sessions and deploy scripts should use. Target
  boxes by LAN IP / the `~/.ssh/config` alias, **not** the `*.ts.net`
  name.
- **Tailscale SSH** (`ssh bdr@<100.x tailnet IP>` or `ssh bdr@<host>.tail0ed3f6.ts.net`):
  currently gated by an interactive re-auth —
  `# Tailscale SSH requires an additional check. To authenticate, visit:
  https://login.tailscale.com/a/...`. That's the tailnet SSH ACL using
  `"action": "check"` (periodic browser re-auth with a `checkPeriod`),
  not a key or connectivity problem — node keys are valid and the peers
  are online. A human can click the URL; an **unattended session hangs
  on it forever**. To make Tailscale SSH usable headless, Brad changes
  the relevant `ssh` rule in the tailnet policy file to
  `"action": "accept"` (or sets a long `"checkPeriod"`, e.g. `"720h"`)
  at <https://login.tailscale.com/admin/acls>.

## Current inventory (as of 2026-09-06)

| File | Target | Purpose |
|---|---|---|
| `bdrdev_to_bdrdevgit` | `github.com:bDotRad/BdRDev.git` | This project's own deploy key (via `~/.ssh/config` alias `github.com-bdrdev`) |
| `bdrdev_to_planbdradgit` | `github.com:bDotRad/PlanBdRad.git` | PlanBdRad repo deploy key, confirmed read+write |
| `bdrdev_to_planbdradserver` | ~~`bdr@192.168.100.20` (`PlanBdRadServer`)~~ | **DEAD.** The `PlanBdRadServer` / `BdRSrvAMI` VM at `192.168.100.20` was retired and replaced by the physical Pi `BdRPiSrvAMI` at `10.10.10.20`. Key file no longer present on this host (removed 2026-09-06 cleanup). Use `bdrdev_to_bdrpiamiserver` for the replacement box. |
| `bdrdev_to_bdramassistgit` | `github.com:bDotRad/BdRAMAssist.git` | BdRAMAssist repo deploy key, generated 2026-08-26 — **not yet installed** as a deploy key on GitHub (adding it via API was blocked by a safety check); current push access is via the account-level `gh` HTTPS credential helper instead. Add the `.pub` under the repo's Settings -> Deploy keys (with write access) to switch to this SSH key. |
| `id_ed25519_bdramassist` (was on the retired **BdRSrvAMI** VM, not this host) | `github.com:bDotRad/BdRAMAssist.git` | Read-only deploy key that lived on the `BdRSrvAMI` VM (`192.168.100.20`), now retired. Historical — whatever the replacement Pi `BdRPiSrvAMI` (`10.10.10.20`) uses to pull BdRAMAssist is configured on that box under `~/projects/BdRPiAMI/` and isn't tracked here. Left in the table as a record of the old VM's setup. |
| `bdrdev_to_bdrdungeongit` | `github.com:bDotRad/BdRDungeon.git` | BdRDungeon repo deploy key, generated 2026-08-26 — same not-yet-installed situation as the BdRAMAssist key above; pushing via `gh` HTTPS credential helper for now. |
| `bdrdev_to_bdrwebguidevgit` | `github.com:bDotRad/BdRWebGUIDev.git` | BdRWebGUIDev repo deploy key, generated 2026-09-04. Comment `BdRDev-to-BdRWebGUIDevGIT`. **Not yet installed** as a deploy key on GitHub and **no `~/.ssh/config` alias yet** — the unattended session's classifier blocked the config edit, so both are handed to Brad in `BdRWebGUIDev/_Requests/rProject Setup.md`. Pushing via `gh` HTTPS credential helper until then. Intended alias: `github.com-bdrwebguidev`. |
| ~~`id_ed25519_pi`~~ | `bdotrad@192.168.1.187` (`BdRadBirdDetector`) | **Key file missing from `~/.ssh` on this host as of 2026-09-06** — not carried over / removed in cleanup. Also `192.168.1.187` is on a different subnet from this host's `10.10.8.0/22` and the box isn't on the tailnet, so it's unreachable from here regardless of the key. Regenerate + reinstall in that Pi's `authorized_keys` if fleet-side access to BdRBirdDetector is needed again. |
| `bdrdev_to_bdrpiamiserver` | `bdr@10.10.10.20` (`~/.ssh/config` alias `BdRPiAMI`; the box's own hostname is now `BdRPiSrvAMI`) | SSH into the AMI Raspberry Pi (Ubuntu 24.04 aarch64, replaces the retired VM `BdRSrvAMI`). **Regenerated 2026-09-05** — both halves re-dated then; the 2026-08-27 key was replaced. **LAN key auth confirmed working 2026-09-06**: `ssh BdRPiAMI` connects headless as `bdr`, public half is installed in the Pi's `authorized_keys`. The tailnet path to the same box (`bdr@100.86.25.88`) is *not* headless — see the Tailscale SSH section above. |
| ~~`id_ed25519`~~ | unknown | **No longer present in `~/.ssh` on this host as of 2026-09-06** — the unexplained generic key was removed. Resolved. |

**Resolved 2026-09-06**: the stale `PlanBdRad`-comment key that used to
sit in `~/.ssh/authorized_keys` on this host is gone. `authorized_keys`
now trusts only one key, comment `BdRDev-to-BdRPiSrvDevServer`.

**2026-08-25**: all four `bdraigui_*` key files renamed to `bdrdev_*`
(content unchanged, filenames/`~/.ssh/config` only) as part of the
BdRAIGUI→BdRDev project rename. See MIGRATION_REPORT.md.

**2026-09-06**: this host is now the physical Pi `bdrpisrvdev`
(`10.10.8.11` LAN / `100.116.147.74` tailnet). Key *filenames* keep the
`bdrdev_` prefix. `id_ed25519` and `id_ed25519_pi` are no longer on the
box. Tailscale SSH between fleet boxes needs an ACL change to be
headless (see the Tailscale SSH section). LAN key SSH to `BdRPiAMI`
(`10.10.10.20`) verified working.
