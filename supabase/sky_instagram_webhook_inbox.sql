-- SKY Android / Instagram: private durable inbox for authenticated Meta webhook events.
-- No public PostgREST read/write grants; Edge Function uses its server-side role.
create table if not exists public.sky_instagram_webhook_events (
  event_key text primary key check (event_key ~ '^[a-f0-9]{64}$'),
  event_type text not null check (event_type in ('message', 'comment', 'mention')),
  ig_account_id text not null check (char_length(ig_account_id) between 1 and 80),
  actor_id text check (actor_id is null or char_length(actor_id) between 1 and 80),
  target_id text check (target_id is null or char_length(target_id) between 1 and 80),
  external_event_id text check (external_event_id is null or char_length(external_event_id) between 1 and 180),
  message_text text check (message_text is null or char_length(message_text) <= 4000),
  event_at timestamptz,
  received_at timestamptz not null default now(),
  processing_status text not null default 'received'
    check (processing_status in ('received', 'reviewed', 'archived'))
);
create index if not exists sky_instagram_webhook_events_received_idx
  on public.sky_instagram_webhook_events (received_at desc);
alter table public.sky_instagram_webhook_events enable row level security;
revoke all privileges on table public.sky_instagram_webhook_events from public, anon, authenticated;
-- No RLS policies deliberately: public API callers cannot access this inbox.
-- Only server-side service_role reads/writes. No automatic public replies.
