package ar.edu.itba.sds.tp3.output;

import ar.edu.itba.sds.tp3.config.SimulationConfig;
import ar.edu.itba.sds.tp3.event.Event;
import ar.edu.itba.sds.tp3.event.Wall;
import ar.edu.itba.sds.tp3.model.SimulationState;
import ar.edu.itba.sds.tp3.simulation.SimulationObserver;
import ar.edu.itba.sds.tp3.simulation.SimulationResult;
import com.fasterxml.jackson.databind.json.JsonMapper;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class OutputManager implements SimulationObserver, AutoCloseable {
    private final SimulationConfig config;
    private final Path directory;
    private final String timestamp;
    private final Map<String, Object> metadata = new LinkedHashMap<>();
    private final List<BufferedWriter> writers = new ArrayList<>();
    private BufferedWriter states;
    private BufferedWriter goals;
    private BufferedWriter collisions;
    private double lastStateTime = -1;
    private long lastStateEvent = -1;

    public OutputManager(Path output, Path configPath, SimulationConfig config) throws IOException {
        this.config = config;
        Instant now = Instant.now();
        String filename = configPath.getFileName().toString();
        int extension = filename.lastIndexOf('.');
        String configName = extension > 0 ? filename.substring(0, extension) : filename;
        var formatter = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS").withZone(ZoneOffset.UTC);
        Files.createDirectories(output);
        Instant directoryTime = now;
        Path createdDirectory;
        while (true) {
            try {
                createdDirectory = Files.createDirectory(output.resolve(configName + "_" + formatter.format(directoryTime)));
                break;
            } catch (FileAlreadyExistsException collision) {
                // Mantener el formato sin sobrescribir ni agregar sufijos aleatorios.
                directoryTime = directoryTime.plusMillis(1);
            }
        }
        timestamp = formatter.format(directoryTime);
        directory = createdDirectory;
        metadata.put("runId", directory.getFileName().toString());
        metadata.put("configName", configName);
        metadata.put("timestamp", now.toString());
        metadata.put("status", "RUNNING");
        metadata.put("seed", config.simulation().seed());
        metadata.put("config", config);
        metadata.put("L", config.simulation().length());
        metadata.put("W", config.simulation().width());
        metadata.put("d", config.simulation().goalSize());
        metadata.put("N", config.particles().count());
        metadata.put("r", config.particles().radius());
        metadata.put("m", config.particles().mass());
        metadata.put("v0", config.particles().initialSpeed());
        metadata.put("maxTime", config.simulation().maxTime());
        metadata.put("obstacles", config.obstacles());
        metadata.put("algorithm", "EVENT_DRIVEN_PRIORITY_QUEUE");
        metadata.put("animationReady", config.output().writeStates()
                && config.output().everyEvents() == 1 && config.output().writeCollisions());
        metadata.put("runtimeScope", "queue initialization and event loop including CSV writes; excludes particle generation and final metadata");
        try {
            writeMetadata();
            if (config.output().writeStates()) states = open("states", "time,event,id,x,y,vx,vy,state");
            if (config.output().writeGoals()) goals = open("goals", "time,event,particleId,goalSide,totalGoals,usedFraction");
            if (config.output().writeCollisions()) collisions = open("collisions", "time,event,type,particleA,particleB,obstacleId,wall");
        } catch (IOException error) {
            try { close(); } catch (IOException closeError) { error.addSuppressed(closeError); }
            throw error;
        }
    }

    public Path directory() {
        return directory;
    }

    private BufferedWriter open(String name, String header) throws IOException {
        var writer = Files.newBufferedWriter(directory.resolve(name + "_" + timestamp + ".csv"),
                StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW);
        writers.add(writer);
        writer.write(header);
        writer.newLine();
        return writer;
    }

    @Override
    public void state(SimulationState state, long eventNumber) throws IOException {
        if (states == null || (state.time() == lastStateTime && eventNumber == lastStateEvent)) return;
        for (var p : state.particles()) {
            states.write(state.time() + "," + eventNumber + "," + p.id() + "," + p.position().x()
                    + "," + p.position().y() + "," + p.velocity().x() + "," + p.velocity().y() + "," + p.state());
            states.newLine();
        }
        lastStateTime = state.time();
        lastStateEvent = eventNumber;
    }

    @Override
    public void collision(SimulationState state, Event event, long eventNumber) throws IOException {
        if (collisions == null) return;
        String b = event.particleB() < 0 ? "" : Integer.toString(state.particles().get(event.particleB()).id());
        String obstacle = event.obstacle() < 0 ? "" : Integer.toString(state.obstacles().get(event.obstacle()).id());
        collisions.write(state.time() + "," + eventNumber + "," + event.type() + ","
                + state.particles().get(event.particleA()).id() + "," + b + "," + obstacle
                + "," + (event.wall() == null ? "" : event.wall()));
        collisions.newLine();
    }

    @Override
    public void goal(double time, long eventNumber, int particleId, Wall side,
                     int totalGoals, double usedFraction) throws IOException {
        if (goals == null) return;
        goals.write(time + "," + eventNumber + "," + particleId + "," + side + "," + totalGoals + "," + usedFraction);
        goals.newLine();
    }

    public void finish(SimulationResult result) throws IOException {
        var summary = open("summary", "seed,N,totalEvents,totalGoals,runtimeMilliseconds");
        summary.write(config.simulation().seed() + "," + config.particles().count() + "," + result.totalEvents()
                + "," + result.totalGoals()
                + "," + result.runtimeMilliseconds());
        summary.newLine();
        for (var writer : writers) writer.flush();
        metadata.put("status", "COMPLETED");
        metadata.put("finalTime", result.state().time());
        metadata.put("totalEvents", result.totalEvents());
        metadata.put("totalGoals", result.totalGoals());
        metadata.put("runtimeMilliseconds", result.runtimeMilliseconds());
        writeMetadata();
    }

    public void fail(Exception error) throws IOException {
        metadata.put("status", "FAILED");
        metadata.put("error", error.getMessage());
        writeMetadata();
    }

    private void writeMetadata() throws IOException {
        JsonMapper.builder().build().writerWithDefaultPrettyPrinter()
                .writeValue(directory.resolve("metadata_" + timestamp + ".json").toFile(), metadata);
    }

    @Override
    public void close() throws IOException {
        IOException failure = null;
        for (var writer : writers) {
            try {
                writer.close();
            } catch (IOException error) {
                if (failure == null) failure = error;
                else failure.addSuppressed(error);
            }
        }
        if (failure != null) throw failure;
    }
}
