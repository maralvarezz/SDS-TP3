package ar.edu.itba.sds.tp3.config;

import ar.edu.itba.sds.tp3.model.Vector2D;
import com.fasterxml.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Carga posiciones iniciales de particulas desde un archivo externo, si
 * config.json declara "initialPositionsFile". Es un mecanismo opcional,
 * separado de ConfigLoader, para experimentos que necesitan una condicion
 * inicial distinta a la generacion aleatoria por rechazo secuencial (por
 * ejemplo, comparar cuantas particulas entran con un empaquetado hexagonal).
 * No reemplaza ni modifica la generacion aleatoria por defecto.
 */
public final class InitialPositionsLoader {
    private InitialPositionsLoader() {}

    public static List<Vector2D> loadIfPresent(Path configPath) throws IOException {
        var mapper = JsonMapper.builder().build();
        var tree = mapper.readTree(configPath.toFile());
        if (tree == null || !tree.isObject()) return null;
        var node = tree.get("initialPositionsFile");
        if (node == null || node.isNull()) return null;
        String fileName = node.asText();
        Path baseDir = configPath.getParent();
        Path filePath = baseDir == null ? Path.of(fileName) : baseDir.resolve(fileName);
        if (!Files.isRegularFile(filePath)) {
            throw new IOException("initialPositionsFile no encontrado: " + filePath);
        }
        var positions = new ArrayList<Vector2D>();
        List<String> lines = Files.readAllLines(filePath);
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.isEmpty()) continue;
            String[] parts = line.split("\\s+");
            if (parts.length != 2) {
                throw new IOException("Línea inválida en " + filePath + ":" + (i + 1)
                        + " (se esperaba \"x y\"): " + line);
            }
            try {
                positions.add(new Vector2D(Double.parseDouble(parts[0]), Double.parseDouble(parts[1])));
            } catch (NumberFormatException error) {
                throw new IOException("Línea inválida en " + filePath + ":" + (i + 1) + ": " + line, error);
            }
        }
        return positions;
    }
}
