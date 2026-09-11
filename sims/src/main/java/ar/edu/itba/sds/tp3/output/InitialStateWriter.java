package ar.edu.itba.sds.tp3.output;

import ar.edu.itba.sds.tp3.config.SimulationConfig;
import ar.edu.itba.sds.tp3.model.SimulationState;
import com.fasterxml.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Locale;

public final class InitialStateWriter {
    public Path write(Path output, SimulationConfig config, SimulationState state) throws IOException {
        Instant now = Instant.now();
        String timestamp = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS")
                .withZone(ZoneOffset.UTC).format(now);
        Files.createDirectories(output);
        Path directory = Files.createTempDirectory(output, timestamp + "_initial_seed"
                + config.simulation().seed() + "_");
        var metadata = new LinkedHashMap<String, Object>();
        metadata.put("runId", directory.getFileName().toString());
        metadata.put("timestamp", now.toString());
        metadata.put("phase", "INITIALIZATION_ONLY");
        metadata.put("seed", config.simulation().seed());
        metadata.put("config", config);
        metadata.put("time", state.time());
        JsonMapper.builder().build().writerWithDefaultPrettyPrinter()
                .writeValue(directory.resolve("metadata_" + timestamp + ".json").toFile(), metadata);
        if (config.output().writeStates()) {
            try (var writer = Files.newBufferedWriter(directory.resolve("states_" + timestamp + ".csv"),
                    StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW)) {
                writer.write("time,event,id,x,y,vx,vy,state\n");
                for (var particle : state.particles()) {
                    writer.write(String.format(Locale.ROOT, "%s,0,%d,%s,%s,%s,%s,%s%n",
                            state.time(), particle.id(), particle.position().x(), particle.position().y(),
                            particle.velocity().x(), particle.velocity().y(), particle.state()));
                }
            }
        }
        return directory;
    }
}
