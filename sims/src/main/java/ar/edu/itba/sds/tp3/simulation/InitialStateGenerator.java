package ar.edu.itba.sds.tp3.simulation;

import ar.edu.itba.sds.tp3.config.SimulationConfig;
import ar.edu.itba.sds.tp3.model.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public final class InitialStateGenerator {
    // Limite de trabajo por particula, no un parametro fisico.
    private static final int MAX_ATTEMPTS_PER_PARTICLE = 100_000;

    public SimulationState generate(SimulationConfig config) {
        if (config.simulation().seed() == null) {
            throw new IllegalArgumentException("Resolver la seed antes de generar el estado inicial");
        }
        var random = new Random(config.simulation().seed());
        var obstacles = new ArrayList<Obstacle>();
        for (int i = 0; i < config.obstacles().size(); i++) {
            var obstacle = config.obstacles().get(i);
            obstacles.add(new Obstacle(i, new Vector2D(obstacle.x(), obstacle.y()), obstacle.radius()));
        }
        var particles = new ArrayList<Particle>();
        var parameters = config.particles();
        double radius = parameters.radius();
        for (int id = 0; id < parameters.count(); id++) {
            Vector2D position = null;
            for (int attempt = 0; attempt < MAX_ATTEMPTS_PER_PARTICLE; attempt++) {
                var candidate = new Vector2D(
                        radius + random.nextDouble() * (config.simulation().length() - 2 * radius),
                        radius + random.nextDouble() * (config.simulation().width() - 2 * radius));
                if (isAvailable(candidate, radius, particles, obstacles)) {
                    position = candidate;
                    break;
                }
            }
            if (position == null) {
                throw new IllegalArgumentException("No se pudo ubicar la particula " + id + " de "
                        + parameters.count() + " tras " + MAX_ATTEMPTS_PER_PARTICLE
                        + " intentos. Revisar densidad y obstaculos. Seed: " + config.simulation().seed());
            }
            double angle = random.nextDouble() * 2 * Math.PI;
            var velocity = new Vector2D(parameters.initialSpeed() * Math.cos(angle),
                    parameters.initialSpeed() * Math.sin(angle));
            particles.add(new Particle(id, position, velocity, radius, parameters.mass(), ParticleState.FRESH));
        }
        return new SimulationState(0, particles, obstacles);
    }

    private boolean isAvailable(Vector2D position, double radius,
                                List<Particle> particles, List<Obstacle> obstacles) {
        // Se rechaza todo solapamiento inicial; no se relajan las distancias con tolerancias.
        for (var particle : particles) {
            if (position.distanceTo(particle.position()) < radius + particle.radius()) return false;
        }
        for (var obstacle : obstacles) {
            if (position.distanceTo(obstacle.position()) < radius + obstacle.radius()) return false;
        }
        return true;
    }
}
