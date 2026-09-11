package ar.edu.itba.sds.tp3.model;

public record Vector2D(double x, double y) {
    public Vector2D {
        if (!Double.isFinite(x) || !Double.isFinite(y)) {
            throw new IllegalArgumentException("Las componentes del vector deben ser finitas");
        }
    }

    public Vector2D add(Vector2D other) {
        return new Vector2D(x + other.x, y + other.y);
    }

    public Vector2D scale(double factor) {
        return new Vector2D(x * factor, y * factor);
    }

    public double distanceTo(Vector2D other) {
        return Math.hypot(x - other.x, y - other.y);
    }

    public double magnitude() {
        return Math.hypot(x, y);
    }
}
