# PlantNova API

API REST de diagnóstico fitosanitario para huertos urbanos de Lima
Metropolitana. Documentación interactiva en `/docs`.

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
reintenta. Conviene resolverlo en un interceptor HTTP, no en cada
pantalla.

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

Sirve para comprobar al abrir la app si la sesión guardada sigue
siendo válida.

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
  "foto_url": null
}
```

`species_id` es **opcional**: si el usuario cultiva algo que no está
en la guía, debe poder registrarlo igual.

- `ubicacion`: `Balcon`, `Ventana`, `Terraza`, `Patio`, `Interior`,
  `Jardin`
- `etapa`: `Germinacion`, `Crecimiento`, `Floracion`,
  `Fructificacion`, `Cosecha`

### `GET /plants` → 200

```json
[
  {
    "id": "uuid",
    "apodo": "Maizito",
    "especie": "Maíz",
    "ubicacion": "Balcon",
    "etapa": "Crecimiento",
    "estado": "En_tratamiento",
    "foto_url": null,
    "riego_frecuencia_dias": 4,
    "ultimo_riego": "2026-09-09",
    "proximo_riego": "2026-09-13",
    "dias_para_riego": 4
  }
]
```

`estado` es `Sin_diagnostico`, `Sana` o `En_tratamiento`. **Lo calcula
el backend**, no se envía nunca. Lo mismo con
`riego_frecuencia_dias`, que resulta de la especie o el diagnóstico
ajustados por el clima del día y la ubicación.

`dias_para_riego` negativo significa riego atrasado.

### `GET /plants/{id}` → 200

Añade a lo anterior:

```json
{
  "species_id": "uuid",
  "fecha_siembra": "2026-08-01",
  "riego_nota": "Regar solo al sustrato, nunca al follaje.",
  "otros_cuidados": "Eliminar las hojas afectadas.",
  "created_at": "2026-09-01T10:00:00Z",
  "diagnosticos": [
    {
      "id": "uuid",
      "nombre_enfermedad": "Mancha gris de la hoja",
      "estado": "Enferma",
      "confianza": 78.76,
      "imagen_url": "https://...firmada...",
      "created_at": "2026-09-09T15:00:00Z"
    }
  ]
}
```

`riego_nota` y `otros_cuidados` provienen del último diagnóstico.

### `PUT /plants/{id}` → 200

Acepta campos parciales. No admite `estado` ni
`riego_frecuencia_dias`. Cambiar `ubicacion` o `species_id`
recalcula el riego.

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
      "frecuencia_dias": 7,
      "num_aplicaciones": 3,
      "nota": "..."
    }
  ],
  "insumos_no_caseros": [
    { "producto": "...", "presentacion": "...",
      "donde_comprar": "...", "distrito": "...",
      "precio_referencial": "..." }
  ],
  "imagen_url": "https://...firmada...",
  "gradcam_url": "https://...firmada...",
  "created_at": "2026-09-09T15:00:00Z"
}
```

Tres campos merecen atención en la interfaz:

- **`confianza_baja`**: por debajo del 60 % el modelo no está seguro.
  Muestra una advertencia en lugar de presentar el resultado como
  certero. Suele indicar que la foto no es una hoja.
- **`especie_confirmada`**: `false` cuando el cultivo detectado no
  coincide con la especie registrada en la planta. Avísale al
  usuario en vez de asumir que el diagnóstico corresponde.
- **`tratamientos`**: el primero es el plan que el sistema programa
  como actividades. Los siguientes son alternativas informativas.

Las URL de imagen son **enlaces firmados que caducan en una hora**.
No las guardes en caché ni las persistas: vuelve a pedir el
diagnóstico para obtener enlaces vigentes.

Errores: `400` imagen ilegible, `413` supera 10 MB, `415` formato no
admitido, `404` la planta no existe.

### `PATCH /diagnoses/{id}/link` → 200

```json
{ "plant_id": "uuid" }
```

El diagnóstico va en la URL y la planta en el cuerpo. Al vincular se
recalculan el estado y el riego de la planta, y se programa el
tratamiento. `409` si ya pertenece a otra planta.

Flujo esperado al cerrar la pantalla de resultado:

1. **Vincular a una planta existente** → este endpoint.
2. **Registrar una planta nueva** → `POST /plants`, luego este
   endpoint con el `id` devuelto.
3. **Descartar** → no llames a nada.

### `GET /diagnoses/{id}` → 200

Mismo cuerpo, con enlaces de imagen recién firmados.

---

## Actividades (menú Inicio)

### `GET /activities?fecha=2026-09-09` → 200

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
    "fecha_programada": "2026-09-09",
    "fecha_completada": null,
    "dias_atraso": 0,
    "aplicacion_num": 1,
    "total_aplicaciones": 3,
    "receta_nombre": "Caldo bordelés casero",
    "diagnosis_id": "uuid",
    "proyectada": false
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

### `POST /activities` → 201

```json
{
  "plant_id": "uuid",
  "tipo": "Riego",
  "titulo": "Regar Maizito",
  "descripcion": null,
  "fecha_programada": "2026-09-10"
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

También admite `titulo`, `descripcion` y `fecha_programada`. `409` si
ya estaba completada.

### `DELETE /activities/{id}` → 204

---

## Perfil

### `GET /profile` → 200

```json
{
  "id": "uuid",
  "email": "ana@correo.com",
  "nombre": "Ana",
  "foto_url": null,
  "distrito": "Miraflores",
  "notificaciones": true,
  "plantas_registradas": 3,
  "created_at": "2026-09-01T10:00:00Z"
}
```

### `PATCH /profile` → 200

Admite `nombre`, `foto_url`, `distrito` y `notificaciones`.

### `GET /profile/districts` → 200

Lista de distritos admitidos. **Úsala para poblar el selector**: el
distrito se valida contra ella y filtra los puntos de venta de
insumos que devuelve el diagnóstico. Texto libre da `400`.

### `PUT /profile/password` → 204

```json
{ "password_actual": "clave12345", "password_nueva": "nueva12345" }
```

Se exige la contraseña actual a propósito: sin ella, un token robado
bastaría para tomar la cuenta. `401` si no es correcta.

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
| 409 | Conflicto de estado (ya completada, ya vinculada) |
| 413 | Imagen mayor a 10 MB |
| 415 | Formato de imagen no admitido |
| 422 | El cuerpo no cumple el esquema (validación de FastAPI) |

---

## Generar el cliente Dart

En lugar de escribir los modelos a mano, genéralos desde el contrato:

```bash
curl http://localhost:8000/openapi.json -o openapi.json
openapi-generator generate -i openapi.json -g dart-dio -o cliente/
```
