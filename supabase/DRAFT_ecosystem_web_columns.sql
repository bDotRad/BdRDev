-- ============================================================================
-- DRAFT MIGRATION  -  servers AND projects: split web access into
--                     local_url + ts_url; drop servers.software_freetext
-- ----------------------------------------------------------------------------
-- STATUS: DRAFT. Deliberately NOT placed in migrations/ so it does not get
-- picked up by an unattended schema-apply. Run by hand on the self-hosted
-- Supabase (supabase-db container) on the dev box, same as
-- DRAFT_fold_apps_PartBC_only.sql was.
--
-- Tracked by:  _Requests/rEcosystem web-access columns/request.md
-- Design:      supabase/DATA_MODEL.md  ("server" + "project" field tables)
--
-- The projects side (web_url -> local_url + ts_url) was added after the
-- servers-only first pass, on Brad's follow-up "I need it for the projects
-- too". Same shape as the servers change.
--
-- COUPLED to app code. The matching app/common.py + app/fleet_db.py +
-- app/templates/index.html change (local_url / ts_url, no software) must be
-- deployed together with this: run this file, THEN restart the dashboard.
-- In between, the running (old) dashboard keeps working off state/ecosystem.json
-- if its Supabase read trips on the shape change.
--
-- Target: Postgres 17, self-hosted Supabase. Safe to re-run (guarded rename,
-- add/drop if exists, name-keyed data updates that no-op on a second pass).
--
-- Run order matters: recreate the view (dropping its dependency on
-- software_freetext) BEFORE dropping that column.
-- ============================================================================

begin;

-- ===========================================================================
-- 1.  SCHEMA  -  servers + projects: rename web_url -> local_url, add ts_url
-- ===========================================================================
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'servers'
      and column_name = 'web_url'
  ) then
    alter table public.servers rename column web_url to local_url;
  end if;
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'projects'
      and column_name = 'web_url'
  ) then
    alter table public.projects rename column web_url to local_url;
  end if;
end $$;

alter table public.servers  add column if not exists ts_url text not null default '';
alter table public.projects add column if not exists ts_url text not null default '';

comment on column public.servers.local_url is
  'LAN / mDNS address (e.g. https://<host>.local). Rendered as a link. Was web_url.';
comment on column public.servers.ts_url is
  'Primary Tailscale front-door URL (https://<node>.tail0ed3f6.ts.net[:port]). '
  'Blank where the box is not on the tailnet or `tailscale serve` is not set up. '
  'Per-app tailnet ports are not modelled here.';
comment on column public.projects.local_url is
  'Deployed app URL on the LAN / mDNS (e.g. https://<app>.local). Rendered as a '
  'link. Was web_url (folded in from apps.web_address).';
comment on column public.projects.ts_url is
  'Tailscale front-door URL for the deployed app '
  '(https://<node>.tail0ed3f6.ts.net[:port]). Blank where the app is not exposed '
  'on the tailnet.';


-- ===========================================================================
-- 2.  VIEW  -  fleet_ecosystem_json. Server AND project objects now carry
--             local_url + ts_url instead of a single web_url (server also
--             drops software). Must run before the software_freetext drop
--             below (releases the view's dependency).
-- ===========================================================================
create or replace view public.fleet_ecosystem_json
with (security_invoker = true) as
select jsonb_build_object(
  'servers', (
    select coalesce(jsonb_agg(t.obj order by t.sort_order, t.name), '[]'::jsonb)
    from (
      select sv.sort_order, sv.name,
        jsonb_build_object(
          'name', sv.name, 'tag', sv.tag, 'address', sv.address,
          'tailscale', sv.tailscale_ip,
          'local_url', sv.local_url,
          'ts_url', sv.ts_url,
          'host', sv.host, 'os', sv.os, 'ram', sv.ram, 'disk', sv.disk,
          'claude',   exists (select 1 from public.server_software ss join public.software sw on sw.id = ss.software_id where ss.server_id = sv.id and sw.name = 'Claude Code'),
          'nginx',    exists (select 1 from public.server_software ss join public.software sw on sw.id = ss.software_id where ss.server_id = sv.id and sw.name = 'Nginx'),
          'supabase', exists (select 1 from public.server_software ss join public.software sw on sw.id = ss.software_id where ss.server_id = sv.id and sw.name = 'Supabase'),
          'sqlite',   exists (select 1 from public.server_software ss join public.software sw on sw.id = ss.software_id where ss.server_id = sv.id and sw.name = 'SQLite'),
          'git', sv.git_notes, 'provisioned', sv.provisioned, 'dev_host', sv.dev_host
        ) as obj
      from public.servers sv
    ) t
  ),
  'projects', (
    select coalesce(jsonb_agg(t.obj order by t.sort_order, t.name), '[]'::jsonb)
    from (
      select pr.sort_order, pr.name,
        jsonb_build_object(
          'name',      pr.name,
          'exists',    pr.exists_flag,
          'runs_on',   coalesce((select s.name from public.servers s where s.id = pr.runs_on_server_id), ''),
          'local_url', pr.local_url,
          'ts_url',    pr.ts_url,
          'database',  pr.database,
          'status',   pr.status,
          'roles',    coalesce((
            select jsonb_agg(r.name order by r.sort_order)
            from public.project_roles prr join public.roles r on r.id = prr.role_id
            where prr.project_id = pr.id
          ), '[]'::jsonb)
        ) as obj
      from public.projects pr
    ) t
  ),
  'notes', coalesce((select notes from public.fleet_meta where id = 1), '')
) as ecosystem;

comment on view public.fleet_ecosystem_json is
  'Single-row view. Column "ecosystem" (jsonb) matches common.load_ecosystem(): '
  'servers[]={name,tag,address,tailscale,local_url,ts_url,host,os,ram,disk,'
  'claude,nginx,supabase,sqlite,git,provisioned,dev_host}; '
  'projects[]={name,exists,runs_on,local_url,ts_url,database,status,roles[]}; notes"".';

grant select on public.fleet_ecosystem_json to anon, authenticated, service_role;


-- ===========================================================================
-- 3.  SCHEMA  -  drop the now-unreferenced software_freetext column
-- ===========================================================================
alter table public.servers drop column if exists software_freetext;


-- ===========================================================================
-- 4.  DATA LOAD  -  ecosystem-servers-tidied.csv from the request folder
-- ===========================================================================
-- Renames key off the OLD name, so a second run is a no-op for those rows.

-- BdRVSrvDev -> BdRPiSrvDev  (now a Pi at 10.10.8.11; Supabase runs here too)
update public.servers set
  name         = 'BdRPiSrvDev',
  tag          = 'this host, local',
  address      = '10.10.8.11',
  tailscale_ip = '100.116.147.74',
  local_url    = 'https://bdrpisrvdev.local',
  ts_url       = 'https://bdrpisrvdev.tail0ed3f6.ts.net',
  host         = 'Raspberry Pi',
  os           = 'Ubuntu Server',
  ram          = '8GB',
  disk         = '512GB SSD',
  provisioned  = true,
  dev_host     = true
where name = 'BdRVSrvDev';

-- Supabase now runs on the dev box (127.0.0.1:8000) -> add the software link
insert into public.server_software (server_id, software_id)
select s.id, sw.id
from public.servers s
cross join public.software sw
where s.name = 'BdRPiSrvDev' and sw.name = 'Supabase'
on conflict do nothing;

-- BdRPiAMI -> BdRPiSrvAMI  (matches Tailscale node bdrpisrvami + the nginx configs)
-- ts_url: the box IS on the tailnet with a valid *.ts.net cert; the MagicDNS
-- root currently lands on the auth-gated Supabase vhost (401), the per-app
-- ports are :8443 PlanBdRad / :8444 BdRAMAssist (see section 4b).
update public.servers set
  name         = 'BdRPiSrvAMI',
  tag          = 'Raspberry Pi 8GB',
  address      = '10.10.10.20',
  tailscale_ip = '100.86.25.88',
  local_url    = 'https://bdrpiami.local',
  ts_url       = 'https://bdrpisrvami.tail0ed3f6.ts.net',
  host         = 'Raspberry Pi',
  os           = 'Raspberry Pi',
  ram          = '8GB',
  provisioned  = true,
  dev_host     = false
where name = 'BdRPiAMI';
-- re-run catch-up (rename already happened on a prior pass)
update public.servers set ts_url = 'https://bdrpisrvami.tail0ed3f6.ts.net'
  where name = 'BdRPiSrvAMI' and coalesce(ts_url, '') = '';

-- BdRSrvDungeon  -  not provisioned, both URLs blank
update public.servers set
  local_url   = '',
  ts_url      = '',
  provisioned = false
where name = 'BdRSrvDungeon';

-- BdRBirdDetector  -  LAN only, plain http (no TLS on that box), not on tailnet
update public.servers set
  local_url = 'http://bdrbirddetector.local',
  ts_url    = ''
where name = 'BdRBirdDetector';

-- ===========================================================================
-- 4b. DATA LOAD  -  projects.local_url / ts_url. The column is `local_url`
--     by this point (renamed in section 1). Fills the gaps left by the
--     fold-apps migration and sets every known per-app tailnet URL:
--       BdRDev      https://bdrpisrvdev.tail0ed3f6.ts.net        (:443)
--       CloudCLI    https://bdrpisrvdev.tail0ed3f6.ts.net:8443
--       PlanBdRad   https://bdrpisrvami.tail0ed3f6.ts.net:8443
--       BdRAMAssist https://bdrpisrvami.tail0ed3f6.ts.net:8444
--     BdRIS / BdRDungeon have no deployment; BdRBirdDetector is LAN-only.
--     Guarded on the current value, so a second run is a no-op and a
--     hand-edit via the grid is never clobbered.
-- ===========================================================================
update public.projects set
    local_url = 'https://bdrpisrvdev.local',
    ts_url    = 'https://bdrpisrvdev.tail0ed3f6.ts.net'
  where name = 'BdRDev'
    and coalesce(local_url, '') in ('', 'http://192.168.100.10:8420')
    and coalesce(ts_url, '') = '';
update public.projects set ts_url = 'https://bdrpisrvdev.tail0ed3f6.ts.net:8443'
  where name = 'CloudCLI'       and coalesce(ts_url, '') = '';
-- BdRPiSrvAMI apps: nginx serves each on its own HTTPS port on the tailnet
-- (valid *.ts.net cert). Verified 2026-09-04: :8443 -> "BdR PlanB",
-- :8444 -> "BdR AM Assist". The *.local hosts are LAN-mDNS only.
update public.projects set
    local_url = 'https://planbdrad.local',
    ts_url    = 'https://bdrpisrvami.tail0ed3f6.ts.net:8443'
  where name = 'PlanBdRad'      and coalesce(ts_url, '') = '';
update public.projects set
    local_url = 'https://bdramassist.local',
    ts_url    = 'https://bdrpisrvami.tail0ed3f6.ts.net:8444'
  where name = 'BdRAMAssist'    and coalesce(ts_url, '') = '';
update public.projects set local_url = 'http://bdrbirddetector.local'
  where name = 'BdRBirdDetector' and coalesce(local_url, '') = '';

-- Refresh PostgREST's schema cache so the renamed column shows on the REST API.
notify pgrst, 'reload schema';

commit;


-- ===========================================================================
-- SANITY CHECKS  (run after COMMIT)
-- ===========================================================================
-- select name, address, local_url, ts_url, provisioned, dev_host
--   from public.servers order by sort_order, name;
-- select name, runs_on_server_id, local_url, ts_url, status
--   from public.projects order by sort_order, name;
-- select jsonb_pretty((select ecosystem->'servers'  from public.fleet_ecosystem_json));
-- select jsonb_pretty((select ecosystem->'projects' from public.fleet_ecosystem_json));
-- \d public.servers    -- expect local_url + ts_url, no software_freetext
-- \d public.projects   -- expect local_url + ts_url, no web_url
