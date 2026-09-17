WAITING RESPONSE

# Routine OS package updates on AMI

Split off from `rSrvhomeOwnedByBdRPiSrvAMI` (archived
`260917_1933_srvhomeAMIOwnership.md`) — its Task 3 asked for these same
6 packages, but the redesign/deploy part of that request is done and
verified, so it's archived; this is just the leftover routine
maintenance, low priority.

`apt history.log` on `AMI` shows no manual `apt upgrade -y` since the
partial one on 2026-09-09 (`containerd.io` only — the rest were still
phased-held at the time). As of 2026-09-17, `apt list --upgradable`
shows considerably more than the original 6, since a week of routine
updates has piled up on top (only security-relevant ones get picked up
automatically by `unattended-upgrade`; these are regular-channel):

```
base-files, docker-buildx-plugin, docker-ce-cli, docker-ce-rootless-extras,
docker-ce, krb5-locales, libgssapi-krb5-2, libk5crypto3, libkrb5-3,
libkrb5support0, libnetplan1, libperl5.38t64, libsqlite3-0,
motd-news-config, netplan-generator, netplan.io, perl-base,
perl-modules-5.38, perl, python-apt-common, python3-apt,
python3-distupgrade, python3-netplan, tailscale, ubuntu-release-upgrader-core
```

Nothing here is urgent or blocking anything else — this is just so it
doesn't get lost now that the parent request is archived.

@@@ --- Action --- @@@

1. Clear pending OS updates on AMI

"on AMI"
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y

2. Verify

"on AMI — should show nothing left upgradable"
apt list --upgradable

@@@ ------------- @@@
