package ar.edu.itba.sds.tp3.simulation;

import ar.edu.itba.sds.tp3.model.SimulationState;

public record SimulationResult(SimulationState state, long totalEvents, int totalGoals,
                               double runtimeMilliseconds) {}
