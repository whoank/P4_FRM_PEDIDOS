# auth_config.py
# Configuracion del modulo de autenticacion por sesion (cookie), leida desde
# variables de entorno con valores por defecto seguros para desarrollo local.
#
# Este modulo NO depende de la base de datos ni de FastAPI: solo lee el entorno
# y expone constantes/settings reutilizables por auth_service, auth_dependencies
# y el router de auth. Asi se evita duplicar la lectura de env en varios sitios.
#
# Nota: los defaults estan pensados para desarrollo local por HTTP (COOKIE_SECURE
# en False). En un despliegue real por HTTPS conviene poner COOKIE_SECURE=true
# mediante la variable de entorno correspondiente.

import os


def _leer_bool(nombre: str, defecto: bool) -> bool:
    """Lee una variable de entorno booleana desde una cadena "true"/"false".

    Acepta (sin distinguir mayusculas) "true", "1", "yes", "si" como verdadero.
    Cualquier otro valor se interpreta como falso. Si la variable no existe,
    devuelve el valor por defecto indicado.
    """
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ("true", "1", "yes", "si")


# --- Constantes de configuracion -------------------------------------------

# Minutos de vida de una sesion antes de expirar. Por defecto 480 (8 horas),
# suficiente para una jornada de trabajo.
SESSION_EXPIRATION_MINUTES: int = int(os.getenv("SESSION_EXPIRATION_MINUTES", "480"))

# Marca la cookie como Secure (solo se envia por HTTPS). En desarrollo local
# por HTTP debe ser False; en produccion por HTTPS conviene ponerla en True.
COOKIE_SECURE: bool = _leer_bool("COOKIE_SECURE", False)

# Nombre de la cookie de sesion que se guarda en el navegador.
COOKIE_NAME: str = os.getenv("COOKIE_NAME", "cp_session")

# Politica SameSite de la cookie. Se fija en "lax": suficiente para un frontend
# y un backend en el mismo host (localhost) y razonable frente a CSRF basico.
COOKIE_SAMESITE: str = "lax"
