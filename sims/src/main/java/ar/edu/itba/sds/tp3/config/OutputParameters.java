package ar.edu.itba.sds.tp3.config;

public record OutputParameters(int everyEvents, boolean writeStates,
                               boolean writeGoals, boolean writeCollisions) {
    public OutputParameters {
        Validation.require(everyEvents > 0, "output.everyEvents debe ser positivo");
    }
}
