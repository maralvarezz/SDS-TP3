package ar.edu.itba.sds.tp3;

import ar.edu.itba.sds.tp3.config.ConfigLoader;
import ar.edu.itba.sds.tp3.config.InitialPositionsLoader;
import ar.edu.itba.sds.tp3.output.OutputManager;
import ar.edu.itba.sds.tp3.simulation.InitialStateGenerator;
import ar.edu.itba.sds.tp3.simulation.Simulation;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Random;

public final class Main {
    private Main() {}

    public static void main(String[] args) {
        try {
            if (args.length != 0) {
                throw new IllegalArgumentException("Los parametros se definen en input/config.json; ejecutar sin argumentos");
            }
            Path configPath = Path.of("input/config.json");
            Path outputPath = Path.of("output");
            var config = new ConfigLoader().load(configPath);
            if (config.simulation().seed() == null) {
                config = config.withSeed(new Random().nextLong());
            }
            var initialPositions = InitialPositionsLoader.loadIfPresent(configPath);
            var state = new InitialStateGenerator().generate(config, initialPositions);
            try (var output = new OutputManager(outputPath, configPath, config)) {
                System.out.println("Simulando " + state.particles().size() + " particulas, seed=" + config.simulation().seed());
                System.out.println("Archivos: " + output.directory().toAbsolutePath());
                try {
                    var result = new Simulation().run(config, state, output);
                    output.finish(result);
                    System.out.println("Tiempo simulado: " + result.state().time() + " s; colisiones: " + result.totalEvents());
                    System.out.println("Goles: " + result.totalGoals() + "; t90: "
                            + (result.t90() == null ? "no alcanzado" : result.t90() + " s"));
                } catch (IOException | RuntimeException error) {
                    try { output.fail(error); } catch (IOException writeError) { error.addSuppressed(writeError); }
                    throw error;
                }
            }
        } catch (IOException | RuntimeException e) {
            System.err.println("Error: " + e.getMessage());
            System.exit(1);
        }
    }
}
