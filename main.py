"""
NexusAPI — портфельный FastAPI-сервис с интеграцией Loki
"""

import hashlib
import platform
import uuid
import random
import os
import time
import httpx
from datetime import datetime
from typing import Literal

import psutil
import pytz
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

app = FastAPI(
    title="NexusAPI",
    description="""
## 🚀 NexusAPI — Developer Utility Backend

### Стек:
`FastAPI` · `Python 3.11` · `Docker` · `GitHub Actions CI/CD` · `Grafana` · `Loki`
""",
    version="2.0.0",
)

LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")


async def send_log_to_loki(message: str, level: str = "info", **extra_labels):
    """
    Отправляет лог в Loki через POST /loki/api/v1/push.

    Формат Loki:
    {
      "streams": [
        {
          "stream": { "app": "nexus-api", "level": "info" },
          "values": [["<unix_nano>", "<message>"]]
        }
      ]
    }
    """
    timestamp_ns = str(int(time.time() * 1_000_000_000))
    labels = {"app": "nexus-api", "level": level}
    labels.update(extra_labels)

    payload = {
        "streams": [{"stream": labels, "values": [[timestamp_ns, message]]}]
    }

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                f"{LOKI_URL}/loki/api/v1/push",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
    except Exception:
        pass  # не ломаем приложение если Loki недоступен


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware — логирует каждый входящий запрос."""
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)

    msg = (
        f"method={request.method} "
        f"path={request.url.path} "
        f"status={response.status_code} "
        f"duration={duration}ms"
    )
    level = "error" if response.status_code >= 500 else (
        "warning" if response.status_code >= 400 else "info"
    )
    await send_log_to_loki(msg, level=level, endpoint=request.url.path)
    return response


DEV_QUOTES = [
    {"text": "Любой дурак может написать код, понятный компьютеру.", "author": "Martin Fowler"},
    {"text": "Простота — предпосылка надёжности.", "author": "Edsger W. Dijkstra"},
    {"text": "Преждевременная оптимизация — корень всех зол.", "author": "Donald Knuth"},
    {"text": "Код читают чаще, чем пишут.", "author": "Guido van Rossum"},
    {"text": "Не комментируй плохой код — перепиши его.", "author": "Brian W. Kernighan"},
]


class TimezoneConvertRequest(BaseModel):
    datetime_str: str = Field(..., example="2024-01-15 14:30:00")
    from_tz: str = Field(..., example="Europe/Moscow")
    to_tz: str = Field(..., example="America/New_York")


class HashRequest(BaseModel):
    text: str = Field(..., example="hello world")
    algorithm: Literal["sha256", "md5", "sha512"] = Field("sha256")


class LogRequest(BaseModel):
    message: str = Field(..., example="Тестовый лог от пользователя")
    level: Literal["info", "warning", "error"] = Field("info")


@app.get("/", tags=["Info"])
async def root():
    return {"project": "NexusAPI", "version": "2.0.0", "docs": "/docs"}


@app.get("/health", tags=["Monitoring"], summary="Состояние сервера")
async def health():
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cpu": {"usage_percent": psutil.cpu_percent(interval=0.1)},
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "usage_percent": psutil.virtual_memory().percent,
        },
        "uptime": f"{hours}h {minutes}m {seconds}s",
    }


@app.get("/datetime", tags=["Datetime"], summary="Текущее время")
async def get_datetime(tz: str = "Europe/Moscow"):
    try:
        timezone = pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail=f"Неизвестный часовой пояс: '{tz}'")
    now = datetime.now(timezone)
    return {
        "timezone": tz,
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": now.strftime("%A"),
        "unix_timestamp": int(now.timestamp()),
    }


@app.post("/timezone/convert", tags=["Datetime"], summary="Конвертация часового пояса")
async def convert_timezone(body: TimezoneConvertRequest):
    try:
        src_tz = pytz.timezone(body.from_tz)
        dst_tz = pytz.timezone(body.to_tz)
    except pytz.UnknownTimeZoneError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        naive_dt = datetime.strptime(body.datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(status_code=400, detail="Формат: YYYY-MM-DD HH:MM:SS")
    src_dt = src_tz.localize(naive_dt)
    dst_dt = src_dt.astimezone(dst_tz)
    return {
        "input": {"datetime": body.datetime_str, "timezone": body.from_tz},
        "output": {"datetime": dst_dt.strftime("%Y-%m-%d %H:%M:%S"), "timezone": body.to_tz},
    }


@app.get("/devquote", tags=["Fun"], summary="Цитата разработчика")
async def dev_quote():
    quote = random.choice(DEV_QUOTES)
    return {"quote": quote["text"], "author": quote["author"]}


@app.post("/tools/hash", tags=["Tools"], summary="Хеширование строки")
async def hash_text(body: HashRequest):
    h = hashlib.new(body.algorithm)
    h.update(body.text.encode("utf-8"))
    return {"input": body.text, "algorithm": body.algorithm, "hash": h.hexdigest()}


@app.get("/tools/uuid", tags=["Tools"], summary="Генерация UUID")
async def generate_uuid(count: int = 1):
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count: 1-20")
    result = [str(uuid.uuid4()) for _ in range(count)]
    return {"count": count, "uuids": result if count > 1 else result[0]}


@app.post("/logs/send", tags=["Logs"], summary="Отправить лог в Loki")
async def send_log(body: LogRequest):
    """
    Отправляет произвольное сообщение в Loki.
    Используй для проверки — открой Grafana и убедись что лог появился.
    """
    await send_log_to_loki(body.message, level=body.level, source="manual")
    return {"status": "sent", "message": body.message, "level": body.level}
