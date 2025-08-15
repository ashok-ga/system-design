# IoT Fleet Management (Devices at Edge)

## Requirements
- 100k–1M devices
- Secure provisioning
- OTA updates
- Telemetry
- Commands

## Scale
- 10–50k msgs/s
- Intermittent connectivity

## Core Architecture
- Device registry (PKI)
- MQTT broker
- Shadow/state service
- OTA distribution
- Rules engine

## Storage
- Time-series DB for telemetry
- Object store for firmware

## Flow
- Connect → authenticate → publish telemetry → rules → act/store; OTA staged rollout

## Trade-offs
- Online/offline state reconciliation

## Diagram
```
[Device] -> [MQTT Broker] -> [Shadow Service] -> [Rules Engine] -> [OTA]
```

## Notes
- Use PKI for secure provisioning
- OTA staged rollout for reliability
