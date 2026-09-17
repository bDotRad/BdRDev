# Deprecated — do not use

`bdr-fleet-ca.*` was DEV's local root CA under the old per-project CA
scheme. Retired 2026-09-17 per `BdRDev/_Instructions/HTTPS.md`: the
fleet no longer distributes or trusts any CA — every box's LAN cert is
now a standalone self-signed leaf (see `../../gen-selfsigned.sh`).

`BdRPiSrvAMI` and `BdRPiSrvDungeon` each had their own independent CA
also named `fleetCA` (three different CAs, same name, trusting one did
nothing for the others) — this was never actually a shared fleet CA
despite the name. Don't recreate that pattern.

Kept here (not deleted) only because Brad may have already installed
this CA's public cert on some device — if `.local` sites suddenly show
a *different* self-signed warning after the migration, that's expected;
the old CA-trust can be removed from those devices whenever convenient,
it's just no longer doing anything useful.
