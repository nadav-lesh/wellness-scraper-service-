"""
Super Pharm Israel Scraper — nodriver (React SPA, needs JS rendering).
Target: https://www.super-pharm.co.il/departments/vitamins-supplements
"""

import asyncio
import os
import nodriver as uc

SUPERPHARM_URL = "https://www.super-pharm.co.il/departments/vitamins-supplements"


async def scrape_superpharm(limit: int = 5) -> dict:
    browser = None
    try:
        browser = await uc.start(
            browser_executable_path=os.getenv("CHROME_BIN", "/usr/bin/chromium"),
            browser_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-setuid-sandbox"],
            headless=True,
        )
        tab = await browser.get(SUPERPHARM_URL)

        # Wait up to 20s for product cards to render
        selectors = [".product-item", ".shelf-item", "[data-product-id]", ".product-card", ".product-tile"]
        cards = []
        for _ in range(20):
            for sel in selectors:
                cards = await tab.query_selector_all(sel)
                if cards:
                    break
            if cards:
                break
            await asyncio.sleep(1)

        products = []
        for card in cards[:limit * 2]:
            try:
                name  = await _text(card, ".product-name, .item-name, h3, .product-title")
                price = await _text(card, ".product-price, .price-value, .price")
                link  = await _attr(card, "a[href]", "href")
                img   = await _attr(card, "img", "src")

                if not name or len(name) < 3:
                    continue

                products.append({
                    "name":   name,
                    "price":  price,
                    "url":    link if link.startswith("http") else f"https://www.super-pharm.co.il{link}",
                    "image":  img,
                    "source": "superpharm",
                })

                if len(products) >= limit:
                    break
            except Exception:
                continue

        return {"source": "superpharm", "products": products}

    except Exception as e:
        print(f"[SuperPharm] Scrape failed: {e}")
        return {"source": "superpharm", "products": [], "error": str(e)}
    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                pass


async def _text(parent, selector: str) -> str:
    """Try multiple comma-separated selectors, return first match."""
    for sel in selector.split(","):
        try:
            el = await parent.query_selector(sel.strip())
            if el:
                val = await el.get_attribute("textContent")
                text = (val or "").strip()
                if text:
                    return text
        except Exception:
            continue
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
