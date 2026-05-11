"""
NexusAPI — портфельный FastAPI-сервис
Автор: [твоё имя]
"""

import hashlib
import platform
import uuid
import random
from datetime import datetime
from typing import Literal

import psutil
import pytz
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ─── Метаданные приложения ─────────────────────────────────────────────────────

app = FastAPI(
    title="NexusAPI",
    description="""
## 🚀 NexusAPI — Developer Utility Backend

Универсальный бэкенд-сервис с набором полезных инструментов для разработчиков.

### Возможности:
- 📊 **Health** — мониторинг состояния сервера в реальном времени
- 🕐 **Datetime** — точное время с поддержкой часовых поясов
- 💬 **Dev Quotes** — вдохновляющие цитаты из мира разработки
- 🔧 **Tools** — хеширование и генерация UUID

### Стек:
`FastAPI` · `Python 3.11` · `Docker` · `GitHub Actions CI/CD`
""",
    version="1.0.0",
    contact={
        "name": "GitHub",
        "url": "https://github.com/your-username/nexus-api",
    },
    license_info={"name": "MIT"},
)

# ─── Цитаты ───────────────────────────────────────────────────────────────────

DEV_QUOTES = [
    {"text": "Любой дурак может написать код, понятный компьютеру. Хороший программист пишет код, понятный людям.", "author": "Martin Fowler"},
    {"text": "Простота — предпосылка надёжности.", "author": "Edsger W. Dijkstra"},
    {"text": "Сначала сделай так, чтобы работало. Потом — чтобы работало правильно. Потом — чтобы работало быстро.", "author": "Kent Beck"},
    {"text": "Преждевременная оптимизация — корень всех зол.", "author": "Donald Knuth"},
    {"text": "Код читают чаще, чем пишут.", "author": "Guido van Rossum"},
    {"text": "Лучший код — это код, который не нужно писать.", "author": "Jeff Atwood"},
    {"text": "Отладка вдвое сложнее написания кода. Поэтому если ты пишешь код настолько умно, насколько можешь, то ты по определению недостаточно умён для его отладки.", "author": "Brian W. Kernighan"},
    {"text": "Работающий код важнее исчерпывающей документации.", "author": "Agile Manifesto"},
    {"text": "Не комментируй плохой код — перепиши его.", "author": "Brian W. Kernighan"},
    {"text": "Программирование — это не о том, что ты знаешь, а о том, что ты можешь выяснить.", "author": "Chris Pine"},
]

# ─── Pydantic-модели ──────────────────────────────────────────────────────────

class TimezoneConvertRequest(BaseModel):
    datetime_str: str = Field(
        ...,
        example="2024-01-15 14:30:00",
        description="Дата и время в формате YYYY-MM-DD HH:MM:SS",
    )
    from_tz: str = Field(..., example="Europe/Moscow", description="Исходный часовой пояс")
    to_tz: str = Field(..., example="America/New_York", description="Целевой часовой пояс")


class HashRequest(BaseModel):
    text: str = Field(..., example="hello world", description="Строка для хеширования")
    algorithm: Literal["sha256", "md5", "sha512"] = Field(
        "sha256", description="Алгоритм хеширования"
    )


# ─── Эндпоинты ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"], summary="Приветствие")
async def root():
    """Возвращает информацию о проекте и список доступных эндпоинтов."""
    return {
        "project": "NexusAPI",
        "version": "1.0.0",
        "description": "Developer Utility Backend — FastAPI + Docker + GitHub Actions CI/CD",
        "docs": "/docs",
        "endpoints": {
            "health":            "GET  /health",
            "datetime":          "GET  /datetime",
            "timezone_convert":  "POST /timezone/convert",
            "dev_quote":         "GET  /devquote",
            "hash":              "POST /tools/hash",
            "uuid":              "GET  /tools/uuid",
        },
        "stack": ["Python 3.11", "FastAPI", "Pydantic v2", "Docker", "GitHub Actions"],
    }


@app.get("/health", tags=["Monitoring"], summary="Состояние сервера")
async def health():
    """
    Возвращает метрики системы в реальном времени:
    - Загрузка CPU
    - Использование RAM
    - Uptime процесса
    - Платформа
    """
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time

    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
        },
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=0.1),
            "cores_logical": psutil.cpu_count(logical=True),
            "cores_physical": psutil.cpu_count(logical=False),
        },
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "usage_percent": psutil.virtual_memory().percent,
        },
        "uptime": f"{hours}h {minutes}m {seconds}s",
    }


@app.get("/datetime", tags=["Datetime"], summary="Текущее время")
async def get_datetime(tz: str = "Europe/Moscow"):
    """
    Возвращает текущее дату и время с учётом часового пояса.

    **Примеры зон:** `Europe/Moscow`, `UTC`, `America/New_York`, `Asia/Tokyo`
    """
    try:
        timezone = pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail=f"Неизвестный часовой пояс: '{tz}'")

    now = datetime.now(timezone)
    return {
        "timezone": tz,
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "utc_offset": now.strftime("%z"),
        "unix_timestamp": int(now.timestamp()),
    }


@app.post("/timezone/convert", tags=["Datetime"], summary="Конвертация часового пояса")
async def convert_timezone(body: TimezoneConvertRequest):
    """
    Конвертирует дату и время из одного часового пояса в другой.

    **Формат входного времени:** `YYYY-MM-DD HH:MM:SS`
    """
    try:
        src_tz = pytz.timezone(body.from_tz)
        dst_tz = pytz.timezone(body.to_tz)
    except pytz.UnknownTimeZoneError as e:
        raise HTTPException(status_code=400, detail=f"Неизвестный часовой пояс: {e}")

    try:
        naive_dt = datetime.strptime(body.datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используй: YYYY-MM-DD HH:MM:SS",
        )

    src_dt = src_tz.localize(naive_dt)
    dst_dt = src_dt.astimezone(dst_tz)

    return {
        "input": {
            "datetime": body.datetime_str,
            "timezone": body.from_tz,
        },
        "output": {
            "datetime": dst_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": body.to_tz,
            "utc_offset": dst_dt.strftime("%z"),
        },
    }


@app.get("/devquote", tags=["Fun"], summary="Цитата разработчика")
async def dev_quote():
    """Возвращает случайную цитату из мира программирования."""
    quote = random.choice(DEV_QUOTES)
    return {
        "quote": quote["text"],
        "author": quote["author"],
        "total_quotes": len(DEV_QUOTES),
    }


@app.post("/tools/hash", tags=["Tools"], summary="Хеширование строки")
async def hash_text(body: HashRequest):
    """
    Хеширует переданную строку выбранным алгоритмом.

    **Поддерживаемые алгоритмы:** `sha256`, `md5`, `sha512`
    """
    h = hashlib.new(body.algorithm)
    h.update(body.text.encode("utf-8"))
    return {
        "input": body.text,
        "algorithm": body.algorithm,
        "hash": h.hexdigest(),
        "length": len(h.hexdigest()),
    }


@app.get("/tools/uuid", tags=["Tools"], summary="Генерация UUID")
async def generate_uuid(count: int = 1):
    """
    Генерирует один или несколько UUID v4.

    - **count** — количество UUID (1–20)
    """
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count должен быть от 1 до 20")

    result = [str(uuid.uuid4()) for _ in range(count)]
    return {
        "count": count,
        "uuids": result if count > 1 else result[0],
    }
