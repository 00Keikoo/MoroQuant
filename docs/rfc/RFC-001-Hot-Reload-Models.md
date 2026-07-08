# RFC-001: Hot Reloading ML Models

## Status
Proposed

## Problem Statement
Updating machine learning model weights currently requires restarting the inference server daemon. This restart drops active WebSocket connections and causes a brief window of telemetry unavailability, degrading real-time performance tracking.

## Motivation
In live trading, model parameter adjustments or weight updates should occur with zero downtime. We need a mechanism to swap loaded weights dynamically in memory while the inference engine process remains active.

## Current State
The backend loads model files from the local filesystem during startup initialization. There is no route or system event listener to trigger a re-load, requiring a full container restart to apply new model parameters.

## Proposed Solution
Introduce a dynamic memory loader inside the inference service:
1. Implement a thread-safe model container pointer (e.g. atomic references).
2. Create an admin-only endpoint (`POST /api/v1/model/reload`) or folder watcher to reload the file in a background thread.
3. Once the new model is ready, atomically swap the active model reference pointer.
4. Clean up the memory allocated to the old model.

## Alternatives
- **Blue-Green Service Deployment**: Spawn a secondary worker container with the new weights, update the API routing, and shut down the old container. *Pros*: Clean separation. *Cons*: High latency, resource overhead, and setup complexity.
- **On-Demand Loading**: Read the weights file on every incoming request. *Pros*: Simple. *Cons*: Destroys latency profiles of the trading pipeline.

## Open Questions
- What is the memory overhead of holding two models simultaneously during the reload swap?
- How do we handle active inference requests mid-swap? Should they execute on the old or new model?

## Risks
- **OutOfMemory (OOM) Errors**: Swapping large weights requires peak memory spikes that might exceed sandbox limits.
- **Race Conditions**: Parallel inference requests could experience segmentation faults if pointer swapping isn't thread-safe.

## Decision Criteria
- Zero dropped WebSocket client connections during update.
- Swap latency under 100 milliseconds.
- Minimum system resource usage overhead.
