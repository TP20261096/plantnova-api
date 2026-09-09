import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.core.supabase import service_client

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

Dificultad = Literal["Facil", "Media", "Dificil"]
EstadoDiagnostico = Literal["Sana", "Enferma", "Plagada"]
Urgencia = Literal["Baja", "Media", "Alta"]
Seccion = Literal[
    "Preparacion", "Siembra", "Cuidados", "Cosecha", "Consejos"
]


# ---------------------------------------------------------------------
# Modelos de validación
# ---------------------------------------------------------------------
class SpeciesIn(BaseModel):
    """Una especie del módulo Guía."""

    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    nombre_comun: str
    nombre_cientifico: str | None = None
    familia: str | None = None
    imagen_url: str | None = None
    resumen: str
    dificultad: Dificultad
    luz_recomendada: str | None = None
    riego_base_dias: int = Field(ge=1, le=30)
    diagnosticable: bool = False
    secciones: dict[Seccion, str]


class RecetaIn(BaseModel):
    """Un remedio casero."""

    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    nombre: str
    descripcion: str | None = None
    ingredientes: list[dict] = []
    preparacion: list[str] = []
    modo_uso: str | None = None
    precauciones: str | None = None
    costo_aprox: str | None = None


class TratamientoIn(BaseModel):
    """Vínculo entre una enfermedad y una receta."""

    receta_slug: str
    frecuencia_dias: int = Field(default=7, ge=1, le=30)
    num_aplicaciones: int = Field(default=3, ge=1, le=10)
    nota: str | None = None
    
    @model_validator(mode="before")
    @classmethod
    def _aplicar_defectos(cls, datos: dict) -> dict:
        """Descarta las claves nulas para que actúe el valor por defecto.

        Args:
            datos: Registro tal como viene del archivo JSON.

        Returns:
            El mismo registro sin las claves cuyo valor era null.
        """
        if not isinstance(datos, dict):
            return datos
        return {k: v for k, v in datos.items() if v is not None}


class DiseaseIn(BaseModel):
    """Una de las 36 clases que emite el modelo."""

    clase_raw: str
    species_slug: str | None = None
    nombre_enfermedad: str
    nombre_cientifico: str | None = None
    estado: EstadoDiagnostico
    urgencia: Urgencia = "Media"
    descripcion: str | None = None
    sintomas: str | None = None
    causas: str | None = None
    prevencion: str | None = None
    riego_frecuencia_dias: int | None = Field(default=None, ge=1, le=30)
    riego_nota: str | None = None
    otros_cuidados: str | None = None
    insumos_no_caseros: list[dict] = []
    tratamientos: list[TratamientoIn] = []


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def _leer(nombre: str, modelo: type[BaseModel]) -> list:
    """Lee y valida un archivo JSON del directorio data.

    Args:
        nombre: Nombre del archivo, sin ruta.
        modelo: Clase Pydantic contra la que se valida cada elemento.

    Returns:
        Lista de instancias validadas.

    Raises:
        SystemExit: Si el archivo no existe o algún registro es
            inválido. Se aborta antes de escribir en la base para no
            dejarla a medias.
    """
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        sys.exit(f"No se encontró {ruta}")

    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    validados = []
    for i, item in enumerate(crudo):
        try:
            validados.append(modelo(**item))
        except ValidationError as exc:
            sys.exit(f"Error en {nombre}, registro {i}:\n{exc}")

    print(f"  {nombre}: {len(validados)} registros válidos")
    return validados


def _mapa_slug(tabla: str, columna: str = "slug") -> dict[str, str]:
    """Construye un índice clave natural a UUID.

    Args:
        tabla: Nombre de la tabla a consultar.
        columna: Columna que actúa como clave natural.

    Returns:
        Diccionario de clave natural a id.
    """
    filas = service_client().table(tabla).select(f"id,{columna}").execute()
    return {fila[columna]: fila["id"] for fila in filas.data}


# ---------------------------------------------------------------------
# Cargas
# ---------------------------------------------------------------------
def cargar_species() -> None:
    """Inserta o actualiza especies y sus secciones de guía."""
    especies = _leer("species.json", SpeciesIn)
    cliente = service_client()

    cliente.table("species").upsert(
        [e.model_dump(exclude={"secciones"}) for e in especies],
        on_conflict="slug",
    ).execute()

    ids = _mapa_slug("species")
    secciones = [
        {
            "species_id": ids[e.slug],
            "seccion": seccion,
            "contenido": contenido,
        }
        for e in especies
        for seccion, contenido in e.secciones.items()
    ]
    cliente.table("species_sections").upsert(
        secciones, on_conflict="species_id,seccion"
    ).execute()
    print(f"  species: {len(especies)} | secciones: {len(secciones)}")


def cargar_recetas() -> None:
    """Inserta o actualiza los remedios caseros."""
    recetas = _leer("recetas.json", RecetaIn)
    service_client().table("recetas").upsert(
        [r.model_dump() for r in recetas], on_conflict="slug"
    ).execute()
    print(f"  recetas: {len(recetas)}")


def cargar_diseases() -> None:
    """Inserta las clases del modelo y sus tratamientos asociados."""
    enfermedades = _leer("diseases.json", DiseaseIn)
    cliente = service_client()
    especies = _mapa_slug("species")
    recetas = _mapa_slug("recetas")

    faltantes = {
        d.species_slug
        for d in enfermedades
        if d.species_slug and d.species_slug not in especies
    }
    if faltantes:
        sys.exit(f"species_slug inexistentes en species.json: {faltantes}")

    filas = []
    for d in enfermedades:
        fila = d.model_dump(exclude={"tratamientos", "species_slug"})
        fila["species_id"] = especies.get(d.species_slug or "")
        filas.append(fila)

    cliente.table("disease_catalog").upsert(
        filas, on_conflict="clase_raw"
    ).execute()

    enfermedades_id = _mapa_slug("disease_catalog", "clase_raw")
    vinculos = []
    for d in enfermedades:
        for t in d.tratamientos:
            if t.receta_slug not in recetas:
                sys.exit(
                    f"{d.clase_raw} referencia la receta inexistente "
                    f"'{t.receta_slug}'"
                )
            vinculos.append(
                {
                    "disease_id": enfermedades_id[d.clase_raw],
                    "receta_id": recetas[t.receta_slug],
                    "frecuencia_dias": t.frecuencia_dias,
                    "num_aplicaciones": t.num_aplicaciones,
                    "nota": t.nota,
                }
            )

    if vinculos:
        cliente.table("disease_treatments").upsert(
            vinculos, on_conflict="disease_id,receta_id"
        ).execute()
    print(f"  disease_catalog: {len(filas)} | tratamientos: {len(vinculos)}")


CARGAS = {
    "species": cargar_species,
    "recetas": cargar_recetas,
    "diseases": cargar_diseases,
}


def main() -> None:
    """Ejecuta las cargas respetando el orden de dependencias."""
    objetivos = sys.argv[1:] or list(CARGAS)
    for nombre in objetivos:
        if nombre not in CARGAS:
            sys.exit(f"Dominio desconocido: {nombre}")
        print(f"Cargando {nombre}...")
        CARGAS[nombre]()
    print("Listo.")


if __name__ == "__main__":
    main()