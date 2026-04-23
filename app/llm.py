"""Async OpenAI client — strict structured output + plain-text narrative."""
from __future__ import annotations
import json
from typing import Type, TypeVar
from openai import AsyncOpenAI
from pydantic import BaseModel
from app.config import settings

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("WAS_OPENAI_API_KEY is not set.")
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def structured(system: str, user: str, schema: Type[T], *, model: str | None = None) -> T:
    client = get_client()
    mdl = model or settings.model
    try:
        resp = await client.beta.chat.completions.parse(
            model=mdl,
            temperature=settings.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=schema,
        )
        parsed = resp.choices[0].message.parsed
        if parsed is not None:
            return parsed
    except Exception:
        pass

    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    resp = await client.chat.completions.create(
        model=mdl,
        temperature=settings.temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"{system}\n\nRespond with JSON matching:\n{schema_json}"},
            {"role": "user", "content": user},
        ],
    )
    return schema.model_validate_json(resp.choices[0].message.content or "{}")
