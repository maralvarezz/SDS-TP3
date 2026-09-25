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
            if (args.length > 1) {
                throw new IllegalArgumentException("Uso: java -jar sims/target/sds_tp3_g8.jar [configPath]");
            }
            Path configPath = args.length == 0 ? Path.of("input/config.json") : Path.of(args[0]);
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
                    System.out.println("Goles: " + result.totalGoals()
                            + " (t90 se calcula en postproceso a partir de goals_*.csv)");
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
