# Meeting Room Scheduler

## Problem Statement
Book rooms avoiding conflicts, search by capacity/resources, support recurring bookings.

## Functional Requirements
- Create rooms
- Book/cancel
- Search free slots
- Recurring bookings

## Core Concepts
- `Room(id, capacity, features)`
- `Booking(roomId, interval, user)`
- `IntervalTree` or ordered map per room for conflict checks

## High-Level Design
- **Room Management:**
    - Add/edit/delete rooms
    - Track features (A/V, whiteboard, etc.)
- **Booking:**
    - Book/cancel with conflict checks
    - Recurring bookings: expand to individual slots
- **Search:**
    - Find free rooms by time/capacity/features
- **Edge Cases:**
    - Buffer times between meetings
    - Recurrence expansion

## Step-by-Step Solution
1. **Define classes:** Room, Booking, IntervalTree
2. **Booking logic:** conflict checks
3. **Search:** by time/capacity/features
4. **API:** create room, book, search

## Edge Cases
- Overlapping bookings
- Recurring conflicts
- Room feature changes
