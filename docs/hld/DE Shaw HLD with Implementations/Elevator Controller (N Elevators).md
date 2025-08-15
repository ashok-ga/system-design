# Elevator Controller (N Elevators)

## Problem Statement
Schedule N elevators to minimize wait time. Handle hall/cab calls, group control, and safety.

## Functional Requirements
- Handle hall & cab calls
- States: IDLE, MOVING, DOOR_OPEN
- Group control, peak modes

## Core Concepts
- `Elevator(id, currentFloor, direction, queue)` (State pattern)
- `Scheduler.assign(call)` (Nearest Car / Look Algorithm)

## High-Level Design
- **Elevator:**
    - Each elevator tracks current floor, direction, and queue of stops
    - State transitions: IDLE ↔ MOVING ↔ DOOR_OPEN
- **Scheduler:**
    - Assigns calls to elevators (nearest car, look algorithm)
    - Handles peak modes (morning/evening)
- **Safety:**
    - Door interlocks, overload sensors

## Step-by-Step Solution
1. **Elevator class:** state, queue, move logic
2. **Scheduler:** assign calls, optimize for wait time
3. **Safety:** enforce interlocks
4. **Simulation:** test with multiple elevators/calls

## Edge Cases
- Simultaneous calls
- Overload
- Emergency stop
