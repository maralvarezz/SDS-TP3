package ar.edu.itba.sds.tp3.physics;

import ar.edu.itba.sds.tp3.event.Event;
import ar.edu.itba.sds.tp3.model.*;

import java.util.ArrayList;

public final class CollisionResolver {
    public SimulationState resolve(SimulationState state, Event event) {
        var particles = new ArrayList<>(state.particles());
        var a = particles.get(event.particleA());
        var velocity = a.velocity();
        switch (event.type()) {
            case PARTICLE_VERTICAL_WALL -> velocity = new Vector2D(-velocity.x(), velocity.y());
            case PARTICLE_HORIZONTAL_WALL -> velocity = new Vector2D(velocity.x(), -velocity.y());
            case PARTICLE_OBSTACLE -> {
                var center = state.obstacles().get(event.obstacle()).position();
                double dx = a.position().x() - center.x(), dy = a.position().y() - center.y();
                double distance = Math.hypot(dx, dy);
                double nx = dx / distance, ny = dy / distance;
                double normalSpeed = velocity.x() * nx + velocity.y() * ny;
                velocity = new Vector2D(velocity.x() - 2 * normalSpeed * nx,
                        velocity.y() - 2 * normalSpeed * ny);
            }
            case PARTICLE_PARTICLE -> {
                var b = particles.get(event.particleB());
                double dx = b.position().x() - a.position().x(), dy = b.position().y() - a.position().y();
                double distance = Math.hypot(dx, dy);
                double nx = dx / distance, ny = dy / distance;
                double relativeNormalSpeed = (b.velocity().x() - velocity.x()) * nx
                        + (b.velocity().y() - velocity.y()) * ny;
                // Impulso elastico de Teorica 3, diap. 20, usando la normal unitaria de contacto.
                double impulse = 2 * a.mass() * b.mass() * relativeNormalSpeed / (a.mass() + b.mass());
                velocity = new Vector2D(velocity.x() + impulse * nx / a.mass(),
                        velocity.y() + impulse * ny / a.mass());
                var bVelocity = new Vector2D(b.velocity().x() - impulse * nx / b.mass(),
                        b.velocity().y() - impulse * ny / b.mass());
                particles.set(event.particleB(), withVelocity(b, bVelocity));
            }
            case SIMULATION_END -> throw new IllegalArgumentException("El fin de simulacion no es una colision");
        }
        particles.set(event.particleA(), withVelocity(a, velocity));
        return new SimulationState(state.time(), particles, state.obstacles());
    }

    private Particle withVelocity(Particle particle, Vector2D velocity) {
        return new Particle(particle.id(), particle.position(), velocity, particle.radius(), particle.mass(), particle.state());
    }
}
