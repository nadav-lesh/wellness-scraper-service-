"""
Super Pharm Israel Scraper
--------------------------
Super Pharm is a React SPA — plain HTTPX returns empty HTML.
Using nodriver (headless Chromium) to render the page fully.

Target: https://www.super-pharm.co.il/departments/vitamins-supplements
"""

import os
import nodriver as uc
from tenacity import retry, stop_after_attempt, wait_exponential

SUPERPHARM_URL = "https://www.super-pharm.co.il/departments/vitamins-supplements"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=3, max=10))
async def scrape_superpharm(limit: int = 5) -> dict:
    browser = await uc.start(
        browser_executable_path=os.getenv("CHROME_BIN", "/usr/bin/chromium"),
        browser_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        headless=True,
    )
    try:
        page = await browser.get(SUPERPHARM_URL)
        await page.wait_for(".product-item, .shelf-item, [data-product-id], .product-card", timeout=20)

        products = []
        cards = await page.query_selector_all(".product-item, .shelf-item, [data-product-id], .product-card")

        for card in cards[:limit * 2]:
            try:
                name_el  = await card.query_selector(".product-name, .item-name, h3, .product-title")
                price_el = await card.query_selector(".product-price, .price-value, .price")
                link_el  = await card.query_selector("a[href]")
                img_el   = await card.query_selector("img")

                name = (await name_el.get_attribute("textContent") or "").strip() if name_el else ""
                if not name or len(name) < 3:
                    continue

                price = (await price_el.get_attribute("textContent") or "").strip() if price_el else ""
                href  = await link_el.get_attribute("href") if link_el else ""
                img   = await img_el.get_attribute("src") if img_el else ""

                products.append({
                    "name":   name,
                    "price":  price,
                    "url":    href if href.startswith("http") else f"https://www.super-pharm.co.il{href}",
                    "image":  img,
                    "source": "superpharm",
                })

                if len(products) >= limit:
                    break
            except Exception:
                continue

        if not products:
            raise RuntimeError("SuperPharm scraper found 0 products — selectors may need updating")

        return {"source": "superpharm", "products": products}

    finally:
        browser.stop()
