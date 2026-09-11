package ar.edu.itba.sds.tp3.model;

import java.util.List;

public record SimulationState(double time, List<Particle> particles, List<Obstacle> obstacles) {
    public SimulationState {
        if (!Double.isFinite(time) || time < 0) throw new IllegalArgumentException("Tiempo invalido");
        particles = List.copyOf(particles);
        obstacles = List.copyOf(obstacles);
    }
}
