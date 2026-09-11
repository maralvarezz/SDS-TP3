package ar.edu.itba.sds.tp3.event;

/** El orden tambien define el desempate entre eventos simultaneos. */
public enum EventType {
    PARTICLE_PARTICLE,
    PARTICLE_VERTICAL_WALL,
    PARTICLE_HORIZONTAL_WALL,
    PARTICLE_OBSTACLE,
    SIMULATION_END
}
