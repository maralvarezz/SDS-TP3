package ar.edu.itba.sds.tp3;

import ar.edu.itba.sds.tp3.config.*;
import ar.edu.itba.sds.tp3.output.InitialStateWriter;
import ar.edu.itba.sds.tp3.simulation.InitialStateGenerator;
import com.fasterxml.jackson.databind.json.JsonMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class InitialStateWriterTest {
    @TempDir Path directory;

    @Test
    void recordsReproducibleMetadataAndNeverReusesDirectory() throws Exception {
        var config = new SimulationConfig(new SimulationParameters(1.2, 0.68, 0.2, 30, 7L),
                new ParticleParameters(3, 0.0175, 0.025, 1),
                new OutputParameters(1, true, true, false), List.of());
        var state = new InitialStateGenerator().generate(config);
        var writer = new InitialStateWriter();
        var first = writer.write(directory, config, state);
        var second = writer.write(directory, config, state);
        assertNotEquals(first, second);
        try (var paths = Files.list(first)) {
            var files = paths.toList();
            var metadata = files.stream().filter(p -> p.toString().endsWith(".json")).findFirst().orElseThrow();
            var mapper = JsonMapper.builder().build();
            var tree = mapper.readTree(metadata.toFile());
            assertEquals(7, tree.get("seed").asLong());
            assertEquals("INITIALIZATION_ONLY", tree.get("phase").asText());
            assertEquals(config, mapper.treeToValue(tree.get("config"), SimulationConfig.class));
            var csv = files.stream().filter(p -> p.toString().endsWith(".csv")).findFirst().orElseThrow();
            assertEquals(4, Files.readAllLines(csv).size());
        }
    }
}
