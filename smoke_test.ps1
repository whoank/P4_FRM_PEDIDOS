<#
.SYNOPSIS
    Prueba de humo (smoke test) del despliegue de "Control de Pedidos" con Docker Compose.

.DESCRIPTION
    Verificacion UNICA de infraestructura (no es una prueba de logica de negocio ni se
    automatiza con muchas iteraciones). Comprueba que, con la aplicacion ya levantada con
    'docker compose up --build', el sistema responde correctamente:

      1) El backend responde en http://localhost:8000
           - GET /api/health  -> 200 y {"status":"ok"}   (vida del servicio)
           - GET /api/clientes -> 200                     (confirma la conexion a la
             PostgreSQL del host de Windows via host.docker.internal:5432)
      2) El frontend responde en http://localhost:3000    (200)

    Este script es idempotente y NO destructivo: solo hace peticiones HTTP de lectura.
    No arranca ni detiene contenedores; nunca modifica datos.

.PREREQUISITOS
    - Docker Desktop en Windows en ejecucion.
    - El servicio PostgreSQL del host de Windows corriendo, con la base creada y las
      credenciales configuradas en el archivo .env (DATABASE_URL).
    - La aplicacion levantada previamente en OTRA terminal desde la raiz del proyecto:
          docker compose up --build
      (Opcional) Verifica que ambos servicios esten "running" con:  docker compose ps

.USO
    Desde la raiz del proyecto, en PowerShell:
        ./smoke_test.ps1
    Parametros opcionales:
        ./smoke_test.ps1 -BackendUrl http://localhost:8000 -FrontendUrl http://localhost:3000

.SALIDA
    Codigo de salida 0 si TODAS las comprobaciones pasan; 1 si alguna falla.
#>

[CmdletBinding()]
param(
    # URL base del backend (puerto publicado por el contenedor backend).
    [string]$BackendUrl = "http://localhost:8000",
    # URL del frontend (puerto publicado por el contenedor frontend).
    [string]$FrontendUrl = "http://localhost:3000",
    # Tiempo maximo de espera por peticion (segundos).
    [int]$TimeoutSeg = 10
)

# Detener ante errores no controlados para que el codigo de salida sea fiable.
$ErrorActionPreference = "Stop"

# Contadores de resultado.
$total = 0
$fallos = 0

function Escribir-Encabezado {
    Write-Host ""
    Write-Host "=== Prueba de humo: Control de Pedidos (Docker Compose) ===" -ForegroundColor Cyan
    Write-Host "Verificacion UNICA de infraestructura. No modifica datos." -ForegroundColor DarkGray
    Write-Host "Backend : $BackendUrl" -ForegroundColor DarkGray
    Write-Host "Frontend: $FrontendUrl" -ForegroundColor DarkGray
    Write-Host ""
}

# Realiza una peticion HTTP GET y valida el codigo de estado esperado.
# Devuelve $true si OK, $false si FALLO. Escribe un mensaje claro en espanol.
function Probar-Http {
    param(
        [string]$Descripcion,   # Que estamos comprobando (texto para el usuario).
        [string]$Url,           # URL a solicitar.
        [int]$EstadoEsperado = 200
    )

    $script:total++
    try {
        # -UseBasicParsing evita depender del motor de Internet Explorer en Windows.
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeg
        if ($resp.StatusCode -eq $EstadoEsperado) {
            Write-Host ("[OK]    {0} -> {1} {2}" -f $Descripcion, $resp.StatusCode, $Url) -ForegroundColor Green
            return $true
        }
        else {
            Write-Host ("[FALLO] {0} -> se esperaba {1} pero se recibio {2} ({3})" -f `
                $Descripcion, $EstadoEsperado, $resp.StatusCode, $Url) -ForegroundColor Red
            $script:fallos++
            return $false
        }
    }
    catch {
        # Casos tipicos: contenedor no arrancado, puerto no publicado, backend sin
        # conexion a PostgreSQL del host, o el servicio aun iniciando.
        Write-Host ("[FALLO] {0} -> no se pudo conectar con {1}" -f $Descripcion, $Url) -ForegroundColor Red
        Write-Host ("        Detalle: {0}" -f $_.Exception.Message) -ForegroundColor DarkYellow
        $script:fallos++
        return $false
    }
}

Escribir-Encabezado

Write-Host "Recordatorio: la aplicacion debe estar levantada ('docker compose up --build')" -ForegroundColor Yellow
Write-Host "y el servicio PostgreSQL del host de Windows debe estar corriendo." -ForegroundColor Yellow
Write-Host ""

# 1) Backend vivo: GET /api/health -> 200 {"status":"ok"}
Probar-Http -Descripcion "Backend vivo (GET /api/health)" -Url ("{0}/api/health" -f $BackendUrl) | Out-Null

# 2) Backend + PostgreSQL del host: GET /api/clientes -> 200
#    Que este endpoint responda 200 confirma que el backend se conecto a la
#    PostgreSQL del host via host.docker.internal:5432.
Probar-Http -Descripcion "Backend conectado a PostgreSQL del host (GET /api/clientes)" -Url ("{0}/api/clientes" -f $BackendUrl) | Out-Null

# 3) Frontend responde: GET / -> 200
Probar-Http -Descripcion "Frontend responde (GET /)" -Url $FrontendUrl | Out-Null

# --- Resumen final ---------------------------------------------------------
Write-Host ""
Write-Host "=== Resumen ===" -ForegroundColor Cyan
$exitos = $total - $fallos
Write-Host ("Comprobaciones: {0}   Exitos: {1}   Fallos: {2}" -f $total, $exitos, $fallos)

if ($fallos -eq 0) {
    Write-Host "RESULTADO: OK - el despliegue responde correctamente." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "RESULTADO: FALLO - revisa que los contenedores esten 'running' (docker compose ps)," -ForegroundColor Red
    Write-Host "que el servicio PostgreSQL del host este corriendo y que .env (DATABASE_URL) sea correcto." -ForegroundColor Red
    exit 1
}
