# ------------------------------------------------------------
# Nota de adaptación a este repositorio (no estaba en el original):
#   - Instalar dependencias con:  pip install -r requirements.txt
#   - Las rutas de la sección 1 están tal cual se usaron
#     originalmente en Windows (unidad D:\...). Editalas para que
#     apunten a donde tengas tus datos antes de correr el script.
# ------------------------------------------------------------

# ============================================================
# DESARROLLO VERTICAL DE LA CIUDAD - LiDAR 2024 vs MDS 2019
# BLOQUE 9 (CORREGIDO) - MOSAICO DEL MDS 2019, YA A 2.5 m
# ============================================================
#
# VERSIÓN ANTERIOR DE ESTE BLOQUE: mosaicaba las hojas a su
# resolución nativa (resultó ser 10 cm, no 2.5 m como se había
# asumido) y RECIÉN DESPUÉS se pensaba remuestrear. Con hojas de
# 1x1 km a 10 cm, cada una tiene 10.000 x 10.000 píxeles: 28 hojas
# mosaicadas a resolución nativa arman un raster de más de 2.700
# millones de píxeles (~11 GB en memoria) — de ahí la demora de
# más de media hora.
#
# ESTA VERSIÓN remuestrea CADA hoja a 2.5 m primero (achicándola
# ~625 veces) y recién después las mosaica, así nunca se llega a
# construir el raster gigante a 10 cm. El remuestreo usa
# Resampling.max (el valor más alto entre los ~625 píxeles de 10cm
# que caen en cada celda de 2.5m): igual que en el raster de
# edificios del LiDAR (Bloque 8), esto conserva la altura del techo
# más alto en vez de diluirla mezclándola con la calle alrededor
# (que es lo que pasaría con Resampling.average o bilinear).
#
# Nota técnica: Resampling.max no funciona dentro de
# rasterio.merge (solo sirve para operaciones de warp, no de
# lectura directa) — por eso el remuestreo se hace acá con
# rasterio.warp.reproject hoja por hoja, y merge() se usa solo al
# final, para unir las hojas ya achicadas.
#
# Requiere: pip install rasterio numpy
# ============================================================
import os
import sys
import glob
import time
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from rasterio.merge import merge
# ------------------------------------------------------------
# 1. RUTAS Y PARÁMETROS
# ------------------------------------------------------------
carpeta_tif = r"D:\LiDAR\tif"
ruta_salida = r"D:\LiDAR\tif\mds_2019_mosaico.tif"
RESOLUCION_DESTINO = 2.5  # metros
# ------------------------------------------------------------
# 1-bis. SI EL MOSAICO DE SALIDA YA EXISTE, NO REPROCESAR
# ------------------------------------------------------------
# Agregado en este repositorio (no estaba en el bloque original): tal
# como estaba escrito, este bloque siempre releía TODAS las hojas a
# 10 cm y sobreescribía ruta_salida, incluso si ya existía. Es el paso
# que puede tardar varios minutos. Con esta guarda, si el mosaico ya
# está generado, se salta el reprocesamiento. Poné FORZAR_RECALCULO =
# True solo si cambiaste las hojas de entrada y necesitás regenerarlo.
FORZAR_RECALCULO = False
if os.path.exists(ruta_salida) and not FORZAR_RECALCULO:
    print(f"Ya existe '{ruta_salida}'.")
    print(
        "No se reprocesan las hojas de 10 cm (FORZAR_RECALCULO=False). "
        "Si cambiaste los datos de entrada y necesitás regenerarlo, "
        "poné FORZAR_RECALCULO = True arriba y volvé a correr el bloque."
    )
    sys.exit(0)
archivos = sorted(glob.glob(os.path.join(carpeta_tif, "*.tif")))
# Excluir la propia salida si ya existe de una corrida anterior en la
# misma carpeta: si no, el glob de arriba la agarra como si fuera una
# hoja más de entrada. Pasó en la práctica: infló el tiempo de corrida
# de ~4 a ~15 minutos por tener que reproyectar el mosaico viejo (a
# veces todavía gigante, a resolución nativa) como si fuera una hoja
# más, y contamina el resultado con una "hoja" que en realidad es la
# salida de otra corrida.
ruta_salida_abs = os.path.abspath(ruta_salida)
archivos_excluidos = [a for a in archivos if os.path.abspath(a) == ruta_salida_abs]
archivos = [a for a in archivos if os.path.abspath(a) != ruta_salida_abs]
if archivos_excluidos:
    print("Excluida de las hojas de entrada (es la salida de una corrida anterior):")
    for a in archivos_excluidos:
        print("  -", os.path.basename(a))
if len(archivos) == 0:
    raise FileNotFoundError(
        f"No se encontraron .tif en {carpeta_tif}. Revisar la ruta."
    )
print("=" * 70)
print(f"Hojas a procesar: {len(archivos)}")
print("=" * 70)
for a in archivos:
    print(" -", os.path.basename(a))
# ------------------------------------------------------------
# 2. VERIFICAR CRS (y avisar la resolución real de origen)
# ------------------------------------------------------------
crs_referencia = None
for a in archivos:
    with rasterio.open(a) as src:
        if crs_referencia is None:
            crs_referencia = src.crs
            res_origen = src.res
        elif src.crs != crs_referencia:
            print(f"AVISO: {os.path.basename(a)} tiene un CRS distinto ({src.crs})")
print(f"\nCRS de referencia: {crs_referencia}")
print(f"Resolución nativa de las hojas: {res_origen}")
print(f"Resolución de salida: {RESOLUCION_DESTINO} m")
# ------------------------------------------------------------
# 3. REMUESTREAR CADA HOJA A 2.5 m (Resampling.max) EN MEMORIA
# ------------------------------------------------------------
t0 = time.time()
memfiles = []
datasets_chicos = []
for i, ruta in enumerate(archivos, 1):
    nombre = os.path.basename(ruta)
    with rasterio.open(ruta) as src:
        bounds = src.bounds
        dtype_origen = src.dtypes[0]
        nodata_origen = src.nodata
        ancho_dest = int(np.ceil((bounds.right - bounds.left) / RESOLUCION_DESTINO))
        alto_dest = int(np.ceil((bounds.top - bounds.bottom) / RESOLUCION_DESTINO))
        transform_dest = from_origin(
            bounds.left, bounds.top, RESOLUCION_DESTINO, RESOLUCION_DESTINO
        )
        destino = np.full((alto_dest, ancho_dest), np.nan, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=destino,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=nodata_origen,
            dst_transform=transform_dest,
            dst_crs=src.crs,
            dst_nodata=np.nan,
            resampling=Resampling.max,
        )
    perfil_chico = dict(
        driver="GTiff",
        height=alto_dest,
        width=ancho_dest,
        count=1,
        dtype="float32",
        crs=crs_referencia,
        transform=transform_dest,
        nodata=np.nan,
    )
    mem = MemoryFile()
    with mem.open(**perfil_chico) as dst:
        dst.write(destino, 1)
    memfiles.append(mem)
    datasets_chicos.append(mem.open())
    print(
        f"[{i}/{len(archivos)}] {nombre}: {(alto_dest, ancho_dest)} "
        f"tras remuestrear  ({time.time() - t0:.1f}s acumulados)"
    )
# ------------------------------------------------------------
# 4. MOSAICAR LAS HOJAS YA CHICAS
# ------------------------------------------------------------
mosaico, transform_salida = merge(datasets_chicos, resampling=Resampling.nearest)
for ds in datasets_chicos:
    ds.close()
for mem in memfiles:
    mem.close()
print("\n" + "=" * 70)
print("MOSAICO ARMADO")
print("=" * 70)
print("Forma del mosaico (bandas, filas, columnas):", mosaico.shape)
print(f"Tiempo total: {time.time() - t0:.1f} s")
# ------------------------------------------------------------
# 5. GUARDAR
# ------------------------------------------------------------
perfil = dict(
    driver="GTiff",
    height=mosaico.shape[1],
    width=mosaico.shape[2],
    count=1,
    dtype="float32",
    crs=crs_referencia,
    transform=transform_salida,
    nodata=np.nan,
)
with rasterio.open(ruta_salida, "w", **perfil) as dst:
    dst.write(mosaico[0], 1)
print("\nMosaico (2.5 m) guardado en:")
print(ruta_salida)
# ------------------------------------------------------------
# 6. ESTADÍSTICAS RÁPIDAS DE CONTROL
# ------------------------------------------------------------
with rasterio.open(ruta_salida) as src:
    datos = src.read(1)
    validos = datos[~np.isnan(datos)]
    print("\n" + "=" * 70)
    print("CONTROL RÁPIDO DEL MOSAICO")
    print("=" * 70)
    print("CRS:", src.crs)
    print("Resolución:", src.res)
    print("Dimensiones:", src.width, "x", src.height)
    print("Extensión:", src.bounds)
    if len(validos) > 0:
        print(f"Valores válidos: {len(validos):,} de {datos.size:,}")
        print("Mínimo:", validos.min())
        print("Máximo:", validos.max())
        print("Media:", validos.mean())
