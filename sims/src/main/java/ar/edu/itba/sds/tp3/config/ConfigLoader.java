package ar.edu.itba.sds.tp3.config;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public final class ConfigLoader {
    public SimulationConfig load(Path path) throws IOException {
        var mapper = JsonMapper.builder()
                .enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES)
                .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
                .disable(DeserializationFeature.ACCEPT_FLOAT_AS_INT)
                .disable(MapperFeature.ALLOW_COERCION_OF_SCALARS)
                .build();
        // Los campos obligatorios se validan antes del mapeo: seed es el unico opcional.
        var tree = mapper.readTree(path.toFile());
        if (tree == null || !tree.isObject()) throw new IOException("La configuración debe ser un objeto JSON");
        var root = (ObjectNode) tree;

        // initialPositionsFile lo consume por separado InitialPositionsLoader
        // (usado desde Main junto a InitialStateGenerator); aca solo se
        // descarta del arbol para que no llegue como campo desconocido al mapeo.
        root.remove("initialPositionsFile");

        // obstaclesFile es un atajo opcional: apunta a un archivo de texto con el
        // formato de entrega de la competencia ("xk yk Rk" por linea), para que ese
        // mismo archivo sea a la vez el origen de los obstaculos y el artefacto a
        // entregar, sin duplicar la configuracion en dos lugares. Se resuelve y se
        // descarta del arbol antes de mapear, para no dejar un campo desconocido.
        var obstaclesFileNode = root.remove("obstaclesFile");
        String obstaclesFile = (obstaclesFileNode != null && !obstaclesFileNode.isNull())
                ? obstaclesFileNode.asText() : null;
        if (obstaclesFile != null) {
            var inline = root.get("obstacles");
            if (inline != null && inline.isArray() && !inline.isEmpty()) {
                throw new IOException("No se puede combinar obstaclesFile con un array obstacles no vacío");
            }
            root.set("obstacles", readObstaclesFile(path.getParent(), obstaclesFile, mapper));
        }

        String[][] sections = {
                {"simulation", "length", "width", "goalSize", "maxTime"},
                {"particles", "count", "radius", "mass", "initialSpeed"},
                {"output", "everyEvents", "writeStates", "writeGoals", "writeCollisions"}
        };
        for (var section : sections) {
            var node = root.get(section[0]);
            if (node == null || !node.isObject()) throw new IOException("Falta la sección " + section[0]);
            for (int i = 1; i < section.length; i++) {
                if (!node.hasNonNull(section[i])) {
                    throw new IOException("Falta el campo " + section[0] + "." + section[i]);
                }
            }
        }
        var obstacles = root.get("obstacles");
        if (obstacles == null || !obstacles.isArray()) throw new IOException("obstacles debe ser un array");
        for (var obstacle : obstacles) {
            for (String field : new String[]{"x", "y", "radius"}) {
                if (!obstacle.hasNonNull(field)) throw new IOException("Falta obstacle." + field);
            }
        }
        return mapper.treeToValue(root, SimulationConfig.class);
    }

    private ArrayNode readObstaclesFile(Path configDirectory, String fileName, JsonMapper mapper) throws IOException {
        Path filePath = configDirectory == null ? Path.of(fileName) : configDirectory.resolve(fileName);
        if (!Files.isRegularFile(filePath)) {
            throw new IOException("obstaclesFile no encontrado: " + filePath);
        }
        var array = mapper.createArrayNode();
        List<String> lines = Files.readAllLines(filePath);
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.isEmpty()) continue;
            String[] parts = line.split("\\s+");
            if (parts.length != 3) {
                throw new IOException("Línea inválida en " + filePath + ":" + (i + 1)
                        + " (se esperaba \"x y radius\"): " + line);
            }
            double x, y, radius;
            try {
                x = Double.parseDouble(parts[0]);
                y = Double.parseDouble(parts[1]);
                radius = Double.parseDouble(parts[2]);
            } catch (NumberFormatException error) {
                throw new IOException("Línea inválida en " + filePath + ":" + (i + 1) + ": " + line, error);
            }
            var obstacle = mapper.createObjectNode();
            obstacle.put("x", x);
            obstacle.put("y", y);
            obstacle.put("radius", radius);
            array.add(obstacle);
        }
        return array;
    }
}
