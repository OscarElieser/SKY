-- SKY Instagram owner-authorized outgoing messages, Supabase project only.
-- Applied to the linked project on 2026-10-30 with RLS and no public policies.
-- Access is exclusively via the authenticated Edge Function (service_role).
create table if not exists public.sky_instagram_outbound_approvals (
  approval_id uuid primary key default gen_random_uuid(),
  device_token_hash text not null references public.sky_instagram_mobile_devices(token_hash),
  event_key text not null references public.sky_instagram_webhook_events(event_key),
  reply_digest text not null check (reply_digest ~ '^[a-f0-9]{64}$'),
  recipient_id text not null check (recipient_id ~ '^[0-9]{5,30}$'),
  ig_account_id text not null check (ig_account_id ~ '^[0-9]{5,30}$'),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  state text not null default 'prepared'
    check (state in ('prepared','sending','sent','failed','unknown')),
  meta_message_id text null check (meta_message_id is null or length(meta_message_id) <= 250),
  completed_at timestamptz null,
  constraint sky_instagram_outbound_unique_reply
    unique (event_key, reply_digest, device_token_hash),
  constraint sky_instagram_outbound_expiry
    check (expires_at > created_at and expires_at <= created_at + interval '10 minutes')
);
create index if not exists sky_ig_outbound_recent
  on public.sky_instagram_outbound_approvals(device_token_hash, created_at desc);
alter table public.sky_instagram_outbound_approvals enable row level security;
revoke all on public.sky_instagram_outbound_approvals from public, anon, authenticated;
grant select, insert, update on public.sky_instagram_outbound_approvals to service_role;
