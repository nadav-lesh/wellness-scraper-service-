"""
iHerb Scraper
-------------
Scrapes the iHerb Israel bestsellers page using nodriver (headless Chromium)
because iHerb uses Cloudflare protection that blocks simple HTTP requests.

We target: https://il.iherb.com/c/supplements?sort=BestSellers

nodriver bypasses Cloudflare's bot detection by driving a real browser with
a realistic fingerprint — no `webdriver` flags, no CDP patches.
"""

import asyncio
import os
import nodriver as uc
from tenacity import retry, stop_after_attempt, wait_exponential

IHERB_URL = "https://il.iherb.com/c/supplements?sort=BestSellers"
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")  # Fallback only


async def scrape_iherb(limit: int = 5) -> dict:
    try:
        return await _scrape_with_nodriver(limit)
    except Exception as e:
        if SCRAPINGBEE_API_KEY:
            return await _scrape_with_scrapingbee(limit)
        raise RuntimeError(f"iHerb scrape failed: {e}") from e


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=3, max=10))
async def _scrape_with_nodriver(limit: int) -> dict:
    browser = await uc.start(
        browser_executable_path=os.getenv("CHROME_BIN", "/usr/bin/chromium"),
        headless=True,
    )
    try:
        page = await browser.get(IHERB_URL)
        # Wait for product cards to appear
        await page.wait_for("div.product-cell", timeout=20)

        products = []
        cards = await page.query_selector_all("div.product-cell")

        for card in cards[:limit]:
            try:
                name_el = await card.query_selector(".product-title")
                price_el = await card.query_selector(".price")
                link_el = await card.query_selector("a.absolute-link")
                img_el = await card.query_selector("img.product-image")

                name = (await name_el.get_attribute("textContent") or "").strip() if name_el else ""
                price = (await price_el.get_attribute("textContent") or "").strip() if price_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                img = await img_el.get_attribute("src") if img_el else ""

                if name:
                    products.append({
                        "name": name,
                        "price": price,
                        "url": href if href.startswith("http") else f"https://il.iherb.com{href}",
                        "image": img,
                        "source": "iherb",
                    })
            except Exception:
                continue  # Skip malformed cards

        return {"source": "iherb", "products": products[:limit]}

    finally:
        browser.stop()


async def _scrape_with_scrapingbee(limit: int) -> dict:
    """Fallback: use ScrapingBee managed browser when nodriver is blocked."""
    import httpx
    from bs4 import BeautifulSoup

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://app.scrapingbee.com/api/v1/",
            params={
                "api_key": SCRAPINGBEE_API_KEY,
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
        name_el = card.select_one(".product-title")
        price_el = card.select_one(".price")
        link_el = card.select_one("a.absolute-link")
        img_el = card.select_one("img.product-image")

        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            continue

        href = link_el.get("href", "") if link_el else ""
        products.append({
            "name": name,
            "price": price_el.get_text(strip=True) if price_el else "",
            "url": href if href.startswith("http") else f"https://il.iherb.com{href}",
            "image": img_el.get("src", "") if img_el else "",
            "source": "iherb_fallback",
        })

    return {"source": "iherb", "products": products}
