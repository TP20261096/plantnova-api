-- HU006: preferencia de apariencia, para que viaje con la cuenta y
-- no se pierda al cambiar de dispositivo.
create type tema_app as enum ('Sistema', 'Claro', 'Oscuro');

alter table profiles
    add column tema tema_app not null default 'Sistema';

-- HU026: respaldo documental de cada remedio casero.
alter table recetas
    add column fuentes jsonb not null default '[]'::jsonb;

comment on column recetas.fuentes is
    'Lista de objetos {titulo, url} con las fuentes que respaldan el remedio.';

-- HU036: consejos generales de la pantalla de Inicio. Son catálogo,
-- no dependen del usuario ni de sus plantas.
create table tips (
    id         uuid primary key default gen_random_uuid(),
    slug       text not null unique,
    titulo     text not null,
    contenido  text not null,
    orden      smallint not null default 0,
    created_at timestamptz not null default now()
);

alter table tips enable row level security;

create policy cat_tips_read on tips
    for select to authenticated using (true);

create index idx_tips_orden on tips (orden);