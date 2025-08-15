# Parking Lot

## Problem Statement
Design a multi-floor parking lot with spot types and pricing. Support park/unpark, nearest spot allocation, and billing.

## Functional Requirements
- Park/unpark vehicle
- Find nearest suitable spot
- Track tickets and fees

## Core Concepts
- `ParkingLot`, `Floor`, `Spot(type, id, isFree)`, `Vehicle(type)`
- `Allocator` (nearest/cheapest)
- `Ticket`, `Billing`

## High-Level Design
- **Structure:**
    - ParkingLot contains Floors
    - Each Floor has Spots (by type: regular, compact, handicapped, etc.)
- **Allocation:**
    - On park, find nearest free spot of required type
    - On unpark, calculate fee, free spot
- **Ticketing:**
    - Issue ticket on entry, track time
    - On exit, calculate fee (duration × rate)
- **Edge Cases:**
    - Overflow (lot full)
    - Reservations
    - Lost tickets

## Step-by-Step Solution
1. **Define classes:** ParkingLot, Floor, Spot, Vehicle, Ticket
2. **Allocator:** nearest/cheapest strategy
3. **Billing:** calculate fees
4. **API:** park, unpark, status endpoints

## Edge Cases
- Multiple vehicle types
- Lost ticket handling
- Dynamic pricing
