package ar.edu.itba.sds.tp3.config;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.file.Path;

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
        String[][] sections = {
                {"simulation", "length", "width", "goalSize", "maxTime"},
                {"particles", "count", "radius", "mass", "initialSpeed"},
                {"output", "everyEvents", "writeStates", "writeGoals", "writeCollisions"}
        };
        for (var section : sections) {
            var node = tree.get(section[0]);
            if (node == null || !node.isObject()) throw new IOException("Falta la sección " + section[0]);
            for (int i = 1; i < section.length; i++) {
                if (!node.hasNonNull(section[i])) {
                    throw new IOException("Falta el campo " + section[0] + "." + section[i]);
                }
            }
        }
        var obstacles = tree.get("obstacles");
        if (obstacles == null || !obstacles.isArray()) throw new IOException("obstacles debe ser un array");
        for (var obstacle : obstacles) {
            for (String field : new String[]{"x", "y", "radius"}) {
                if (!obstacle.hasNonNull(field)) throw new IOException("Falta obstacle." + field);
            }
        }
        return mapper.treeToValue(tree, SimulationConfig.class);
    }
}
