# Judges Video Demonstration Script: InnerOS LiveOps (< 3 Minutes)

**Target Duration:** 2 minutes 45 seconds (Under the 3-minute hard limit).  
**Recording Setup:**  
- Left screen / Window 1: Mattermost channel `#inneros-live-operations`.  
- Right screen / Window 2: Standalone LiveOps Judges Console (`https://liveops.pcdoctor.ai/`).  
- Terminal / Optional overlay: AMD 1.5 system monitor showing ROCm GPU utilization during inference.  
- Clear audio narration in English.

---

## 00:00 – 00:25 | Hook & The Physical Dilemma

**Visual:** Camera on narrator or screen showing Mattermost `#inneros-live-operations` alongside the Standalone LiveOps Console.

**Spoken Narration (English):**
> "Most AI agents today operate behind a glass wall—writing code or answering chat questions. But in mission-critical facilities, smart edge nodes, and automated buildings, the real challenge is physical operations: who authorized an actuation, and how do you guarantee an AI model didn't hallucinate an uncontrolled action?  
> I'm Rafael from InnerChispa, and this is **InnerOS LiveOps**, built on **Switch**."

---

## 00:25 – 00:55 | Switch as the Essential Backbone (Sub-Second Latency)

**Visual:** In Mattermost `#inneros-live-operations`, type:
`@inneros-incident-triage !ping`  
Followed immediately by:
`@inneros-incident-triage !status`

**Spoken Narration (English):**
> "Switch is our indispensable operational backbone. It provides sovereign local event streaming, authenticated participant claims, and room-scoped security.  
> As you see here, when I send `!ping`, Switch streams the event through its native WebSocket protocol to our Python agent on an AMD host. The agent replies in under a second.  
> Our `!status` command confirms our sovereign environment: running on AMD 1.5, connected to local vLLM, with our physical safety gate strictly ACTIVE."

---

## 00:55 – 01:30 | Sovereign Anomaly Triage via Local AMD ROCm Inference

**Visual:** In Mattermost, type:
`@inneros-incident-triage !incident`  
Show the reply populating in Mattermost with the root-cause hypothesis and proposed action ID (`ACT-XXXXXX`).

**Spoken Narration (English):**
> "Now let's simulate an operational infrastructure anomaly on synthetic node-alpha-4.  
> The agent ingests the anomaly telemetry and queries our local Qwen3-Coder 30B model running on our AMD Radeon AI PRO R9700 GPU via ROCm.  
> In just two seconds—with zero external cloud tokens or API spend—it produces a root-cause hypothesis identifying buffer overflow, and proposes a narrowly scoped remediation: Action `ACT-XXXXXX`.  
> Crucially, the model CANNOT execute this action on its own. It requires explicit, short-lived human authorization."

---

## 01:30 – 01:55 | The Deterministic Safety Gate: Rejecting Unauthorized Action

**Visual:** In Mattermost, deliberately type:
`@inneros-incident-triage !approve ACT-FAKE999`  
Show the agent immediately rejecting: `[INNEROS BLOCKED] No pending approval found for action ID 'ACT-FAKE999'.`

**Spoken Narration (English):**
> "Watch what happens if someone attempts to run an unapproved command or exploit an invalid ID.  
> Our deterministic security policy layer halts execution immediately. Unapproved requests never touch system targets. Autonomy without governance is not allowed."

---

## 01:55 – 02:25 | Valid Human Approval & Tamper-Evident SHA-256 Digest

**Visual:** In Mattermost, issue the valid approval:  
`@inneros-incident-triage !approve ACT-XXXXXX`  
Show the execution confirmation, closed incident, and SHA-256 receipt.

**Spoken Narration (English):**
> "Now, the authenticated operator provides explicit authorization for the proposed action.  
> The agent executes the safe diagnostic cycle, verifies readback, and generates a tamper-evident SHA-256 cryptographic digest linking the incident ID, operator identity, timestamp, and target state. The incident is verified and closed."

---

## 02:25 – 02:45 | Standalone Judges Console & Multi-Track Value

**Visual:** Switch browser tab to `https://liveops.pcdoctor.ai/`. Show the live status chips, the simulated playground walkthrough, the recorded live receipts table, and the 8/8 PASS E2E test matrix.

**Spoken Narration (English):**
> "Everything is mirrored in real time on our standalone public LiveOps Console at `liveops.pcdoctor.ai`, deployed via Cloudflare Tunnel.  
> For enterprise facility management—our **Best Business Workflow**—this replaces fragmented monitoring dashboards with a single auditable room.  
> For home lab resilience—our **Best Personal Workflow**—it gives homeowners safe remote oversight of smart breakers without cloud lock-in."

---

## 02:45 – 02:55 | Closing

**Visual:** Quick view of the public GitHub repository and final test summary.

**Spoken Narration (English):**
> "With Switch Rooms and InnerOS, human operators and AI agents collaborate as genuine teammates—local-first, fully sovereign, and verifiable. Thank you."

---

## Video Recording Checklist

- [ ] Video duration strictly between 2:15 and 2:55.
- [ ] Mattermost `#inneros-live-operations` clearly visible.
- [ ] Standalone LiveOps Console `https://liveops.pcdoctor.ai/` shown in browser with HTTPS lock icon.
- [ ] Uploaded to YouTube as **Unlisted** (or Loom) with link copied into the submission form.
