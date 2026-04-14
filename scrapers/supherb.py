"""
Supherb Israel Scraper
----------------------
Supherb is WooCommerce — serves static HTML, plain HTTPX works.
Target: https://supherb.co.il/shop/?orderby=popularity
"""

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
    try:
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

        print(f"[Supherb] Found {len(products)} products")
        return {"source": "supherb", "products": products}

    except Exception as e:
        print(f"[Supherb] Scrape failed: {e}")
        return {"source": "supherb", "products": [], "error": str(e)}
