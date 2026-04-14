"""
Super Pharm Israel Scraper
--------------------------
Super Pharm is a React SPA — plain HTTPX returns empty HTML.
Requires ScrapingBee or similar managed browser service.

Set SCRAPINGBEE_API_KEY in Railway to enable.
"""

import os
import httpx
from bs4 import BeautifulSoup

SUPERPHARM_URL = "https://www.super-pharm.co.il/departments/vitamins-supplements"


async def scrape_superpharm(limit: int = 5) -> dict:
    api_key = os.environ.get("SCRAPINGBEE_API_KEY")
    if not api_key:
        print("[SuperPharm] SCRAPINGBEE_API_KEY not set — skipping SuperPharm scrape")
        return {"source": "superpharm", "products": [], "error": "SCRAPINGBEE_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://app.scrapingbee.com/api/v1/",
                params={
                    "api_key": api_key,
                    "url": SUPERPHARM_URL,
                    "render_js": "true",
                    "wait_for": ".product-item",
                },
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select(".product-item, .shelf-item, [data-product-id]")[:limit * 2]
        products = []

        for card in cards:
            name_el  = card.select_one(".product-name, .item-name, h3")
            price_el = card.select_one(".product-price, .price-value, .price")
            link_el  = card.select_one("a[href]")
            img_el   = card.select_one("img")

            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 3:
                continue

            href = link_el.get("href", "") if link_el else ""
            products.append({
                "name":   name,
                "price":  price_el.get_text(strip=True) if price_el else "",
                "url":    href if href.startswith("http") else f"https://www.super-pharm.co.il{href}",
                "image":  img_el.get("src", "") if img_el else "",
                "source": "superpharm",
            })

            if len(products) >= limit:
                break

        return {"source": "superpharm", "products": products}

    except Exception as e:
        print(f"[SuperPharm] ScrapingBee failed: {e}")
        return {"source": "superpharm", "products": [], "error": str(e)}
