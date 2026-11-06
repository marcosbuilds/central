-- Central Colaborativa: first authoritative coordination slice.
-- This migration is intentionally not executed against the existing Seloryn
-- Collective organization. A dedicated Supabase project must be provisioned
-- before applying it.

create extension if not exists pgcrypto;

do $$
begin
  create type public.organization_member_role as enum ('owner', 'admin', 'developer', 'viewer');
exception
  when duplicate_object then null;
end
$$;

do $$
begin
  create type public.project_status as enum ('open', 'closing', 'closed', 'reopening');
exception
  when duplicate_object then null;
end
$$;

do $$
begin
  create type public.project_member_role as enum ('owner', 'admin', 'developer', 'viewer');
exception
  when duplicate_object then null;
end
$$;

do $$
begin
  create type public.lock_state as enum ('active', 'released', 'expired');
exception
  when duplicate_object then null;
end
$$;

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) between 1 and 120),
  slug text not null unique check (slug = lower(slug) and slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

create table if not exists public.organization_members (
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.organization_member_role not null default 'developer',
  created_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null check (length(trim(name)) between 1 and 160),
  slug text not null,
  description text not null default '',
  status public.project_status not null default 'open',
  workspace_revision bigint not null default 0 check (workspace_revision >= 0),
  generation bigint not null default 0 check (generation >= 0),
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, slug)
);

create table if not exists public.project_members (
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.project_member_role not null default 'developer',
  created_at timestamptz not null default now(),
  primary key (project_id, user_id)
);

create table if not exists public.devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  organization_id uuid not null references public.organizations(id) on delete cascade,
  device_name text not null check (length(trim(device_name)) between 1 and 120),
  syncthing_device_id text,
  last_seen_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.project_tasks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  title text not null check (length(trim(title)) between 1 and 240),
  description text not null default '',
  area_path text not null default '',
  status text not null default 'ready' check (status in ('draft', 'ready', 'reserved', 'in_progress', 'in_review', 'blocked', 'done', 'cancelled')),
  owner_user_id uuid references auth.users(id) on delete set null,
  dependency_task_id uuid references public.project_tasks(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.agent_sessions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid references public.devices(id) on delete set null,
  provider text not null check (provider in ('codex', 'claude', 'other')),
  agent_id text not null,
  task_id uuid references public.project_tasks(id) on delete set null,
  status text not null default 'offline' check (status in ('starting', 'active', 'offline', 'stale', 'closed')),
  last_heartbeat_at timestamptz,
  started_at timestamptz not null default now(),
  closed_at timestamptz
);

create table if not exists public.resource_locks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  task_id uuid references public.project_tasks(id) on delete set null,
  resource_type text not null check (resource_type in ('project', 'task', 'module', 'directory', 'file', 'dependency')),
  resource_path text not null,
  normalized_path text not null,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid not null references public.devices(id) on delete restrict,
  agent_id text not null,
  session_id uuid not null references public.agent_sessions(id) on delete restrict,
  acquired_at timestamptz not null default now(),
  last_renewed_at timestamptz not null default now(),
  expires_at timestamptz not null,
  state public.lock_state not null default 'active',
  fencing_token bigint not null check (fencing_token > 0),
  created_at timestamptz not null default now()
);

create index if not exists resource_locks_project_active_idx
  on public.resource_locks (project_id, state, expires_at);
create index if not exists resource_locks_project_path_idx
  on public.resource_locks (project_id, normalized_path);

create table if not exists public.project_events (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  actor_user_id uuid references auth.users(id) on delete set null,
  event_type text not null,
  sequence bigint not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (project_id, sequence)
);

create table if not exists public.change_sets (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  task_id uuid references public.project_tasks(id) on delete set null,
  author_user_id uuid not null references auth.users(id) on delete cascade,
  base_revision bigint not null check (base_revision >= 0),
  state text not null default 'draft' check (state in ('draft', 'submitted', 'approved', 'rejected', 'integrated')),
  manifest jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.change_reviews (
  id uuid primary key default gen_random_uuid(),
  change_set_id uuid not null references public.change_sets(id) on delete cascade,
  reviewer_user_id uuid not null references auth.users(id) on delete cascade,
  decision text not null check (decision in ('approved', 'rejected', 'needs_changes')),
  note text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.sync_states (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  device_id uuid not null references public.devices(id) on delete cascade,
  state text not null default 'unknown' check (state in ('unknown', 'syncing', 'synced', 'offline', 'error', 'conflict')),
  pending_items integer not null default 0 check (pending_items >= 0),
  last_observed_at timestamptz,
  detail text not null default '',
  unique (project_id, device_id)
);

create table if not exists public.project_invitations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  invited_by uuid not null references auth.users(id) on delete cascade,
  invited_email text not null,
  role public.project_member_role not null default 'developer',
  token_hash text not null unique,
  expires_at timestamptz not null,
  accepted_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.project_rules (
  project_id uuid primary key references public.projects(id) on delete cascade,
  rules_markdown text not null default '',
  agents_markdown text not null default '',
  claude_markdown text not null default '',
  sync_policy jsonb not null default '{}'::jsonb,
  updated_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default now()
);

create or replace function public.is_organization_member(p_organization_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_members member
    where member.organization_id = p_organization_id
      and member.user_id = auth.uid()
  );
$$;

create or replace function public.is_project_member(p_project_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.project_members member
    where member.project_id = p_project_id
      and member.user_id = auth.uid()
  );
$$;

create or replace function public.can_manage_organization(p_organization_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_members member
    where member.organization_id = p_organization_id
      and member.user_id = auth.uid()
      and member.role in ('owner', 'admin')
  );
$$;

create or replace function public.can_manage_project(p_project_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.project_members member
    where member.project_id = p_project_id
      and member.user_id = auth.uid()
      and member.role in ('owner', 'admin')
  );
$$;

create or replace function public.create_organization(p_name text, p_slug text)
returns public.organizations
language plpgsql
security definer
set search_path = ''
as $$
declare
  created public.organizations;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if length(trim(coalesce(p_name, ''))) not between 1 and 120 then
    raise exception using errcode = '22023', message = 'organization_name_invalid';
  end if;
  if lower(trim(coalesce(p_slug, ''))) !~ '^[a-z0-9][a-z0-9-]{1,62}$' then
    raise exception using errcode = '22023', message = 'organization_slug_invalid';
  end if;

  insert into public.organizations (name, slug, created_by)
  values (trim(p_name), lower(trim(p_slug)), auth.uid())
  returning * into created;

  insert into public.organization_members (organization_id, user_id, role)
  values (created.id, auth.uid(), 'owner');

  return created;
end;
$$;

create or replace function public.create_project(
  p_organization_id uuid,
  p_name text,
  p_slug text,
  p_description text default ''
)
returns public.projects
language plpgsql
security definer
set search_path = ''
as $$
declare
  created public.projects;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if not public.can_manage_organization(p_organization_id) then
    raise exception using errcode = '42501', message = 'organization_management_denied';
  end if;
  if length(trim(coalesce(p_name, ''))) not between 1 and 160 then
    raise exception using errcode = '22023', message = 'project_name_invalid';
  end if;
  if lower(trim(coalesce(p_slug, ''))) !~ '^[a-z0-9][a-z0-9-]{1,62}$' then
    raise exception using errcode = '22023', message = 'project_slug_invalid';
  end if;

  insert into public.projects (organization_id, name, slug, description, created_by)
  values (p_organization_id, trim(p_name), lower(trim(p_slug)), coalesce(p_description, ''), auth.uid())
  returning * into created;

  insert into public.project_members (project_id, user_id, role)
  values (created.id, auth.uid(), 'owner');
  insert into public.project_rules (project_id, updated_by)
  values (created.id, auth.uid());

  return created;
end;
$$;

create or replace function public.normalize_resource_path(p_path text)
returns text
language plpgsql
immutable
strict
as $$
declare
  separator constant text := chr(92);
  cleaned text;
  segment text;
  segments text[] := array[]::text[];
begin
  cleaned := lower(trim(replace(p_path, '/', separator)));
  foreach segment in array string_to_array(cleaned, separator)
  loop
    if segment is null or segment = '' or segment = '.' then
      continue;
    end if;
    if segment = '..' then
      raise exception using errcode = '22023', message = 'resource_path_outside_project';
    end if;
    segments := array_append(segments, segment);
  end loop;
  return coalesce(array_to_string(segments, separator), '');
end;
$$;

create or replace function public.resource_paths_overlap(p_left text, p_right text)
returns boolean
language sql
immutable
strict
as $$
  select p_left = ''
      or p_right = ''
      or p_left = p_right
      or left(p_left, length(p_right) + 1) = p_right || chr(92)
      or left(p_right, length(p_left) + 1) = p_left || chr(92);
$$;

create or replace function public.acquire_resource_lock(
  p_project_id uuid,
  p_task_id uuid,
  p_resource_type text,
  p_resource_path text,
  p_device_id uuid,
  p_agent_id text,
  p_session_id uuid,
  p_lease_seconds integer default 90
)
returns public.resource_locks
language plpgsql
security definer
set search_path = ''
as $$
declare
  normalized text;
  current_lock public.resource_locks;
  next_fencing_token bigint;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if not public.is_project_member(p_project_id) then
    raise exception using errcode = '42501', message = 'project_access_denied';
  end if;
  if p_lease_seconds < 15 or p_lease_seconds > 900 then
    raise exception using errcode = '22023', message = 'lease_seconds_out_of_range';
  end if;
  if p_device_id is null or p_session_id is null or nullif(trim(p_agent_id), '') is null then
    raise exception using errcode = '22023', message = 'lock_owner_identity_required';
  end if;
  if p_resource_path is null or nullif(trim(p_resource_path), '') is null and p_resource_type <> 'project' then
    raise exception using errcode = '22023', message = 'resource_path_required';
  end if;
  if p_task_id is not null and not exists (
    select 1 from public.project_tasks task where task.id = p_task_id and task.project_id = p_project_id
  ) then
    raise exception using errcode = '22023', message = 'task_project_mismatch';
  end if;

  normalized := public.normalize_resource_path(coalesce(p_resource_path, ''));

  -- PostgreSQL has no native ancestor/descendant exclusion constraint. The
  -- advisory transaction lock serializes all lock decisions for one project,
  -- making the overlap check and insert one atomic critical section.
  perform pg_advisory_xact_lock(hashtextextended(p_project_id::text, 0));

  update public.resource_locks
     set state = 'expired'
   where project_id = p_project_id
     and state = 'active'
     and expires_at <= now();

  select lock.*
    into current_lock
    from public.resource_locks lock
   where lock.project_id = p_project_id
     and lock.state = 'active'
     and lock.expires_at > now()
     and public.resource_paths_overlap(lock.normalized_path, normalized)
   order by lock.acquired_at
   limit 1;

  if found then
    if current_lock.owner_user_id = auth.uid()
       and current_lock.device_id is not distinct from p_device_id
       and current_lock.agent_id = p_agent_id
       and current_lock.session_id is not distinct from p_session_id
       and current_lock.resource_type = p_resource_type
       and current_lock.normalized_path = normalized then
      update public.resource_locks
         set last_renewed_at = now(),
             expires_at = now() + make_interval(secs => p_lease_seconds)
       where id = current_lock.id
       returning * into current_lock;
      return current_lock;
    end if;

    raise exception using
      errcode = '23P01',
      message = 'resource_lock_conflict',
      detail = current_lock.id::text;
  end if;

  select coalesce(max(lock.fencing_token), 0) + 1
    into next_fencing_token
    from public.resource_locks lock
   where lock.project_id = p_project_id;

  insert into public.resource_locks (
    project_id, task_id, resource_type, resource_path, normalized_path,
    owner_user_id, device_id, agent_id, session_id, expires_at, fencing_token
  ) values (
    p_project_id, p_task_id, p_resource_type, p_resource_path, normalized,
    auth.uid(), p_device_id, p_agent_id, p_session_id,
    now() + make_interval(secs => p_lease_seconds), next_fencing_token
  )
  returning * into current_lock;

  insert into public.project_events (project_id, actor_user_id, event_type, sequence, payload)
  select p_project_id,
         auth.uid(),
         'resource_lock.acquired',
         coalesce(max(event.sequence), 0) + 1,
         jsonb_build_object(
           'lock_id', current_lock.id,
           'resource_type', current_lock.resource_type,
           'resource_path', current_lock.normalized_path,
           'fencing_token', current_lock.fencing_token
         )
    from public.project_events event
   where event.project_id = p_project_id;

  return current_lock;
end;
$$;

create or replace function public.renew_resource_lock(
  p_lock_id uuid,
  p_device_id uuid,
  p_agent_id text,
  p_session_id uuid,
  p_lease_seconds integer default 90
)
returns public.resource_locks
language plpgsql
security definer
set search_path = ''
as $$
declare
  renewed public.resource_locks;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if p_lease_seconds < 15 or p_lease_seconds > 900 then
    raise exception using errcode = '22023', message = 'lease_seconds_out_of_range';
  end if;
  if p_device_id is null or p_session_id is null or nullif(trim(p_agent_id), '') is null then
    raise exception using errcode = '22023', message = 'lock_owner_identity_required';
  end if;

  update public.resource_locks lock
     set last_renewed_at = now(),
         expires_at = now() + make_interval(secs => p_lease_seconds)
   where lock.id = p_lock_id
     and lock.owner_user_id = auth.uid()
     and lock.device_id is not distinct from p_device_id
     and lock.agent_id = p_agent_id
     and lock.session_id is not distinct from p_session_id
     and lock.state = 'active'
     and lock.expires_at > now()
     and public.is_project_member(lock.project_id)
  returning lock.* into renewed;

  if not found then
    raise exception using errcode = '42501', message = 'lock_renewal_denied_or_expired';
  end if;
  return renewed;
end;
$$;

create or replace function public.release_resource_lock(
  p_lock_id uuid,
  p_device_id uuid,
  p_agent_id text,
  p_session_id uuid
)
returns public.resource_locks
language plpgsql
security definer
set search_path = ''
as $$
declare
  released public.resource_locks;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if p_device_id is null or p_session_id is null or nullif(trim(p_agent_id), '') is null then
    raise exception using errcode = '22023', message = 'lock_owner_identity_required';
  end if;

  update public.resource_locks lock
     set state = 'released',
         last_renewed_at = now()
   where lock.id = p_lock_id
     and lock.owner_user_id = auth.uid()
     and lock.device_id is not distinct from p_device_id
     and lock.agent_id = p_agent_id
     and lock.session_id is not distinct from p_session_id
     and lock.state = 'active'
     and public.is_project_member(lock.project_id)
  returning lock.* into released;

  if not found then
    raise exception using errcode = '42501', message = 'lock_release_denied';
  end if;
  return released;
end;
$$;

alter table public.organizations enable row level security;
alter table public.organization_members enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.devices enable row level security;
alter table public.project_tasks enable row level security;
alter table public.agent_sessions enable row level security;
alter table public.resource_locks enable row level security;
alter table public.project_events enable row level security;
alter table public.change_sets enable row level security;
alter table public.change_reviews enable row level security;
alter table public.sync_states enable row level security;
alter table public.project_invitations enable row level security;
alter table public.project_rules enable row level security;

create policy organizations_select on public.organizations
  for select using (public.is_organization_member(id));

create policy organization_members_select on public.organization_members
  for select using (public.is_organization_member(organization_id));
create policy organization_members_manage on public.organization_members
  for all using (public.can_manage_organization(organization_id))
  with check (public.can_manage_organization(organization_id));

create policy projects_select on public.projects
  for select using (public.is_project_member(id));
create policy projects_manage on public.projects
  for update using (public.can_manage_project(id)) with check (public.can_manage_project(id));

create policy project_members_select on public.project_members
  for select using (public.is_project_member(project_id));
create policy project_members_manage on public.project_members
  for all using (public.can_manage_project(project_id)) with check (public.can_manage_project(project_id));

create policy devices_owner_select on public.devices
  for select using (user_id = auth.uid() or public.is_organization_member(organization_id));
create policy devices_owner_manage on public.devices
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy project_tasks_select on public.project_tasks
  for select using (public.is_project_member(project_id));
create policy project_tasks_manage on public.project_tasks
  for all using (public.is_project_member(project_id)) with check (public.is_project_member(project_id));

create policy agent_sessions_select on public.agent_sessions
  for select using (public.is_project_member(project_id));
create policy agent_sessions_owner_manage on public.agent_sessions
  for all using (user_id = auth.uid() and public.is_project_member(project_id))
  with check (user_id = auth.uid() and public.is_project_member(project_id));

create policy resource_locks_select on public.resource_locks
  for select using (public.is_project_member(project_id));

create policy project_events_select on public.project_events
  for select using (public.is_project_member(project_id));

create policy change_sets_select on public.change_sets
  for select using (public.is_project_member(project_id));
create policy change_sets_manage on public.change_sets
  for all using (author_user_id = auth.uid() and public.is_project_member(project_id))
  with check (author_user_id = auth.uid() and public.is_project_member(project_id));

create policy change_reviews_select on public.change_reviews
  for select using (
    exists (
      select 1 from public.change_sets change_set
      where change_set.id = change_reviews.change_set_id
        and public.is_project_member(change_set.project_id)
    )
  );

create policy sync_states_select on public.sync_states
  for select using (public.is_project_member(project_id));

create policy project_invitations_select on public.project_invitations
  for select using (public.can_manage_project(project_id));
create policy project_invitations_manage on public.project_invitations
  for all using (public.can_manage_project(project_id))
  with check (public.can_manage_project(project_id));

create policy project_rules_select on public.project_rules
  for select using (public.is_project_member(project_id));
create policy project_rules_manage on public.project_rules
  for all using (public.can_manage_project(project_id))
  with check (public.can_manage_project(project_id));

grant usage on schema public to authenticated;
revoke all on all tables in schema public from anon;
revoke all on all functions in schema public from anon;
grant select on all tables in schema public to authenticated;
grant update on public.projects to authenticated;
grant insert, update, delete on public.organization_members to authenticated;
grant insert, update, delete on public.project_members to authenticated;
grant insert, update, delete on public.devices to authenticated;
grant insert, update, delete on public.project_tasks to authenticated;
grant insert, update, delete on public.agent_sessions to authenticated;
grant insert, update, delete on public.change_sets to authenticated;
grant insert, update, delete on public.change_reviews to authenticated;
grant insert, update, delete on public.sync_states to authenticated;
grant insert, update, delete on public.project_invitations to authenticated;
grant insert, update, delete on public.project_rules to authenticated;
revoke execute on function public.is_organization_member(uuid) from public;
revoke execute on function public.is_project_member(uuid) from public;
revoke execute on function public.can_manage_organization(uuid) from public;
revoke execute on function public.can_manage_project(uuid) from public;
revoke execute on function public.create_organization(text, text) from public;
revoke execute on function public.create_project(uuid, text, text, text) from public;
revoke execute on function public.acquire_resource_lock(uuid, uuid, text, text, uuid, text, uuid, integer) from public;
revoke execute on function public.renew_resource_lock(uuid, uuid, text, uuid, integer) from public;
revoke execute on function public.release_resource_lock(uuid, uuid, text, uuid) from public;
grant execute on function public.is_organization_member(uuid) to authenticated;
grant execute on function public.is_project_member(uuid) to authenticated;
grant execute on function public.can_manage_organization(uuid) to authenticated;
grant execute on function public.can_manage_project(uuid) to authenticated;
grant execute on function public.create_organization(text, text) to authenticated;
grant execute on function public.create_project(uuid, text, text, text) to authenticated;
grant execute on function public.acquire_resource_lock(uuid, uuid, text, text, uuid, text, uuid, integer) to authenticated;
grant execute on function public.renew_resource_lock(uuid, uuid, text, uuid, integer) to authenticated;
grant execute on function public.release_resource_lock(uuid, uuid, text, uuid) to authenticated;

-- Realtime is a delivery optimization; persistent tables remain authoritative.
alter publication supabase_realtime add table public.project_events;
alter publication supabase_realtime add table public.resource_locks;
