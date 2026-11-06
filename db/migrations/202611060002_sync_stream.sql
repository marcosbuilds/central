-- Central Colaborativa: real file-sync coordination and resumable event delivery.
-- Bytes stay in Syncthing. This migration stores only identity, policy, status
-- and durable project events.

alter table public.devices
  add column if not exists client_key text;

create unique index if not exists devices_owner_client_key_uq
  on public.devices (organization_id, user_id, client_key)
  where client_key is not null;

create index if not exists devices_organization_active_idx
  on public.devices (organization_id, revoked_at, created_at);

alter table public.project_events
  add column if not exists idempotency_key text;

create unique index if not exists project_events_idempotency_key_uq
  on public.project_events (project_id, idempotency_key)
  where idempotency_key is not null;

create index if not exists project_events_project_sequence_order_idx
  on public.project_events (project_id, sequence);

create table if not exists public.sync_folders (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  folder_id text not null check (length(trim(folder_id)) between 1 and 128),
  label text not null check (length(trim(label)) between 1 and 160),
  relative_path text not null check (length(trim(relative_path)) between 1 and 500),
  mode text not null default 'send-receive'
    check (mode in ('send-only', 'receive-only', 'send-receive')),
  enabled boolean not null default true,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, folder_id),
  unique (project_id, relative_path)
);

create index if not exists sync_folders_project_enabled_idx
  on public.sync_folders (project_id, enabled);

create or replace function public.register_device(
  p_organization_id uuid,
  p_client_key text,
  p_device_name text,
  p_syncthing_device_id text default null
)
returns public.devices
language plpgsql
security definer
set search_path = ''
as $$
declare
  device public.devices;
  normalized_key text := nullif(trim(coalesce(p_client_key, '')), '');
  normalized_name text := nullif(trim(coalesce(p_device_name, '')), '');
  normalized_syncthing_id text := nullif(trim(coalesce(p_syncthing_device_id, '')), '');
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if not public.is_organization_member(p_organization_id) then
    raise exception using errcode = '42501', message = 'organization_access_denied';
  end if;
  if normalized_key is null or length(normalized_key) > 128 then
    raise exception using errcode = '22023', message = 'device_client_key_invalid';
  end if;
  if normalized_name is null or length(normalized_name) > 120 then
    raise exception using errcode = '22023', message = 'device_name_invalid';
  end if;
  if normalized_syncthing_id is not null and length(normalized_syncthing_id) > 160 then
    raise exception using errcode = '22023', message = 'syncthing_device_id_invalid';
  end if;

  if normalized_syncthing_id is not null and exists (
    select 1
      from public.devices existing
     where existing.organization_id = p_organization_id
       and existing.syncthing_device_id = normalized_syncthing_id
       and existing.revoked_at is null
       and existing.user_id <> auth.uid()
  ) then
    raise exception using errcode = '23505', message = 'syncthing_device_already_registered';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended(
      p_organization_id::text || ':' || auth.uid()::text || ':' || normalized_key,
      0
    )
  );

  select existing.*
    into device
    from public.devices existing
   where existing.organization_id = p_organization_id
     and existing.user_id = auth.uid()
     and existing.client_key = normalized_key
   limit 1;

  if found then
    update public.devices existing
       set device_name = normalized_name,
           syncthing_device_id = coalesce(normalized_syncthing_id, existing.syncthing_device_id),
           last_seen_at = now(),
           revoked_at = null
     where existing.id = device.id
     returning existing.* into device;
    return device;
  end if;

  insert into public.devices (
    user_id, organization_id, device_name, syncthing_device_id, client_key, last_seen_at
  ) values (
    auth.uid(), p_organization_id, normalized_name, normalized_syncthing_id, normalized_key, now()
  ) returning * into device;

  return device;
end;
$$;

create or replace function public.get_project_devices(p_project_id uuid)
returns setof public.devices
language sql
stable
security definer
set search_path = ''
as $$
  select device.*
    from public.devices device
    join public.projects project
      on project.id = p_project_id
     and project.organization_id = device.organization_id
    join public.project_members member
      on member.project_id = project.id
     and member.user_id = device.user_id
   where public.is_project_member(p_project_id)
     and device.revoked_at is null
     and nullif(trim(device.syncthing_device_id), '') is not null
   order by device.created_at asc;
$$;

create or replace function public.heartbeat_device(p_device_id uuid)
returns public.devices
language plpgsql
security definer
set search_path = ''
as $$
declare
  device public.devices;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;

  update public.devices current_device
     set last_seen_at = now()
   where current_device.id = p_device_id
     and current_device.user_id = auth.uid()
     and public.is_organization_member(current_device.organization_id)
     and current_device.revoked_at is null
  returning current_device.* into device;

  if not found then
    raise exception using errcode = '42501', message = 'device_heartbeat_denied';
  end if;
  return device;
end;
$$;

create or replace function public.revoke_device(p_device_id uuid)
returns public.devices
language plpgsql
security definer
set search_path = ''
as $$
declare
  device public.devices;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;

  update public.devices current_device
     set revoked_at = coalesce(current_device.revoked_at, now())
   where current_device.id = p_device_id
     and (
       current_device.user_id = auth.uid()
       or public.can_manage_organization(current_device.organization_id)
     )
  returning current_device.* into device;

  if not found then
    raise exception using errcode = '42501', message = 'device_revoke_denied';
  end if;
  return device;
end;
$$;

create or replace function public.upsert_sync_state(
  p_project_id uuid,
  p_device_id uuid,
  p_state text,
  p_pending_items integer default 0,
  p_detail text default ''
)
returns public.sync_states
language plpgsql
security definer
set search_path = ''
as $$
declare
  state_row public.sync_states;
  project_organization_id uuid;
  normalized_detail text := coalesce(trim(p_detail), '');
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if p_state not in ('unknown', 'syncing', 'synced', 'offline', 'error', 'conflict') then
    raise exception using errcode = '22023', message = 'sync_state_invalid';
  end if;
  if p_pending_items < 0 then
    raise exception using errcode = '22023', message = 'pending_items_invalid';
  end if;
  if length(normalized_detail) > 500 then
    raise exception using errcode = '22023', message = 'sync_detail_too_long';
  end if;
  if not public.is_project_member(p_project_id) then
    raise exception using errcode = '42501', message = 'project_access_denied';
  end if;

  select project.organization_id
    into project_organization_id
    from public.projects project
   where project.id = p_project_id;

  if not exists (
    select 1
      from public.devices device
     where device.id = p_device_id
       and device.user_id = auth.uid()
       and device.organization_id = project_organization_id
       and device.revoked_at is null
  ) then
    raise exception using errcode = '42501', message = 'device_project_access_denied';
  end if;

  insert into public.sync_states (
    project_id, device_id, state, pending_items, last_observed_at, detail
  ) values (
    p_project_id, p_device_id, p_state, p_pending_items, now(), normalized_detail
  )
  on conflict (project_id, device_id) do update
    set state = excluded.state,
        pending_items = excluded.pending_items,
        last_observed_at = excluded.last_observed_at,
        detail = excluded.detail
  returning * into state_row;

  return state_row;
end;
$$;

create or replace function public.append_project_event(
  p_project_id uuid,
  p_event_type text,
  p_payload jsonb default '{}'::jsonb,
  p_idempotency_key text default null
)
returns public.project_events
language plpgsql
security definer
set search_path = ''
as $$
declare
  event_row public.project_events;
  normalized_type text := nullif(trim(coalesce(p_event_type, '')), '');
  normalized_key text := nullif(trim(coalesce(p_idempotency_key, '')), '');
  next_sequence bigint;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if not public.is_project_member(p_project_id) then
    raise exception using errcode = '42501', message = 'project_access_denied';
  end if;
  if not exists (
    select 1
      from public.project_members member
     where member.project_id = p_project_id
       and member.user_id = auth.uid()
       and member.role <> 'viewer'::public.project_member_role
  ) then
    raise exception using errcode = '42501', message = 'event_write_denied';
  end if;
  if normalized_type is null or length(normalized_type) > 120 then
    raise exception using errcode = '22023', message = 'event_type_invalid';
  end if;
  if normalized_type !~ '^[a-z0-9][a-z0-9_.-]{0,119}$' then
    raise exception using errcode = '22023', message = 'event_type_invalid';
  end if;
  if normalized_key is not null and length(normalized_key) > 180 then
    raise exception using errcode = '22023', message = 'idempotency_key_invalid';
  end if;
  if octet_length(coalesce(p_payload, '{}'::jsonb)::text) > 65536 then
    raise exception using errcode = '22023', message = 'event_payload_too_large';
  end if;

  -- Every event writer must serialize on this same project lock. This keeps
  -- sequence assignment and insertion atomic with the existing lock RPCs.
  perform pg_advisory_xact_lock(hashtextextended(p_project_id::text, 0));

  if normalized_key is not null then
    select existing.*
      into event_row
      from public.project_events existing
     where existing.project_id = p_project_id
       and existing.idempotency_key = normalized_key
     limit 1;
    if found then
      if event_row.event_type <> normalized_type
         or event_row.payload <> coalesce(p_payload, '{}'::jsonb) then
        raise exception using errcode = '23505', message = 'idempotency_key_conflict';
      end if;
      return event_row;
    end if;
  end if;

  select coalesce(max(existing.sequence), 0) + 1
    into next_sequence
    from public.project_events existing
   where existing.project_id = p_project_id;

  insert into public.project_events (
    project_id, actor_user_id, event_type, sequence, payload, idempotency_key
  ) values (
    p_project_id, auth.uid(), normalized_type, next_sequence,
    coalesce(p_payload, '{}'::jsonb), normalized_key
  ) returning * into event_row;

  return event_row;
end;
$$;

create or replace function public.ensure_sync_folder(
  p_project_id uuid,
  p_folder_id text,
  p_label text,
  p_relative_path text,
  p_mode text default 'send-receive'
)
returns public.sync_folders
language plpgsql
security definer
set search_path = ''
as $$
declare
  folder public.sync_folders;
  normalized_folder_id text := nullif(trim(coalesce(p_folder_id, '')), '');
  normalized_label text := nullif(trim(coalesce(p_label, '')), '');
  normalized_path text := nullif(trim(coalesce(p_relative_path, '')), '');
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authentication_required';
  end if;
  if not public.is_project_member(p_project_id) then
    raise exception using errcode = '42501', message = 'project_access_denied';
  end if;
  if normalized_folder_id is null or length(normalized_folder_id) > 128 then
    raise exception using errcode = '22023', message = 'folder_id_invalid';
  end if;
  if normalized_label is null or length(normalized_label) > 160 then
    raise exception using errcode = '22023', message = 'folder_label_invalid';
  end if;
  if normalized_path is null or length(normalized_path) > 500 then
    raise exception using errcode = '22023', message = 'folder_path_invalid';
  end if;
  if p_mode not in ('send-only', 'receive-only', 'send-receive') then
    raise exception using errcode = '22023', message = 'folder_mode_invalid';
  end if;

  insert into public.sync_folders (
    project_id, folder_id, label, relative_path, mode, enabled, created_by, updated_at
  ) values (
    p_project_id, normalized_folder_id, normalized_label, normalized_path,
    p_mode, true, auth.uid(), now()
  )
  on conflict (project_id, folder_id) do update
    set label = excluded.label,
        enabled = true,
        updated_at = now()
  returning * into folder;

  return folder;
end;
$$;

alter table public.sync_folders enable row level security;

drop policy if exists sync_folders_select on public.sync_folders;
create policy sync_folders_select on public.sync_folders
  for select using (public.is_project_member(project_id));

drop policy if exists sync_folders_manage on public.sync_folders;
create policy sync_folders_manage on public.sync_folders
  for all using (public.can_manage_project(project_id))
  with check (public.can_manage_project(project_id));

grant select, insert, update, delete on public.sync_folders to authenticated;

revoke execute on function public.register_device(uuid, text, text, text) from public;
revoke execute on function public.heartbeat_device(uuid) from public;
revoke execute on function public.revoke_device(uuid) from public;
revoke execute on function public.upsert_sync_state(uuid, uuid, text, integer, text) from public;
revoke execute on function public.append_project_event(uuid, text, jsonb, text) from public;
revoke execute on function public.get_project_devices(uuid) from public;
grant execute on function public.register_device(uuid, text, text, text) to authenticated;
grant execute on function public.heartbeat_device(uuid) to authenticated;
grant execute on function public.revoke_device(uuid) to authenticated;
grant execute on function public.upsert_sync_state(uuid, uuid, text, integer, text) to authenticated;
grant execute on function public.append_project_event(uuid, text, jsonb, text) to authenticated;
grant execute on function public.get_project_devices(uuid) to authenticated;
grant execute on function public.ensure_sync_folder(uuid, text, text, text, text) to authenticated;

-- Device and state writes go through the authenticated RPCs above. Keeping
-- direct table writes revoked prevents a caller from manufacturing a device
-- in an organization they do not belong to or bypassing the device checks.
revoke insert, update, delete on public.devices from authenticated;
revoke insert, update, delete on public.sync_states from authenticated;
revoke insert, update, delete on public.sync_folders from authenticated;

drop policy if exists devices_owner_manage on public.devices;
drop policy if exists sync_folders_manage on public.sync_folders;
drop policy if exists project_tasks_manage on public.project_tasks;
create policy project_tasks_manage on public.project_tasks
  for all using (public.can_manage_project(project_id))
  with check (public.can_manage_project(project_id));

-- Realtime is private and is only a notification transport. The policy maps
-- the channel topic back to the project membership check. Do not enable RLS
-- here: Supabase owns realtime.messages and documents that it is already RLS
-- protected; only policies are managed by application migrations.
drop policy if exists central_project_realtime_select on realtime.messages;
create policy central_project_realtime_select on realtime.messages
  for select to authenticated
  using (
    public.is_project_member(
      nullif(
        (regexp_match(
          realtime.topic(),
          '^realtime:project:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$'
        ))[1],
        ''
      )::uuid
    )
  );

do $$
begin
  if not exists (
    select 1
      from pg_publication_rel relation
      join pg_class table_ref on table_ref.oid = relation.prrelid
      join pg_publication publication on publication.oid = relation.prpubid
     where publication.pubname = 'supabase_realtime'
       and table_ref.relname = 'sync_states'
       and table_ref.relnamespace = 'public'::regnamespace
  ) then
    execute 'alter publication supabase_realtime add table public.sync_states';
  end if;
end
$$;

