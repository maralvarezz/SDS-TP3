package ar.edu.itba.sds.tp3.config;

public record ObstacleConfig(double x, double y, double radius) {
    public ObstacleConfig {
        Validation.require(Double.isFinite(x) && Double.isFinite(y),
                "Las coordenadas del obstaculo deben ser finitas");
        Validation.positive(radius, "obstacle.radius");
    }
}
