package ar.edu.itba.sds.tp3;

import ar.edu.itba.sds.tp3.model.*;
import ar.edu.itba.sds.tp3.physics.MotionUpdater;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class MotionUpdaterTest {
    @Test
    void freeFlightUpdatesPositionsAndTimeOnly() {
        var particle = new Particle(0, new Vector2D(1, 2), new Vector2D(3, -1), 0.1, 1, ParticleState.FRESH);
        var initial = new SimulationState(2, List.of(particle), List.of());
        var result = new MotionUpdater().advanceTo(initial, 4);
        assertEquals(new Vector2D(7, 0), result.particles().getFirst().position());
        assertEquals(particle.velocity(), result.particles().getFirst().velocity());
        assertEquals(particle.state(), result.particles().getFirst().state());
        assertEquals(4, result.time());
        assertEquals(new Vector2D(1, 2), initial.particles().getFirst().position());
        assertThrows(IllegalArgumentException.class, () -> new MotionUpdater().advanceTo(initial, 1));
    }
}
