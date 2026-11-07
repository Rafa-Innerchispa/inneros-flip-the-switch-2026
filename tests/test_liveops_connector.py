"""Unit and integration tests for InnerOS LiveOps Switch Connector."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from inneros_incident_room.connector import LiveOpsEngine, LocalModelClient


class TestLiveOpsConnector(unittest.TestCase):
    def setUp(self):
        self.engine = LiveOpsEngine(
            switch_url="http://127.0.0.1:62326",
            room_name="inneros-live-operations",
            agent_name="inneros-incident-triage",
            node_id="TEST-NODE"
        )
        self.engine.room_id = "test-room-id"
        self.engine.agent_id = "test-agent-id"
        self.engine.api_key = "test-key"

    def test_ping_command(self):
        reply = self.engine.handle_command("user1", "!ping")
        self.assertIsNotNone(reply)
        self.assertIn("PONG", reply)
        self.assertIn("TEST-NODE", reply)

    def test_status_command(self):
        reply = self.engine.handle_command("user1", "!status")
        self.assertIsNotNone(reply)
        self.assertIn("INNEROS STATUS TEST-NODE", reply)

    def test_incident_and_approval_flow(self):
        # 1. Trigger incident
        incident_reply = self.engine.handle_command("user1", "!incident")
        self.assertIsNotNone(incident_reply)
        self.assertIn("INNEROS INCIDENT", incident_reply)
        self.assertIn("Proposed Gated Action:", incident_reply)

        # Extract action ID
        act_id = list(self.engine.pending_actions.keys())[0]
        self.assertTrue(act_id.startswith("ACT-"))

        # 2. Approve action
        approve_reply = self.engine.handle_command("user1", f"!approve {act_id}")
        self.assertIsNotNone(approve_reply)
        self.assertIn("INNEROS ACTION EXECUTED", approve_reply)
        self.assertIn("SHA256:", approve_reply)
        self.assertEqual(len(self.engine.pending_actions), 0)

    def test_incident_and_deny_flow(self):
        # 1. Trigger incident
        self.engine.handle_command("user1", "!incident")
        act_id = list(self.engine.pending_actions.keys())[0]

        # 2. Deny action
        deny_reply = self.engine.handle_command("user1", f"!deny {act_id}")
        self.assertIsNotNone(deny_reply)
        self.assertIn("INNEROS DENIED", deny_reply)
        self.assertEqual(len(self.engine.pending_actions), 0)

    def test_unauthorized_action(self):
        reply = self.engine.handle_command("user1", "!approve NON_EXISTENT")
        self.assertIn("BLOCKED", reply)


if __name__ == "__main__":
    unittest.main()
