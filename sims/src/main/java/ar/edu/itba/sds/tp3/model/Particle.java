package ar.edu.itba.sds.tp3.model;

import java.util.Objects;

/** Estado inmutable de una particula en un instante. */
public record Particle(int id, Vector2D position, Vector2D velocity,
                       double radius, double mass, ParticleState state) {
    public Particle {
        if (id < 0 || !Double.isFinite(radius) || radius <= 0 || !Double.isFinite(mass) || mass <= 0) {
            throw new IllegalArgumentException("Id, radio o masa de particula invalidos");
        }
        Objects.requireNonNull(position);
        Objects.requireNonNull(velocity);
        Objects.requireNonNull(state);
    }
}
