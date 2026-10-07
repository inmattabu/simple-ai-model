import os
import time
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

app = FastAPI(title="Simple Chat Bot", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30
MAX_HISTORY_ITEMS = 12
MAX_HISTORY_MESSAGE_LENGTH = 2000
MAX_MESSAGE_LENGTH = 2000


class RateLimiter:
    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        timestamps = self._requests.setdefault(key, [])
        timestamps[:] = [ts for ts in timestamps if now - ts < self.window_seconds]

        if len(timestamps) >= self.max_requests:
            return False

        timestamps.append(now)
        return True


rate_limiter = RateLimiter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[dict[str, str]] | None = None


class ChatResponse(BaseModel):
    reply: str


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)


def sanitize_message(message: str) -> str:
    normalized = message.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(normalized) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message exceeds {MAX_MESSAGE_LENGTH} characters.")
    if "\x00" in normalized:
        raise HTTPException(status_code=400, detail="Message contains invalid characters.")
    return normalized


def sanitize_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if not history:
        return []

    if not isinstance(history, list):
        raise ValueError("History must be a list of messages.")

    cleaned: list[dict[str, str]] = []
    for item in history[:MAX_HISTORY_ITEMS]:
        if not isinstance(item, dict):
            raise ValueError("Each history item must be an object.")

        role = item.get("role")
        content = item.get("content")

        if role not in {"user", "assistant"}:
            raise ValueError("Only user and assistant roles are allowed in request history.")
        if not isinstance(content, str):
            raise ValueError("History content must be a string.")

        trimmed = content.strip()
        if not trimmed:
            continue

        if len(trimmed) > MAX_HISTORY_MESSAGE_LENGTH:
            trimmed = trimmed[:MAX_HISTORY_MESSAGE_LENGTH]

        cleaned.append({"role": role, "content": trimmed})

    return cleaned


def normalize_base_url(raw_base_url: str | None) -> str | None:
    if raw_base_url is None or not raw_base_url.strip():
        return None

    candidate = raw_base_url.strip().rstrip("/")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("OPENAI_BASE_URL must be a valid http(s) URL.")

    allowed_urls = {
        url.strip().rstrip("/")
        for url in os.getenv(
            "OPENAI_ALLOWED_BASE_URLS",
            "https://api.openai.com/v1",
        ).split(",")
        if url.strip()
    }

    if candidate not in allowed_urls:
        raise ValueError(
            "OPENAI_BASE_URL is not in the trusted allowlist. "
            f"Allowed values: {', '.join(sorted(allowed_urls))}"
        )

    return candidate


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured.")

    base_url = normalize_base_url(os.getenv("OPENAI_BASE_URL"))
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url is not None:
        client_kwargs["base_url"] = base_url
    return OpenAI(**client_kwargs)


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "simple-chat-bot"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    client_ip = get_client_ip(http_request)
    if not rate_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    try:
        client = get_client()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        history = sanitize_history(request.history)

        sanitized_message = sanitize_message(request.message)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": "You are a helpful chatbot for labs2jobs.com."}
        ]

        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})

        messages.append({"role": "user", "content": sanitized_message})

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )

        reply = completion.choices[0].message.content or "I do not have a response for that yet."
        return ChatResponse(reply=reply)
    except Exception as exc:  # pragma: no cover - depends on external API availability
        raise HTTPException(status_code=500, detail=f"Failed to generate a response: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "9009"))
    uvicorn.run("app:app", host=host, port=port, reload=True)
