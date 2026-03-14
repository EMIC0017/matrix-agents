import uuid

from shared.models import AgentMessage, AgentResult, AgentStatus


class TestAgentResult:
    def test_success_result(self):
        result = AgentResult(agent="Trinity", status="success", content="Done.")
        assert result.agent == "Trinity"
        assert result.status == "success"
        assert result.data == {}
        assert result.error is None

    def test_error_result(self):
        result = AgentResult(
            agent="Morpheus", status="error", content="", error="LLM timeout"
        )
        assert result.status == "error"
        assert result.error == "LLM timeout"


class TestAgentMessage:
    def test_create_message(self):
        msg = AgentMessage(
            source="Neo",
            target="Trinity",
            action="execute",
            payload={"task": "summarize"},
        )
        assert msg.source == "Neo"
        assert msg.target == "Trinity"
        assert msg.id is not None
        assert msg.priority == 5
        assert msg.correlation_id is None

    def test_message_with_correlation(self):
        cid = uuid.uuid4()
        msg = AgentMessage(
            source="Neo",
            target="Trinity",
            action="execute",
            payload={},
            correlation_id=cid,
        )
        assert msg.correlation_id == cid


class TestAgentStatus:
    def test_default_status(self):
        status = AgentStatus(name="Trinity", role="Executive Assistant")
        assert status.status == "IDLE"
