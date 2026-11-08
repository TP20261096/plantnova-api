-- El distrito se elige al registrarse y viaja en los metadatos del usuario,
-- igual que el nombre. El trigger que crea la fila de profiles tiene que
-- recogerlo; si no, la cuenta nace sin distrito y el riego de sus primeras
-- plantas se calcula con el clima de Lima centro.
--
-- Se deja como columna opcional a propósito: las cuentas creadas antes de
-- este cambio no tienen distrito y lo completan desde el perfil.

create or replace function public.handle_new_user()
  returns trigger
  language plpgsql
  security definer
  set search_path to 'public'
as $function$
begin
    insert into public.profiles (id, nombre, distrito)
    values (
        new.id,
        new.raw_user_meta_data ->> 'nombre',
        new.raw_user_meta_data ->> 'distrito'
    );
    return new;
end;
$function$;
