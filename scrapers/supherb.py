"""
Supherb Israel Scraper — WooCommerce store, tries HTTPX first then nodriver.
Target: https://supherb.co.il/shop/?orderby=popularity
"""

import asyncio
import os
import httpx
from bs4 import BeautifulSoup

SUPHERB_URL = "https://supherb.co.il/shop/?orderby=popularity"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
}


async def scrape_supherb(limit: int = 5) -> dict:
    # Try plain HTTPX first (WooCommerce usually serves static HTML)
    try:
        result = await _scrape_httpx(limit)
        if result["products"]:
            return result
    except Exception as e:
        print(f"[Supherb] HTTPX failed: {e}")

    # Fallback to nodriver
    try:
        return await _scrape_nodriver(limit)
    except Exception as e:
        print(f"[Supherb] nodriver failed: {e}")
        return {"source": "supherb", "products": [], "error": str(e)}


async def _scrape_httpx(limit: int) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        resp = await client.get(SUPHERB_URL)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select("li.product, .product-item, .type-product")[:limit * 2]
    products = []

    for card in cards:
        name_el  = card.select_one(".woocommerce-loop-product__title, h2, .product-title, .product-name")
        price_el = card.select_one(".price, .woocommerce-Price-amount")
        link_el  = card.select_one("a[href]")
        img_el   = card.select_one("img")

        name = name_el.get_text(strip=True) if name_el else ""
        if not name or len(name) < 3:
            continue

        href = link_el.get("href", "") if link_el else ""
        img  = ""
        if img_el:
            img = img_el.get("data-large_image") or img_el.get("src") or img_el.get("data-src", "")

        products.append({
            "name":   name,
            "price":  price_el.get_text(strip=True) if price_el else "",
            "url":    href,
            "image":  img,
            "source": "supherb",
        })

        if len(products) >= limit:
            break

    return {"source": "supherb", "products": products}


async def _scrape_nodriver(limit: int) -> dict:
    import nodriver as uc
    browser = None
    try:
        browser = await uc.start(
            browser_executable_path=os.getenv("CHROME_BIN", "/usr/bin/chromium"),
            browser_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-setuid-sandbox"],
            headless=True,
        )
        tab = await browser.get(SUPHERB_URL)

        cards = []
        for _ in range(20):
            cards = await tab.query_selector_all("li.product, .type-product")
            if cards:
                break
            await asyncio.sleep(1)

        products = []
        for card in cards[:limit * 2]:
            try:
                name_el  = await card.query_selector(".woocommerce-loop-product__title, h2")
                price_el = await card.query_selector(".price")
                link_el  = await card.query_selector("a[href]")
                img_el   = await card.query_selector("img")

                name = ((await name_el.get_attribute("textContent")) or "").strip() if name_el else ""
                if not name or len(name) < 3:
                    continue

                products.append({
                    "name":   name,
                    "price":  ((await price_el.get_attribute("textContent")) or "").strip() if price_el else "",
                    "url":    ((await link_el.get_attribute("href")) or "") if link_el else "",
                    "image":  ((await img_el.get_attribute("src")) or "") if img_el else "",
                    "source": "supherb",
                })

                if len(products) >= limit:
                    break
            except Exception:
                continue

        return {"source": "supherb", "products": products}
    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                pass
