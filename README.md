# PlantNova API

API REST de diagnóstico fitosanitario para huertos urbanos de Lima
Metropolitana. 29 endpoints en ocho módulos. Documentación
interactiva en `/docs`.

**URL base en desarrollo:** la que entregue el túnel, o
`http://10.0.2.2:8000` si corres el backend en la misma máquina que
el emulador de Android (`localhost` apunta al propio emulador, no al
equipo anfitrión).

---

## Autenticación

Todos los endpoints exigen el token salvo `/auth/register`,
`/auth/login`, `/auth/refresh` y `/health`.

```
Authorization: Bearer <access_token>
```

El `access_token` **caduca a los pocos minutos**. Cuando una petición
responda `401`, llama a `/auth/refresh` con el `refresh_token` y
reintenta. Resuélvelo en un interceptor HTTP, no en cada pantalla, y
distingue el `401` de un tiempo de espera agotado: un arranque en
frío del servidor puede tardar hasta un minuto y no significa que la
sesión haya expirado.

---

## Auth

### `POST /auth/register` → 201

```json
{ "email": "ana@correo.com", "password": "clave12345", "nombre": "Ana" }
```

Respuesta (igual en register, login y refresh):

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "v1.Mr7...",
  "expires_in": 3600,
  "usuario": { "id": "uuid", "email": "ana@correo.com", "nombre": "Ana" }
}
```

### `POST /auth/login` → 200

```json
{ "email": "ana@correo.com", "password": "clave12345" }
```

`401` si las credenciales no coinciden.

### `POST /auth/refresh` → 200

```json
{ "refresh_token": "v1.Mr7..." }
```

`401` si el token caducó: hay que volver a iniciar sesión.

### `POST /auth/logout` → 204
### `GET /auth/me` → 200

Devuelve `id`, `email` y `nombre`. Sirve para comprobar al abrir la
app si la sesión guardada sigue siendo válida, y da el nombre para el
saludo de Inicio.

---

## Inicio

### `GET /weather` → 200

```json
{
  "ciudad": "Miraflores",
  "temperatura": 19.4,
  "humedad": 83,
  "viento_kmh": 11.2,
  "observado": "2026-11-07T16:00"
}
```

Usa el distrito del perfil; sin distrito informa el de Lima centro.
**No pidas permisos de ubicación**: el dato sale del perfil.

Es la misma fuente que alimenta el cálculo de riego, así que no uses
otro proveedor de clima en el cliente: el usuario vería una humedad
distinta de la que el backend usó para programar sus riegos.

`503` si la fuente externa no responde y no hay lectura previa.

### `GET /tips` → 200

```json
[
  {
    "id": "uuid",
    "slug": "riego_manana",
    "titulo": "Riega temprano",
    "contenido": "Riega a primera hora de la mañana..."
  }
]
```

Vienen ya ordenados. No dependen del jardín: se muestran aunque el
usuario no tenga plantas.

---

## Actividades

### `GET /activities?fecha=2026-11-07` → 200

Sin `fecha` devuelve hoy.

```json
[
  {
    "id": "uuid",
    "plant_id": "uuid",
    "planta": "Maizito",
    "tipo": "Tratamiento",
    "estado": "Pendiente",
    "titulo": "Aplicar Caldo bordelés casero",
    "descripcion": "Aplicar al atardecer.",
    "fecha_programada": "2026-11-07",
    "fecha_completada": null,
    "dias_atraso": 0,
    "aplicacion_num": 1,
    "total_aplicaciones": 3,
    "receta_nombre": "Caldo bordelés casero",
    "diagnosis_id": "uuid",
    "proyectada": false,
    "proxima_tarea": null
  }
]
```

Detalles que cambian cómo se pinta la lista:

- Las **atrasadas vienen primero**, ya ordenadas. `dias_atraso` mayor
  que cero indica retraso; muéstralo en la tarjeta.
- Hay **una sola tarea pendiente por planta y tipo**. Si el usuario
  no riega en dos semanas verá una tarjeta atrasada, no catorce.
- En **fechas futuras** los riegos llegan con `"id": null` y
  `"proyectada": true`. Son previsiones, no registros: píntalas
  atenuadas y **no permitas completarlas**.
- `tipo` `Revision` debe **abrir la cámara**: cierra el ciclo de
  tratamiento con una nueva captura.

### `GET /activities/range?desde=&hasta=` → 200

Alimenta el selector de siete días. Sin parámetros devuelve hoy y los
seis días siguientes. Máximo 31 días por petición.

```json
{
  "2026-11-07": [ { "...": "actividad" } ],
  "2026-11-08": []
}
```

Devuelve **un diccionario con una clave por fecha**, no una lista
plana: los días sin tareas llegan como `[]` y no hay que deducir qué
fechas faltan. Una tarea atrasada aparece repetida en cada día desde
su fecha hasta hoy; es intencional, sigue pendiente.

### `POST /activities` → 201

```json
{
  "plant_id": "uuid",
  "tipo": "Riego",
  "titulo": "Regar Maizito",
  "descripcion": null,
  "fecha_programada": "2026-11-10"
}
```

`409` si esa planta ya tiene una tarea pendiente de ese tipo.

### `PATCH /activities/{id}` → 200

```json
{ "estado": "Completada" }
```

Completar dispara el encadenamiento automático:

- **Riego** → registra la fecha en la planta y recalcula la
  frecuencia con el clima del día.
- **Tratamiento** → programa la siguiente aplicación contando desde
  la fecha real de cumplimiento, no desde la programada.
- **Última aplicación** → crea la actividad de `Revision`.

La respuesta trae **`proxima_tarea`** con la siguiente tarea
pendiente de todo el jardín, que es lo que muestra la pantalla de
confirmación. Llega en `null` cuando no queda nada por hacer: muestra
un "todo al día" en vez de una pantalla vacía.

También admite `titulo`, `descripcion` y `fecha_programada`. `409` si
ya estaba completada.

### `DELETE /activities/{id}` → 204

---

## Jardín

### `POST /plants` → 201

```json
{
  "apodo": "Maizito",
  "ubicacion": "Balcon",
  "etapa": "Crecimiento",
  "species_id": "uuid o null",
  "fecha_siembra": "2026-08-01",
  "ultimo_riego": "2026-11-07"
}
```

`species_id` es **opcional**: si el usuario cultiva algo que no está
en la guía, debe poder registrarlo igual, y el diagnóstico completa
la especie después. `ultimo_riego` es la referencia con la que se
calcula el próximo riego (Hoy, Ayer o Hace días en la interfaz).

- `ubicacion`: `Balcon`, `Ventana`, `Terraza`, `Patio`, `Interior`,
  `Jardin`
- `etapa`: `Germinacion`, `Crecimiento`, `Floracion`,
  `Fructificacion`, `Cosecha`

### `GET /plants?estado=` → 200

`estado` filtra por `Sin_diagnostico`, `Sana` o `En_tratamiento`.
Sin el parámetro devuelve todas.

```json
[
  {
    "id": "uuid",
    "apodo": "Maizito",
    "especie": "Maíz",
    "ubicacion": "Balcon",
    "etapa": "Crecimiento",
    "estado": "En_tratamiento",
    "foto_url": "https://...firmada...",
    "riego_frecuencia_dias": 4,
    "ultimo_riego": "2026-11-04",
    "proximo_riego": "2026-11-08",
    "dias_para_riego": 1,
    "proximo_tratamiento": "2026-11-09",
    "dias_para_tratamiento": 2,
    "proximo_tipo": "Tratamiento"
  }
]
```

`estado` y `riego_frecuencia_dias` **los calcula el backend**; no se
envían nunca. La frecuencia resulta de la especie o del diagnóstico,
ajustada por el clima del distrito y la ubicación de la planta.

Las dos cuentas regresivas de la tarjeta:

- **Riego**: `dias_para_riego`. Negativo significa atrasado, cero es
  "Riego hoy".
- **Dosis**: `dias_para_tratamiento` junto con `proximo_tipo`, que
  vale `Tratamiento` mientras queden aplicaciones, `Revision` cuando
  el ciclo terminó y toca volver a fotografiar, `RevisionCompletada`
  si ya se hizo, y `null` cuando no hay nada (planta sana o sin
  diagnosticar: no pintes la línea de dosis).

Una planta en `Revision` sigue con estado `En_tratamiento`, así que
el filtro "En tratamiento" la incluye.

### `GET /plants/{id}` → 200

Añade a lo anterior:

```json
{
  "species_id": "uuid",
  "fecha_siembra": "2026-08-01",
  "riego_nota": "Regar solo al sustrato, nunca al follaje.",
  "otros_cuidados": "Eliminar las hojas afectadas.",
  "tratamientos": [ { "...": "igual que en el diagnóstico" } ],
  "created_at": "2026-09-01T10:00:00Z",
  "diagnosticos": [
    {
      "id": "uuid",
      "nombre_enfermedad": "Mancha gris de la hoja",
      "estado": "Enferma",
      "confianza": 78.76,
      "imagen_url": "https://...firmada...",
      "created_at": "2026-11-04T15:00:00Z"
    }
  ]
}
```

`riego_nota`, `otros_cuidados` y `tratamientos` provienen del último
diagnóstico. Los diagnósticos vienen del más reciente al más antiguo.

### `PUT /plants/{id}` → 200

Acepta campos parciales: `apodo`, `ubicacion`, `etapa`, `species_id`,
`fecha_siembra`, `ultimo_riego`. No admite `estado`, `foto_url` ni
`riego_frecuencia_dias`. Cambiar ubicación, especie o último riego
recalcula la frecuencia.

### `POST /plants/{id}/photo` → 200

`multipart/form-data`, campo `imagen` (JPEG, PNG o WEBP, máx. 10 MB).
Devuelve la planta con el mismo cuerpo que `GET /plants/{id}`. La
imagen se reduce a 1024 px y se guarda como JPEG.

### `DELETE /plants/{id}` → 204

Borra en cascada los diagnósticos y actividades de esa planta.

---

## Guía

### `GET /guide/species` → 200

Parámetros opcionales: `q` (busca por nombre) y `diagnosticables`
(booleano).

```json
[
  {
    "id": "uuid",
    "slug": "maiz",
    "nombre_comun": "Maíz",
    "nombre_cientifico": "Zea mays",
    "imagen_url": null,
    "resumen": "...",
    "dificultad": "Media",
    "riego_base_dias": 3,
    "diagnosticable": true
  }
]
```

Este mismo endpoint alimenta el **selector de especie al registrar
una planta**: el `id` que devuelve es el `species_id` que espera
`POST /plants`.

### `GET /guide/species/{slug}` → 200

```json
{
  "familia": "Poaceae",
  "luz_recomendada": "6 horas de sol directo",
  "secciones": [
    { "seccion": "Preparacion", "contenido": "..." },
    { "seccion": "Siembra", "contenido": "..." },
    { "seccion": "Cuidados", "contenido": "..." },
    { "seccion": "Cosecha", "contenido": "..." },
    { "seccion": "Consejos", "contenido": "..." }
  ]
}
```

Las secciones llegan **ya ordenadas**; recórrelas tal cual.

---

## Captura

### `POST /diagnose` → 201

`multipart/form-data`:

| Campo | Tipo | Obligatorio |
|---|---|---|
| `imagen` | archivo JPEG, PNG o WEBP, máx. 10 MB | sí |
| `plant_id` | texto | no |

Si no envías `plant_id`, el diagnóstico queda **sin planta asociada**
y se vincula después.

```json
{
  "id": "uuid",
  "plant_id": null,
  "estado": "Enferma",
  "cultivo": "Maíz",
  "especie_slug": "maiz",
  "nombre_enfermedad": "Mancha gris de la hoja",
  "nombre_cientifico": "Cercospora zeae-maydis",
  "confianza": 78.76,
  "confianza_baja": false,
  "especie_confirmada": false,
  "urgencia": "Media",
  "top3": [
    { "clase_raw": "Corn_Corn_Gray_leaf_spot",
      "nombre_enfermedad": "Mancha gris de la hoja",
      "confianza": 78.76 }
  ],
  "descripcion": "...",
  "sintomas": "...",
  "causas": "...",
  "prevencion": "...",
  "riego_frecuencia_dias": 4,
  "riego_nota": "...",
  "otros_cuidados": "...",
  "tratamientos": [
    {
      "nombre": "Caldo bordelés casero",
      "descripcion": "...",
      "ingredientes": [{ "item": "Cal apagada", "cantidad": "100 g" }],
      "preparacion": ["Paso 1", "Paso 2"],
      "modo_uso": "...",
      "precauciones": "...",
      "costo_aprox": "S/ 8 por litro",
      "fuentes": [{ "titulo": "...", "url": "https://..." }],
      "frecuencia_dias": 7,
      "num_aplicaciones": 3,
      "nota": "..."
    }
  ],
  "insumos_no_caseros": ["..."],
  "imagen_url": "https://...firmada...",
  "gradcam_url": "https://...firmada...",
  "created_at": "2026-11-07T15:00:00Z"
}
```

Cuatro campos merecen atención en la interfaz:

- **`confianza_baja`**: por debajo del 60 % el modelo no está seguro.
  Muestra el aviso y ofrece repetir la foto, y **no muestres el botón
  de guardar**. El servidor aplica la misma regla: si mandaste
  `plant_id` y la confianza quedó baja, la respuesta vuelve con
  `plant_id: null`. No es un error, es la regla.
- **`especie_confirmada`**: `false` cuando el cultivo detectado no
  coincide con la especie que el usuario registró, o cuando no había
  ninguna con qué comparar.
- **`tratamientos`**: el primero es el prioritario, el que el sistema
  programa como actividad. Los siguientes son alternativas.
- **`fuentes`**: respaldo documental del remedio, para el final de la
  sección de tratamiento.

Las URL de imagen son **enlaces firmados que caducan en una hora**.
No las guardes en caché ni las persistas: vuelve a pedir el recurso
para obtener enlaces vigentes.

Errores: `400` imagen ilegible, `413` supera 10 MB, `415` formato no
admitido, `404` la planta no existe.

### `PATCH /diagnoses/{id}/link` → 200

```json
{ "plant_id": "uuid" }
```

El diagnóstico va en la URL y la planta en el cuerpo. Al vincular, la
planta hereda la especie y la foto del diagnóstico si no las tenía, y
se recalculan su estado, su riego y su plan de tratamiento.

`409` si ya pertenece a otra planta, o si la confianza está por
debajo del 60 %.

Flujo al cerrar la pantalla de resultado:

1. **Vincular a una planta existente** → este endpoint.
2. **Registrar una planta nueva** → `POST /plants`, luego este
   endpoint con el `id` devuelto.
3. **Descartar** → no llames a nada.

### `GET /diagnoses/{id}` → 200

Mismo cuerpo, con enlaces de imagen recién firmados. Es lo que abre
el historial de una planta en modo solo lectura.

---

## Perfil

### `GET /profile` → 200

```json
{
  "id": "uuid",
  "email": "ana@correo.com",
  "nombre": "Ana",
  "foto_url": "https://...firmada...",
  "distrito": "Miraflores",
  "notificaciones": true,
  "tema": "Sistema",
  "plantas_registradas": 3,
  "diagnosticos_realizados": 7,
  "tareas_pendientes": 4,
  "tareas_completadas": 21,
  "created_at": "2026-09-01T10:00:00Z"
}
```

### `PATCH /profile` → 200

Admite `nombre`, `distrito`, `notificaciones` y `tema`
(`Sistema`, `Claro` u `Oscuro`).

Cambiar el distrito **recalcula el riego de todas las plantas**,
porque el clima de referencia pasa a ser otro. Esa petición tarda
algo más de lo normal.

### `POST /profile/avatar` → 200

`multipart/form-data`, campo `foto`. Devuelve el perfil actualizado.

### `GET /profile/districts` → 200

Lista de distritos admitidos. **Úsala para poblar el selector**: el
distrito se valida contra ella y determina el clima y los puntos de
venta de insumos. Texto libre da `400`.

### `PUT /profile/password` → 204

```json
{ "password_actual": "clave12345", "password_nueva": "nueva12345" }
```

Se exige la contraseña actual: sin ella, un token robado bastaría
para tomar la cuenta. `401` si no es correcta.

### `DELETE /profile` → 204

Irreversible. Borra cuenta, plantas, diagnósticos, actividades e
imágenes. Pide confirmación explícita en la interfaz.

---

## Códigos de error

Todos devuelven `{ "detail": "mensaje" }`, apto para mostrar
directamente al usuario.

| Código | Significado |
|---|---|
| 400 | Datos inválidos o ningún campo enviado |
| 401 | Token ausente, caducado o credenciales incorrectas |
| 404 | El recurso no existe o es de otro usuario |
| 409 | Conflicto de estado (ya completada, ya vinculada, confianza baja) |
| 413 | Imagen mayor a 10 MB |
| 415 | Formato de imagen no admitido |
| 422 | El cuerpo no cumple el esquema (validación de FastAPI) |
| 503 | El servicio de clima no responde |

---

## Levantar la API

Con Python 3.12 en la máquina:

```bash
source .venv/Scripts/activate      # Scripts en Windows, bin en Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Con Docker, sin instalar Python ni PyTorch:

```bash
docker compose up --build
```

En ambos casos hacen falta dos archivos que **no están en el
repositorio**: `.env` con las claves de Supabase (copia
`.env.example`) y `models/best_model_v2.pth`, el checkpoint del
modelo.

La API queda en `http://localhost:8000` y la documentación en
`http://localhost:8000/docs`. Desde el emulador de Android usa
`http://10.0.2.2:8000`.

## Cargar el catálogo

```bash
python -m scripts.ingest                  # todo
python -m scripts.ingest recetas tips     # solo esos dominios
```

Lee de `data/`, valida antes de escribir nada y aborta indicando
archivo y registro si algo está mal. Carga en orden: `species`,
`recetas`, `diseases`, `tips`.

## Generar el cliente Dart

En lugar de escribir los modelos a mano, genéralos desde el contrato:

```bash
curl http://localhost:8000/openapi.json -o openapi.json
openapi-generator generate -i openapi.json -g dart-dio -o cliente/
```
