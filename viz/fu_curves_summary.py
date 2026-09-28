from fu_curves import plot_curves

SUMMARY_LABELS = [
    "mesa_vacia",
    "R=0.339",
    "embudo_gap=0.45",
    "competencia_R=0.3",
]

if __name__ == "__main__":
    plot_curves(labels=SUMMARY_LABELS, name="resumen_1_2")
