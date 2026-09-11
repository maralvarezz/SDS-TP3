package ar.edu.itba.sds.tp3.physics;

import ar.edu.itba.sds.tp3.model.Particle;
import ar.edu.itba.sds.tp3.model.SimulationState;

/** Vuelo libre hasta el instante del proximo evento. */
public final class MotionUpdater {
    public SimulationState advanceTo(SimulationState state, double time) {
        if (!Double.isFinite(time) || time < state.time()) {
            throw new IllegalArgumentException("El tiempo destino debe ser finito y no anterior al actual");
        }
        double elapsed = time - state.time();
        var particles = state.particles().stream()
                .map(p -> new Particle(p.id(), p.position().add(p.velocity().scale(elapsed)),
                        p.velocity(), p.radius(), p.mass(), p.state()))
                .toList();
        return new SimulationState(time, particles, state.obstacles());
    }
}
