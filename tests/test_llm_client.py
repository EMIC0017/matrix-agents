from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.llm_client import BedrockClient


class TestBedrockClient:
    def test_init_with_base_url(self):
        client = BedrockClient(base_url="https://gateway.example.com/bedrock")
        assert client.base_url == "https://gateway.example.com/bedrock"

    @pytest.mark.asyncio
    async def test_chat_formats_request(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello from Bedrock")]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        client = BedrockClient(base_url="https://gateway.example.com/bedrock")
        client._client = mock_client

        result = await client.chat(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result == "Hello from Bedrock"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]

    @pytest.mark.asyncio
    async def test_chat_timeout_raises(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=TimeoutError("Request timed out")
        )

        client = BedrockClient(base_url="https://gateway.example.com/bedrock")
        client._client = mock_client

        with pytest.raises(TimeoutError):
            await client.chat(
                system_prompt="test",
                messages=[{"role": "user", "content": "test"}],
            )
