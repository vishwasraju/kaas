import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from logging_config import setup_logging
from routes.home import router as home_router
from routes.upload import router as upload_router

# Initialize logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="PDF to OKF",
    description="Lossless PDF to Open Knowledge Format converter",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(home_router)
app.include_router(upload_router)


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}