package ar.edu.itba.sds.tp3.simulation;

import ar.edu.itba.sds.tp3.config.SimulationConfig;
import ar.edu.itba.sds.tp3.event.*;
import ar.edu.itba.sds.tp3.model.*;
import ar.edu.itba.sds.tp3.physics.*;

import java.io.IOException;
import java.util.ArrayList;

public final class Simulation {
    // Guardia contra contactos degenerados que no permiten avanzar el tiempo.
    private static final int MAX_EVENTS_AT_SAME_TIME = 100_000;

    public SimulationResult run(SimulationConfig config, SimulationState initial,
                                SimulationObserver observer) throws IOException {
        long started = System.nanoTime();
        var queue = new EventQueue(initial, config.simulation());
        var motion = new MotionUpdater();
        var resolver = new CollisionResolver();
        var state = initial;
        long totalEvents = 0;
        int totalGoals = 0;
        Double t90 = null;
        int sameTimeEvents = 0;
        observer.state(state, 0);
        while (true) {
            Event event = queue.next();
            if (event.time() < state.time()) throw new IllegalStateException("Evento valido en el pasado");
            sameTimeEvents = event.time() == state.time() ? sameTimeEvents + 1 : 0;
            if (sameTimeEvents > MAX_EVENTS_AT_SAME_TIME) {
                throw new IllegalStateException("Demasiados contactos simultaneos en t=" + state.time());
            }
            state = motion.advanceTo(state, event.time());
            if (event.type() == EventType.SIMULATION_END) {
                // Frame final obligatorio; el escritor evita duplicar un frame ya emitido.
                observer.state(state, totalEvents);
                break;
            }
            state = resolver.resolve(state, event);
            totalEvents++;
            var particle = state.particles().get(event.particleA());
            if (event.type() == EventType.PARTICLE_VERTICAL_WALL
                    && particle.state() == ParticleState.FRESH
                    && Math.abs(particle.position().y() - config.simulation().width() / 2)
                    <= config.simulation().goalSize() / 2) {
                var particles = new ArrayList<>(state.particles());
                particles.set(event.particleA(), new Particle(particle.id(), particle.position(),
                        particle.velocity(), particle.radius(), particle.mass(), ParticleState.USED));
                state = new SimulationState(state.time(), particles, state.obstacles());
                totalGoals++;
                double fraction = (double) totalGoals / state.particles().size();
                if (t90 == null && fraction >= 0.9) t90 = state.time();
                observer.goal(state.time(), totalEvents, particle.id(), event.wall(), totalGoals, fraction);
            }
            observer.collision(state, event, totalEvents);
            if (totalEvents % config.output().everyEvents() == 0) observer.state(state, totalEvents);
            queue.updateAfter(event, state);
        }
        return new SimulationResult(state, totalEvents, totalGoals, t90,
                (System.nanoTime() - started) / 1_000_000.0);
    }
}
