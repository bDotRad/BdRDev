-- ============================================================================
-- DRAFT MIGRATION  -  servers AND projects: add `nickname` (display label)
-- ----------------------------------------------------------------------------
-- STATUS: DRAFT. Deliberately NOT placed in migrations/ so it does not get
-- picked up by an unattended schema-apply. Run by hand on the self-hosted
-- Supabase (supabase-db container) on the dev box, same as
-- DRAFT_ecosystem_web_columns.sql.
--
-- WHY: `servers.name` / `projects.name` are machine identities -- a server
-- hostname, a repo directory basename -- so they can't carry spaces or
-- punctuation. `nickname` is a free-text display label for the web pages
-- ("BdR Dev", "AM Assist Pi", ...). Blank nickname falls back to `name` at
-- render time, so this column is optional per row and starts empty.
--
-- ORDER: stacks on top of DRAFT_ecosystem_web_columns.sql (the view body
-- below assumes servers/projects already have local_url + ts_url and that
-- servers.software_freetext is gone). Run that one first, or if it's already
-- applied just run this -- every statement here is guarded / idempotent.
--
-- COUPLED to app code. The matching app/common.py + app/fleet_db.py +
-- app/templates/index.html change (the `nickname` key + the "Nick Name"
-- grid column) must be deployed together with this: run this file, THEN
-- restart the dashboard. In between, the running (old) dashboard keeps
-- working -- _normalize_ecosystem() tolerates the extra JSON key.
--
-- Target: Postgres 17, self-hosted Supabase. Safe to re-run.
-- ============================================================================

begin;

-- ===========================================================================
-- 1.  SCHEMA  -  add nickname to both tables
-- ===========================================================================
alter table public.servers  add column if not exists nickname text not null default '';
alter table public.projects add column if not exists nickname text not null default '';

comment on column public.servers.nickname is
  'Free-text display label for the web pages (may contain spaces / '
  'punctuation). Blank -> the UI falls back to servers.name.';
comment on column public.projects.nickname is
  'Free-text display label for the web pages (may contain spaces / '
  'punctuation). Blank -> the UI falls back to projects.name.';


-- ===========================================================================
-- 2.  VIEW  -  fleet_ecosystem_json. Server AND project objects now carry
--             `nickname` (right after `name`). Body otherwise identical to
--             the version in DRAFT_ecosystem_web_columns.sql.
-- ===========================================================================
create or replace view public.fleet_ecosystem_json
with (security_invoker = true) as
select jsonb_build_object(
  'servers', (
    select coalesce(jsonb_agg(t.obj order by t.sort_order, t.name), '[]'::jsonb)
    from (
      select sv.sort_order, sv.name,
        jsonb_build_object(
          'name', sv.name, 'nickname', sv.nickname,
          'tag', sv.tag, 'address', sv.address,
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
          'nickname',  pr.nickname,
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
  'servers[]={name,nickname,tag,address,tailscale,local_url,ts_url,host,os,ram,'
  'disk,claude,nginx,supabase,sqlite,git,provisioned,dev_host}; '
  'projects[]={name,nickname,exists,runs_on,local_url,ts_url,database,status,'
  'roles[]}; notes"".';

grant select on public.fleet_ecosystem_json to anon, authenticated, service_role;


-- ===========================================================================
-- 3.  DATA LOAD  -  optional. Nicknames start empty; fill them in via the
--     Ecosystem grid, or uncomment + edit these guarded updates.
-- ===========================================================================
-- update public.servers  set nickname = 'BdR Dev Pi'  where name = 'BdRPiSrvDev' and nickname = '';
-- update public.projects set nickname = 'AM Assist'    where name = 'BdRAMAssist' and nickname = '';

-- Refresh PostgREST's schema cache so the new column shows on the REST API.
notify pgrst, 'reload schema';

commit;


-- ===========================================================================
-- SANITY CHECKS  (run after COMMIT)
-- ===========================================================================
-- select name, nickname from public.servers  order by sort_order, name;
-- select name, nickname from public.projects order by sort_order, name;
-- select jsonb_pretty((select ecosystem->'servers'  from public.fleet_ecosystem_json));
-- select jsonb_pretty((select ecosystem->'projects' from public.fleet_ecosystem_json));
-- \d public.servers    -- expect nickname
-- \d public.projects   -- expect nickname
