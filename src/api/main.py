"""
FastAPI application for Report Designer.

Provides REST API endpoints for managing templates, sections, subsections,
and data sources.

Usage:
    uvicorn src.api.main:app --reload --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..db import initialize_database
from .routes import (
    templates_router,
    sections_router,
    subsections_router,
    data_sources_router,
    export_router,
    generate_router,
    uploads_router,
    chat_router,
    template_versions_router,
)

app = FastAPI(
    title="Report Designer API",
    description="API for managing report templates, sections, and content generation",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS middleware
default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", default_origins).split(",")
    if origin.strip()
]
if not cors_origins:
    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

# Browsers reject wildcard origins when credentials are enabled.
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _bootstrap_database() -> None:
    """Initialize local sqlite schema/data when needed."""
    initialize_database()


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers with /api/v1 prefix
app.include_router(templates_router, prefix="/api/v1")
app.include_router(sections_router, prefix="/api/v1")
app.include_router(subsections_router, prefix="/api/v1")
app.include_router(data_sources_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(generate_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(template_versions_router, prefix="/api/v1")
