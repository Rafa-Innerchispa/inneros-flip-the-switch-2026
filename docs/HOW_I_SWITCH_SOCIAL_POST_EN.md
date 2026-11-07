# #HowISwitch — Verified Social Post (November 7, 2026)

**Prepared for Rafael López / InnerChispa. Not automatically published.**

## Recommended LinkedIn / X post

What happens when an AI agent can diagnose infrastructure problems but must never authorize its own actions?

For the **Flip the Switch Hackathon**, we built **InnerOS LiveOps** at InnerChispa.

Instead of a chatbot answering in isolation, our operators and a custom Python agent collaborate in a self-hosted Mattermost room through **Switch**.

Here's what we verified:
- Real Mattermost → Switch → Python agent messages and replies, traced with correlation IDs.
- Local incident triage using Qwen3-Coder on an AMD Radeon AI PRO R9700 with ROCm/vLLM.
- A deterministic approval policy that blocks unknown action IDs.
- Archived command results and SHA-256 evidence receipts for authorized diagnostic tests.
- A read-only public dashboard showing current service health separately from historical test records.

Our incident integration test uses synthetic anomaly input. The communication, inference, and policy checks run on real infrastructure; we do **not** claim a physical device was repaired.

**Switch connects the people. Local AI analyzes. Human authorization remains in charge.**

🔎 https://liveops.pcdoctor.ai/
💻 https://github.com/Rafa-Innerchispa/inneros-flip-the-switch-2026

Rafael López | CEO, InnerChispa LLC

#HowISwitch #FlipTheSwitch #InnerOS #LocalAI #Mattermost #ROCm

## Compact X post

Built InnerOS LiveOps for #FlipTheSwitch: real Mattermost → Switch → local Qwen on AMD, traceable replies, human approval gates, and recorded SHA-256 diagnostic receipts. Real integration; synthetic anomaly test; no invented device actuation. https://liveops.pcdoctor.ai/ #HowISwitch

## Submission instructions

1. Publish the post from your own social profile.
2. Copy the public URL of that post into the optional **Your #HowISwitch post** field on the Flip the Switch submission page.
3. Keep the separate **Blog post** link for the optional Best Blog prize. A GitHub markdown draft is not itself proof of social publication.
