# routers/clientes.py
# Router de la API para el recurso Cliente (Req. 2, 3, 4).
#
# Expone el CRUD basico de clientes bajo el prefijo /api/clientes:
#   - GET    /api/clientes        -> lista todos los clientes.
#   - POST   /api/clientes        -> crea un cliente (201).
#   - GET    /api/clientes/{id}   -> obtiene un cliente (404 si no existe).
#   - PUT    /api/clientes/{id}   -> actualiza un cliente (404 si no existe).
#
# Las reglas de negocio (nombre/telefono obligatorios y no solo espacios, y las
# longitudes maximas) se validan reutilizando la capa de servicios pura
# (services.py) y se devuelven como 400 con un mensaje en espanol en `detail`.
# La validacion "de forma" de Pydantic (min/max_length en schemas.py) sigue
# aplicando y puede producir 422; ver la nota de decision mas abajo.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# get_db entrega una sesion de base de datos por peticion (database.py).
from database import get_db

# Modelo ORM Cliente (models.py).
from models import Cliente

# Esquemas Pydantic de request/response para Cliente (schemas.py).
from schemas import ClienteCrear, ClienteRespuesta

# Validaciones de negocio puras reutilizadas desde la capa de servicios.
from services import validar_campo_obligatorio, validar_longitud_maxima

# Dependencia de autenticacion: protege todos los endpoints (requiere sesion).
from auth_dependencies import get_current_user

# APIRouter con prefijo comun y etiqueta para la documentacion automatica.
# main.py incluira este router en la Tarea 10.
router = APIRouter(prefix="/api/clientes", tags=["clientes"])


# ---------------------------------------------------------------------------
# Validacion de negocio compartida entre POST y PUT
# ---------------------------------------------------------------------------
def _validar_cliente(datos: ClienteCrear) -> None:
    """Aplica las reglas de negocio de un Cliente y lanza 400 si alguna falla.

    Reutiliza la capa de servicios para:
      - nombre obligatorio (no vacio ni solo espacios)  -> Req. 2.2, 4.2.
      - telefono obligatorio (no vacio ni solo espacios) -> Req. 2.3.
      - longitudes maximas (nombre 100, telefono 20, direccion 200) -> Req. 2.4.

    Decision de diseno (design.md -> Error Handling): las reglas de negocio se
    devuelven como 400 con un mensaje descriptivo en `detail`. Pydantic ya
    rechaza por esquema (422) las longitudes al deserializar el request; esta
    validacion adicional garantiza el mensaje descriptivo en espanol exigido por
    el diseno (por ejemplo, cadenas compuestas SOLO por espacios, que Pydantic
    con min_length=1 no detecta porque tienen longitud > 0).
    """
    # Campos obligatorios: nombre y telefono no pueden ser vacios ni solo espacios.
    # Nota: el nombre de campo se pasa tal cual para construir el mensaje
    # "El {campo} es obligatorio." (usamos "Telefono"/"Nombre" con la forma del
    # design.md). El acento de "Telefono" no es critico para la logica.
    error = validar_campo_obligatorio(datos.nombre, "Nombre")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    error = validar_campo_obligatorio(datos.telefono, "Telefono")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Longitudes maximas por campo (Req. 2.4). direccion es opcional (puede None).
    error = validar_longitud_maxima(datos.nombre, 100, "Nombre")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    error = validar_longitud_maxima(datos.telefono, 20, "Telefono")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    error = validar_longitud_maxima(datos.direccion, 200, "Direccion")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


def _obtener_cliente_o_404(cliente_id: int, db: Session) -> Cliente:
    """Busca un cliente por id o lanza 404 con mensaje descriptivo (Req. 15.3, 16.1)."""
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El Cliente no existe.",
        )
    return cliente


# ---------------------------------------------------------------------------
# GET /api/clientes -> lista de clientes (Req. 3.1)
# ---------------------------------------------------------------------------
@router.get("", response_model=list[ClienteRespuesta])
def listar_clientes(
    db: Session = Depends(get_db), _usuario=Depends(get_current_user)
) -> list[Cliente]:
    """Devuelve todos los clientes. Si no hay ninguno, devuelve una lista vacia.

    El mensaje de "no hay clientes registrados" lo muestra el frontend (Req. 3.2).
    """
    return db.query(Cliente).all()


# ---------------------------------------------------------------------------
# POST /api/clientes -> crea un cliente (Req. 2.1, 2.6)
# ---------------------------------------------------------------------------
@router.post("", response_model=ClienteRespuesta, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    datos: ClienteCrear,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
) -> Cliente:
    """Crea un nuevo cliente y lo devuelve con su id asignado (201)."""
    # Validaciones de negocio antes de tocar la base de datos (Req. 2.2, 2.3, 2.4).
    _validar_cliente(datos)

    # Creamos el objeto ORM y lo persistimos.
    cliente = Cliente(
        nombre=datos.nombre,
        telefono=datos.telefono,
        direccion=datos.direccion,
    )
    db.add(cliente)
    db.commit()
    # refresh recarga el objeto desde la BD para obtener el id autogenerado.
    db.refresh(cliente)
    return cliente


# ---------------------------------------------------------------------------
# GET /api/clientes/{id} -> obtiene un cliente (404 si no existe)
# ---------------------------------------------------------------------------
@router.get("/{cliente_id}", response_model=ClienteRespuesta)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
) -> Cliente:
    """Devuelve un cliente por su id; responde 404 si no existe (Req. 15.3)."""
    return _obtener_cliente_o_404(cliente_id, db)


# ---------------------------------------------------------------------------
# PUT /api/clientes/{id} -> actualiza un cliente (Req. 4.1, 4.2, 4.3)
# ---------------------------------------------------------------------------
@router.put("/{cliente_id}", response_model=ClienteRespuesta)
def actualizar_cliente(
    cliente_id: int,
    datos: ClienteCrear,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
) -> Cliente:
    """Actualiza los datos de un cliente existente (200); 404 si no existe."""
    # Primero comprobamos que exista (404) antes de validar el cuerpo.
    cliente = _obtener_cliente_o_404(cliente_id, db)

    # Reglas de negocio: nombre/telefono obligatorios y longitudes (Req. 4.2, 2.4).
    _validar_cliente(datos)

    # Aplicamos los cambios y persistimos.
    cliente.nombre = datos.nombre
    cliente.telefono = datos.telefono
    cliente.direccion = datos.direccion
    db.commit()
    db.refresh(cliente)
    return cliente
