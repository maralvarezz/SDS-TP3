package ar.edu.itba.sds.tp3.config;

public record SimulationParameters(double length, double width, double goalSize,
                                   double maxTime, Long seed) {
    public SimulationParameters {
        Validation.positive(length, "simulation.length");
        Validation.positive(width, "simulation.width");
        Validation.positive(goalSize, "simulation.goalSize");
        Validation.positive(maxTime, "simulation.maxTime");
        Validation.require(goalSize <= width, "goalSize debe ser <= width");
    }
}
