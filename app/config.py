"""Config — reads from env (WAS_*), .env file, or Streamlit secrets."""
from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE = Path(__file__).parent.parent


def _load_streamlit_secrets() -> None:
    """When running under Streamlit, mirror st.secrets into os.environ so pydantic picks them up."""
    try:
        import streamlit as st  # type: ignore
        if not hasattr(st, "secrets"):
            return
        try:
            _ = dict(st.secrets)  # probe — may raise if no secrets.toml
        except Exception:
            return
        for key in (
            "WAS_OPENAI_API_KEY", "WAS_ALPHA_VANTAGE_KEY",
            "WAS_MODEL", "WAS_TEMPERATURE",
        ):
            if key in st.secrets and key not in os.environ:
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass


_load_streamlit_secrets()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    alpha_vantage_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.3

    guide_pdf_path: str = str(BASE / "data" / "mi-guide-to-the-markets-us.pdf")
    output_dir: str = str(BASE / "output")
    cache_dir: str = str(BASE / "cache")

    price_cache_ttl_seconds: int = 900
    av_request_delay_seconds: float = 13.0


settings = Settings()
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
Path(settings.cache_dir).mkdir(parents=True, exist_ok=True)
