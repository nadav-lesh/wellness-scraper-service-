"""
Supherb Israel Scraper
----------------------
Scrapes the bestsellers / top-products page from Supherb (Israeli supplement brand).
Supherb's site is largely static-rendered — plain HTTPX should work.

Target: https://supherb.co.il/shop/?orderby=popularity
"""

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

SUPHERB_URL = "https://supherb.co.il/shop/?orderby=popularity"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
async def scrape_supherb(limit: int = 5) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        resp = await client.get(SUPHERB_URL)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # WooCommerce-based store — standard product card selectors
    products = []
    cards = soup.select("li.product, .product-item")[:limit * 2]

    for card in cards:
        name_el = card.select_one(".woocommerce-loop-product__title, h2, .product-title")
        price_el = card.select_one(".price, .woocommerce-Price-amount")
        link_el = card.select_one("a[href]")
        img_el = card.select_one("img")

        name = name_el.get_text(strip=True) if name_el else ""
        if not name or len(name) < 3:
            continue

        href = link_el.get("href", "") if link_el else ""
        img = img_el.get("src") or img_el.get("data-src", "") if img_el else ""

        # Prefer the full-size image over the thumbnail
        if img_el and img_el.get("data-large_image"):
            img = img_el["data-large_image"]

        products.append({
            "name": name,
            "price": price_el.get_text(strip=True) if price_el else "",
            "url": href,
            "image": img,
            "source": "supherb",
        })

        if len(products) >= limit:
            break

    if not products:
        raise RuntimeError(
            "Supherb scraper found 0 products. "
            "CSS selectors may need updating — check the live site structure."
        )

    return {"source": "supherb", "products": products}
