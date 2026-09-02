# Análisis LiDAR 2024 — Montevideo

Procedimiento y resultados de dos análisis hechos a partir del vuelo LiDAR
2024 de Montevideo: (1) qué tipos de superficie identifica la nube de
puntos según su clasificación ASPRS, y (2) cuánto creció la ciudad en
altura entre 2019 y 2024, comparando los edificios detectados por el
LiDAR 2024 contra el Modelo de Superficie (MDS) 2019.

Este repositorio documenta los **Bloques 7 a 10** de ese procedimiento.
El código hace referencia en varios comentarios a "Bloques 1-5" y
"Bloque 6" anteriores (una comparación DTM 2017 vs LiDAR 2024, y un
trabajo preliminar sobre las hojas LiDAR de la carpeta `Basurero`): esos
bloques son el antecedente de este trabajo pero no forman parte de esta
versión del repositorio.

## Qué hace cada bloque

### Bloque 7 — Clasificación de superficies del LiDAR
`scripts/bloque_07_clasificacion_lidar.py`

Cada punto de una nube LiDAR trae un campo `classification`: un código
numérico (0-255, estándar ASPRS para LAS) que indica qué tipo de
superficie representa ese punto — terreno, vegetación, agua, edificio,
etc. Ese código no lo calcula este script ni ArcGIS al abrir el archivo:
viene asignado desde que el proveedor procesó el vuelo (con LAStools,
TerraScan u otro software equivalente).

El script recorre todos los `.laz`/`.las` de una carpeta (por defecto,
las hojas de la zona `Basurero`), leyendo cada archivo **por bloques**
(chunks de 5 millones de puntos) para no cargar la nube entera en
memoria, y cuenta cuántos puntos hay de cada código. Como salida
imprime una tabla con la cantidad y el porcentaje de puntos por tipo de
superficie, más un desglose por archivo del porcentaje clasificado como
terreno.

Es relevante para el resto del análisis por dos motivos: el código 2
(terreno) es el que alimenta el DTM de los Bloques 1-5, así que su
proporción da una idea directa de cuántos puntos sostienen esa
superficie; y el código 9 (agua) importa en zonas de humedal, porque el
láser no siempre devuelve un retorno confiable sobre agua y esos puntos
tienden a faltar o quedar mal definidos en el DTM.

### Bloque 8 — Raster de edificios 2024 (2.5 m)
`scripts/bloque_08_raster_edificios_2024.py`

Filtra los puntos clasificados como edificio (código ASPRS 6) en todos
los `.laz`/`.las` de una carpeta, y los convierte en un raster de 2.5 m
tomando el valor Z más alto de cada celda. Es el equivalente en Python a
correr "LAS Dataset To Raster" en ArcGIS con Interpolation Type =
Binning, Cell Assignment Type = Maximum, filtrado a la clase Building.

La grilla de salida cubre la extensión combinada de **todos** los
archivos de entrada, y el máximo por celda se acumula a través de todos
ellos (no archivo por archivo), para que un edificio que cruce el borde
entre dos tiles quede bien representado. El resultado se guarda como
GeoTIFF en `EPSG:5382` (SIRGAS-ROU98 / UTM zona 21S — ver referencia al
final).

### Bloque 9 — Mosaico del MDS 2019, ya a 2.5 m
`scripts/bloque_09_mosaico_mds_2019.py`

Arma un único mosaico a 2.5 m a partir de las hojas del Modelo de
Superficie 2019. La versión anterior de este bloque mosaicaba las hojas
a su resolución nativa (10 cm, no 2.5 m como se había asumido) y recién
después pensaba remuestrear: con hojas de 1×1 km a 10 cm (10.000 ×
10.000 píxeles cada una), 28 hojas mosaicadas a resolución nativa arman
un raster de más de 2.700 millones de píxeles (~11 GB en memoria), de
ahí una demora de más de media hora.

Esta versión remuestrea **cada hoja a 2.5 m primero** (achicándola
~625 veces) con `Resampling.max` — el valor más alto entre los ~625
píxeles de 10 cm que caen en cada celda de 2.5 m, igual que en el
raster de edificios del Bloque 8 — y recién después mosaica las hojas
ya chicas, así nunca se llega a construir el raster gigante a 10 cm.
`Resampling.max` no funciona dentro de `rasterio.merge` (solo sirve
para operaciones de warp, no de lectura directa): por eso el
remuestreo se hace hoja por hoja con `rasterio.warp.reproject`, y
`merge()` se usa solo al final para unir las hojas ya achicadas.

El script también excluye automáticamente su propio archivo de salida
de la lista de hojas de entrada, por si se lo vuelve a correr sobre la
misma carpeta.

### Bloque 10 — Alinear y calcular la diferencia
`scripts/bloque_10_diferencia_alturas.py`

Remuestrea el mosaico MDS 2019 (Bloque 9) para que caiga exactamente
sobre la grilla del raster de edificios 2024 (Bloque 8), usando
`Resampling.bilinear`, y calcula la diferencia `2024 − 2019`.

La diferencia queda **restringida a donde el LiDAR 2024 detectó un
edificio** (fuera de ahí es NoData), por diseño: esto capta
construcción nueva y edificios que crecieron, pero no demoliciones ni
edificios que bajaron de altura, porque el MDS 2019 no viene
clasificado y no se puede restringir de la misma forma del otro lado.
El script valida que el MDS 2019 realmente esté a ~2.5 m antes de
seguir (si detecta que quedó a resolución nativa, corta con un error
explicando qué revisar).

## Estructura del repositorio

```
.
├── README.md
├── requirements.txt
├── .gitignore
├── .gitattributes          # Git LFS para resultados/rasters/*.tif
├── LICENSE
├── configurar_repo.ps1     # helper de PowerShell para publicar en GitHub
├── scripts/
│   ├── bloque_07_clasificacion_lidar.py
│   ├── bloque_08_raster_edificios_2024.py
│   ├── bloque_09_mosaico_mds_2019.py
│   └── bloque_10_diferencia_alturas.py
└── resultados/
    └── rasters/
        ├── README.md        # qué archivo va acá y por qué
        └── (acá copiás los .tif reales luego de correr los scripts)
```

## Requisitos

- Python 3.9 o superior
- Paquetes (ver `requirements.txt`):

```
pip install -r requirements.txt
```

`lazrs` es el backend que usa `laspy` para leer/escribir `.laz`
comprimidos. En Windows, el paquete `rasterio` instala su propia copia
de GDAL, así que no hace falta instalar GDAL por separado.

## Cómo correr el procedimiento

**Si ya tenés generados los tres `.tif` de resultados** (como es el caso
después de haber corrido esto una vez), no hace falta volver a correr
ningún script: andá directo a la sección "Resultados" más abajo y
copiá esos archivos a `resultados/rasters/`. Esta sección es para
reproducir el procedimiento de cero.

Los cuatro scripts están pensados para correrse en orden (7 → 8 → 9 →
10), porque cada uno depende de la salida del anterior. Los Bloques 8,
9 y 10 incluyen una guarda al principio (agregada en este repositorio,
no estaba en el original que se corrió la primera vez): si el archivo
de salida de ese bloque ya existe, el script avisa y corta ahí, sin
reprocesar nada. Por eso, aunque los corras de nuevo sin querer (por
ejemplo, al ejecutar todo el notebook de punta a punta), no vuelven a
releer los `.laz` ni las hojas de 10 cm si el resultado ya está.
Cada bloque tiene arriba una variable `FORZAR_RECALCULO` (en `False`
por defecto) para forzar el recálculo si de verdad cambiaste los datos
de entrada.

1. `python scripts/bloque_07_clasificacion_lidar.py` — lee los `.laz`/`.las`
   crudos y cuenta puntos por clasificación. Independiente de los demás
   bloques (no genera ni usa ninguno de los tres `.tif` de resultados,
   así que no tiene guarda de "ya existe": siempre corre).
2. `python scripts/bloque_08_raster_edificios_2024.py` — si no existe
   `edificios_lidar_2024_2_5m.tif`, lee los `.laz`/`.las` crudos de cero
   y lo genera. Es el paso lento del procedimiento (relee toda la nube
   de puntos), asique conviene dejar que la guarda lo salte cuando ya
   está hecho.
3. `python scripts/bloque_09_mosaico_mds_2019.py` — si no existe
   `mds_2019_mosaico.tif`, lee las hojas `.tif` originales (10 cm) de
   cero y arma el mosaico. También es lento.
4. `python scripts/bloque_10_diferencia_alturas.py` — si no existe
   `diferencia_edificios_2024_menos_mds_2019.tif`, toma los dos rasters
   anteriores ya generados (`edificios_lidar_2024_2_5m.tif` y
   `mds_2019_mosaico.tif`) y calcula la diferencia entre ambos. Esta
   cuenta es rápida (resta dos rasters ya achicados a 2.5 m, no relee
   nubes de puntos ni hojas de 10 cm), pero igual respeta la guarda.

**Importante:** las rutas de entrada/salida de cada script (sección
"PARÁMETROS" o "RUTAS" al principio de cada archivo) están tal cual se
usaron originalmente, apuntando a carpetas en `D:\LiDAR\...` de la PC
donde se corrió el procedimiento la primera vez. Antes de correrlos en
otra máquina, editá esas rutas para que apunten a donde tengas tus
propios datos.

## Resultados

Los tres `.tif` finales van en `resultados/rasters/` (ver el README de
esa carpeta para el detalle de cada archivo). No vienen incluidos en la
versión inicial de este repositorio porque se generan localmente al
correr los scripts — la sección "Publicar el repositorio en GitHub"
más abajo explica cómo agregarlos.

Si ya los generaste antes (por ejemplo, ya tenés en tu carpeta local
`edificios_lidar_2024_2_5m.tif`, `mds_2019_mosaico.tif` y
`diferencia_edificios_2024_menos_mds_2019.tif`), simplemente copialos a
`resultados/rasters/` tal cual están — no hace falta recalcular nada.

## Referencia: códigos de clasificación ASPRS (LAS 1.4)

Tabla usada por el Bloque 7 para traducir cada código numérico a un
nombre de superficie:

| Código | Superficie |
|---|---|
| 0 | Nunca clasificado |
| 1 | Sin asignar |
| 2 | Terreno (ground) |
| 3 | Vegetación baja (<0.5 m) |
| 4 | Vegetación media (0.5-2 m) |
| 5 | Vegetación alta (>2 m) |
| 6 | Edificio |
| 7 | Punto bajo (ruido) |
| 8 | Reservado / model key (según versión de LAS) |
| 9 | Agua |
| 10 | Riel (vía férrea) |
| 11 | Superficie de ruta/carretera |
| 12 | Reservado / overlap (según versión de LAS) |
| 13 | Cable - guardia |
| 14 | Cable - conductor |
| 15 | Torre de transmisión |
| 16 | Conector de cable (aislador) |
| 17 | Tablero de puente |
| 18 | Ruido alto |
| 19 | Maquinaria elevada / cinta transportadora |
| 20 | Terreno ignorado |
| 21 | Nieve |
| 22 | Exclusión temporal |
| 64-255 | Definido por el usuario/proveedor (fuera del estándar ASPRS) |
| resto | Reservado (sin uso estándar todavía) |

## Limitaciones y cosas para revisar

- La diferencia del Bloque 10 es **asimétrica a propósito**: solo existe
  donde el LiDAR 2024 detectó edificio, así que capta crecimiento y
  construcción nueva, pero no demoliciones ni edificios que bajaron de
  altura.
- Antes de confiar en los valores de la diferencia, conviene revisarla
  sobre 2-3 edificios grandes que se sepa que **no** cambiaron entre
  2019 y 2024, para descartar un corrimiento de datum vertical entre
  ambos relevamientos.
- Valores negativos en la diferencia deberían ser raros con el criterio
  de NoData actual — si aparecen muchos, es señal de revisar la
  hipótesis de que el terreno no cambió entre 2019 y 2024 en esa zona.
- En zonas de humedal, el porcentaje de puntos clasificados como agua
  (código 9, Bloque 7) es un indicador de qué tan confiable es el
  terreno derivado ahí: el láser no siempre devuelve un retorno
  confiable sobre agua.

## Publicar el repositorio en GitHub (Windows)

El repositorio todavía no existe en GitHub. Pasos para crearlo como
**público** (para que cualquiera pueda entrar a verlo) y subir este
contenido desde Windows:

### 1. Instalar herramientas (una sola vez)

- [Git para Windows](https://git-scm.com/download/win)
- [Git LFS](https://git-lfs.com/) — necesario para los `.tif` de
  `resultados/rasters/`. Después de instalarlo, corré una vez:
  ```
  git lfs install
  ```

Si es la primera vez que usás git en esta PC, también necesitás decirle
quién sos (una sola vez, sirve para todos tus repositorios):

```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tu-email@ejemplo.com"
```

### 2. Crear el repositorio vacío en GitHub

En [github.com/new](https://github.com/new): elegí un nombre (por
ejemplo `analisis-lidar-2024-montevideo`), marcá **Public**, y dejá
**sin marcar** las opciones de agregar README, .gitignore o licencia
(este paquete ya los trae — marcarlas allá genera conflictos al
pushear). Copiá la URL que te da GitHub al terminar
(`https://github.com/tu-usuario/tu-repo.git`).

### 3. Publicar desde esta carpeta

**Opción A — con el script de ayuda incluido:** abrí PowerShell en esta
carpeta y corré:

```powershell
.\configurar_repo.ps1 -RemoteUrl "https://github.com/tu-usuario/tu-repo.git"
```

Si PowerShell bloquea el script por política de ejecución, corré antes
(una sola vez, solo para esa ventana):
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Opción B — a mano**, los mismos pasos que hace el script:

```powershell
git lfs install
git init
git add .
git commit -m "Version inicial: procedimiento (Bloques 7-10) y estructura del proyecto"
git branch -M main
git remote add origin https://github.com/tu-usuario/tu-repo.git
git push -u origin main
```

### 4. Agregar los resultados reales

Una vez que corriste los cuatro scripts y tenés los `.tif` en tu PC,
copialos a `resultados/rasters/` (ver esa carpeta) y:

```powershell
git add resultados/rasters/*.tif
git commit -m "Agregar rasters de resultados"
git push
```

## Licencia

Se incluye una licencia MIT por defecto en `LICENSE` (ver el archivo
para más detalle y para completar el nombre del titular). Reemplazala o
borrala si preferís otra licencia u optar por no licenciarlo.

---
Referencia: [EPSG:5382 — SIRGAS-ROU98 / UTM zone 21S](https://epsg.io/5382)
