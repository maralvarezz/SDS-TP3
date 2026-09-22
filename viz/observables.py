"""Observables agregados derivados en postproceso a partir de los outputs
crudos que ya escribe Java (goals_*.csv). El motor Java no calcula ni
persiste ningun observable agregado sobre la corrida: unicamente registra
eventos (ver AGENTS.md, secciones 2 y 13).
"""
from common import one_file, rows


def t90_from_goals(directory):
    """t90 = primer instante (evento) en el que Fu = totalGoals / N >= 0.90,
    leido directamente de goals_*.csv de la corrida (requiere writeGoals=true
    para esa corrida). No interpola entre eventos: el tiempo del evento en el
    que se alcanza el 90% es t90 (AGENTS.md, seccion 13).

    Devuelve None si la corrida no alcanzo Fu >= 0.90 antes de terminar.
    """
    for row in rows(one_file(directory, "goals_*.csv")):
        if float(row["usedFraction"]) >= 0.9:
            return float(row["time"])
    return None
