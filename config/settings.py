from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    matrix_env: str = "zion"
    log_level: str = "INFO"

    # Slack
    slack_mode: str = "console"  # "console" or "slack"
    slack_bot_token: str = ""
    slack_channel_id: str = ""

    # LLM (Bedrock via AI Gateway)
    anthropic_bedrock_base_url: str = ""

    # Redis
    redis_host: str = "zion-redis"
    redis_port: int = 6379

    # ChromaDB
    chroma_host: str = "zion-chromadb"
    chroma_port: int = 8001

    # Brain (shared memory)
    brain_mode: str = "persistent"  # "ephemeral", "persistent", "docker"
    brain_data_path: str = "data/brain"

    # MCP Server
    mcp_port: int = 8002
    mcp_access_key: str = ""  # Empty = no auth (dev mode)

    # Slack Capture
    slack_capture_channel_id: str = ""

    # Orchestration
    orchestrator_type: str = "matrix"  # "matrix" or "cowork"

    # Safety
    max_agent_iterations: int = 50
    sandbox_mode: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
