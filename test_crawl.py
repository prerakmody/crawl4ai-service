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

resp = requests.post("http://localhost:8000/crawl", json=payload, timeout=90)
data = resp.json()

for r in data.get("results", []):
    print("URL:", r["url"])
    print("Success:", r["success"])
    print("Status:", r.get("status_code"))
    if r.get("error_message"):
        print("Error:", r["error_message"])
    md = r.get("markdown") or ""
    print("Markdown (first 800 chars):\n", md[:800])
