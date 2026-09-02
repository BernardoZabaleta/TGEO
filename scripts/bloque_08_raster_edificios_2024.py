# ------------------------------------------------------------
# Nota de adaptación a este repositorio (no estaba en el original):
#   - Instalar dependencias con:  pip install -r requirements.txt
#   - Las rutas de la sección 1 están tal cual se usaron
#     originalmente en Windows (unidad D:\...). Editalas para que
#     apunten a donde tengas tus datos antes de correr el script.
# ------------------------------------------------------------

# ============================================================
# DESARROLLO VERTICAL DE LA CIUDAD - LiDAR 2024 vs MDS 2019
# BLOQUE 8 - RASTER DE EDIFICIOS (2.5 m) A PARTIR DEL LiDAR 2024
# ============================================================
#
# Lee todos los .laz de una carpeta, se queda solo con los puntos
# clasificados como edificio (código ASPRS 6, ver Bloque 7), y los
# convierte en un raster de 2.5 m tomando el valor Z más alto de
# cada celda (equivalente en Python a "LAS Dataset To Raster" con
# Interpolation Type = Binning, Cell Assignment Type = Maximum,
# filtrado a la clase Building).
#
# Se arma UNA sola grilla que cubre la extensión combinada de
# TODOS los archivos de entrada, y se acumula el máximo por celda
# a través de todos los archivos (no archivo por archivo), para
# que un edificio que cruce el borde entre dos tiles quede bien
# representado.
#
# Requiere: pip install laspy lazrs rasterio numpy
# (en Jupyter: %pip install laspy lazrs rasterio numpy)
# ============================================================
import os
import sys
import glob
import numpy as np
import laspy
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
# ------------------------------------------------------------
# 1. PARÁMETROS
# ------------------------------------------------------------
carpeta_laz = r"D:\LiDAR"
ruta_salida = r"D:\LiDAR\edificios_lidar_2024_2_5m.tif"
RESOLUCION = 2.5  # metros
CODIGO_EDIFICIO = 6  # ASPRS: Building
CRS_SALIDA = "EPSG:5382"  # el mismo que venimos usando en todo el proyecto
TAMANO_CHUNK = 5_000_000
# ------------------------------------------------------------
# 1-bis. SI EL RASTER DE SALIDA YA EXISTE, NO REPROCESAR
# ------------------------------------------------------------
# Agregado en este repositorio (no estaba en el bloque original): tal
# como estaba escrito, este bloque siempre releía TODOS los .laz/.las
# desde cero y sobreescribía ruta_salida, incluso si ya existía. Eso
# es lo más lento del procedimiento (relee la nube de puntos entera).
# Con esta guarda, si el archivo de salida ya está generado, se salta
# el reprocesamiento. Poné FORZAR_RECALCULO = True solo si cambiaste
# los .laz de entrada y necesitás regenerarlo de verdad.
FORZAR_RECALCULO = False
if os.path.exists(ruta_salida) and not FORZAR_RECALCULO:
    print(f"Ya existe '{ruta_salida}'.")
    print(
        "No se reprocesan los .laz/.las (FORZAR_RECALCULO=False). Si "
        "cambiaste los datos de entrada y necesitás regenerarlo, poné "
        "FORZAR_RECALCULO = True arriba y volvé a correr el bloque."
    )
    sys.exit(0)
archivos = sorted(
    glob.glob(os.path.join(carpeta_laz, "*.laz"))
    + glob.glob(os.path.join(carpeta_laz, "*.las"))
)
if len(archivos) == 0:
    raise FileNotFoundError(
        f"No se encontraron .laz/.las en {carpeta_laz}. Revisar la ruta."
    )
print("=" * 70)
print(f"Archivos a procesar: {len(archivos)}")
print("=" * 70)
for a in archivos:
    print(" -", os.path.basename(a))
# ------------------------------------------------------------
# 2. EXTENSIÓN GLOBAL (solo headers, sin leer puntos todavía)
# ------------------------------------------------------------
min_x = min_y = np.inf
max_x = max_y = -np.inf
for ruta in archivos:
    with laspy.open(ruta) as f:
        h = f.header
        min_x = min(min_x, h.mins[0])
        max_x = max(max_x, h.maxs[0])
        min_y = min(min_y, h.mins[1])
        max_y = max(max_y, h.maxs[1])
# Origen de grilla "redondo", múltiplo exacto de la resolución
origen_x = np.floor(min_x / RESOLUCION) * RESOLUCION
origen_y = np.ceil(max_y / RESOLUCION) * RESOLUCION  # esquina superior
n_cols = int(np.ceil((max_x - origen_x) / RESOLUCION))
n_filas = int(np.ceil((origen_y - min_y) / RESOLUCION))
print("\n" + "=" * 70)
print("GRILLA DE SALIDA")
print("=" * 70)
print(f"\nExtensión combinada: X [{min_x:.2f}, {max_x:.2f}]  Y [{min_y:.2f}, {max_y:.2f}]")
print(f"Origen (esquina superior izquierda): ({origen_x}, {origen_y})")
print(f"Columnas x Filas: {n_cols} x {n_filas}  (resolución {RESOLUCION} m)")
transform = from_origin(origen_x, origen_y, RESOLUCION, RESOLUCION)
# ------------------------------------------------------------
# 3. ACUMULAR EL MÁXIMO POR CELDA, A TRAVÉS DE TODOS LOS ARCHIVOS
# ------------------------------------------------------------
grilla_max = np.full((n_filas, n_cols), -np.inf, dtype=np.float64)
puntos_edificio_total = 0
puntos_fuera_de_grilla = 0
for ruta in archivos:
    nombre = os.path.basename(ruta)
    n_edificio_archivo = 0
    with laspy.open(ruta) as f:
        for puntos in f.chunk_iterator(TAMANO_CHUNK):
            clases = np.asarray(puntos.classification)
            es_edificio = clases == CODIGO_EDIFICIO
            if not np.any(es_edificio):
                continue
            x = np.asarray(puntos.x)[es_edificio]
            y = np.asarray(puntos.y)[es_edificio]
            z = np.asarray(puntos.z)[es_edificio]
            col = np.floor((x - origen_x) / RESOLUCION).astype(np.int64)
            fila = np.floor((origen_y - y) / RESOLUCION).astype(np.int64)
            dentro = (
                (col >= 0) & (col < n_cols) & (fila >= 0) & (fila < n_filas)
            )
            puntos_fuera_de_grilla += int((~dentro).sum())
            col = col[dentro]
            fila = fila[dentro]
            z = z[dentro]
            np.maximum.at(grilla_max, (fila, col), z)
            n_edificio_archivo += len(z)
    puntos_edificio_total += n_edificio_archivo
    print(f"Procesado: {nombre} ({n_edificio_archivo:,} puntos de edificio)")
print(f"\nTotal de puntos de edificio usados: {puntos_edificio_total:,}")
if puntos_fuera_de_grilla > 0:
    print(
        f"Puntos descartados por caer justo fuera de la grilla "
        f"(redondeo de borde): {puntos_fuera_de_grilla:,}"
    )
# ------------------------------------------------------------
# 4. CONVERTIR CELDAS SIN NINGÚN PUNTO A NoData
# ------------------------------------------------------------
sin_datos = np.isneginf(grilla_max)
grilla_final = grilla_max.astype(np.float32)
grilla_final[sin_datos] = np.nan
celdas_con_dato = int((~sin_datos).sum())
celdas_totales = grilla_final.size
print(
    f"\nCeldas con al menos un punto de edificio: {celdas_con_dato:,} de "
    f"{celdas_totales:,} ({celdas_con_dato / celdas_totales * 100:.2f}%)"
)
# ------------------------------------------------------------
# 5. GUARDAR COMO GEOTIFF
# ------------------------------------------------------------
perfil = dict(
    driver="GTiff",
    height=n_filas,
    width=n_cols,
    count=1,
    dtype="float32",
    crs=CRS.from_string(CRS_SALIDA),
    transform=transform,
    nodata=np.nan,
)
with rasterio.open(ruta_salida, "w", **perfil) as dst:
    dst.write(grilla_final, 1)
print("\n" + "=" * 70)
print("LISTO")
print("=" * 70)
print("Raster de edificios (LiDAR 2024) guardado en:")
print(ruta_salida)
