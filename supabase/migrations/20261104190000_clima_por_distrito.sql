-- El caché de clima pasa de un único punto (Lima centro) a uno por
-- distrito. La clave primaria deja de ser la fecha sola porque ahora
-- hay una lectura por distrito y día.
alter table clima_diario
    add column distrito text not null default 'Lima';

alter table clima_diario
    drop constraint clima_diario_pkey;

alter table clima_diario
    add constraint clima_diario_pkey primary key (fecha, distrito);

comment on table clima_diario is
    'Una lectura por distrito y día. Si la API externa falla se usa el promedio estacional de Lima y no se cachea.';