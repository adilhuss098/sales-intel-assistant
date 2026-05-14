import anthropic
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

_client = None


def _get_api_key() -> str:
    # Streamlit Cloud stores secrets in st.secrets
    try:
        import streamlit as st
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    # Local: reads from .env
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to .env (local) or Streamlit secrets (cloud).")
    return key


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=_get_api_key())
    return _client


def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.md"
    return path.read_text()


def call_model(
    model: str,
    system: str,
    user: str,
    max_tokens: int = 4096,
    cache_system: bool = True,
) -> str:
    client = get_client()

    system_content = [
        {
            "type": "text",
            "text": system,
            **({"cache_control": {"type": "ephemeral"}} if cache_system else {}),
        }
    ]

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_content,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text
