SET local check_function_bodies = off;

CREATE TABLE "public"."activities" (
  "id"                 uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "user_id"            uuid                     NOT NULL,
  "plant_id"           uuid                     NOT NULL,
  "diagnosis_id"       uuid,
  "receta_id"          uuid,
  "titulo"             text                     NOT NULL,
  "descripcion"        text,
  "fecha_programada"   date                     NOT NULL,
  "fecha_completada"   date,
  "aplicacion_num"     smallint,
  "total_aplicaciones" smallint,
  "created_at"         timestamp with time zone NOT NULL DEFAULT now(),
  "updated_at"         timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "activities_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."activities"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."clima_diario" (
  "fecha"            date                     NOT NULL,
  "humedad_media"    numeric(5,2)             NOT NULL,
  "precipitacion_mm" numeric(6,2)             NOT NULL DEFAULT 0,
  "temp_media"       numeric(5,2),
  "fuente"           text                     NOT NULL DEFAULT 'open-meteo'::text,
  "created_at"       timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "clima_diario_pkey" PRIMARY KEY (fecha)
);

ALTER TABLE "public"."clima_diario"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."diagnoses" (
  "id"                 uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "user_id"            uuid                     NOT NULL,
  "plant_id"           uuid,
  "disease_id"         uuid,
  "clase_raw"          text                     NOT NULL,
  "confianza"          numeric(5,2)             NOT NULL,
  "top3"               jsonb                    NOT NULL DEFAULT '[]'::jsonb,
  "imagen_url"         text                     NOT NULL,
  "gradcam_url"        text,
  "especie_confirmada" boolean                  NOT NULL DEFAULT false,
  "created_at"         timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "diagnoses_confianza_check" CHECK (((confianza >= (0)::numeric) AND (confianza <= (100)::numeric))),
  CONSTRAINT "diagnoses_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."diagnoses"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."disease_catalog" (
  "id"                    uuid     NOT NULL DEFAULT gen_random_uuid(),
  "clase_raw"             text     NOT NULL,
  "species_id"            uuid,
  "nombre_enfermedad"     text     NOT NULL,
  "nombre_cientifico"     text,
  "descripcion"           text,
  "sintomas"              text,
  "causas"                text,
  "prevencion"            text,
  "riego_frecuencia_dias" smallint,
  "riego_nota"            text,
  "otros_cuidados"        text,
  "insumos_no_caseros"    jsonb    NOT NULL DEFAULT '[]'::jsonb,
  CONSTRAINT "disease_catalog_clase_raw_key" UNIQUE (clase_raw),
  CONSTRAINT "disease_catalog_pkey" PRIMARY KEY (id),
  CONSTRAINT "disease_catalog_riego_frecuencia_dias_check" CHECK (((riego_frecuencia_dias >= 1) AND (riego_frecuencia_dias <= 30)))
);

ALTER TABLE "public"."disease_catalog"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."disease_treatments" (
  "id"               uuid     NOT NULL DEFAULT gen_random_uuid(),
  "disease_id"       uuid     NOT NULL,
  "receta_id"        uuid     NOT NULL,
  "frecuencia_dias"  smallint NOT NULL DEFAULT 7,
  "num_aplicaciones" smallint NOT NULL DEFAULT 3,
  "nota"             text,
  CONSTRAINT "disease_treatments_disease_id_receta_id_key" UNIQUE (disease_id, receta_id),
  CONSTRAINT "disease_treatments_frecuencia_dias_check" CHECK (((frecuencia_dias >= 1) AND (frecuencia_dias <= 30))),
  CONSTRAINT "disease_treatments_num_aplicaciones_check" CHECK (((num_aplicaciones >= 1) AND (num_aplicaciones <= 10))),
  CONSTRAINT "disease_treatments_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."disease_treatments"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."plants" (
  "id"                    uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "user_id"               uuid                     NOT NULL,
  "species_id"            uuid,
  "apodo"                 text                     NOT NULL,
  "fecha_siembra"         date,
  "riego_frecuencia_dias" smallint,
  "ultimo_riego"          date,
  "foto_url"              text,
  "created_at"            timestamp with time zone NOT NULL DEFAULT now(),
  "updated_at"            timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "plants_pkey" PRIMARY KEY (id),
  CONSTRAINT "plants_riego_frecuencia_dias_check" CHECK (((riego_frecuencia_dias >= 1) AND (riego_frecuencia_dias <= 30)))
);

ALTER TABLE "public"."plants"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."profiles" (
  "id"             uuid                     NOT NULL,
  "nombre"         text,
  "foto_url"       text,
  "distrito"       text,
  "notificaciones" boolean                  NOT NULL DEFAULT true,
  "created_at"     timestamp with time zone NOT NULL DEFAULT now(),
  "updated_at"     timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "profiles_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."profiles"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."recetas" (
  "id"           uuid  NOT NULL DEFAULT gen_random_uuid(),
  "slug"         text  NOT NULL,
  "nombre"       text  NOT NULL,
  "descripcion"  text,
  "ingredientes" jsonb NOT NULL DEFAULT '[]'::jsonb,
  "preparacion"  jsonb NOT NULL DEFAULT '[]'::jsonb,
  "modo_uso"     text,
  "precauciones" text,
  "costo_aprox"  text,
  CONSTRAINT "recetas_pkey" PRIMARY KEY (id),
  CONSTRAINT "recetas_slug_key" UNIQUE (slug)
);

ALTER TABLE "public"."recetas"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."species_sections" (
  "id"         uuid NOT NULL DEFAULT gen_random_uuid(),
  "species_id" uuid NOT NULL,
  "contenido"  text NOT NULL,
  CONSTRAINT "species_sections_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."species_sections"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."species" (
  "id"                uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "slug"              text                     NOT NULL,
  "nombre_comun"      text                     NOT NULL,
  "nombre_cientifico" text,
  "familia"           text,
  "imagen_url"        text,
  "resumen"           text                     NOT NULL,
  "dificultad"        text                     NOT NULL,
  "luz_recomendada"   text,
  "riego_base_dias"   smallint                 NOT NULL,
  "diagnosticable"    boolean                  NOT NULL DEFAULT false,
  "created_at"        timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "species_dificultad_check" CHECK ((dificultad = ANY (ARRAY['Facil'::text, 'Media'::text, 'Dificil'::text]))),
  CONSTRAINT "species_pkey" PRIMARY KEY (id),
  CONSTRAINT "species_riego_base_dias_check" CHECK (((riego_base_dias >= 1) AND (riego_base_dias <= 30))),
  CONSTRAINT "species_slug_key" UNIQUE (slug)
);

ALTER TABLE "public"."species"
  ENABLE ROW LEVEL SECURITY;

CREATE TYPE "public"."estado_actividad" AS ENUM (
  'Pendiente',
  'Completada',
  'Cancelada'
);

ALTER TABLE "public"."activities"
  ADD COLUMN "estado" public.estado_actividad NOT NULL DEFAULT 'Pendiente'::public.estado_actividad;

CREATE TYPE "public"."estado_diagnostico" AS ENUM (
  'Sana',
  'Enferma',
  'Plagada'
);

ALTER TABLE "public"."diagnoses"
  ADD COLUMN "estado" public.estado_diagnostico NOT NULL;

ALTER TABLE "public"."disease_catalog"
  ADD COLUMN "estado" public.estado_diagnostico NOT NULL;

CREATE TYPE "public"."estado_planta" AS ENUM (
  'Sin_diagnostico',
  'Sana',
  'En_tratamiento'
);

ALTER TABLE "public"."plants"
  ADD COLUMN "estado" public.estado_planta NOT NULL DEFAULT 'Sin_diagnostico'::public.estado_planta;

CREATE TYPE "public"."etapa_planta" AS ENUM (
  'Germinacion',
  'Crecimiento',
  'Floracion',
  'Fructificacion',
  'Cosecha'
);

ALTER TABLE "public"."plants"
  ADD COLUMN "etapa" public.etapa_planta NOT NULL DEFAULT 'Crecimiento'::public.etapa_planta;

CREATE TYPE "public"."nivel_urgencia" AS ENUM (
  'Baja',
  'Media',
  'Alta'
);

ALTER TABLE "public"."disease_catalog"
  ADD COLUMN "urgencia" public.nivel_urgencia NOT NULL DEFAULT 'Media'::public.nivel_urgencia;

CREATE TYPE "public"."seccion_guia" AS ENUM (
  'Preparacion',
  'Siembra',
  'Cuidados',
  'Cosecha',
  'Consejos'
);

ALTER TABLE "public"."species_sections"
  ADD COLUMN "seccion" public.seccion_guia NOT NULL;

CREATE TYPE "public"."tipo_actividad" AS ENUM (
  'Riego',
  'Tratamiento',
  'Revision'
);

ALTER TABLE "public"."activities"
  ADD COLUMN "tipo" public.tipo_actividad NOT NULL;

CREATE TYPE "public"."ubicacion_planta" AS ENUM (
  'Balcon',
  'Ventana',
  'Terraza',
  'Patio',
  'Interior',
  'Jardin'
);

ALTER TABLE "public"."plants"
  ADD COLUMN "ubicacion" public.ubicacion_planta NOT NULL;

CREATE OR REPLACE FUNCTION public.handle_new_user()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'public'
  AS $function$
begin
    insert into public.profiles (id, nombre)
    values (new.id, new.raw_user_meta_data ->> 'nombre');
    return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.touch_updated_at()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  AS $function$
begin
    new.updated_at = now();
    return new;
end;
$function$;

ALTER TABLE "public"."activities"
  ADD CONSTRAINT "activities_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."activities"
  ADD CONSTRAINT "activities_diagnosis_id_fkey" FOREIGN KEY (diagnosis_id) REFERENCES public.diagnoses(id) ON DELETE SET NULL;

ALTER TABLE "public"."diagnoses"
  ADD CONSTRAINT "diagnoses_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."diagnoses"
  ADD CONSTRAINT "diagnoses_disease_id_fkey" FOREIGN KEY (disease_id) REFERENCES public.disease_catalog(id);

ALTER TABLE "public"."disease_treatments"
  ADD CONSTRAINT "disease_treatments_disease_id_fkey" FOREIGN KEY (disease_id) REFERENCES public.disease_catalog(id) ON DELETE CASCADE;

ALTER TABLE "public"."activities"
  ADD CONSTRAINT "activities_plant_id_fkey" FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE CASCADE;

ALTER TABLE "public"."diagnoses"
  ADD CONSTRAINT "diagnoses_plant_id_fkey" FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE CASCADE;

ALTER TABLE "public"."plants"
  ADD CONSTRAINT "plants_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."profiles"
  ADD CONSTRAINT "profiles_id_fkey" FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."activities"
  ADD CONSTRAINT "activities_receta_id_fkey" FOREIGN KEY (receta_id) REFERENCES public.recetas(id);

ALTER TABLE "public"."disease_treatments"
  ADD CONSTRAINT "disease_treatments_receta_id_fkey" FOREIGN KEY (receta_id) REFERENCES public.recetas(id);

ALTER TABLE "public"."disease_catalog"
  ADD CONSTRAINT "disease_catalog_species_id_fkey" FOREIGN KEY (species_id) REFERENCES public.species(id);

ALTER TABLE "public"."plants"
  ADD CONSTRAINT "plants_species_id_fkey" FOREIGN KEY (species_id) REFERENCES public.species(id);

ALTER TABLE "public"."species_sections"
  ADD CONSTRAINT "species_sections_species_id_fkey" FOREIGN KEY (species_id) REFERENCES public.species(id) ON DELETE CASCADE;

ALTER TABLE "public"."species_sections"
  ADD CONSTRAINT "species_sections_species_id_seccion_key" UNIQUE (species_id, seccion);

CREATE INDEX idx_activities_agenda ON public.activities USING btree (user_id, fecha_programada);

CREATE INDEX idx_diagnoses_plant ON public.diagnoses USING btree (plant_id, created_at DESC);

CREATE INDEX idx_diagnoses_user ON public.diagnoses USING btree (user_id, created_at DESC);

CREATE INDEX idx_disease_species ON public.disease_catalog USING btree (species_id);

CREATE INDEX idx_plants_user ON public.plants USING btree (user_id);

CREATE INDEX idx_species_sections_species ON public.species_sections USING btree (species_id);

CREATE UNIQUE INDEX uniq_actividad_pendiente ON public.activities USING btree (plant_id, tipo)
  WHERE (estado = 'Pendiente'::public.estado_actividad);

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

CREATE TRIGGER trg_activities_touch
  BEFORE UPDATE ON public.activities
  FOR EACH ROW
  EXECUTE FUNCTION public.touch_updated_at();

CREATE TRIGGER trg_plants_touch
  BEFORE UPDATE ON public.plants
  FOR EACH ROW
  EXECUTE FUNCTION public.touch_updated_at();

CREATE TRIGGER trg_profiles_touch
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.touch_updated_at();

CREATE POLICY "actividades_propias" ON "public"."activities"
  FOR ALL
  TO "authenticated"
  USING ((user_id = ( SELECT auth.uid() AS uid)))
  WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));

CREATE POLICY "cat_clima_read" ON "public"."clima_diario"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "diagnosticos_propios" ON "public"."diagnoses"
  FOR ALL
  TO "authenticated"
  USING ((user_id = ( SELECT auth.uid() AS uid)))
  WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));

CREATE POLICY "cat_disease_read" ON "public"."disease_catalog"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "cat_treatments_read" ON "public"."disease_treatments"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "plantas_propias" ON "public"."plants"
  FOR ALL
  TO "authenticated"
  USING ((user_id = ( SELECT auth.uid() AS uid)))
  WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));

CREATE POLICY "perfil_propio" ON "public"."profiles"
  FOR ALL
  TO "authenticated"
  USING ((id = ( SELECT auth.uid() AS uid)))
  WITH CHECK ((id = ( SELECT auth.uid() AS uid)));

CREATE POLICY "cat_recetas_read" ON "public"."recetas"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "cat_species_read" ON "public"."species"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "cat_sections_read" ON "public"."species_sections"
  FOR SELECT
  TO "authenticated"
  USING (true);

COMMENT ON TABLE "public"."clima_diario" IS 'Una fila por día. Si la API externa falla se inserta el promedio estacional de Lima con fuente = estacional.';

COMMENT ON TABLE "public"."species" IS 'Especies cultivables. Alimenta el módulo Guía y clasifica las plantas del jardín.';

GRANT EXECUTE ON FUNCTION "public"."handle_new_user"() TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "public"."touch_updated_at"() TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."activities" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."clima_diario" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."diagnoses" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."disease_catalog" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."disease_treatments" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."plants" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."profiles" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."recetas" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."species" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."species_sections" TO "anon", "authenticated", "postgres", "service_role";

GRANT USAGE ON TYPE "public"."estado_actividad" TO "postgres";

GRANT USAGE ON TYPE "public"."estado_diagnostico" TO "postgres";

GRANT USAGE ON TYPE "public"."estado_planta" TO "postgres";

GRANT USAGE ON TYPE "public"."etapa_planta" TO "postgres";

GRANT USAGE ON TYPE "public"."nivel_urgencia" TO "postgres";

GRANT USAGE ON TYPE "public"."seccion_guia" TO "postgres";

GRANT USAGE ON TYPE "public"."tipo_actividad" TO "postgres";

GRANT USAGE ON TYPE "public"."ubicacion_planta" TO "postgres";

