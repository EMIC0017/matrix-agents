from anthropic import AsyncAnthropicBedrock

from config.settings import settings


class BedrockClient:
    """Thin wrapper around the Anthropic SDK configured for Bedrock via AI Gateway.

    Uses AsyncAnthropicBedrock with dummy AWS credentials because the Instacart AI
    Gateway handles auth at the proxy level. The Bedrock client is needed to produce
    the correct URL path format (/model/.../invoke) that the gateway expects.
    """

    DEFAULT_MODEL = "claude-sonnet-4"

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.anthropic_bedrock_base_url
        self._client = AsyncAnthropicBedrock(
            aws_region="us-east-1",
            aws_access_key="not-needed",
            aws_secret_key="not-needed",
            base_url=self.base_url if self.base_url else None,
        )

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str | None = None,
        timeout: float = 30.0,
    ) -> str:
        """Send a chat request and return the response text."""
        response = await self._client.messages.create(
            model=model or self.DEFAULT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            timeout=timeout,
        )
        return response.content[0].text
