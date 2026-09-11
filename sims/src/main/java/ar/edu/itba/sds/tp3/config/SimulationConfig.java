package ar.edu.itba.sds.tp3.config;

import java.util.List;

public record SimulationConfig(SimulationParameters simulation, ParticleParameters particles,
                               OutputParameters output, List<ObstacleConfig> obstacles) {
    public SimulationConfig {
        Validation.require(simulation != null && particles != null && output != null && obstacles != null,
                "Se requieren simulation, particles, output y obstacles");
        obstacles = List.copyOf(obstacles);
        Validation.require(2 * particles.radius() < Math.min(simulation.length(), simulation.width()),
                "El diametro de las particulas debe ser menor que las dimensiones de la mesa");
        for (int i = 0; i < obstacles.size(); i++) {
            var obstacle = obstacles.get(i);
            double radius = obstacle.radius();
            Validation.require(radius >= particles.radius(), "Obstaculo " + i + ": radio menor al de particula");
            Validation.require(obstacle.x() >= radius && obstacle.x() <= simulation.length() - radius
                            && obstacle.y() >= radius && obstacle.y() <= simulation.width() - radius,
                    "Obstaculo " + i + ": fuera de la mesa");
            for (int j = 0; j < i; j++) {
                var other = obstacles.get(j);
                Validation.require(Math.hypot(obstacle.x() - other.x(), obstacle.y() - other.y())
                                >= radius + other.radius(),
                        "Obstaculos solapados: " + j + " y " + i);
            }
        }
    }

    public SimulationConfig withSeed(long seed) {
        return new SimulationConfig(new SimulationParameters(simulation.length(), simulation.width(),
                simulation.goalSize(), simulation.maxTime(), seed), particles, output, obstacles);
    }
}
