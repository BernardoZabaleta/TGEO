# ------------------------------------------------------------
# Nota de adaptación a este repositorio (no estaba en el original):
#   - Instalar dependencias con:  pip install -r requirements.txt
#     (equivalente, fuera de Jupyter, al %pip install de la celda
#     original)
#   - La ruta de la sección 1 está tal cual se usó originalmente en
#     Windows (unidad D:\...). Editala para que apunte a donde
#     tengas tus datos antes de correr el script.
# ------------------------------------------------------------

# ============================================================
# COMPARACIÓN DTM 2017 vs LiDAR 2024
# BLOQUE 7 - QUÉ TIPOS DE SUPERFICIE RECONOCE EL LiDAR (CLASIFICACIÓN)
# ============================================================
#
# Cada punto de una nube LiDAR trae un campo "classification": un
# código numérico (0-255) que indica qué tipo de superficie
# representa ese punto (terreno, vegetación, agua, edificio, etc.).
# Así es como el .laz "reconoce" tipos de superficie: no analiza
# nada en el momento de abrirlo, cada punto ya viene etiquetado con
# ese código desde el procesamiento del vuelo (el software que usó
# el proveedor — LAStools, TerraScan, u otro equivalente — se lo
# asignó antes de entregarte el archivo). El estándar de referencia
# para esos códigos es el de ASPRS para el formato LAS.
#
# El .lasd de ArcGIS (LIDAR_MVD_2024_J-_LasDataset.lasd) es solo un
# índice/acceso directo a los .laz reales: no se puede leer con
# laspy. Este bloque lee los .laz/.las originales (por defecto, los
# de D:\LiDAR que ya veníamos usando para el Bloque 6) y cuenta
# cuántos puntos hay de cada código de clasificación, en todos los
# archivos, leyendo por bloques para no cargar la nube entera en
# memoria de una vez.
#
# Requiere: pip install laspy lazrs pandas
# (en Jupyter: %pip install laspy lazrs pandas)
# ============================================================
import os
import glob
import numpy as np
import pandas as pd
import laspy
# ------------------------------------------------------------
# 1. CARPETA CON LOS .LAZ ORIGINALES
# ------------------------------------------------------------
carpeta_laz = r"D:\LiDAR\Basurero"
archivos = sorted(
    glob.glob(os.path.join(carpeta_laz, "*.laz"))
    + glob.glob(os.path.join(carpeta_laz, "*.las"))
)
if len(archivos) == 0:
    raise FileNotFoundError(
        "No se encontraron .laz/.las en esa carpeta. Revisar la ruta."
    )
print("=" * 70)
print(f"Archivos a procesar: {len(archivos)}")
print("=" * 70)
for a in archivos:
    print(" -", os.path.basename(a))
# ------------------------------------------------------------
# 2. SIGNIFICADO ESTÁNDAR DE CADA CÓDIGO (ASPRS, LAS 1.4)
# ------------------------------------------------------------
NOMBRES_ASPRS = {
    0: "Nunca clasificado",
    1: "Sin asignar",
    2: "Terreno (ground)",
    3: "Vegetación baja (<0.5 m)",
    4: "Vegetación media (0.5-2 m)",
    5: "Vegetación alta (>2 m)",
    6: "Edificio",
    7: "Punto bajo (ruido)",
    8: "Reservado / model key (según versión de LAS)",
    9: "Agua",
    10: "Riel (vía férrea)",
    11: "Superficie de ruta/carretera",
    12: "Reservado / overlap (según versión de LAS)",
    13: "Cable - guardia",
    14: "Cable - conductor",
    15: "Torre de transmisión",
    16: "Conector de cable (aislador)",
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
        return "Definido por el usuario/proveedor (fuera del estándar ASPRS)"
    return "Reservado (sin uso estándar todavía)"
# ------------------------------------------------------------
# 3. CONTAR PUNTOS POR CÓDIGO, LEYENDO POR BLOQUES (chunks)
# ------------------------------------------------------------
TAMANO_CHUNK = 5_000_000
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
# ------------------------------------------------------------
# 4. TABLA RESUMEN (SOLO CÓDIGOS QUE REALMENTE APARECEN)
# ------------------------------------------------------------
codigos_presentes = np.where(conteo_total > 0)[0]
total_puntos = int(conteo_total.sum())
filas = []
for codigo in codigos_presentes:
    n = int(conteo_total[codigo])
    filas.append(
        {
            "codigo": int(codigo),
            "superficie": nombre_clase(int(codigo)),
            "cantidad_puntos": n,
            "porcentaje": n / total_puntos * 100,
        }
    )
tabla = pd.DataFrame(filas).sort_values("cantidad_puntos", ascending=False)
pd.set_option("display.width", 160)
print("\n" + "=" * 70)
print(f"TIPOS DE SUPERFICIE PRESENTES (total: {total_puntos:,} puntos)")
print("=" * 70)
print(tabla.to_string(index=False))
print("\n" + "=" * 70)
print("CÓMO LO IDENTIFICA")
print("=" * 70)
print(
    "\nCada punto trae este código guardado en su atributo"
    "\n'classification' desde que el proveedor procesó el vuelo — no"
    "\nes algo que ArcGIS ni este script calculen ahora, solo lo"
    "\nleen. El código 2 (terreno) es el que se usa para generar el"
    "\nDTM que veníamos comparando en los Bloques 1-5: vale la pena"
    "\nmirar qué porcentaje del total es código 2, porque de esos"
    "\npuntos sale directamente la superficie que estás analizando."
    "\nEn un humedal, también prestale atención al código 9 (agua):"
    "\nsi tiene un porcentaje considerable, son los puntos más"
    "\npropensos a quedar mal definidos o directamente ausentes en"
    "\nel DTM (el láser no siempre devuelve retorno confiable sobre"
    "\nagua), conectando con la duda de los ceros que veíamos antes."
)
# ------------------------------------------------------------
# 5. DESGLOSE POR ARCHIVO (código 2 = terreno, como referencia)
# ------------------------------------------------------------
print("\n" + "=" * 70)
print("DESGLOSE POR ARCHIVO (% de puntos clasificados como terreno)")
print("=" * 70)
for nombre, conteo in conteo_por_archivo.items():
    total_archivo = int(conteo.sum())
    terreno = int(conteo[2]) if len(conteo) > 2 else 0
    pct = (terreno / total_archivo * 100) if total_archivo > 0 else 0
    print(
        f"{nombre}: {terreno:,} de {total_archivo:,} puntos son "
        f"terreno ({pct:.1f}%)"
    )
