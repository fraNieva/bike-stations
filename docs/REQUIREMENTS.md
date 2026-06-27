# Requirements

Business and technical requirements gathered from the client (Bicing maintenance team).

## Context

Bicing operates 256 electric bike stations in Barcelona. The bikes are provided by Nextbike,
who supplies per-bike telemetry (battery level) but no station-level charging data.
The maintenance team cannot currently determine if a station is actively charging its bikes.

The goal is to install Arduino boards at stations to detect charging status and alert
the maintenance team when a station stops charging.

## Scope — POC

- One station for initial testing
- Validate end-to-end communication: Arduino → server → data stored
- Validate alert detection

## Scope — Pilot (Phase 2)

- 40–50 stations
- Full alerting and dashboard

## Device and Data Collection

- Each station has one Arduino board measuring the station's main charging lines
- The board reports every **10–15 minutes** continuously (not only on change)
- The board has local memory to buffer events if 4G signal is lost and resend on reconnection
- Phase 1: one measurement per station (total charging line)
- Phase 2: two measurements per station (two independent charging lines)
- Payload per event: `station_id`, `is_charging`, `voltage`, `amperage`, `gps`, `timestamp`
- Station IDs must match the existing Nextbike station identifiers

## Data Retention

- Raw telemetry (`station_events`): **7 days**, then deleted automatically
- Alerts: **permanent** — never deleted
- Reports of alert history must be available

## Alert Rules

- A station is considered to have a problem after **2 consecutive non-charging events**
- At 10–15 min intervals, this means ~20–30 minutes without charging triggers an alert
- Alerts fire in **real time** (not daily digest)
- No time windows — stations must charge 24/7
- If an open alert already exists for a station, no duplicate is created
- Each alert has a status: `open` or `resolved`
- Alerts are resolved manually by the maintenance operator

## Notifications (pending implementation — deferred)

When an alert is created, notify via:
- **Telegram**
- **Email**
- **In-app notification** (dashboard)

> Implementation deferred pending client confirmation on preferred delivery method.

## Users and Access

- Single user for POC: Mariano (maintenance manager)
- Authentication: email + password
- One role only (no admin/operator distinction for now)
- System must support adding more users in the future

## Dashboard (not yet built)

- Show current charging status of all monitored stations
- Show open and resolved alerts
- Allow operator to mark alerts as resolved with notes
- Real-time updates (WebSocket or polling)
- Alert history report with filtering by date range and station (`GET /reports/alerts` — backend implemented)
- Built in React or Next.js

## Infrastructure

- Backend hosted on Railway
- Database: PostgreSQL on Railway
- Devices communicate via 4G (not WiFi — stations are outdoors)
- Device authentication via API key (one key per board)

## Out of Scope

- Integration with Nextbike data
- SLA tracking
- Remote control of charging stations
- Billing or consumption reporting (possible future phase)