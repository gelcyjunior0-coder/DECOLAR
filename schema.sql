-- ============================================================================
-- Rate Shopper (Decolar) — schema do banco. Cole no SQL Editor do Supabase.
-- ============================================================================
create extension if not exists "pgcrypto";

create table if not exists hotels (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  is_own_property boolean not null default false,
  tier            text,
  url             text,          -- URL da página do hotel na DECOLAR (com uma data qualquer)
  active          boolean not null default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table if not exists app_settings (
  id            uuid primary key default gen_random_uuid(),
  window_start  date not null default '2026-10-01',
  window_end    date not null default '2026-12-31',
  los           int  not null default 1,
  adults        int  not null default 1,
  currency      text not null default 'BRL'
);

create table if not exists scrape_runs (
  id                 uuid primary key default gen_random_uuid(),
  status             text not null default 'running'
                       check (status in ('running','success','partial','failed')),
  trigger            text not null default 'manual' check (trigger in ('manual','cron')),
  started_at         timestamptz not null default now(),
  finished_at        timestamptz,
  observations_count int not null default 0,
  errors             jsonb not null default '[]'::jsonb
);

create table if not exists price_observations (
  id            uuid primary key default gen_random_uuid(),
  hotel_id      uuid not null references hotels(id) on delete cascade,
  scrape_run_id uuid not null references scrape_runs(id) on delete cascade,
  stay_date     date not null,
  category      text not null check (category in ('cheapest_overall','ocean_view','suite')),
  price         numeric(10,2),
  currency      text not null default 'BRL',
  room_name     text,
  available     boolean not null default true,
  source        text not null default 'decolar',
  captured_at   timestamptz not null default now(),
  unique (hotel_id, stay_date, category, scrape_run_id)
);
create index if not exists idx_obs_lookup
  on price_observations (hotel_id, stay_date, category, scrape_run_id);

create table if not exists profiles (
  id    uuid primary key default gen_random_uuid(),
  email text,
  role  text not null default 'analyst' check (role in ('admin','analyst'))
);

-- SEED: 5 concorrentes + Sofitel (inativo). Preencha 'url' com a página da Decolar depois.
insert into hotels (name, is_own_property, tier, active) values
  ('Belmond Copacabana Palace',          false, 'Ultra-luxury icon',          true),
  ('Fasano Rio de Janeiro',              false, 'Ultra-luxury boutique',      true),
  ('Emiliano Rio',                       false, 'Ultra-luxury boutique',      true),
  ('Janeiro Hotel (Leblon)',             false, 'Luxury lifestyle boutique',  true),
  ('Fairmont Rio de Janeiro Copacabana', false, 'Luxury resort-urban',        true),
  ('Sofitel Rio de Janeiro Ipanema',     true,  'Luxury flagship',            false)
on conflict do nothing;

insert into app_settings (window_start, window_end, los, adults, currency)
select '2026-10-01','2026-12-31',1,1,'BRL'
where not exists (select 1 from app_settings);

-- RLS: leitura para autenticados; escrita só pela service_role (o scraper).
alter table hotels             enable row level security;
alter table app_settings       enable row level security;
alter table scrape_runs        enable row level security;
alter table price_observations enable row level security;
alter table profiles           enable row level security;
create policy "auth read hotels"   on hotels             for select to authenticated using (true);
create policy "auth read settings" on app_settings       for select to authenticated using (true);
create policy "auth read runs"     on scrape_runs        for select to authenticated using (true);
create policy "auth read obs"      on price_observations for select to authenticated using (true);
create policy "auth read profiles" on profiles           for select to authenticated using (true);
