-- SKY Instagram only; execute in a NEW SKY Supabase project.
-- Never apply to BAQUEANO. The service role is the sole data accessor.
create table if not exists public.sky_instagram_oauth_states (
  state_hash text primary key check (state_hash ~ '^[a-f0-9]{64}$'),
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.sky_instagram_connections (
  id text primary key check (id = 'owner'),
  token_ciphertext text not null,
  token_iv text not null,
  scopes jsonb not null default '[]'::jsonb,
  token_expires_at timestamptz,
  verified_at timestamptz not null,
  created_at timestamptz not null default now()
);

alter table public.sky_instagram_oauth_states enable row level security;
alter table public.sky_instagram_connections enable row level security;
revoke all on public.sky_instagram_oauth_states from public, anon, authenticated;
revoke all on public.sky_instagram_connections from public, anon, authenticated;
grant select, insert, update, delete on public.sky_instagram_oauth_states to service_role;
grant select, insert, update, delete on public.sky_instagram_connections to service_role;
-- No client RLS policies: even a logged-in user must not query tokens.
create index if not exists sky_instagram_oauth_states_expire_idx
  on public.sky_instagram_oauth_states (expires_at);
-- Delete stale state rows periodically using a trusted server maintenance job:
-- delete from public.sky_instagram_oauth_states where expires_at < now() - interval '1 day';
