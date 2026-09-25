"""Grafico Fu(t) resumen del punto 1.2: mesa vacia + UN representante final por
cada una de las 3 familias (no uno por cada eje explorado dentro de una
familia), en vez de todas las corridas exploratorias que fu_curves.json va
acumulando. Para debug/explorar todo lo guardado, seguir usando
`python3 viz/fu_curves.py` directamente.

x=0.6 (familia A, barrido de posicion con un radio de referencia todavia sin
optimizar) y embudo_r=0.02 (familia B, circulos chicos tangentes con gap
todavia sin optimizar) quedaron afuera a proposito: son resultados
INTERMEDIOS de sus respectivos barridos, ya superados por R=0.339 (misma
posicion x=0.6=L/2, radio ya optimizado) y embudo_gap=0.45 (mismo radio chico
0.02, gap ya optimizado) -- mismo criterio que se uso para armar diffusion.py
(punto 1.3), ver ese script.

Requiere que estos scripts ya se hayan corrido al menos una vez (para que sus
curvas queden guardadas en fu_curves.json bajo estas etiquetas):
  radius_comparison.py            -> "R=0.339"           (familia A, final)
  flanking_position_comparison.py -> "embudo_gap=0.45"    (familia B, final)
  goal_semicircle_comparison.py   -> "competencia_R=0.3"  (familia C, final)
"""
from fu_curves import plot_curves

SUMMARY_LABELS = [
    "mesa_vacia",
    "R=0.339",             # familia A: obstaculo unico, posicion y radio ya optimizados
    "embudo_gap=0.45",     # familia B: circulo grande + 2 chicos, radio y gap ya optimizados
    "competencia_R=0.3",   # familia C: relleno + semicirculos libres, radio ya optimizado
]

if __name__ == "__main__":
    plot_curves(labels=SUMMARY_LABELS, name="resumen_1_2")
