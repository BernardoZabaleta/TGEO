"""
Procesamiento para comparar MDS 2019 (aerofotogrametría) con LiDAR 2024
en una zona de Montevideo.

Flujo:
1. Inspección de las clasificaciones de la nube LiDAR.
2. Selección de puntos clasificados como edificio (ASPRS 6).
3. Generación de un raster de edificios LiDAR 2024 a 2.5 m,
   usando el máximo Z por celda.
4. Remuestreo de cada hoja MDS 2019 de 10 cm a 2.5 m con máximo.
5. Mosaico de las hojas MDS 2019.
6. Alineación del MDS 2019 con la grilla LiDAR 2024.
7. Cálculo de diferencia: LiDAR 2024 - MDS 2019.

Dependencias:
    pip install laspy lazrs pandas rasterio numpy

IMPORTANTE:
- Editar las rutas de entrada/salida.
- EPSG:5382 se conserva como CRS de trabajo.
- El resultado de diferencia queda restringido a celdas donde
  existen puntos LiDAR clasificados como edificio.
"""

import os
import glob
import time
import numpy as np
import pandas as pd
import laspy
import rasterio
from rasterio.io import MemoryFile
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from rasterio.merge import merge
from rasterio.crs import CRS


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

CARPETA_LAZ = r"D:\LiDAR"
CARPETA_MDS_2019 = r"D:\LiDAR\tif"

RASTER_EDIFICIOS_2024 = r"D:\LiDAR\edificios_lidar_2024_2_5m.tif"
MOSAICO_MDS_2019 = r"D:\LiDAR\tif\mds_2019_mosaico.tif"
RASTER_DIFERENCIA = r"D:\LiDAR\diferencia_edificios_2024_menos_mds_2019.tif"

RESOLUCION = 2.5
CRS_SALIDA = "EPSG:5382"
CODIGO_EDIFICIO = 6
TAMANO_CHUNK = 5_000_000


def obtener_archivos_lidar():
    archivos = sorted(
        glob.glob(os.path.join(CARPETA_LAZ, "*.laz"))
        + glob.glob(os.path.join(CARPETA_LAZ, "*.las"))
    )
    if not archivos:
        raise FileNotFoundError(f"No se encontraron .laz/.las en {CARPETA_LAZ}")
    return archivos


# ============================================================
# 2. INSPECCIÓN DE CLASIFICACIONES LiDAR
# ============================================================

NOMBRES_ASPRS = {
    0: "Nunca clasificado",
    1: "Sin asignar",
    2: "Terreno (ground)",
    3: "Vegetación baja (<0.5 m)",
    4: "Vegetación media (0.5-2 m)",
    5: "Vegetación alta (>2 m)",
    6: "Edificio",
    7: "Punto bajo (ruido)",
    8: "Reservado / model key",
    9: "Agua",
    10: "Riel",
    11: "Superficie de ruta/carretera",
    12: "Reservado / overlap",
    13: "Cable - guardia",
    14: "Cable - conductor",
    15: "Torre de transmisión",
    16: "Conector de cable",
    17: "Tablero de puente",
    18: "Ruido alto",
    19: "Maquinaria elevada / cinta transportadora",
    20: "Terreno ignorado",
    21: "Nieve",
    22: "Exclusión temporal",
}


def nombre_clase(codigo):
    if codigo in NOMBRES_ASPRS:
        return NOMBRES_ASPRS[codigo]
    if 64 <= codigo <= 255:
        return "Definido por usuario/proveedor"
    return "Reservado"


def analizar_clasificaciones(archivos):
    conteo_total = np.zeros(256, dtype=np.int64)
    conteo_por_archivo = {}

    for ruta in archivos:
        nombre = os.path.basename(ruta)
        conteo_archivo = np.zeros(256, dtype=np.int64)

        with laspy.open(ruta) as f:
            for puntos in f.chunk_iterator(TAMANO_CHUNK):
                codigos = np.asarray(puntos.classification)
                conteo_archivo += np.bincount(codigos, minlength=256)

        conteo_por_archivo[nombre] = conteo_archivo
        conteo_total += conteo_archivo

        print(f"Procesado: {nombre} ({conteo_archivo.sum():,} puntos)")

    total_puntos = int(conteo_total.sum())
    filas = []

    for codigo in np.where(conteo_total > 0)[0]:
        n = int(conteo_total[codigo])
        filas.append({
            "codigo": int(codigo),
            "superficie": nombre_clase(int(codigo)),
            "cantidad_puntos": n,
            "porcentaje": n / total_puntos * 100,
        })

    tabla = pd.DataFrame(filas).sort_values(
        "cantidad_puntos", ascending=False
    )

    print("\nCLASIFICACIONES PRESENTES")
    print(tabla.to_string(index=False))

    return tabla, conteo_por_archivo


# ============================================================
# 3. CREAR RASTER DE EDIFICIOS LiDAR 2024 A 2.5 m
# ============================================================

def crear_raster_edificios(archivos):
    min_x = min_y = np.inf
    max_x = max_y = -np.inf

    # Extensión global usando solamente los headers.
    for ruta in archivos:
        with laspy.open(ruta) as f:
            h = f.header
            min_x = min(min_x, h.mins[0])
            max_x = max(max_x, h.maxs[0])
            min_y = min(min_y, h.mins[1])
            max_y = max(max_y, h.maxs[1])

    origen_x = np.floor(min_x / RESOLUCION) * RESOLUCION
    origen_y = np.ceil(max_y / RESOLUCION) * RESOLUCION

    n_cols = int(np.ceil((max_x - origen_x) / RESOLUCION))
    n_filas = int(np.ceil((origen_y - min_y) / RESOLUCION))

    transform = from_origin(
        origen_x, origen_y, RESOLUCION, RESOLUCION
    )

    grilla_max = np.full(
        (n_filas, n_cols), -np.inf, dtype=np.float64
    )

    puntos_edificio_total = 0

    for ruta in archivos:
        nombre = os.path.basename(ruta)
        n_edificio = 0

        with laspy.open(ruta) as f:
            for puntos in f.chunk_iterator(TAMANO_CHUNK):
                clases = np.asarray(puntos.classification)
                mascara = clases == CODIGO_EDIFICIO

                if not np.any(mascara):
                    continue

                x = np.asarray(puntos.x)[mascara]
                y = np.asarray(puntos.y)[mascara]
                z = np.asarray(puntos.z)[mascara]

                col = np.floor(
                    (x - origen_x) / RESOLUCION
                ).astype(np.int64)

                fila = np.floor(
                    (origen_y - y) / RESOLUCION
                ).astype(np.int64)

                dentro = (
                    (col >= 0) & (col < n_cols) &
                    (fila >= 0) & (fila < n_filas)
                )

                col = col[dentro]
                fila = fila[dentro]
                z = z[dentro]

                np.maximum.at(grilla_max, (fila, col), z)
                n_edificio += len(z)

        puntos_edificio_total += n_edificio
        print(
            f"{nombre}: {n_edificio:,} puntos clasificados como edificio"
        )

    grilla_final = grilla_max.astype(np.float32)
    grilla_final[np.isneginf(grilla_max)] = np.nan

    perfil = {
        "driver": "GTiff",
        "height": n_filas,
        "width": n_cols,
        "count": 1,
        "dtype": "float32",
        "crs": CRS.from_string(CRS_SALIDA),
        "transform": transform,
        "nodata": np.nan,
    }

    with rasterio.open(RASTER_EDIFICIOS_2024, "w", **perfil) as dst:
        dst.write(grilla_final, 1)

    print(f"\nRaster guardado: {RASTER_EDIFICIOS_2024}")
    print(f"Total de puntos de edificio: {puntos_edificio_total:,}")


# ============================================================
# 4. REMUESTREAR Y MOSAICAR MDS 2019
# ============================================================

def crear_mosaico_mds_2019():
    archivos = sorted(
        glob.glob(os.path.join(CARPETA_MDS_2019, "*.tif"))
    )

    salida_abs = os.path.abspath(MOSAICO_MDS_2019)
    archivos = [
        a for a in archivos
        if os.path.abspath(a) != salida_abs
    ]

    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron hojas .tif en {CARPETA_MDS_2019}"
        )

    crs_referencia = None
    memfiles = []
    datasets = []

    for ruta in archivos:
        with rasterio.open(ruta) as src:
            if crs_referencia is None:
                crs_referencia = src.crs

            bounds = src.bounds

            ancho = int(
                np.ceil(
                    (bounds.right - bounds.left) / RESOLUCION
                )
            )
            alto = int(
                np.ceil(
                    (bounds.top - bounds.bottom) / RESOLUCION
                )
            )

            transform_dest = from_origin(
                bounds.left,
                bounds.top,
                RESOLUCION,
                RESOLUCION,
            )

            destino = np.full(
                (alto, ancho), np.nan, dtype=np.float32
            )

            reproject(
                source=rasterio.band(src, 1),
                destination=destino,
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=src.nodata,
                dst_transform=transform_dest,
                dst_crs=src.crs,
                dst_nodata=np.nan,
                resampling=Resampling.max,
            )

        perfil = {
            "driver": "GTiff",
            "height": alto,
            "width": ancho,
            "count": 1,
            "dtype": "float32",
            "crs": crs_referencia,
            "transform": transform_dest,
            "nodata": np.nan,
        }

        mem = MemoryFile()
        with mem.open(**perfil) as dst:
            dst.write(destino, 1)

        memfiles.append(mem)
        datasets.append(mem.open())

        print(f"Remuestreada: {os.path.basename(ruta)}")

    mosaico, transform_salida = merge(
        datasets,
        resampling=Resampling.nearest
    )

    for ds in datasets:
        ds.close()
    for mem in memfiles:
        mem.close()

    perfil_final = {
        "driver": "GTiff",
        "height": mosaico.shape[1],
        "width": mosaico.shape[2],
        "count": 1,
        "dtype": "float32",
        "crs": crs_referencia,
        "transform": transform_salida,
        "nodata": np.nan,
    }

    with rasterio.open(MOSAICO_MDS_2019, "w", **perfil_final) as dst:
        dst.write(mosaico[0], 1)

    print(f"\nMosaico MDS 2019 guardado: {MOSAICO_MDS_2019}")


# ============================================================
# 5. ALINEAR MDS 2019 Y CALCULAR DIFERENCIA
# ============================================================

def calcular_diferencia():
    with rasterio.open(RASTER_EDIFICIOS_2024) as src:
        edificios = src.read(1).astype(np.float32)
        perfil_destino = src.profile
        transform_destino = src.transform
        crs_destino = src.crs
        ancho = src.width
        alto = src.height

        if src.nodata is not None and not np.isnan(src.nodata):
            edificios[edificios == src.nodata] = np.nan

    with rasterio.open(MOSAICO_MDS_2019) as src:
        origen = src.read(1).astype(np.float32)

        if src.nodata is not None and not np.isnan(src.nodata):
            origen[origen == src.nodata] = np.nan

        mds_alineado = np.full(
            (alto, ancho), np.nan, dtype=np.float32
        )

        reproject(
            source=origen,
            destination=mds_alineado,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=np.nan,
            dst_transform=transform_destino,
            dst_crs=crs_destino,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )

    diferencia = edificios - mds_alineado

    mascara = ~np.isnan(diferencia)
    valores = diferencia[mascara]

    if valores.size == 0:
        raise ValueError(
            "No quedaron píxeles válidos para calcular la diferencia."
        )

    print("\nESTADÍSTICAS DE LA DIFERENCIA")
    print(f"Píxeles válidos: {valores.size:,}")
    print(f"Mínimo: {valores.min():.3f}")
    print(f"Máximo: {valores.max():.3f}")
    print(f"Media: {valores.mean():.3f}")
    print(f"Mediana: {np.median(valores):.3f}")
    print(f"Desvío estándar: {valores.std():.3f}")

    perfil_destino.update(
        dtype="float32",
        nodata=np.nan,
        count=1,
    )

    with rasterio.open(
        RASTER_DIFERENCIA, "w", **perfil_destino
    ) as dst:
        dst.write(diferencia, 1)

    print(f"\nDiferencia guardada: {RASTER_DIFERENCIA}")


# ============================================================
# 6. EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    archivos_lidar = obtener_archivos_lidar()

    analizar_clasificaciones(archivos_lidar)
    crear_raster_edificios(archivos_lidar)
    crear_mosaico_mds_2019()
    calcular_diferencia()

    print("\nProcesamiento completo.")
