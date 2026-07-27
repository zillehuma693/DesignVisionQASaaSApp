from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def analyze_scan(self, url: str, bugs: list[dict]) -> str:
        pass

    @abstractmethod
    async def analyze_bug(self, bug: dict) -> tuple[str, str]:
        pass


class FallbackAIProvider(AIProvider):
    name = "fallback"

    async def analyze_scan(self, url: str, bugs: list[dict]) -> str:
        if not bugs:
            return f"Scan of {url} completed with no issues detected. The page appears healthy."
        critical = sum(1 for b in bugs if b.get("severity") == "critical")
        high = sum(1 for b in bugs if b.get("severity") == "high")
        return (
            f"Scan of {url} found {len(bugs)} issue(s): "
            f"{critical} critical, {high} high severity. "
            "Review accessibility, broken resources, and console errors first."
        )

    async def analyze_bug(self, bug: dict) -> tuple[str, str]:
        explanation = (
            f"This {bug.get('severity', 'medium')} issue in {bug.get('component', 'Unknown')} "
            f"was detected via automated analysis: {bug.get('description', '')}"
        )
        fix = bug.get("fix_suggestion") or "Inspect the element and apply appropriate fixes based on the issue type."
        return explanation, fix


class OpenAIProvider(AIProvider):
    name = "openai"

    async def analyze_scan(self, url: str, bugs: list[dict]) -> str:
        import httpx

        prompt = f"Summarize QA scan results for {url}. Bugs: {bugs[:20]}. Be concise, actionable."
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def analyze_bug(self, bug: dict) -> tuple[str, str]:
        import httpx

        prompt = (
            f"Analyze this frontend bug and suggest a fix.\n"
            f"Title: {bug.get('title')}\nDescription: {bug.get('description')}\n"
            f"Selector: {bug.get('selector')}\n"
            f"Return JSON with keys: explanation, fix_suggestion"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return content[:500], content[500:1000] if len(content) > 500 else content


class OllamaProvider(AIProvider):
    name = "ollama"

    async def _chat(self, prompt: str) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def analyze_scan(self, url: str, bugs: list[dict]) -> str:
        prompt = f"Summarize QA scan for {url}. Found {len(bugs)} bugs. Be concise."
        return await self._chat(prompt)

    async def analyze_bug(self, bug: dict) -> tuple[str, str]:
        content = await self._chat(f"Explain and fix: {bug.get('title')} - {bug.get('description')}")
        mid = len(content) // 2
        return content[:mid], content[mid:]


def get_ai_provider() -> AIProvider:
    provider = settings.ai_provider.lower()
    if settings.ai_enabled and provider == "openai" and settings.openai_api_key:
        return OpenAIProvider()
    if settings.ai_enabled and provider == "ollama":
        return OllamaProvider()
    if settings.ai_enabled and provider in ("anthropic", "gemini"):
        logger.info("Provider %s configured but using fallback for MVP", provider)
    return FallbackAIProvider()
