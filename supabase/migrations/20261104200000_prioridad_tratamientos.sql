-- La prioridad del tratamiento pasa del código a los datos. Hasta
-- ahora la decidía una cadena de condiciones sobre el nombre de la
-- clase, imposible de justificar o citar en la documentación.
alter table disease_treatments
    add column prioridad smallint not null default 1
        check (prioridad between 0 and 9);

comment on column disease_treatments.prioridad is
    'Menor es más prioritario. 0 marca el tratamiento principal de la enfermedad.';

-- Reproduce la decisión que tomaba la heurística, para que el
-- comportamiento no cambie al eliminarla. El orden de las ramas es
-- el mismo que tenía el if/elif del servicio.
with ideal as (
    select d.id as disease_id,
           case
               when d.clase_raw ilike '%mosaic_virus%'
                   then 'leche_herramientas'
               when d.clase_raw ilike '%yellow_leaf_curl%'
                 or d.clase_raw ilike '%greening%'
                   then 'trampas_amarillas'
               when d.clase_raw ilike '%spider_mites%'
                 or d.clase_raw ilike '%aphid%'
                   then 'jabon_potasico'
               when d.urgencia = 'Alta'
                 or d.clase_raw ilike '%late_blight%'
                 or d.clase_raw ilike '%black_rot%'
                 or d.clase_raw ilike '%canker%'
                   then 'caldo_bordeles_casero'
               when d.clase_raw ilike '%bacterial%'
                and d.clase_raw not ilike '%rot%'
                   then 'ajo_aji'
               else 'bicarbonato'
           end as slug
    from disease_catalog d
)
update disease_treatments dt
set prioridad = 0
from ideal i, recetas r
where dt.disease_id = i.disease_id
  and dt.receta_id = r.id
  and r.slug = i.slug;