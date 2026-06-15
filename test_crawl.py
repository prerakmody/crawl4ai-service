import requests

payload = {
    "urls": ["https://baarique.in/products/kalamkari-katori-small-set-of-2"],
    "crawler_config": {
        "type": "CrawlerRunConfig",
        "params": {
            "stream": False,
            "scraping_strategy": {"type": "LXMLWebScrapingStrategy", "params": {}},
            "table_extraction": {"type": "DefaultTableExtraction", "params": {}},
            "remove_overlay_elements": True,
            "exclude_social_media_links": True,
            "exclude_social_media_domains": [
                "facebook.com", "twitter.com", "x.com", "linkedin.com",
                "instagram.com", "pinterest.com", "tiktok.com",
                "snapchat.com", "reddit.com", "youtube.com",
            ],
            "cache_mode": "enabled",
        },
    },
}

targets = {
    "localhost": "http://localhost:8000/crawl",
    "vercel": "https://crawl4ai-service.vercel.app/crawl",
}

for name, crawl4ai_url in targets.items():
    print(f"\n=== {name}: {crawl4ai_url} ===")
    try:
        resp = requests.post(crawl4ai_url, json=payload, timeout=90)
    except requests.RequestException as exc:
        print("Request failed:", exc)
        continue

    print("HTTP:", resp.status_code)
    print("Content-Type:", resp.headers.get("content-type"))

    try:
        data = resp.json()
    except ValueError:
        print("Non-JSON response (first 800 chars):\n", resp.text[:800])
        continue

    for r in data.get("results", []):
        print("URL:", r["url"])
        print("Success:", r["success"])
        print("Status:", r.get("status_code"))
        if r.get("error_message"):
            print("Error:", r["error_message"])
        md = r.get("markdown") or ""
        print("Markdown length:", len(md))
        print("Markdown (first 800 chars):\n", md[:800])
