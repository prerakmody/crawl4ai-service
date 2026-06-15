from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Crawl4AI Service")


class CrawlerConfigRequest(BaseModel):
    type: str
    params: Dict[str, Any] = {}


class CrawlRequest(BaseModel):
    urls: List[str]
    crawler_config: CrawlerConfigRequest


def build_run_config(params: Dict[str, Any]):
    from crawl4ai import CrawlerRunConfig, CacheMode

    kwargs: Dict[str, Any] = {}

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


@app.post("/crawl")
async def crawl(request: CrawlRequest):
    if request.crawler_config.type != "CrawlerRunConfig":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported config type: {request.crawler_config.type}",
        )

    run_config = build_run_config(request.crawler_config.params)

    from crawl4ai import AsyncWebCrawler

    results = []
    async with AsyncWebCrawler() as crawler:
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

    return {"results": results}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
