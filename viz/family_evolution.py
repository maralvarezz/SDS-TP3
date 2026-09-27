"""Punto 1.2: panel "evolucion temporal (Fu(t))" por familia, para el esquema
de presentacion pedido por la catedra (animacion caracteristica + evolucion
temporal de particulas convertidas + input vs observable <t90>, por
familia, y comparacion final de los 3 mejores ejemplares).

No corre Java: reusa las curvas Fu(t) que fu_curves.py ya tiene cacheadas
(fu_curves.json) de cuando se corrieron radius_comparison.py,
flanking_position_comparison.py y goal_semicircle_comparison.py. Cada panel
muestra unicamente mesa vacia + el representante FINAL de esa familia (no
todo el barrido -- eso ya se ve en el "input vs observable" de cada
familia).
"""
from fu_curves import plot_curves

FAMILIES = [
    ("familia_A_obstaculo_unico", ["mesa_vacia", "R=0.339"]),
    ("familia_B_embudo", ["mesa_vacia", "embudo_gap=0.45"]),
    ("familia_C_competencia", ["mesa_vacia", "competencia_R=0.3"]),
]

if __name__ == "__main__":
    for name, labels in FAMILIES:
        path = plot_curves(labels=labels, name=name)
        print(f"{name}: {path}")
