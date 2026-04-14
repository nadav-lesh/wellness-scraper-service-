"""
iHerb Scraper
-------------
iHerb uses Cloudflare protection — requires a managed browser service
(ScrapingBee, Bright Data, etc.) to bypass. Returns empty until configured.

Set SCRAPINGBEE_API_KEY in Railway to enable.
"""

import os
import httpx
from bs4 import BeautifulSoup

IHERB_URL = "https://il.iherb.com/c/supplements?sort=BestSellers"


async def scrape_iherb(limit: int = 5) -> dict:
    api_key = os.environ.get("SCRAPINGBEE_API_KEY")
    if not api_key:
        print("[iHerb] SCRAPINGBEE_API_KEY not set — skipping iHerb scrape")
        return {"source": "iherb", "products": [], "error": "SCRAPINGBEE_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://app.scrapingbee.com/api/v1/",
                params={
                    "api_key": api_key,
                    "url": IHERB_URL,
                    "render_js": "true",
                    "wait_for": "div.product-cell",
                },
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("div.product-cell")[:limit]
        products = []

        for card in cards:
            name_el  = card.select_one(".product-title")
            price_el = card.select_one(".price")
            link_el  = card.select_one("a.absolute-link")
            img_el   = card.select_one("img.product-image")

            name = name_el.get_text(strip=True) if name_el else ""
            if not name:
                continue

            href = link_el.get("href", "") if link_el else ""
            products.append({
                "name":   name,
                "price":  price_el.get_text(strip=True) if price_el else "",
                "url":    href if href.startswith("http") else f"https://il.iherb.com{href}",
                "image":  img_el.get("src", "") if img_el else "",
                "source": "iherb",
            })

        return {"source": "iherb", "products": products}

    except Exception as e:
        print(f"[iHerb] ScrapingBee failed: {e}")
        return {"source": "iherb", "products": [], "error": str(e)}
