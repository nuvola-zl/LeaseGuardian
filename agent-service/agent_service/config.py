import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_base_url: str
    openai_api_key: str
    openai_model: str
    agent_host: str
    agent_port: int
    openai_embed_model: str
    openai_model_persona: str

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        host = os.getenv("AGENT_SERVICE_HOST", "127.0.0.1").strip()
        port = int(os.getenv("AGENT_SERVICE_PORT", "8000"))

        missing = []
        if not base_url:
            missing.append("OPENAI_BASE_URL")
        if not api_key:
            missing.append("OPENAI_API_KEY")
        if not model:
            missing.append("OPENAI_MODEL")
        if missing:
            raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

        return cls(
            openai_base_url=base_url,
            openai_api_key=api_key,
            openai_model=model,
            agent_host=host,
            agent_port=port,
            openai_embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small").strip(),
            openai_model_persona=os.getenv("OPENAI_MODEL_PERSONA", "qwen-flash").strip(),
        )


settings = Settings.from_env()