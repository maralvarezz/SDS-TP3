package ar.edu.itba.sds.tp3.config;

public record ParticleParameters(int count, double radius, double mass, double initialSpeed) {
    public ParticleParameters {
        Validation.require(count > 0, "particles.count debe ser positivo");
        Validation.positive(radius, "particles.radius");
        Validation.positive(mass, "particles.mass");
        Validation.positive(initialSpeed, "particles.initialSpeed");
    }
}
