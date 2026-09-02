# routers/productos.py
# Router de la API para el recurso Producto (Req. 5, 6, 7).
#
# Expone el CRUD basico de productos bajo el prefijo /api/productos:
#   - GET    /api/productos                    -> lista productos.
#         Acepta ?solo_disponibles=true para filtrar y devolver solo los
#         productos con disponible == True (para el selector de pedidos, Req. 7.3).
#   - POST   /api/productos                    -> crea un producto (201).
#         disponible por defecto True si no se envia (Req. 5.5; el default ya
#         viene de schemas.ProductoCrear).
#   - GET    /api/productos/{id}               -> obtiene un producto (404 si no existe).
#   - PUT    /api/productos/{id}               -> actualiza un producto (404 si no existe).
#
# Las reglas de negocio (nombre obligatorio y no solo espacios; longitud maxima;
# rango del precio) se validan reutilizando la capa de servicios pura
# (services.py) y se devuelven como 400 con un mensaje en espanol en `detail`
# (Req. 15.3, 16.1). La validacion "de forma" de Pydantic (min/max_length,
# rango y tipo numerico del precio en schemas.py) sigue aplicando y puede
# producir 422 (por ejemplo, precio no numerico -> Req. 5.4).

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# get_db entrega una sesion de base de datos por peticion (database.py).
from database import get_db

# Modelo ORM Producto (models.py).
from models import Producto

# Esquemas Pydantic de request/response para Producto (schemas.py).
from schemas import ProductoCrear, ProductoRespuesta

# Validaciones de negocio puras reutilizadas desde la capa de servicios.
from services import (
    validar_campo_obligatorio,
    validar_longitud_maxima,
    validar_precio,
)

# Dependencia de autorizacion: protege todos los endpoints exigiendo el permiso
# "PRODUCTOS" (require_permission valida sesion 401 + 403 si falta el permiso).
from auth_dependencies import require_permission

# APIRouter con prefijo comun y etiqueta para la documentacion automatica.
# main.py incluira este router en la Tarea 10.
router = APIRouter(prefix="/api/productos", tags=["productos"])


# ---------------------------------------------------------------------------
# Validacion de negocio compartida entre POST y PUT
# ---------------------------------------------------------------------------
def _validar_producto(datos: ProductoCrear) -> None:
    """Aplica las reglas de negocio de un Producto y lanza 400 si alguna falla.

    Reutiliza la capa de servicios para:
      - nombre obligatorio (no vacio ni solo espacios)  -> Req. 5.2, 7.1.
      - longitud maxima del nombre (100 caracteres)     -> Req. 5.2.
      - rango del precio (0..999999.99)                 -> Req. 5.3, 7.2.

    Decision de diseno (design.md -> Error Handling): las reglas de negocio se
    devuelven como 400 con un mensaje descriptivo en `detail`. Pydantic ya
    rechaza por esquema (422) longitudes, rangos y el tipo numerico del precio
    al deserializar el request; esta validacion adicional garantiza el mensaje
    descriptivo en espanol y cubre casos que Pydantic no detecta (por ejemplo,
    un nombre compuesto SOLO por espacios, que con min_length=1 tiene longitud > 0).
    """
    # Nombre obligatorio: no vacio ni solo espacios (Req. 5.2).
    error = validar_campo_obligatorio(datos.nombre, "Nombre")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Longitud maxima del nombre (100 caracteres) (Req. 5.2).
    error = validar_longitud_maxima(datos.nombre, 100, "Nombre")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Rango del precio (0..999999.99) (Req. 5.3, 7.2). El mensaje es exactamente
    # el exigido por el design.md ("Contratos de API -> Productos").
    error = validar_precio(datos.precio)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


def _obtener_producto_o_404(producto_id: int, db: Session) -> Producto:
    """Busca un producto por id o lanza 404 con mensaje descriptivo (Req. 15.3, 16.1)."""
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El Producto no existe.",
        )
    return producto


# ---------------------------------------------------------------------------
# GET /api/productos -> lista de productos (Req. 6.1, 7.3)
# ---------------------------------------------------------------------------
@router.get("", response_model=list[ProductoRespuesta])
def listar_productos(
    solo_disponibles: bool = False,
    db: Session = Depends(get_db),
    _usuario=Depends(require_permission("PRODUCTOS")),
) -> list[Producto]:
    """Devuelve la lista de productos.

    Si `solo_disponibles` es True, filtra y devuelve unicamente los productos
    con disponible == True. Esto lo usa el selector de productos al crear
    pedidos, que solo debe ofrecer productos disponibles (Req. 7.3).

    Si no hay productos, devuelve una lista vacia; el mensaje de "no hay
    productos registrados" lo muestra el frontend (Req. 6.2).
    """
    consulta = db.query(Producto)
    if solo_disponibles:
        consulta = consulta.filter(Producto.disponible.is_(True))
    return consulta.all()


# ---------------------------------------------------------------------------
# POST /api/productos -> crea un producto (Req. 5.1, 5.5, 5.6)
# ---------------------------------------------------------------------------
@router.post("", response_model=ProductoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_producto(
    datos: ProductoCrear,
    db: Session = Depends(get_db),
    _usuario=Depends(require_permission("PRODUCTOS")),
) -> Producto:
    """Crea un nuevo producto y lo devuelve con su id asignado (201).

    `disponible` es True por defecto cuando el request no lo incluye, gracias al
    valor predeterminado del esquema ProductoCrear (Req. 5.5).
    """
    # Validaciones de negocio antes de tocar la base de datos (Req. 5.2, 5.3).
    _validar_producto(datos)

    # Creamos el objeto ORM y lo persistimos.
    producto = Producto(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        precio=datos.precio,
        disponible=datos.disponible,
    )
    db.add(producto)
    db.commit()
    # refresh recarga el objeto desde la BD para obtener el id autogenerado.
    db.refresh(producto)
    return producto


# ---------------------------------------------------------------------------
# GET /api/productos/{id} -> obtiene un producto (404 si no existe)
# ---------------------------------------------------------------------------
@router.get("/{producto_id}", response_model=ProductoRespuesta)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_permission("PRODUCTOS")),
) -> Producto:
    """Devuelve un producto por su id; responde 404 si no existe (Req. 15.3)."""
    return _obtener_producto_o_404(producto_id, db)


# ---------------------------------------------------------------------------
# PUT /api/productos/{id} -> actualiza un producto (Req. 7.1, 7.2)
# ---------------------------------------------------------------------------
@router.put("/{producto_id}", response_model=ProductoRespuesta)
def actualizar_producto(
    producto_id: int,
    datos: ProductoCrear,
    db: Session = Depends(get_db),
    _usuario=Depends(require_permission("PRODUCTOS")),
) -> Producto:
    """Actualiza los datos de un producto existente (200); 404 si no existe.

    Valida nombre y precio con la capa de servicios; un precio fuera de rango se
    rechaza con 400 (Req. 7.2).
    """
    # Primero comprobamos que exista (404) antes de validar el cuerpo.
    producto = _obtener_producto_o_404(producto_id, db)

    # Reglas de negocio: nombre obligatorio/longitud y rango de precio (Req. 7.1, 7.2).
    _validar_producto(datos)

    # Aplicamos los cambios y persistimos.
    producto.nombre = datos.nombre
    producto.descripcion = datos.descripcion
    producto.precio = datos.precio
    producto.disponible = datos.disponible
    db.commit()
    db.refresh(producto)
    return producto
