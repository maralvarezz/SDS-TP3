package ar.edu.itba.sds.tp3.config;

final class Validation {
    private Validation() {}

    static void positive(double value, String name) {
        require(Double.isFinite(value) && value > 0, name + " debe ser finito y positivo");
    }

    static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
}
