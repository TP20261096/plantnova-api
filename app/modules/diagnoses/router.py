from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.security import CurrentUser, get_current_user
from app.modules.diagnoses import service
from app.modules.diagnoses.schemas import DiagnosticoOut, VincularRequest

router = APIRouter(tags=["Captura"])


@router.post(
    "/diagnose",
    response_model=DiagnosticoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Analiza una imagen y registra el diagnóstico",
)
def diagnosticar(
    imagen: UploadFile = File(
        description="Foto de la hoja en JPEG, PNG o WEBP"
    ),
    plant_id: str | None = Form(
        default=None,
        description="Opcional. Vincula el diagnóstico desde el inicio",
    ),
    usuario: CurrentUser = Depends(get_current_user),
) -> DiagnosticoOut:
    
    contenido = imagen.file.read()
    plant_id = plant_id.strip() if plant_id else None
    return service.diagnosticar(
        usuario, contenido, imagen.content_type, plant_id or None
    )


@router.patch(
    "/diagnoses/{diagnostico_id}/link",
    response_model=DiagnosticoOut,
    summary="Vincula un diagnóstico a una planta",
)
def vincular(
    diagnostico_id: str,
    datos: VincularRequest,
    usuario: CurrentUser = Depends(get_current_user),
) -> DiagnosticoOut:
    
    return service.vincular(usuario, diagnostico_id, datos.plant_id)


@router.get(
    "/diagnoses/{diagnostico_id}",
    response_model=DiagnosticoOut,
    summary="Consulta un diagnóstico ya registrado",
)
def detalle(
    diagnostico_id: str,
    usuario: CurrentUser = Depends(get_current_user),
) -> DiagnosticoOut:
    #Devuelve el diagnóstico con enlaces de imagen vigentes.
    return service.obtener_diagnostico(usuario, diagnostico_id)