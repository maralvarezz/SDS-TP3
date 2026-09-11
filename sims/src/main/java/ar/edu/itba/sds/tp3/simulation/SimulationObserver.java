package ar.edu.itba.sds.tp3.simulation;

import ar.edu.itba.sds.tp3.event.Event;
import ar.edu.itba.sds.tp3.event.Wall;
import ar.edu.itba.sds.tp3.model.SimulationState;
import java.io.IOException;

/** Recibe observables, sin participar en la prediccion ni en la resolucion fisica. */
public interface SimulationObserver {
    void state(SimulationState state, long eventNumber) throws IOException;
    void collision(SimulationState state, Event event, long eventNumber) throws IOException;
    void goal(double time, long eventNumber, int particleId, Wall side, int totalGoals, double usedFraction) throws IOException;
}
