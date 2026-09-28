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
