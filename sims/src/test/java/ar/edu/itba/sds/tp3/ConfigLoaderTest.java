package ar.edu.itba.sds.tp3;

import ar.edu.itba.sds.tp3.config.ConfigLoader;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

class ConfigLoaderTest {
    @TempDir Path directory;

    private static final String JSON = """
            {
              "simulation": {"length":1.2,"width":0.68,"goalSize":0.2,"maxTime":30},
              "particles": {"count":100,"radius":0.0175,"mass":0.025,"initialSpeed":1},
              "output": {"everyEvents":10,"writeStates":true,"writeGoals":true,"writeCollisions":false},
              "obstacles": []
            }
            """;

    private Path write(String content) throws IOException {
        return Files.writeString(directory.resolve("config.json"), content);
    }

    @Test
    void seedCanBeOmittedAndResolvedWithoutChangingOtherParameters() throws IOException {
        var config = new ConfigLoader().load(write(JSON));
        assertNull(config.simulation().seed());
        assertEquals(100, config.particles().count());
        var effective = config.withSeed(42);
        assertEquals(Long.valueOf(42), effective.simulation().seed());
        assertEquals(config.particles(), effective.particles());
    }

    @Test
    void rejectsMissingFieldsUnknownFieldsAndFractionalCounts() {
        assertThrows(IOException.class, () -> new ConfigLoader().load(write(JSON.replace("\"writeStates\":true,", ""))));
        assertThrows(IOException.class, () -> new ConfigLoader().load(write(JSON.replace("\"count\":100", "\"count\":1.5"))));
        assertThrows(IOException.class, () -> new ConfigLoader().load(write(JSON.replace("\"count\":100", "\"count\":100,\"typo\":1"))));
        assertThrows(IOException.class, () -> new ConfigLoader().load(write(JSON + "{}")));
    }

    @Test
    void loadsObstaclesFromObstaclesFileInCompetitionTxtFormat() throws IOException {
        Files.writeString(directory.resolve("obstacles.txt"), "0.300 0.340 0.040\n0.900 0.340 0.040\n");
        var json = JSON.replace("\"obstacles\": []", "\"obstaclesFile\": \"obstacles.txt\", \"obstacles\": []");
        var config = new ConfigLoader().load(write(json));
        assertEquals(2, config.obstacles().size());
        assertEquals(0.300, config.obstacles().get(0).x());
        assertEquals(0.040, config.obstacles().get(1).radius());
    }

    @Test
    void rejectsObstaclesFileCombinedWithNonEmptyInlineObstacles() throws IOException {
        Files.writeString(directory.resolve("obstacles.txt"), "0.300 0.340 0.040\n");
        var json = JSON.replace("\"obstacles\": []",
                "\"obstaclesFile\": \"obstacles.txt\", \"obstacles\": [{\"x\":0.6,\"y\":0.34,\"radius\":0.05}]");
        assertThrows(IOException.class, () -> new ConfigLoader().load(write(json)));
    }

    @Test
    void rejectsMalformedObstaclesFileLine() throws IOException {
        Files.writeString(directory.resolve("obstacles.txt"), "0.300 0.340\n");
        var json = JSON.replace("\"obstacles\": []", "\"obstaclesFile\": \"obstacles.txt\", \"obstacles\": []");
        assertThrows(IOException.class, () -> new ConfigLoader().load(write(json)));
    }
}
