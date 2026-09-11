# SDS-TP3

## Gráficos simples

Cada punto tendrá su propio script y generará un solo gráfico. Actualmente está
implementado `viz/point_1_2.py` (fracción usada y t90); no hay ejecutor genérico.

Desde la raíz, instalar las dependencias Python en un entorno virtual:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r viz/requirements.txt
.venv/Scripts/python viz/point_1_2.py
```

`input/config.json` contiene los parámetros de simulación y de guardado.
`output.everyEvents` controla la granularidad: 1 guarda un estado por colisión;
10 guarda uno cada diez colisiones. `writeCollisions` registra cada choque con su
tiempo, independientemente de esa frecuencia. Los scripts eligen la última corrida
completada y leen los datos físicos de sus metadatos, sin leer el JSON de entrada.

```powershell
.venv/Scripts/python viz/point_1_2.py
```

Guarda un PNG con timestamp en `<corrida>/plots/`: fracción usada en función del
tiempo simulado, con el umbral del 90 % y t90 (punto 1.2). Lee exclusivamente
`goals_*.csv` y los metadatos de Java. Requiere `writeGoals: true` en la corrida.

Es un gráfico individual; todavía no compara configuraciones ni calcula promedios
o barras de error entre realizaciones.

## Animación

`viz/animation.py` genera un GIF independiente a partir de los archivos de una
corrida completada. La configuración actual guarda los datos necesarios:
`writeStates: true`, `everyEvents: 1` y `writeCollisions: true`.

Después de recompilar Java y ejecutar una nueva corrida:

```powershell
.venv/Scripts/python viz/animation.py
```

El GIF queda en `<corrida>/plots/animation_<timestamp>.gif`. `SPEED = 2` reproduce
dos segundos simulados por segundo de video. Los FPS solo controlan la reproducción;
Java sigue avanzando por eventos. Azul indica FRESH y rojo USED.
`FPS` y `SPEED` son opciones locales en `viz/animation.py`; no pertenecen al JSON
de simulación. Ambos scripts se ejecutan sin argumentos.

`states` registra posiciones, velocidades y estado lógico de todas las partículas
en t=0 y después de cada choque. `collisions` registra tiempo absoluto simulado,
número de evento, tipo, IDs involucrados, obstáculo y pared. `metadata` incluye
geometría, radios, configuración efectiva, seed y `animationReady`.

Python verifica que los eventos de ambos CSV coincidan e interpola visualmente las
posiciones entre estados consecutivos. No predice choques ni modifica la física.
Los contactos simultáneos se consumen en su orden registrado antes de dibujar.
Las corridas antiguas con estados cada 10 eventos no sirven para esta reconstrucción;
el script las rechaza. Guardar cada evento aumenta el tamaño de los CSV.

Trabajo Práctico 3 de Simulación de Sistemas: Billar-Metegol.
Las reglas de desarrollo están en [AGENTS.md](AGENTS.md) y las fuentes oficiales en `docs/`.

## Estructura

```text
docs/       Enunciado y teoría de referencia.
input/      Configuración de entrada: config.json.
output/     Resultados generados, una carpeta por realización; ignorados por Git.
sims/       Módulo Maven: motor Java de dinámica molecular dirigida por eventos.
viz/        Postprocesamiento, estadísticas, gráficos y animaciones en Python.
```

Java y Python se comunican únicamente mediante los archivos de cada corrida en
`output/<run_id>/`. Los parámetros pertenecen a `input/config.json`; Python deberá
leer la configuración efectiva registrada en los metadatos de la corrida.

## Módulo de simulación

Requiere JDK 21 y Maven. Desde la raíz del repositorio o desde `sims/`:

```sh
mvn clean package
```

El `pom.xml` raíz es un agregador con coordenadas
`ar.edu.itba.sds:root_tp3_g8` y contiene el módulo `sims`.
Para importar el proyecto completo en IntelliJ, abrir o vincular ese POM raíz.

Coordenadas Maven del motor: `ar.edu.itba.sds:sds_tp3_g8`.
Código en `sims/src/main/java/ar/edu/itba/sds/tp3/` y pruebas en
`sims/src/test/java/ar/edu/itba/sds/tp3/`.

Distribución de responsabilidades:

| Paquete | Responsabilidad | Clases principales |
| --- | --- | --- |
| `config` | Leer el JSON con Jackson y validar la configuración de entrada. | `SimulationConfig`, `ConfigLoader` y parámetros por sección |
| `model` | Representar entidades y estado, sin lectura ni escritura de archivos. | `Particle`, `ParticleState`, `Obstacle`, `Vector2D`, `SimulationState` |
| `physics` | Calcular tiempos de impacto, avanzar posiciones y resolver colisiones. | `CollisionTimeCalculator`, `MotionUpdater`, `CollisionResolver` |
| `event` | Predecir, ordenar e invalidar choques futuros. | `Event`, `EventType`, `EventQueue`, `Wall` |
| `simulation` | Generar condiciones iniciales y coordinar la ejecución. | `InitialStateGenerator`, `Simulation`, `SimulationResult`, `SimulationObserver` |
| `output` | Escribir estados, goles, colisiones, metadatos y resumen de una corrida. | `OutputManager` |

`Main` carga `input/config.json`, genera el estado inicial y
ejecuta `Simulation`. El estado vive en `SimulationState`, evitando estado global.
La física no depende de la CLI ni de los escritores: `SimulationObserver` recibe
los observables y `OutputManager` los escribe.

El motor usa una `PriorityQueue` de eventos con tiempos absolutos simulados:

1. Al iniciar, calcula los choques posibles de todas las parejas, paredes y obstáculos.
2. Extrae el evento válido más próximo y mueve todas las partículas por MRU hasta él.
3. Resuelve el choque elástico y registra el primer gol, si corresponde.
4. Incrementa la versión de las partículas involucradas y recalcula únicamente sus
   posibles choques. Las predicciones entre partículas no afectadas se conservan.
5. Descarta los eventos cuyas versiones ya no coinciden. Periódicamente limpia los
   eventos obsoletos de la cola sin recalcular los válidos.

La predicción inicial cuesta O(N² + NK); después de un choque se recalculan O(N + K)
candidatos por partícula afectada, además de las operaciones de cola y el MRU de N
partículas. Se usa esta estrategia por indicación del usuario, en lugar de la búsqueda
completa propuesta inicialmente. Agrega contadores de versión e invalidación; no
cambia el contrato de archivos. No había un motor anterior ejecutable para comparar.

No hay pasos temporales fijos, esperas ni sincronización con el reloj real. El último
evento es `SIMULATION_END` en `simulation.maxTime`. Alcanzar `t90` lo registra, pero
la corrida continúa hasta `maxTime`, conservando todas las partículas.

Los empates exactos se resuelven por tipo de evento, índices de partículas,
obstáculo y pared, con `SIMULATION_END` al final. Los contactos múltiples se resuelven
secuencialmente y se recalculan tras cada impulso, incluso en el mismo instante.
Es una convención determinista de choques binarios, no un solucionador de impactos
múltiples acoplados. Una guardia aborta si se acumulan 100 000 eventos sin avanzar.

Las fórmulas provienen de las diapositivas 12, 14, 19, 20 y 22–24 de `docs/Teorica_3.pdf`.
La raíz del tiempo de choque circular se racionaliza para evitar cancelación cerca
del contacto. Se conserva cualquier tiempo positivo, aunque sea pequeño, para no
perder un choque. Solo se admite tiempo cero si existe contacto y aproximación.
`Numerics.EPSILON` tolera penetraciones de redondeo de hasta 1e-10 m; solapamientos
mayores abortan. Las tangencias sin impulso no se encolan. No se desplazan cuerpos
artificialmente para separarlos ni se convierten discriminantes negativos en choques.

## Estado y próximos pasos

Están implementados la configuración, generación inicial, cola incremental,
colisiones elásticas con paredes, partículas y obstáculos, goles y archivos de salida.
La compilación y validación en ejecución quedan pendientes a cargo del usuario.

Después de compilar, ejecutar desde la raíz:

```sh
java -jar sims/target/sds_tp3_g8.jar
```

Ejecutar Java desde la raíz del repositorio, sin argumentos: lee `input/config.json`
y escribe en `output/`. En IntelliJ, ejecutar `ar.edu.itba.sds.tp3.Main` con la raíz
del repositorio como directorio de trabajo y sin argumentos de programa.

El JSON actual usa 30 partículas y tres obstáculos para inspección visual.
Los experimentos de los puntos 1.2 en adelante requieren volver a N=100.
La generación sigue la Teórica 3, diapositiva 10: muestreo secuencial por rechazo,
sin solapamientos. Se limita a 100 000 intentos por partícula; agotar el límite
aborta la inicialización y no prueba que la configuración sea geométricamente imposible.
La semilla se define en `simulation.seed` dentro del JSON como entero de 64 bits.
Si el campo se omite o vale `null`, se genera una aleatoria en cada ejecución.
La semilla efectiva siempre se guarda en `metadata_<timestamp>.json`, junto con
la configuración usada. Para reproducir la corrida anterior, usar `"seed": 12345`
en la sección `simulation` y ejecutar:

```sh
java -jar sims/target/sds_tp3_g8.jar
```

Cada ejecución crea `output/<nombre_config>_<timestamp>/`, tomando el nombre del
archivo de configuración sin su extensión. Por ejemplo: `config_20260911_141718_536`.
El timestamp usa UTC y milisegundos; si la carpeta existe, se incrementa un
milisegundo hasta encontrar un nombre libre, sin sobrescribir corridas previas.
Contiene estos archivos:

- `metadata_<timestamp>.json`: configuración efectiva, seed, estado de la corrida,
  métricas finales y `t90` (`null` si no se alcanza).
- `states_<timestamp>.csv`: todas las partículas en t=0, cada `everyEvents`
  colisiones y al finalizar, si `writeStates` está activo. Son estados posteriores
  al choque y al cambio lógico por gol. El frame final no se duplica.
- `goals_<timestamp>.csv`: primeros contactos de partículas frescas con los arcos,
  si `writeGoals` está activo. Los goles se cuentan aunque el archivo esté desactivado.
- `collisions_<timestamp>.csv`: una fila por choque, si `writeCollisions` está activo.
- `summary_<timestamp>.csv`: una fila por corrida completada, con `t90` vacío si
  no se alcanza. El evento de fin no se cuenta como colisión.

La metadata comienza en `RUNNING`, pasa a `COMPLETED` al finalizar, o a `FAILED`
si se captura un error. Una interrupción abrupta puede dejarla en `RUNNING` y los
CSV incompletos. Solo las corridas `COMPLETED` deben usarse para análisis.

El reloj real solo nombra archivos y mide `runtimeMilliseconds`: inicialización
de la cola y ciclo de eventos, incluyendo escritura CSV durante el ciclo. Excluye
generación de partículas, apertura de archivos y escritura final de metadatos y
resumen. Este observable no controla el tiempo simulado.

Las pruebas de la primera iteración se conservan; por indicación del usuario no
se agregan nuevos tests ni se ejecuta Maven. `InitialStateWriter` se conserva como
utilidad de exportación inicial usada por esas pruebas; la CLI usa `OutputManager`.
Queda pendiente validar el motor en ejecución antes de usar resultados experimentales.

El empaquetado del JAR con dependencias usa el
[patrón oficial de Maven Shade](https://maven.apache.org/plugins/maven-shade-plugin/examples/executable-jar.html).
