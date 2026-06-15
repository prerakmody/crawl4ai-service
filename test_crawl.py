import requests
import time
from logging import getLogger

logger = getLogger()


def isUrlAlive(url: str, timeoutSeconds: int = 5) -> tuple[bool, float]:
    """Check whether a URL is reachable. Returns (alive, elapsed_seconds)."""
    normalizedUrl = url if url.endswith('/') else f"{url}/"
    start = time.time()
    try:
        # Use GET instead of HEAD — many API services don't support HEAD
        response = requests.get(normalizedUrl, timeout=timeoutSeconds, allow_redirects=True)
        # 4xx/5xx means the service is running but the route doesn't exist or is forbidden
        # That still counts as "alive" — the service is responding
        elapsed = time.time() - start
        isAlive = response.status_code < 500
        if isAlive:
            logger.info("URL is alive: %s (status: %s, %.2fs)", normalizedUrl, response.status_code, elapsed)
        else:
            logger.warning("URL returned error: %s (status: %s, %.2fs)", normalizedUrl, response.status_code, elapsed)
        return isAlive, elapsed
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        logger.warning("URL timeout: %s (timeout: %ss, %.2fs)", normalizedUrl, timeoutSeconds, elapsed)
        return False, elapsed
    except requests.exceptions.ConnectionError:
        elapsed = time.time() - start
        logger.warning("URL connection failed: %s (%.2fs)", normalizedUrl, elapsed)
        return False, elapsed
    except requests.exceptions.RequestException as error:
        elapsed = time.time() - start
        logger.warning("URL request failed: %s (%s, %.2fs)", normalizedUrl, error, elapsed)
        return False, elapsed
    except Exception as error:
        elapsed = time.time() - start
        logger.error("Unexpected URL check error: %s (%s, %.2fs)", normalizedUrl, error, elapsed)
        return False, elapsed


# Define services once — base URL, health timeout, and routes
ROUTES = ["/", "/health", "/crawl"]

services = {
    "localhost": {"base": "http://localhost:8000", "health_timeout": 5},
    "vercel":    {"base": "https://crawl4ai-service.vercel.app", "health_timeout": 30},
}

def service_url(name: str, route: str) -> str:
    return f"{services[name]['base']}{route}"

# Step 0 - Check if services are alive via root and /health endpoints
print("=== URL LIVENESS CHECK ===")
for name, svc in services.items():
    for route in ROUTES[:2]:  # "/" and "/health"
        alive, elapsed = isUrlAlive(service_url(name, route), timeoutSeconds=svc['health_timeout'])
        print(f"  {service_url(name, route)}: {'ALIVE' if alive else 'DOWN'} ({elapsed:.2f}s)")

print("\n=== CRAWL TEST ===\n")

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

# Derive crawl URLs from the same service definitions
targets = {name: service_url(name, ROUTES[2]) for name in services}

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
