# resultados/rasters/

Esta carpeta todavía está vacía en este paquete inicial: acá van los
archivos reales que generan los scripts de `scripts/` al correrlos en tu
máquina. No se incluyen en este paquete porque son datos generados
localmente (y pueden pesar bastante).

| Archivo a copiar acá | Lo genera | Qué es |
|---|---|---|
| `edificios_lidar_2024_2_5m.tif` | `scripts/bloque_08_raster_edificios_2024.py` | Altura (Z) más alta por celda de 2.5 m, usando solo los puntos LiDAR 2024 clasificados como edificio (código ASPRS 6). |
| `mds_2019_mosaico.tif` | `scripts/bloque_09_mosaico_mds_2019.py` | Mosaico del Modelo de Superficie 2019, remuestreado de su resolución nativa (10 cm) a 2.5 m con `Resampling.max`. |
| `diferencia_edificios_2024_menos_mds_2019.tif` | `scripts/bloque_10_diferencia_alturas.py` | Diferencia de altura (2024 − 2019), restringida a las celdas donde el LiDAR 2024 detectó edificio. Este es el resultado principal del análisis de desarrollo vertical. |

## Antes de agregar estos archivos al repositorio

Estos `.tif` se versionan con **Git LFS** (ya configurado en
`.gitattributes`, con el alcance limitado a esta carpeta). Instalá
Git LFS una sola vez por máquina:

```
git lfs install
```

Después, copiá los tres archivos acá y agregalos como a cualquier otro
archivo (`git add`, `git commit`, `git push`) — el `.gitattributes` se
encarga de que viajen por LFS y no infle el historial del repositorio.
Los pasos completos están en el README principal, sección
"Publicar el repositorio en GitHub (Windows)".

**Nota sobre cuotas:** el plan gratuito de GitHub para Git LFS incluye
1 GB de almacenamiento y 1 GB de transferencia por mes. Si los tres
rasters combinados superan eso, vas a necesitar comprar más cuota de
LFS o comprimir/recortar los rasters antes de subirlos.
