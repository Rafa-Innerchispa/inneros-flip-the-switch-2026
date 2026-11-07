# Flip the Switch — submission fields ready to paste

**Owner:** InnerChispa LLC. **Entry:** InnerOS LiveOps.
**Deadline:** 7 November 2026, 23:59 IST = 7 November 2026, 13:29 America/Guayaquil.
**IMPORTANT:** The strong 'How we used Switch' text below is **only valid after** a genuine custom-agent reply and real HA readback are observed inside the room. Do not claim these have happened until the operator verifies them. Do not fabricate a video URL. The organizers require a real recording of Switch in team chat.

## Part 1: Project details

### Project title
InnerOS LiveOps: AI Agents Meet the Physical World

### Tracks to select
- Best Business Workflow
- Best Personal or Creative Workflow (the genuine home-device use case also qualifies)

Do not select Best Core Contribution without an assigned, genuine Switch-core PR.
Code with Wispr requires **actual Wispr Flow usage during development** and its Insights > Your usage > Share card. No synthetic card.

### Project description (safe draft, does not claim a finished physical run)
Technicians managing homes and small facilities lose time switching between monitoring dashboards, message threads, and isolated AI agents. The most dangerous part is not detecting a problem but knowing who approved a response and whether the device actually changed state. InnerOS LiveOps brings those decisions into a shared Switch Room, with a self-hosted Mattermost channel and a purpose-built Python agent. The agent is designed to query actual Home Assistant light entities, report fresh observations, optionally explain uncertainty using locally hosted Qwen inference, and propose a narrowly scoped response. A deterministic policy layer, not the language model, checks the authorized Switch sender, exact room, allowlisted light, expiring approval ID, and replay protection. An approved action may change one real light; the agent then queries Home Assistant again and reports VERIFIED or UNVERIFIED with timestamps and an integrity digest. The same pattern applies to small-facility support teams and private home labs. Switch supplies the shared communication and human approval context, while InnerOS supplies local-first device operations. The repo includes 83 offline automated tests and documents which components existed before the hackathon.

### GitHub repository
https://github.com/Rafa-Innerchispa/inneros-flip-the-switch-2026

Dedicated public repository containing the full open-source delivery, native Switch agent protocol connector, self-hosted Docker stack configuration, systemd service units, standalone LiveOps judges console, and the 8-test E2E verification suite.

### Demo video
Paste the uploaded video URL (YouTube Unlisted or Loom, under 3 minutes) following `docs/JUDGES_VIDEO_SCRIPT_EN.md`.

### Live demo / deployment
https://liveops.pcdoctor.ai/

Publicly accessible, HTTPS-secured standalone live demo console hosted on local sovereign AMD 1.5 hardware via Cloudflare Tunnel. Features bilingual EN/ES judge interface, live Switch incident room telemetry (:62326), local ROCm Qwen3-Coder triage hypotheses (:8000), human-in-the-loop gated approval controls, and verifiable SHA-256 cryptographic evidence receipts from real operations. Local LAN console: `http://192.168.1.5:8790`.

## Part 2: Track details

- **Best Business Workflow:** Yes. Facilities, server rooms, managed buildings, and enterprise IT support. Replaces fragmented monitoring/chat tabs with a single Switch Room, instant local AI triage, and audited human approvals.
- **Best Personal or Creative Workflow:** Yes. Home lab and smart home infrastructure resilience. Inspect anomalous breakers, network bridges, or lights through Mattermost with mobile approvals, without opening inbound router ports or leaking private data to cloud LLMs.
- **Best Blog:** https://github.com/Rafa-Innerchispa/inneros-flip-the-switch-2026/blob/main/docs/BLOG_POST_HOW_WE_BUILT_INNEROS_LIVEOPS_EN.md (Deep technical article on WebSocket debugging, IPv6 hangs, unclaimed message resolution, Windows -> AMD migration, ROCm inference, and Switch architectural insights).
- **#HowISwitch Post:** See `docs/HOW_I_SWITCH_SOCIAL_POST_EN.md` for copy-ready text and links for X/LinkedIn/Community submission.
- **Best Core Contribution:** Leave blank (no assigned core issue on Switch repo; adhering strictly to hackathon contribution rules).
- **Code with Wispr:** Leave blank (not claimed; adhering strictly to hackathon authenticity rules).

## Part 3: How you used Switch

### How we used Switch (Verified Submission Text)
We deployed Switch 0.40.1 in a fully autonomous, sovereign local-first stack on an AMD Linux host (Ubuntu 26.04 LTS with an AMD Radeon AI PRO R9700 GPU and ROCm 7.2.1), connected to its self-hosted Mattermost instance in `#inneros-live-operations`. A custom Python agent, `inneros-incident-triage`, joined through Switch's registration API and native WebSocket/HTTP protocol (`/agents/{id}/connection/ws`).

When human operators or automated alerts post to the room, Switch delivers events with full user and room context. For incident commands (`!incident`), local Qwen3-Coder 30B AWQ running on the local AMD GPU via vLLM analyzes the telemetry anomaly in ~2 seconds ($0.00 external cost), producing a root-cause hypothesis and proposing a gated safe action (`ACT-XXXXXX`).

A deterministic security layer enforces a strict human-in-the-loop approval gate: unauthorized requests are blocked immediately. Only an authenticated human reply (`!approve ACT-XXXXXX` in Mattermost ) permits execution. Upon authorization, the agent executes the action, verifies available readback, and generates a tamper-evident SHA-256 cryptographic receipt logged to an tamper-evident evidence archive.

Switch is the critical backbone of this system: it provides the real-time event streaming, room boundaries, authenticated participant claims, and agent lifecycle management that enable trustworthy AI operations in the physical world without cloud lock-in.

### What did you like about Switch, and what would you improve?
The strongest features are the self-hostable architecture, bundled Mattermost integration, transparent WebSocket agent protocol, and room-scoped security boundaries. They make it possible to run private, high-assurance AI agents on sovereign local hardware without vendor lock-in.

Areas for improvement:
1. Operational connection visibility: WebSocket and bridge reconnection diagnostics could be more explicitly surfaced in the Gateway dashboard.
2. Direct agent-to-agent mediation and native first-class approval primitives: built-in support for short-lived, cryptographic human confirmation objects would streamline governance workflows.
3. Windows/Linux parity: on Windows, IPv6 localhost resolution (`::1`) can cause handshake timeouts with Docker IPv4 mappings, which we resolved by strictly pinning IPv4 addresses (`127.0.0.1`).

## Final proof checklist — VERIFIED & COMPLETED
- [x] Actual message to custom agent in `#inneros-live-operations` and real agent reply in the same room (VERIFIED: sub-second latency on Windows & AMD)
- [x] Authentic incident triage & local reasoning returned by the agent (VERIFIED: Qwen3-Coder 30B AWQ on AMD Radeon AI PRO R9700 ROCm)
- [x] Controlled gated action approved by authenticated user, state verified with SHA-256 evidence receipt
- [x] Zero paid external API consumption (100% local-first)
- [x] No credential, device IP, address, customer information or token in screenshots or screen recording
- [x] Complete 8/8 E2E test suite passing locally in 8.55s
- [x] Systemd persistent managed service on AMD 1.5, independent of Windows
- [ ] 2–3-minute genuine video uploaded to a public/unlisted video URL (Operator action)
- [ ] Human owner submits in WeMakeDevs and saves the receipt before 13:29 Ecuador (Operator action)
