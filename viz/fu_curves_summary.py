"""Grafico Fu(t) resumen del punto 1.2: solo mesa vacia + la mejor
configuracion de cada una de las 3 familias finales (para la familia B se
incluyen tanto el mejor radio como la mejor posicion), en vez de todas las
corridas exploratorias que fu_curves.json va acumulando (barridos de R y de
posicion, y las variantes descartadas de la familia C -- embudo, guias,
elipse; ver conversacion). Para debug/explorar todo lo guardado, seguir
usando `python3 viz/fu_curves.py` directamente.

Requiere que estos scripts ya se hayan corrido al menos una vez (para que
sus curvas queden guardadas en fu_curves.json bajo estas etiquetas):
  configuration_comparison.py     -> "x=0.6"            (familia A, posicion)
  radius_comparison.py            -> "R=0.339"          (familia A, radio)
  flanking_circles_comparison.py  -> "embudo_r=0.02"    (familia B, radio)
  flanking_position_comparison.py -> "embudo_gap=0.45"  (familia B, posicion)
  goal_semicircle_comparison.py   -> "competencia_R=0.3" (familia C)
"""
from fu_curves import plot_curves

SUMMARY_LABELS = [
    "mesa_vacia",
    "x=0.6",              # familia A: mejor posicion (K=1)
    "R=0.339",             # familia A: mejor radio (K=1)
    "embudo_r=0.02",       # familia B: mejor radio de los circulos chicos
    "embudo_gap=0.45",     # familia B: mejor posicion de los circulos chicos
    "competencia_R=0.3",   # familia C: mejor semicirculo libre
]

if __name__ == "__main__":
    plot_curves(labels=SUMMARY_LABELS, name="resumen_1_2")
