# ------------------------------------------------------------
# Nota de adaptación a este repositorio (no estaba en el original):
#   - Instalar dependencias con:  pip install -r requirements.txt
#   - Las rutas de la sección 1 están tal cual se usaron
#     originalmente en Windows (unidad D:\...). Editalas para que
#     apunten a donde tengas tus datos antes de correr el script.
# ------------------------------------------------------------

# ============================================================
# DESARROLLO VERTICAL DE LA CIUDAD - LiDAR 2024 vs MDS 2019
# BLOQUE 10 - ALINEAR Y CALCULAR LA DIFERENCIA
# ============================================================
#
# Toma el raster de edificios del LiDAR 2024 (Bloque 8) y el
# mosaico del MDS 2019 (Bloque 9), remuestrea el MDS 2019 para que
# caiga exactamente sobre la grilla del raster de edificios (mismo
# principio que el Bloque 3), y calcula la diferencia 2024 - 2019.
#
# La diferencia queda automáticamente restringida a donde el LiDAR
# 2024 tiene un edificio (fuera de ahí es NoData) — por diseño,
# como hablamos: esto capta construcción nueva y edificios que
# crecieron, pero no demoliciones ni edificios que bajaron de
# altura, porque el MDS 2019 no viene clasificado y no se puede
# restringir de la misma forma del otro lado.
#
# Requiere: pip install rasterio numpy
# ============================================================
import os
import sys
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
# ------------------------------------------------------------
# 1. RUTAS
# ------------------------------------------------------------
ruta_edificios_2024 = r"D:\LiDAR\edificios_lidar_2024_2_5m.tif"
ruta_mds_2019 = r"D:\LiDAR\tif\mds_2019_mosaico.tif"
ruta_diferencia = r"D:\LiDAR\diferencia_edificios_2024_menos_mds_2019.tif"
# ------------------------------------------------------------
# 1-bis. SI LA DIFERENCIA YA EXISTE, NO REPROCESAR
# ------------------------------------------------------------
# Agregado en este repositorio (no estaba en el bloque original), por
# consistencia con los Bloques 8 y 9. Este cálculo es rápido (una
# resta entre dos rasters ya a 2.5 m, no relee nubes de puntos), pero
# si ya tenés la diferencia generada y no cambiaste ninguno de los dos
# rasters de entrada, no hace falta repetirlo. Poné FORZAR_RECALCULO =
# True si querés recalcularla igual.
FORZAR_RECALCULO = False
if os.path.exists(ruta_diferencia) and not FORZAR_RECALCULO:
    print(f"Ya existe '{ruta_diferencia}'.")
    print(
        "No se recalcula (FORZAR_RECALCULO=False). Si cambiaste "
        "edificios_lidar_2024_2_5m.tif o mds_2019_mosaico.tif y "
        "necesitás actualizarla, poné FORZAR_RECALCULO = True arriba y "
        "volvé a correr el bloque."
    )
    sys.exit(0)
# ------------------------------------------------------------
# 2. CARGAR EL RASTER DE EDIFICIOS 2024 (grilla de referencia)
# ------------------------------------------------------------
with rasterio.open(ruta_edificios_2024) as src:
    edificios_2024 = src.read(1)
    perfil_destino = src.profile
    transform_destino = src.transform
    crs_destino = src.crs
    ancho_destino = src.width
    alto_destino = src.height
    bounds_destino = src.bounds
# El Bloque 8 ya guarda NaN como NoData; por las dudas, si el
# archivo trajera otro NoData definido, lo normalizamos a NaN acá.
with rasterio.open(ruta_edificios_2024) as src:
    if src.nodata is not None and not np.isnan(src.nodata):
        edificios_2024 = np.where(
            edificios_2024 == src.nodata, np.nan, edificios_2024
        )
# ------------------------------------------------------------
# 3. REMUESTREAR EL MOSAICO MDS 2019 A ESA MISMA GRILLA
# ------------------------------------------------------------
RESOLUCION_ESPERADA = 2.5  # metros -- debe coincidir con el Bloque 9
TOLERANCIA = 1.0  # metros
with rasterio.open(ruta_mds_2019) as src:
    print(
        f"MDS 2019 ({os.path.basename(ruta_mds_2019)}) -- "
        f"resolución: {src.res}, dimensiones: {src.width} x {src.height}"
    )
    if (
        abs(src.res[0] - RESOLUCION_ESPERADA) > TOLERANCIA
        or abs(src.res[1] - RESOLUCION_ESPERADA) > TOLERANCIA
    ):
        raise ValueError(
            f"El archivo '{ruta_mds_2019}' tiene resolución {src.res}, "
            f"lejos de los ~{RESOLUCION_ESPERADA} m esperados. Lo más "
            "probable es que sea el mosaico viejo a resolución nativa "
            "(10 cm), no el corregido -- volvé a correr el Bloque 9 "
            "corregido (fijate que no haya una celda vieja, sin "
            "corregir, del Bloque 9 más abajo en el notebook que se "
            "ejecute después y lo pise) hasta que termine del todo, y "
            "recién después corré este bloque de nuevo."
        )
    origen = src.read(1).astype(np.float32)
    nodata_origen = src.nodata
    if nodata_origen is not None and not np.isnan(nodata_origen):
        origen[origen == nodata_origen] = np.nan
    mds_2019_alineado = np.full(
        (alto_destino, ancho_destino), np.nan, dtype=np.float32
    )
    reproject(
        source=origen,
        destination=mds_2019_alineado,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=np.nan,
        dst_transform=transform_destino,
        dst_crs=crs_destino,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
pixeles_validos_mds = int(np.sum(~np.isnan(mds_2019_alineado)))
print("=" * 70)
print("MDS 2019 REMUESTREADO A LA GRILLA DEL RASTER DE EDIFICIOS")
print("=" * 70)
print(f"\nForma: {mds_2019_alineado.shape} (igual a la del raster de edificios: {(alto_destino, ancho_destino)})")
print(
    f"Píxeles con dato tras remuestrear: {pixeles_validos_mds:,} de "
    f"{mds_2019_alineado.size:,}"
)
# ------------------------------------------------------------
# 4. CALCULAR LA DIFERENCIA (2024 - 2019)
# ------------------------------------------------------------
diferencia = edificios_2024.astype(np.float32) - mds_2019_alineado
mascara_valida = ~np.isnan(diferencia)
pixeles_validos = int(mascara_valida.sum())
print("\n" + "=" * 70)
print("DIFERENCIA (edificios LiDAR 2024 - MDS 2019)")
print("=" * 70)
print(
    f"\nPíxeles con diferencia calculada: {pixeles_validos:,} de "
    f"{diferencia.size:,} ({pixeles_validos / diferencia.size * 100:.2f}%)"
)
if pixeles_validos == 0:
    raise ValueError(
        "No quedó ningún píxel válido: revisar que las extensiones de "
        "los dos rasters realmente se superpongan y que el raster de "
        "edificios (Bloque 8) tenga celdas con datos."
    )
valores = diferencia[mascara_valida]
print("\nMínimo:", np.min(valores))
print("Máximo:", np.max(valores))
print("Media:", np.mean(valores))
print("Mediana:", np.median(valores))
print("Desvío estándar:", np.std(valores))
# ------------------------------------------------------------
# 5. GUARDAR EL RASTER DE DIFERENCIA
# ------------------------------------------------------------
perfil_dif = perfil_destino.copy()
perfil_dif.update(dtype="float32", nodata=np.nan, count=1)
with rasterio.open(ruta_diferencia, "w", **perfil_dif) as dst:
    dst.write(diferencia, 1)
print("\nRaster de diferencia guardado en:")
print(ruta_diferencia)
print("\n" + "=" * 70)
print("RECORDATORIOS PARA INTERPRETAR EL RESULTADO")
print("=" * 70)
print(
    "\n- Esta diferencia solo existe donde el LiDAR 2024 detectó"
    "\n  edificio: construcción nueva o crecimiento en altura, no"
    "\n  demoliciones ni edificios que bajaron."
    "\n- Antes de confiar en los valores, revisá la diferencia sobre"
    "\n  2-3 edificios grandes que sepas que NO cambiaron entre 2019 y"
    "\n  2024 (para descartar un corrimiento de datum vertical, tal"
    "\n  como veníamos hablando)."
    "\n- Valores positivos: el LiDAR 2024 midió más altura que el MDS"
    "\n  2019 en ese punto (creció o es construcción nueva). Valores"
    "\n  negativos con el criterio de NoData actual deberían ser"
    "\n  raros -- si aparecen muchos, revisar la hipótesis de que el"
    "\n  terreno no cambió entre 2019 y 2024 en esa zona."
)
