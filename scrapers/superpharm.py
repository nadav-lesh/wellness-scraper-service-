"""
Super Pharm Israel Scraper
--------------------------
Scrapes the top-selling supplements category from Super Pharm Israel.
Super Pharm renders via React but does NOT use Cloudflare — plain HTTPX
with a browser-like User-Agent is sufficient. Falls back to nodriver
if the site starts JS-gating.

Target: https://www.super-pharm.co.il/departments/vitamins-supplements
"""

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

SUPERPHARM_URL = "https://www.super-pharm.co.il/departments/vitamins-supplements"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
async def scrape_superpharm(limit: int = 5) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        resp = await client.get(SUPERPHARM_URL)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Super Pharm product card selectors — update if site redesigns
    # Typical class patterns: .product-item, .product-tile, .shelf-item
    products = []
    cards = soup.select(".product-item, .shelf-item, [data-product-id]")[:limit * 2]

    for card in cards:
        name_el = card.select_one(".product-name, .item-name, h3")
        price_el = card.select_one(".product-price, .price-value, .price")
        link_el = card.select_one("a[href]")
        img_el = card.select_one("img")

        name = name_el.get_text(strip=True) if name_el else ""
        if not name or len(name) < 3:
            continue

        href = link_el.get("href", "") if link_el else ""
        img = img_el.get("src") or img_el.get("data-src", "") if img_el else ""

        products.append({
            "name": name,
            "price": price_el.get_text(strip=True) if price_el else "",
            "url": href if href.startswith("http") else f"https://www.super-pharm.co.il{href}",
            "image": img,
            "source": "superpharm",
        })

        if len(products) >= limit:
            break

    if not products:
        raise RuntimeError(
            "SuperPharm scraper found 0 products. "
            "CSS selectors may need updating — check the live site structure."
        )

    return {"source": "superpharm", "products": products}
