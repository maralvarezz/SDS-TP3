package ar.edu.itba.sds.tp3.model;

import java.util.Objects;

/** Obstaculo circular fijo: no posee velocidad ni masa finita. */
public record Obstacle(int id, Vector2D position, double radius) {
    public Obstacle {
        Objects.requireNonNull(position);
        if (id < 0 || !Double.isFinite(radius) || radius <= 0) {
            throw new IllegalArgumentException("Id o radio de obstaculo invalido");
        }
    }
}
