-- OmniTender public Community forum — Supabase schema + Row Level Security.
--
-- ⚠️ UNVERIFIED — this was authored without access to a live Supabase project
-- (no credentials are available to this session). Before this ships:
--   1. Run it against a staging/test Supabase project, not production directly.
--   2. Exercise every path with the Supabase SQL editor's "Run as role" /
--      REST API directly (not just through community-forum.js) — confirm a
--      non-admin genuinely cannot set status/pinned/user_id on their own row,
--      cannot read someone else's pending post, and cannot post an
--      'announcement' without being in forum_admins.
--   3. Only after that passes, run this file once via the Supabase SQL editor
--      (or `supabase db push`) against the real project referenced by the
--      SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY deploy secrets.
-- This is the S-4 red-team pass GOVERNANCE.md requires before merging an
-- auth/data surface — it has NOT happened yet for this file.
--
-- Design: public read of approved posts; any signed-in user may post/comment;
-- every new post starts 'pending' and is invisible to the public until an
-- admin (a row in forum_admins) approves it. Comments are auto-visible once
-- posted, but only on an already-approved post, and only their author (or an
-- admin) can remove one. Status/pinned/ownership are locked down by BEFORE
-- triggers, not just RLS USING/WITH CHECK — RLS alone cannot stop an author
-- from PATCHing their own row's `status` column directly via the REST API.

create table if not exists public.forum_posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  display_name text not null check (char_length(display_name) between 1 and 80),
  title text not null check (char_length(title) between 3 and 160),
  body text not null check (char_length(body) between 3 and 4000),
  category text not null default 'general' check (category in ('general', 'question', 'announcement')),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  pinned boolean not null default false,
  deleted boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.forum_comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.forum_posts(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  display_name text not null check (char_length(display_name) between 1 and 80),
  body text not null check (char_length(body) between 1 and 2000),
  deleted boolean not null default false,
  created_at timestamptz not null default now()
);

-- Moderator roster. Deliberately has no INSERT/UPDATE/DELETE policy below —
-- the only way to add or remove a moderator is the Owner running SQL
-- directly (or via the Supabase dashboard's table editor), never the app.
create table if not exists public.forum_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  added_at timestamptz not null default now()
);

create index if not exists forum_posts_status_idx on public.forum_posts (status, deleted, pinned desc, created_at desc);
create index if not exists forum_comments_post_idx on public.forum_comments (post_id, created_at);

create or replace function public.is_forum_admin(uid uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from public.forum_admins a where a.user_id = uid);
$$;

-- Server-side defaults a client can never override: every insert is owned by
-- the caller and starts pending/unpinned/not-deleted, regardless of what the
-- client sent in those fields.
create or replace function public.forum_posts_before_insert()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.category = 'announcement' and not public.is_forum_admin(auth.uid()) then
    raise exception 'Only a moderator can post an announcement.';
  end if;
  new.user_id := auth.uid();
  new.status := 'pending';
  new.pinned := false;
  new.deleted := false;
  new.created_at := now();
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists forum_posts_before_insert on public.forum_posts;
create trigger forum_posts_before_insert
  before insert on public.forum_posts
  for each row execute function public.forum_posts_before_insert();

-- Column-level lockdown for updates: an author may only edit their own
-- pending/rejected post's content (which re-queues it for review) or set
-- deleted=true on their own post; only a moderator may change status,
-- pinned, or ownership, or restore a deleted post.
create or replace function public.forum_posts_before_update()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_forum_admin(auth.uid()) then
    if new.user_id <> old.user_id then
      raise exception 'Cannot reassign a post''s author.';
    end if;
    if old.user_id <> auth.uid() then
      raise exception 'You can only change your own post.';
    end if;
    if new.status <> old.status or new.pinned <> old.pinned then
      raise exception 'Only a moderator can change status or pinned.';
    end if;
    if old.deleted = true and new.deleted = false then
      raise exception 'Only a moderator can restore a removed post.';
    end if;
    if new.category = 'announcement' then
      raise exception 'Only a moderator can post an announcement.';
    end if;
    if (new.title <> old.title or new.body <> old.body or new.category <> old.category)
       and old.status not in ('pending', 'rejected') then
      raise exception 'You can only edit a post while it is pending or rejected.';
    end if;
    if new.title <> old.title or new.body <> old.body or new.category <> old.category then
      new.status := 'pending';
    end if;
  end if;
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists forum_posts_before_update on public.forum_posts;
create trigger forum_posts_before_update
  before update on public.forum_posts
  for each row execute function public.forum_posts_before_update();

create or replace function public.forum_comments_before_insert()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if not exists (
    select 1 from public.forum_posts p
    where p.id = new.post_id and p.status = 'approved' and p.deleted = false
  ) then
    raise exception 'Cannot comment on a post that is not approved.';
  end if;
  new.user_id := auth.uid();
  new.deleted := false;
  new.created_at := now();
  return new;
end;
$$;

drop trigger if exists forum_comments_before_insert on public.forum_comments;
create trigger forum_comments_before_insert
  before insert on public.forum_comments
  for each row execute function public.forum_comments_before_insert();

-- A comment can only ever be soft-deleted (by its author or a moderator),
-- never edited or un-deleted by a non-moderator.
create or replace function public.forum_comments_before_update()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_forum_admin(auth.uid()) then
    if old.user_id <> auth.uid() then
      raise exception 'You can only remove your own reply.';
    end if;
    if new.body <> old.body or new.user_id <> old.user_id or new.post_id <> old.post_id then
      raise exception 'A reply can only be removed, not edited.';
    end if;
    if old.deleted = true and new.deleted = false then
      raise exception 'Only a moderator can restore a removed reply.';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists forum_comments_before_update on public.forum_comments;
create trigger forum_comments_before_update
  before update on public.forum_comments
  for each row execute function public.forum_comments_before_update();

alter table public.forum_posts enable row level security;
alter table public.forum_comments enable row level security;
alter table public.forum_admins enable row level security;

drop policy if exists forum_posts_select on public.forum_posts;
create policy forum_posts_select on public.forum_posts for select
  using (
    (status = 'approved' and deleted = false)
    or auth.uid() = user_id
    or public.is_forum_admin(auth.uid())
  );

drop policy if exists forum_posts_insert on public.forum_posts;
create policy forum_posts_insert on public.forum_posts for insert
  with check (auth.uid() is not null);

drop policy if exists forum_posts_update on public.forum_posts;
create policy forum_posts_update on public.forum_posts for update
  using (auth.uid() = user_id or public.is_forum_admin(auth.uid()))
  with check (auth.uid() = user_id or public.is_forum_admin(auth.uid()));

drop policy if exists forum_comments_select on public.forum_comments;
create policy forum_comments_select on public.forum_comments for select
  using (
    (
      deleted = false
      and exists (
        select 1 from public.forum_posts p
        where p.id = post_id and p.status = 'approved' and p.deleted = false
      )
    )
    or auth.uid() = user_id
    or public.is_forum_admin(auth.uid())
  );

drop policy if exists forum_comments_insert on public.forum_comments;
create policy forum_comments_insert on public.forum_comments for insert
  with check (auth.uid() is not null);

drop policy if exists forum_comments_update on public.forum_comments;
create policy forum_comments_update on public.forum_comments for update
  using (auth.uid() = user_id or public.is_forum_admin(auth.uid()))
  with check (auth.uid() = user_id or public.is_forum_admin(auth.uid()));

drop policy if exists forum_admins_select on public.forum_admins;
create policy forum_admins_select on public.forum_admins for select
  using (public.is_forum_admin(auth.uid()));

-- To make someone a moderator, run (once you know their auth.users.id):
--   insert into public.forum_admins (user_id) values ('<uuid>');
