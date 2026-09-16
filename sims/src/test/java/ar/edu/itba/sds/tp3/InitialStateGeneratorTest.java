package ar.edu.itba.sds.tp3;

import ar.edu.itba.sds.tp3.config.*;
import ar.edu.itba.sds.tp3.model.*;
import ar.edu.itba.sds.tp3.simulation.InitialStateGenerator;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class InitialStateGeneratorTest {
    private SimulationConfig config(List<ObstacleConfig> obstacles) {
        return new SimulationConfig(new SimulationParameters(1.20, 0.68, 0.20, 30, 12345L),
                new ParticleParameters(100, 0.0175, 0.025, 1),
                new OutputParameters(10, true, true, false), obstacles);
    }

    @Test
    void sameSeedProducesSameState() {
        var generator = new InitialStateGenerator();
        var config = config(List.of());
        assertEquals(generator.generate(config), generator.generate(config));
        assertNotEquals(generator.generate(config), generator.generate(config.withSeed(67890)));
    }

    @Test
    void particlesStartInsideTableWithoutOverlapsAndWithRequestedSpeed() {
        var config = config(List.of(new ObstacleConfig(0.6, 0.34, 0.05)));
        var state = new InitialStateGenerator().generate(config);
        assertEquals(100, state.particles().size());
        assertEquals(0, state.time());
        for (var p : state.particles()) {
            assertEquals(ParticleState.FRESH, p.state());
            assertEquals(config.particles().initialSpeed(), p.velocity().magnitude(), 1e-12);
            assertTrue(p.position().x() >= p.radius());
            assertTrue(p.position().x() <= config.simulation().length() - p.radius());
            assertTrue(p.position().y() >= p.radius());
            assertTrue(p.position().y() <= config.simulation().width() - p.radius());
            for (var q : state.particles()) {
                if (p.id() != q.id()) assertTrue(p.position().distanceTo(q.position()) >= p.radius() + q.radius());
            }
            for (var obstacle : state.obstacles()) {
                assertTrue(p.position().distanceTo(obstacle.position()) >= p.radius() + obstacle.radius());
            }
        }
    }

    @Test
    void invalidObstaclesAreRejected() {
        assertThrows(IllegalArgumentException.class, () -> config(List.of(new ObstacleConfig(0, 0.34, 0.05))));
        assertThrows(IllegalArgumentException.class, () -> config(List.of(new ObstacleConfig(0.6, 0.34, 0.01))));
        assertThrows(IllegalArgumentException.class, () -> config(List.of(
                new ObstacleConfig(0.6, 0.34, 0.05), new ObstacleConfig(0.61, 0.34, 0.05))));
    }

    @Test
    void impossiblePlacementFailsWithSeedInsteadOfReturningPartialState() {
        var config = new SimulationConfig(new SimulationParameters(1, 1, 0.2, 1, 9L),
                new ParticleParameters(2, 0.49, 1, 1),
                new OutputParameters(1, true, false, false), List.of());
        var error = assertThrows(IllegalArgumentException.class, () -> new InitialStateGenerator().generate(config));
        assertTrue(error.getMessage().contains("Seed: 9"));
    }

    @Test
    void fixedPositionsAreUsedVerbatimWithRandomVelocityDirections() {
        var config = new SimulationConfig(new SimulationParameters(1, 1, 0.2, 1, 9L),
                new ParticleParameters(2, 0.1, 1, 1),
                new OutputParameters(1, true, false, false), List.of());
        var positions = List.of(new Vector2D(0.2, 0.2), new Vector2D(0.8, 0.8));
        var state = new InitialStateGenerator().generate(config, positions);
        assertEquals(new Vector2D(0.2, 0.2), state.particles().get(0).position());
        assertEquals(new Vector2D(0.8, 0.8), state.particles().get(1).position());
        for (var p : state.particles()) {
            assertEquals(1, p.velocity().magnitude(), 1e-12);
        }
    }

    @Test
    void overlappingFixedPositionsAreRejected() {
        var config = new SimulationConfig(new SimulationParameters(1, 1, 0.2, 1, 9L),
                new ParticleParameters(2, 0.1, 1, 1),
                new OutputParameters(1, true, false, false), List.of());
        var overlapping = List.of(new Vector2D(0.5, 0.5), new Vector2D(0.55, 0.5));
        assertThrows(IllegalArgumentException.class,
                () -> new InitialStateGenerator().generate(config, overlapping));
    }

    @Test
    void positionCountMustMatchParticlesCount() {
        var config = config(List.of());
        assertThrows(IllegalArgumentException.class,
                () -> new InitialStateGenerator().generate(config, List.of(new Vector2D(0.5, 0.34))));
    }
}
