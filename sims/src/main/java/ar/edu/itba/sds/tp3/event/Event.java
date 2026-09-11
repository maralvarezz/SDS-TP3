package ar.edu.itba.sds.tp3.event;

/** Indices de entidades y versiones de velocidad al predecir el choque; -1 significa ausente. */
public record Event(double time, EventType type, int particleA, int particleB,
                    int obstacle, Wall wall, long versionA, long versionB)
        implements Comparable<Event> {
    public Event {
        if (!Double.isFinite(time) || time < 0 || type == null) {
            throw new IllegalArgumentException("Evento invalido");
        }
    }

    public boolean isValid(long[] versions) {
        return (particleA < 0 || versions[particleA] == versionA)
                && (particleB < 0 || versions[particleB] == versionB);
    }

    @Override
    public int compareTo(Event other) {
        int result = Double.compare(time, other.time);
        if (result == 0) result = type.compareTo(other.type);
        if (result == 0) result = Integer.compare(particleA, other.particleA);
        if (result == 0) result = Integer.compare(particleB, other.particleB);
        if (result == 0) result = Integer.compare(obstacle, other.obstacle);
        if (result == 0) result = Integer.compare(wall == null ? -1 : wall.ordinal(),
                other.wall == null ? -1 : other.wall.ordinal());
        return result;
    }
}
