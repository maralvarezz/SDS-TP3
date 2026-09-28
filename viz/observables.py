from common import one_file, rows


def t90_from_goals(directory):
    for row in rows(one_file(directory, "goals_*.csv")):
        if float(row["usedFraction"]) >= 0.9:
            return float(row["time"])
    return None
