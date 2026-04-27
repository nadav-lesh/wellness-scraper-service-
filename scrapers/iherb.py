"""
iHerb Scraper
-------------
Uses the Apify vaunted/iherb-scraper actor to bypass Cloudflare protection.
Returns top-selling supplements from iHerb Israel bestsellers page.

Set APIFY_API_KEY in Railway to enable.
"""

import os
import httpx

IHERB_BESTSELLERS_URL = "https://il.iherb.com/c/supplements?sort=BestSellers"
APIFY_ACTOR = "vaunted~iherb-scraper"
APIFY_RUN_URL = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"


async def scrape_iherb(limit: int = 5) -> dict:
    api_key = os.environ.get("APIFY_API_KEY")
    if not api_key:
        print("[iHerb] APIFY_API_KEY not set — skipping iHerb scrape")
        return {"source": "iherb", "products": [], "error": "APIFY_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                APIFY_RUN_URL,
                params={"token": api_key, "memory": 1024},
                json={
                    "startUrls": [{"url": IHERB_BESTSELLERS_URL}],
                    "maxItems": limit * 3,  # actor returns ~3 entries per product, we filter below
                },
            )
            resp.raise_for_status()

        raw = resp.json()

        # Actor returns duplicate entries per product (real data + empty placeholders)
        # Keep only entries with a non-empty title and a real product URL
        seen_ids = set()
        products = []
        for item in raw:
            if not item.get("title") or not item.get("url") or item["url"] == "https://www.iherb.com":
                continue
            pid = item.get("productId")
            if pid in seen_ids:
                continue
            seen_ids.add(pid)

            price = item.get("price", 0)
            products.append({
                "name":         item["title"],
                "price":        f"${price:.2f}" if price else "",
                "url":          item["url"],
                "image":        item.get("imageUrl", ""),
                "source":       "iherb",
                "review_count": item.get("reviewCount", 0),
                "stock_status": item.get("stockStatus", ""),
            })

            if len(products) >= limit:
                break

        print(f"[iHerb] Found {len(products)} products")
        return {"source": "iherb", "products": products}

    except Exception as e:
        print(f"[iHerb] Apify scrape failed: {e}")
        return {"source": "iherb", "products": [], "error": str(e)}
