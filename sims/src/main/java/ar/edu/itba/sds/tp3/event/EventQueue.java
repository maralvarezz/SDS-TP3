package ar.edu.itba.sds.tp3.event;

import ar.edu.itba.sds.tp3.config.SimulationParameters;
import ar.edu.itba.sds.tp3.model.SimulationState;
import ar.edu.itba.sds.tp3.physics.CollisionTimeCalculator;

import java.util.PriorityQueue;

public final class EventQueue {
    private final PriorityQueue<Event> events = new PriorityQueue<>();
    private final CollisionTimeCalculator calculator = new CollisionTimeCalculator();
    private final SimulationParameters parameters;
    private final long[] versions;
    private final long cleanupThreshold;

    public EventQueue(SimulationState state, SimulationParameters parameters) {
        this.parameters = parameters;
        this.versions = new long[state.particles().size()];
        long n = versions.length;
        // Eliminar periodicamente predicciones obsoletas sin recalcular las vigentes.
        cleanupThreshold = Math.max(64, 4 * (n * (n - 1) / 2 + n * (state.obstacles().size() + 4L) + 1));
        events.add(new Event(parameters.maxTime(), EventType.SIMULATION_END, -1, -1, -1, null, -1, -1));
        for (int a = 0; a < versions.length; a++) {
            scheduleBoundaries(state, a);
            for (int b = a + 1; b < versions.length; b++) schedulePair(state, a, b);
        }
    }

    public Event next() {
        while (!events.isEmpty()) {
            Event event = events.remove();
            if (event.isValid(versions)) return event;
        }
        throw new IllegalStateException("La cola perdio el evento de fin de simulacion");
    }

    public void updateAfter(Event collision, SimulationState state) {
        int a = collision.particleA(), b = collision.particleB();
        versions[a]++;
        if (b >= 0) versions[b]++;
        scheduleParticle(state, a, -1);
        // La pareja a-b ya fue recalculada al procesar a.
        if (b >= 0) scheduleParticle(state, b, a);
        if (events.size() > cleanupThreshold) events.removeIf(event -> !event.isValid(versions));
    }

    private void scheduleParticle(SimulationState state, int particle, int skip) {
        scheduleBoundaries(state, particle);
        for (int other = 0; other < versions.length; other++) {
            if (other != particle && other != skip) schedulePair(state, Math.min(particle, other), Math.max(particle, other));
        }
    }

    private void schedulePair(SimulationState state, int a, int b) {
        add(state.time(), calculator.particles(state.particles().get(a), state.particles().get(b)),
                EventType.PARTICLE_PARTICLE, a, b, -1, null);
    }

    private void scheduleBoundaries(SimulationState state, int a) {
        var particle = state.particles().get(a);
        for (Wall wall : Wall.values()) {
            var type = wall == Wall.LEFT || wall == Wall.RIGHT
                    ? EventType.PARTICLE_VERTICAL_WALL : EventType.PARTICLE_HORIZONTAL_WALL;
            add(state.time(), calculator.wall(particle, wall, parameters), type, a, -1, -1, wall);
        }
        for (int k = 0; k < state.obstacles().size(); k++) {
            add(state.time(), calculator.obstacle(particle, state.obstacles().get(k)),
                    EventType.PARTICLE_OBSTACLE, a, -1, k, null);
        }
    }

    private void add(double now, double delay, EventType type, int a, int b, int obstacle, Wall wall) {
        if (!Double.isFinite(delay)) return;
        if (delay < 0) throw new IllegalStateException("Tiempo de choque negativo");
        double time = now + delay;
        if (time > parameters.maxTime()) return;
        events.add(new Event(time, type, a, b, obstacle, wall, versions[a], b < 0 ? -1 : versions[b]));
    }
}
