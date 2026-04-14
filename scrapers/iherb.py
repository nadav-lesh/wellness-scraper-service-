"""
iHerb Scraper — uses nodriver (headless Chromium) to bypass Cloudflare.
Target: https://il.iherb.com/c/supplements?sort=BestSellers
"""

import asyncio
import os
import nodriver as uc

IHERB_URL = "https://il.iherb.com/c/supplements?sort=BestSellers"


async def scrape_iherb(limit: int = 5) -> dict:
    browser = None
    try:
        browser = await uc.start(
            browser_executable_path=os.getenv("CHROME_BIN", "/usr/bin/chromium"),
            browser_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-setuid-sandbox"],
            headless=True,
        )
        tab = await browser.get(IHERB_URL)

        # Wait up to 20s for product cards
        for _ in range(20):
            cards = await tab.query_selector_all("div.product-cell")
            if cards:
                break
            await asyncio.sleep(1)

        products = []
        for card in cards[:limit]:
            try:
                name  = await _text(card, ".product-title")
                price = await _text(card, ".price")
                link  = await _attr(card, "a.absolute-link", "href")
                img   = await _attr(card, "img.product-image", "src")

                if not name:
                    continue

                products.append({
                    "name":   name,
                    "price":  price,
                    "url":    link if link.startswith("http") else f"https://il.iherb.com{link}",
                    "image":  img,
                    "source": "iherb",
                })
            except Exception:
                continue

        return {"source": "iherb", "products": products[:limit]}

    except Exception as e:
        print(f"[iHerb] Scrape failed: {e}")
        return {"source": "iherb", "products": [], "error": str(e)}
    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                pass


async def _text(parent, selector: str) -> str:
    try:
        el = await parent.query_selector(selector)
        if not el:
            return ""
        val = await el.get_attribute("textContent")
        return (val or "").strip()
    except Exception:
        return ""


async def _attr(parent, selector: str, attr: str) -> str:
    try:
        el = await parent.query_selector(selector)
        if not el:
            return ""
        val = await el.get_attribute(attr)
        return (val or "").strip()
    except Exception:
        return ""
