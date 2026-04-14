"""
Scraper Service — Package 01
Exposes three endpoints (one per platform) that return the top-selling
supplement products. Called by the n8n master orchestration workflow.

Authentication: x-api-key header via SCRAPER_SERVICE_API_KEY env var.
"""

import os
import asyncio
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

from scrapers.iherb import scrape_iherb
from scrapers.superpharm import scrape_superpharm
from scrapers.supherb import scrape_supherb

app = FastAPI(title="Wellness Scraper Service", version="1.0.0")
api_key_header = APIKeyHeader(name="x-api-key")


def verify_api_key(api_key: str = Security(api_key_header)):
    expected = os.environ.get("SCRAPER_SERVICE_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="SCRAPER_SERVICE_API_KEY not set in environment")
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@app.get("/health")
async def health():
    key_set = bool(os.environ.get("SCRAPER_SERVICE_API_KEY"))
    print(f"[Scraper] Health — API key set: {key_set}, chromium: {os.path.exists(os.getenv('CHROME_BIN', '/usr/bin/chromium'))}")
    return {"status": "ok", "api_key_set": key_set, "chromium": os.path.exists(os.getenv("CHROME_BIN", "/usr/bin/chromium"))}


@app.get("/scrape/iherb")
async def iherb(
    limit: int = 5,
    _: str = Depends(verify_api_key),
):
    """Return top-selling supplements from iHerb (Israel-relevant category)."""
    return await scrape_iherb(limit=limit)


@app.get("/scrape/superpharm")
async def superpharm(
    limit: int = 5,
    _: str = Depends(verify_api_key),
):
    """Return top-selling supplements from Super Pharm Israel."""
    return await scrape_superpharm(limit=limit)


@app.get("/scrape/supherb")
async def supherb(
    limit: int = 5,
    _: str = Depends(verify_api_key),
):
    """Return top-selling products from Supherb Israel."""
    return await scrape_supherb(limit=limit)


@app.get("/scrape/all")
async def all_sources(
    limit: int = 5,
    _: str = Depends(verify_api_key),
):
    """Run all three scrapers and return combined results."""
    results = await asyncio.gather(
        scrape_iherb(limit=limit),
        scrape_superpharm(limit=limit),
        scrape_supherb(limit=limit),
        return_exceptions=True,
    )

    def safe(label, result):
        if isinstance(result, Exception):
            print(f"[Scraper] {label} raised exception: {result}")
            return {"source": label, "error": str(result), "products": []}
        return result

    return {
        "iherb": safe("iherb", results[0]),
        "superpharm": safe("superpharm", results[1]),
        "supherb": safe("supherb", results[2]),
    }
