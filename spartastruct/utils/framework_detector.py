"""Detect Python frameworks used in a project from its import information."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult

# Map of import root names to canonical framework display names
FRAMEWORK_IMPORT_MAP: dict[str, str] = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "pydantic": "Pydantic",
    "pytest": "Pytest",
    "click": "Click",
    "typer": "Typer",
    "aiohttp": "aiohttp",
    "tornado": "Tornado",
    "sanic": "Sanic",
    "litestar": "Litestar",
    "alembic": "Alembic",
    "tortoise": "Tortoise ORM",
    "peewee": "Peewee",
    "motor": "Motor",
    "pymongo": "PyMongo",
    "redis": "Redis",
    "dramatiq": "Dramatiq",
    "rq": "RQ",
    "httpx": "HTTPX",
    "requests": "Requests",
    "boto3": "Boto3",
    "botocore": "Boto3",
    "anthropic": "Anthropic SDK",
    "openai": "OpenAI SDK",
    # JavaScript / TypeScript
    "express": "Express",
    "next": "Next.js",
    "react": "React",
    "react-dom": "React",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "vite": "Vite",
    "webpack": "Webpack",
    "jest": "Jest",
    "vitest": "Vitest",
    "typeorm": "TypeORM",
    "sequelize": "Sequelize",
    "mongoose": "Mongoose",
    "prisma": "Prisma",
    "graphql": "GraphQL",
    "axios": "Axios",
    "socket.io": "Socket.IO",
    "rxjs": "RxJS",
    # Scoped npm packages
    "@nestjs/common": "NestJS",
    "@nestjs/core": "NestJS",
    "@angular/core": "Angular",
    "@angular/common": "Angular",
    "@vue/core": "Vue",
    "@prisma/client": "Prisma",
    "@apollo/server": "Apollo",
    "apollo-server": "Apollo",
}


def detect_frameworks(result: AnalysisResult) -> list[str]:
    """Detect frameworks used in the project from all import information.

    Scans all third-party and local imports across every analyzed file and
    maps import root names to known framework display names. Handles both
    standard packages (dotted paths) and scoped npm packages (@scope/name).

    Args:
        result: The analysis result containing import data for all files.

    Returns:
        Sorted list of detected framework display names (deduplicated).
    """
    detected: set[str] = set()

    for file_result in result.files_analyzed:
        all_imports = file_result.imports.third_party + file_result.imports.local
        for imp in all_imports:
            # Standard packages: root is first dotted segment
            root = imp.split(".")[0].lower()
            if root in FRAMEWORK_IMPORT_MAP:
                detected.add(FRAMEWORK_IMPORT_MAP[root])
                continue
            # Scoped packages: @scope/name — check exact key match and prefix match
            if imp.startswith("@"):
                for key in FRAMEWORK_IMPORT_MAP:
                    if imp.lower() == key.lower() or imp.lower().startswith(key.lower() + "/"):
                        detected.add(FRAMEWORK_IMPORT_MAP[key])
                        break

    return sorted(detected)
