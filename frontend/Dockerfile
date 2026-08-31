# Dockerfile del frontend (SPA de React con Vite).
#
# Decision de diseno (proyecto educativo):
# El diseno indica que, en desarrollo, el contenedor frontend PUEDE usar el
# servidor de Vite para servir la SPA (ver design.md, "Estrategia de
# contenedorizacion y despliegue local (Docker)"). Por simplicidad educativa
# usamos directamente el servidor de desarrollo de Vite en lugar de hacer un
# "build" y servir los archivos estaticos con un servidor aparte.
# Para un despliegue de PRODUCCION real lo recomendable seria:
#   RUN npm run build   ->   servir /app/dist con un servidor estatico (p. ej. nginx).
# Pero para este proyecto el dev server es suficiente y coherente con el diseno.

# Imagen base Node.js 20 (segun design.md).
FROM node:20

# Directorio de trabajo dentro del contenedor.
WORKDIR /app

# 1) Copiar SOLO los manifiestos de dependencias primero.
#    Esto aprovecha la cache de capas de Docker: si package.json (o el lockfile)
#    no cambian, Docker reutiliza la capa de "npm install" y no reinstala todo
#    en cada build.
#    El comodin package-lock.json* hace que la copia funcione tanto si existe
#    el lockfile como si no (para robustez, ya que puede no existir).
COPY package.json package-lock.json* ./

# 2) Instalar dependencias.
#    Usamos "npm install" en lugar de "npm ci" porque el proyecto puede no
#    incluir un package-lock.json; npm install es mas robusto ante esa situacion.
RUN npm install

# 3) Copiar el resto del codigo fuente del frontend.
#    Se hace despues del install para no invalidar la cache de dependencias
#    cuando solo cambia el codigo de la aplicacion.
COPY . .

# El servidor de Vite escucha en el puerto 3000 (configurado en vite.config.js).
EXPOSE 3000

# Comando de arranque: servidor de desarrollo de Vite.
# vite.config.js ya define host: true y port: 3000, pero pasamos
# "--host 0.0.0.0" de forma explicita para garantizar que Vite escuche en
# todas las interfaces de red del contenedor y sea accesible desde el host
# a traves del puerto publicado (3000:3000 en docker-compose).
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
