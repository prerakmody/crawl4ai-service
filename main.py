import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

if os.getenv("VERCEL"):
    os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", tempfile.gettempdir())

app = FastAPI(title="Crawl4AI Service")


class CrawlerConfigRequest(BaseModel):
    type: str
    params: Dict[str, Any] = Field(default_factory=dict)


class CrawlRequest(BaseModel):
    urls: List[str]
    crawler_config: CrawlerConfigRequest


def crawl4ai_base_directory() -> str:
    return os.getenv("CRAWL4_AI_BASE_DIRECTORY") or (
        tempfile.gettempdir() if os.getenv("VERCEL") else str(Path.home())
    )


def should_use_http_crawler(params: Dict[str, Any]) -> bool:
    scraping_strategy = params.get("scraping_strategy", {})
    if scraping_strategy.get("type") != "LXMLWebScrapingStrategy":
        return False

    browser_only_options = [
        "adjust_viewport_to_content",
        "capture_console_messages",
        "capture_mhtml",
        "capture_network_requests",
        "js_code",
        "js_only",
        "magic",
        "pdf",
        "process_iframes",
        "scan_full_page",
        "screenshot",
        "simulate_user",
        "wait_for",
        "wait_for_images",
    ]
    return not any(params.get(option) for option in browser_only_options)


def build_run_config(params: Dict[str, Any]):
    from crawl4ai import CrawlerRunConfig, CacheMode

    kwargs: Dict[str, Any] = {"verbose": False}

    if "scraping_strategy" in params:
        strategy = params["scraping_strategy"]
        if strategy["type"] == "LXMLWebScrapingStrategy":
            try:
                from crawl4ai import LXMLWebScrapingStrategy
            except ImportError:
                from crawl4ai.scraping_strategy import LXMLWebScrapingStrategy
            kwargs["scraping_strategy"] = LXMLWebScrapingStrategy(**strategy.get("params", {}))

    if "cache_mode" in params:
        mode_map = {
            "enabled": CacheMode.ENABLED,
            "disabled": CacheMode.DISABLED,
            "read_only": CacheMode.READ_ONLY,
            "write_only": CacheMode.WRITE_ONLY,
            "bypass": CacheMode.BYPASS,
        }
        kwargs["cache_mode"] = mode_map.get(params["cache_mode"].lower(), CacheMode.ENABLED)

    for flag in ["remove_overlay_elements", "exclude_social_media_links", "stream"]:
        if flag in params:
            kwargs[flag] = params[flag]

    if "exclude_social_media_domains" in params:
        kwargs["exclude_social_media_domains"] = params["exclude_social_media_domains"]

    return CrawlerRunConfig(**kwargs)


def build_crawler(params: Dict[str, Any]):
    from crawl4ai import AsyncWebCrawler, BrowserConfig

    crawler_kwargs: Dict[str, Any] = {
        "base_directory": crawl4ai_base_directory(),
        "config": BrowserConfig(verbose=False),
    }

    if should_use_http_crawler(params):
        from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy

        crawler_kwargs["crawler_strategy"] = AsyncHTTPCrawlerStrategy()

    return AsyncWebCrawler(**crawler_kwargs)


@app.post("/crawl")
async def crawl(request: CrawlRequest):
    if request.crawler_config.type != "CrawlerRunConfig":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported config type: {request.crawler_config.type}",
        )

    try:
        params = request.crawler_config.params
        run_config = build_run_config(params)

        results = []
        async with build_crawler(params) as crawler:
            for url in request.urls:
                result = await crawler.arun(url, config=run_config)
                results.append({
                    "url": url,
                    "success": result.success,
                    "status_code": getattr(result, "status_code", None),
                    "html": result.html,
                    "cleaned_html": result.cleaned_html,
                    "markdown": result.markdown.raw_markdown if result.markdown else None,
                    "links": result.links,
                    "media": result.media,
                    "error_message": result.error_message if not result.success else None,
                })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"results": results}


@app.get("/")
async def root():
    pass


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
