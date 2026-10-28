-- SKY Instagram Android: disposable pairing codes and revocable mobile credentials.
-- Apply ONLY to the SKY-IA project jojzuaeqmjgnqikpnfxk, never BAQUEANO.
create table if not exists public.sky_instagram_pairing_codes (
  code_hash text primary key check (code_hash ~ '^[a-f0-9]{64}$'),
  expires_at timestamptz not null,
  claimed_at timestamptz,
  created_at timestamptz not null default now()
);
create table if not exists public.sky_instagram_mobile_devices (
  token_hash text primary key check (token_hash ~ '^[a-f0-9]{64}$'),
  device_label text not null default 'SKY Android' check (length(device_label) between 1 and 80),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);
alter table public.sky_instagram_pairing_codes enable row level security;
alter table public.sky_instagram_mobile_devices enable row level security;
revoke all on public.sky_instagram_pairing_codes from public, anon, authenticated;
revoke all on public.sky_instagram_mobile_devices from public, anon, authenticated;
grant select, insert, update, delete on public.sky_instagram_pairing_codes to service_role;
grant select, insert, update, delete on public.sky_instagram_mobile_devices to service_role;
create index if not exists sky_instagram_pairing_codes_expires_idx
 on public.sky_instagram_pairing_codes(expires_at);
create index if not exists sky_instagram_mobile_devices_expires_idx
 on public.sky_instagram_mobile_devices(expires_at);
-- Pairing codes are one-time and expire within ten minutes.
-- Device tokens are hashed at rest, expire in 30 days, and are individually revocable.
-- Deliberately no anon/authenticated RLS policy.