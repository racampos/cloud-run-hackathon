"""Parser-Linter Service - FastAPI Application."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from routers import topology, cli

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="NetGenius Parser-Linter Service",
    description="Validation service for network topology and CLI commands",
    version="0.1.0-stub",
)

# Add CORS middleware (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to orchestrator service
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(topology.router, tags=["Topology"])
app.include_router(cli.router, tags=["CLI"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "NetGenius Parser-Linter",
        "version": "0.1.0-stub",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "parser-linter"}


@app.on_event("startup")
async def startup_event():
    """Log service startup."""
    logger.info(
        "parser_linter_starting",
        version="0.1.0-stub",
        port=os.getenv("PORT", "8080"),
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Log service shutdown."""
    logger.info("parser_linter_stopping")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
