# Standalone LiveOps deployment and Meta preservation

## Scope and current status

This branch adds an **independent static judges landing** at `site/index.html` with English default, Spanish toggle, mobile layout and an explicitly **simulated, non-operational** incident journey. It is **not yet deployed**, does not claim live backend access, and must not be presented as proof of live Switch operations.

**IMPORTANT:** The existing `https://guardian.pcdoctor.ai/` site currently identifies itself as "InnerOS Autonomous Infrastructure Guardian (Meta '26)" and contains a LiveOps section. Preserve the Meta experience and restore its exact **pre-LiveOps** UI from a verified prior build or Git commit, not from memory. Do not delete or overwrite data from the Meta project.

## Separation contract

1. **Meta site:** Keep `guardian.pcdoctor.ai` for the Meta hackathon. Before any change, capture its current static files, asset manifest, route map, hash list, DNS record and tunnel config. Identify the original Meta-only commit or deployed backup, and compare with current deployment. Restore only the UI changes introduced for Switch; preserve all Meta features and API contracts.
2. **Flip the Switch site:** Provision a **new** hostname, preferably `liveops.innerchispa.us` or `switch.innerchispa.us`, but only after checking availability and ownership in Cloudflare. Use a separate deployment directory/container and independent public route. Do not use `guardian.pcdoctor.ai/#liveops` as the submission URL once the new site is validated.
3. **No conflicts:** No overwrites of existing DNS records, ingress rules, running tunnels, project directories, shared configuration, frontend build outputs or other hackathons.
4. **Security:** The new static page is publicly safe and does not call operational APIs. A future *authenticated* operator section may query InnerOS through a reverse proxy with least-privilege read-only endpoints. No unauthenticated approve/execute, HA tokens, model tokens, private client incidents, internal node addresses, or device IDs in HTML.
5. **Proof labels:** Keep illustrative incidents marked SIMULATED. Actual live status chips must remain unverified until authenticated, recent health probes and screenshots from an external browser can support a truthful state.
6. **Rollback:** Preserve old Meta deployment and static assets as versioned artifacts; a rollback should switch only the Meta frontend target back to the pre-change build. The Switch site can be disabled without affecting Meta. No server-wide restarts.

## Safe operator implementation plan (Antigravity / local shell)

- Read active tunnels, DNS records, server routes, repositories, running web processes and their exact build roots.
- Identify the Meta-only source snapshot, including timestamps and hashes, before making changes.
- Test original Meta snapshot on an isolated preview hostname or port. Compare core flows and ensure Meta's original endpoints and actions still work.
- Deploy `site/index.html` from this branch to a **separate** static web service. Serve from an independent directory, with a dedicated Cloudflare ingress. Ensure the DNS name is unused and points only to this new service.
- Smoke-test EN and ES, desktop and mobile, keyboard navigation, buttons and links, SSL, no mixed content, and no requests to administrative ports.
- Test Meta before and after; record visual diff, health checks, and URL reachability externally. Update contest README only after the new URL works.
- For public judges' demo, link a separate verified recording of real Switch-to-Mattermost agent roundtrip. Do not claim the static illustration is a live action.

## Acceptance checklist

- [ ] Meta original pre-Switch design restored from a real source snapshot and visually regression tested.
- [ ] Meta functionality works as before; no DNS/routing changes to other projects.
- [ ] Independent public LiveOps hostname available and HTTPS reachable from outside LAN.
- [ ] EN default, ES toggle, and responsive landing verified externally.
- [ ] Public view contains only safe/sanitized data, no physical controls.
- [ ] End-to-end agent evidence available separately, with correlation IDs.
- [ ] New hostname recorded in submission material.
- [ ] Rollback instructions and backup hashes recorded privately.

**Status of this branch:** Source-only implementation of independent frontend. Server/Cloudflare deployment and restoration of the Meta production frontend require access to the actual hosts and original pre-change artifact.
