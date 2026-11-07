# Switch integration, 6 November 2026

**Truth boundary:** Event-specific connector code now exists, but no verified Switch server, authenticated Mattermost room, agent key or live chat exchange has been tested from this environment. The script cannot contact the user's personal computer, UniFi router, customer camera or InnerOS production services. This is a **single Switch agent**, not yet two independently connected agents.

## What was built during the event

- `src/inneros_incident_room/switch_event.py`: Python Switch agent WebSocket consumer + HTTP room reply transport, persistent connection/cursor, ping/pong handling, reconnects, bounded synthetic incident handler.
- `tests/test_switch_event.py`: 17 offline unit tests for identity, room scoping, replay, expiry, denial, evidence integrity, insecure transport and cursor persistence.
- The 24 pre-event tests still pass. Overall local gate: 41 tests passed on Nov 6. Secret-pattern scan passed; it is not a comprehensive audit.

## Setup required for a REAL Switch demo

1. Set up Switch Console and a local server with its bundled Mattermost on an isolated computer following https://docs.switchagents.ai/switch-rooms/getting-started.
2. Create a room with a genuine logged-in operator. Register a custom agent as its owner using the Switch Gateway. For one-time registration, Switch's docs specify `POST /agents` with a separate **registration key**, not the agent's API key. Registration response includes `id` and `api_key` once. NEVER copy this credential into Git, screenshots or shared messages.
3. Add the agent to the room and configure Switch addressing permissions. Capture exact opaque `agent_id`, `room_id` and operator participant ID from authenticated Switch records. Never infer identity from display names.
4. Install the Python module locally (`python -m pip install -e '.[switch]'`) in a virtual environment.
5. Set environment variables **locally**, not in a tracked file:

   - `SWITCH_URL`: bridge server address. Only `http://localhost` / `http://127.0.0.1` or remote HTTPS permitted.
   - `SWITCH_AGENT_ID`: returned ID from registration.
   - `SWITCH_AGENT_API_KEY`: agent key returned from registration (never registration key).
   - `SWITCH_ROOM_ID`: actual room ID.
   - `SWITCH_APPROVER_ID`: exact operator participant ID, e.g. an opaque ID issued by Switch (not the operator's chosen name).

6. Start the bridge: `python -m inneros_incident_room.switch_event`.
7. In the real room address the agent with `!incident`. Read proposed action identifier and address `!deny ACTION_ID`, then open a new incident and address `!approve ACTION_ID`. The code refuses approval from other sender IDs, other rooms, expired decisions or replays. It only changes a synthetic in-memory camera status and checks its own fixture readback.
8. Collect actual room screenshot, Switch server version, timestamped logs, anonymized actor IDs, and a video. **Do not claim success until a human room message appears and the agent posts replies in the real Switch room.**

## Live verification checklist

- [ ] Switch Console installed and healthy on isolated host
- [ ] Mattermost room with authenticated human and custom agent
- [ ] Agent registration completed (secret stored outside source)
- [ ] Addressed message delivered over documented WebSocket to agent
- [ ] Synthetic diagnostic reply posted via Switch HTTP into same room
- [ ] Wrong human/room approval rejected by code
- [ ] Genuine approver denies first attempt; state does not change
- [ ] Genuine approver approves second; synthetic verified receipt posted
- [ ] Reconnect/replay tested on the actual Switch version
- [ ] CI passing in a standalone public repository
- [ ] Real video recorded and submitted manually on WeMakeDevs

## Scope reduction for the remaining time

The official rules require at least **one person and one AI agent** collaborating through Switch. A second fully separate FieldOps agent is optional until the first live E2E passes. Do not make OpenCode, model routing, UniFi or Temporal a blocker. One genuine operator + one working custom agent with safe approval + proof beats an elaborate offline demo that never uses Switch.

## Limitations of this first implementation

This code is a **candidate adapter**, not a successful end-to-end integration. The exact Switch version and connected server still need smoke testing and may require protocol adjustments. Its synthetic readback is deliberately not independent physical telemetry. The SHA-256 digest checks data integrity only and is not a cryptographic signature. It is an experiment under contest constraints, not a commercial production access-control implementation.
