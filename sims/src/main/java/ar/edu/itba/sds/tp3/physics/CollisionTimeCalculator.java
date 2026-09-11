package ar.edu.itba.sds.tp3.physics;

import ar.edu.itba.sds.tp3.model.*;
import ar.edu.itba.sds.tp3.event.Wall;
import ar.edu.itba.sds.tp3.config.SimulationParameters;

import static ar.edu.itba.sds.tp3.physics.Numerics.EPSILON;

public final class CollisionTimeCalculator {
    public double wall(Particle particle, Wall wall, SimulationParameters table) {
        double gap;
        double speed;
        switch (wall) {
            case LEFT -> { gap = particle.position().x() - particle.radius(); speed = -particle.velocity().x(); }
            case RIGHT -> { gap = table.length() - particle.radius() - particle.position().x(); speed = particle.velocity().x(); }
            case BOTTOM -> { gap = particle.position().y() - particle.radius(); speed = -particle.velocity().y(); }
            case TOP -> { gap = table.width() - particle.radius() - particle.position().y(); speed = particle.velocity().y(); }
            default -> throw new IllegalArgumentException("Pared desconocida");
        }
        if (gap < -EPSILON) throw new IllegalStateException("Particula " + particle.id() + " fuera de la mesa");
        if (speed <= 0) return Double.POSITIVE_INFINITY;
        // Un contacto redondeado apenas fuera del dominio se resuelve ahora, sin mover la pared.
        return Math.max(0, gap) / speed;
    }

    public double particles(Particle a, Particle b) {
        return circles(a.position(), a.velocity(), b.position(), b.velocity(), a.radius() + b.radius());
    }

    public double obstacle(Particle particle, Obstacle obstacle) {
        return circles(particle.position(), particle.velocity(), obstacle.position(),
                new Vector2D(0, 0), particle.radius() + obstacle.radius());
    }

    private double circles(Vector2D a, Vector2D va, Vector2D b, Vector2D vb, double sigma) {
        double dx = b.x() - a.x(), dy = b.y() - a.y();
        double vx = vb.x() - va.x(), vy = vb.y() - va.y();
        double distance = Math.hypot(dx, dy);
        if (distance < sigma - EPSILON) throw new IllegalStateException("Solapamiento durante la simulacion");
        double approach = dx * vx + dy * vy;
        if (approach >= 0) return Double.POSITIVE_INFINITY;
        // Contacto inmediato solo si los cuerpos se aproximan: permite resolver esquinas y empates.
        if (distance <= sigma) return 0;
        double speedSquared = vx * vx + vy * vy;
        if (speedSquared == 0) return Double.POSITIVE_INFINITY;
        double separation = (distance - sigma) * (distance + sigma);
        double discriminant = approach * approach - speedSquared * separation;
        // Una tangencia exacta no intercambia impulso. Un discriminante negativo no es choque.
        if (discriminant <= 0) return Double.POSITIVE_INFINITY;
        // Raiz menor de Teorica 3, diap. 14, racionalizada para evitar cancelacion cerca del contacto.
        return separation / (-approach + Math.sqrt(discriminant));
    }
}
