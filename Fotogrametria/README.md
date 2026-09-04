# Fotogrametría con dron: línea de base de una plantación forestal

## Objetivo

Establecer una línea de base del desarrollo de una plantación forestal recientemente implantada, que permita realizar el seguimiento de su crecimiento a lo largo del tiempo.

## Metodología

Con la finalidad de abordar el objetivo propuesto, se generaron los productos fotogramétricos: nube de puntos, modelo digital de superficie (MDS) y ortomosaico, sobre una plantación forestal recientemente implantada, de modo que puedan compararse con relevamientos posteriores para evaluar su desarrollo. El establecimiento se encuentra a próximo (⁓22 Km) a la ciudad de Rivera (Uruguay) y el predio forestado alcanza las 22 ha (Fig. 1).

Se utilizaron 275 imágenes aéreas RGB obtenidas en mayo de 2023 mediante un vuelo (altura media 81 m, área cubierta 38 ha) realizado con el vehículo aéreo no tripulado DJI Phantom 4 Pro, equipado con una cámara FC6310, distancia focal de 8,8 mm, resolución de 4864 × 3648 píxeles, y su posterior procesamiento en el software Pix4Dmapper 4.6.4 (plantilla 3D Maps) mediante el flujo estándar de *structure from motion*. El sistema de coordenadas de salida fue WGS84 / UTM zona 21S (EGM96), con alturas ortométricas referidas al modelo de geoide EGM96. El ortomosaico y el MDS fueron generados a una resolución espacial de 2,5 cm/píxel.

<p align="center">
  <img src="img/Figura_1.jpg" alt="Área de estudio" width="420"><br>
  <em><b>Figura 1.</b> Área de estudio</em>
</p>

## Resultados

El vuelo realizado en mayo 2023 permitió realizar procedimientos fotogramétricos y obtener los insumos fundamentales para poder realizarle el seguimiento al cultivo forestal. Los resultados del ortomosaico (Fig. 2), y del MDS (Fig. 3) y de la nube de puntos (Fig. 4) permiten observar la reciente implantación, lo cual es fundamental para el objetivo propuesto ya que el MDS y la nube de puntos fueron generados mediante imágenes ópticas (RGB), por lo tanto, en una plantación forestal corresponden a las alturas resultantes de vegetación/copa + elevación del terreno (MDT). Dado que las imágenes fueron obtenidas cuando la forestación se encontraba la etapa inicial de su desarrollo, el MDS obtenido es similar al MDT y se puede considerar como la base sobre la cual comparar futuros MDS obtenidos a lo largo de los años para evaluar el progreso del crecimiento. El detalle de los parámetros de procesamiento y los resultados de calidad de los productos obtenidos queda disponible en: <https://github.com/BernardoZabaleta/TGEO/blob/main/Fotogrametria/Quality_report.pdf>

<p align="center">
  <img src="img/Figura_2.jpg" alt="Ortomosaico del área de estudio" width="560"><br>
  <em><b>Figura 2.</b> Ortomosaico del área de estudio, generado por fotogrametría a partir de 275 imágenes aéreas RGB adquiridas con un vehículo aéreo no tripulado en mayo de 2023</em>
</p>

<p align="center">
  <img src="img/Figura_3.jpg" alt="Modelo digital de superficie del área de estudio" width="560"><br>
  <em><b>Figura 3.</b> Modelo digital de superficie del área de estudio, generado por fotogrametría a partir de 275 imágenes aéreas RGB adquiridas con un vehículo aéreo no tripulado en mayo de 2023</em>
</p>

<p align="center">
  <img src="img/Figura_4.jpg" alt="Nube de puntos densa del área de estudio" width="560"><br>
  <em><b>Figura 4.</b> Nube de puntos densa del área de estudio, generada por fotogrametría a partir de 275 imágenes aéreas RGB adquiridas con vehículo aéreo no tripulado en mayo de 2023 (40,3 millones de puntos; densidad media de 107 puntos/m²)</em>
</p>
