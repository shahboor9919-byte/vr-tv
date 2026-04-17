import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger

from engine.aggregator import aggregate_all_sources
from engine.cleaner import clean_channels
from engine.cache import channel_cache, stream_cache

CHANNEL_CACHE_KEY = "channels_v1"
STREAM_TEST_TIMEOUT = 3.0

app_state = {
    "scan_in_progress": False,
    "last_scan_time": None,
    "total_channels": 0,
    "alive_channels": 0,
    "startup_done": False,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 IPTV MindApp starting up...")
    asyncio.create_task(run_full_scan())
    yield
    logger.info("👋 IPTV MindApp shutting down")

app = FastAPI(title="IPTV MindApp", version="3.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

class RefreshRequest(BaseModel):
    extra_m3u_urls: Optional[list[str]] = None
    xtream_host: Optional[str] = None
    xtream_username: Optional[str] = None
    xtream_password: Optional[str] = None

async def run_full_scan(extra_m3u_urls=None, xtream_config=None):
    if app_state["scan_in_progress"]:
        return
    app_state["scan_in_progress"] = True
    start_time = time.time()
    try:
        raw = await aggregate_all_sources(extra_m3u_urls, xtream_config)
        clean_list = clean_channels(raw)
        app_state["total_channels"] = len(clean_list)
        await channel_cache.set(CHANNEL_CACHE_KEY, clean_list)
        app_state["last_scan_time"] = time.time()
        app_state["startup_done"] = True
        logger.info(f"✅ Scan complete: {len(clean_list)} channels in {time.time()-start_time:.1f}s")
    except Exception as e:
        logger.exception(f"Scan failed: {e}")
    finally:
        app_state["scan_in_progress"] = False

async def get_cached_channels():
    return await channel_cache.get(CHANNEL_CACHE_KEY)

@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        with open("static/index.html") as f:
            return f.read()
    except:
        return "<h1>IPTV MindApp</h1><p>Static files missing</p>"

@app.get("/channels")
async def list_channels(category: Optional[str] = None, search: Optional[str] = None,
                        alive_only: bool = Query(False), limit: int = 200, offset: int = 0):
    channels = await get_cached_channels()
    if not channels:
        return JSONResponse({"status": "scanning", "channels": [], "total": 0})
    filtered = [ch for ch in channels if not alive_only or ch.get("alive")]
    if category and category != "All":
        filtered = [ch for ch in filtered if ch.get("category") == category]
    if search:
        filtered = [ch for ch in filtered if search.lower() in ch["name"].lower()]
    filtered.sort(key=lambda x: x["name"])
    total = len(filtered)
    paginated = filtered[offset:offset+limit]
    return JSONResponse({"status": "ok", "total": total, "offset": offset, "limit": limit, "channels": paginated})

@app.get("/watch/{channel_id}")
async def watch_channel(channel_id: int):
    channels = await get_cached_channels()
    ch = next((c for c in channels if c["id"] == channel_id), None)
    if not ch:
        raise HTTPException(404, "Channel not found")
    streams = ch.get("streams", [])
    if not streams:
        raise HTTPException(503, "No streams")
    # اختبار أول تدفق فقط (سيتم إعادة الاختبار كل 10 دقائق)
    cache_key = f"stream_test:{channel_id}"
    cached = await stream_cache.get(cache_key)
    if cached:
        return JSONResponse({"stream_url": cached["working_url"], "backups": cached.get("backups", [])})
    # اختبار سريع لأول رابط
    import aiohttp
    working = None
    for url in streams[:3]:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, timeout=STREAM_TEST_TIMEOUT) as resp:
                    if resp.status == 200:
                        working = url
                        break
        except:
            continue
    if not working:
        raise HTTPException(503, "No working stream")
    await stream_cache.set(cache_key, {"working_url": working, "backups": streams[1:4]}, ttl=600)
    return JSONResponse({"stream_url": working, "backup_streams": streams[1:4]})

@app.post("/refresh")
async def refresh(request: RefreshRequest, background_tasks: BackgroundTasks):
    if app_state["scan_in_progress"]:
        return JSONResponse({"status": "already_scanning"})
    xtream = None
    if request.xtream_host and request.xtream_username:
        xtream = {"host": request.xtream_host, "username": request.xtream_username, "password": request.xtream_password or ""}
    background_tasks.add_task(run_full_scan, request.extra_m3u_urls or [], xtream)
    return JSONResponse({"status": "started"})

@app.get("/health")
async def health():
    cached = await channel_cache.get(CHANNEL_CACHE_KEY)
    return JSONResponse({
        "scan_in_progress": app_state["scan_in_progress"],
        "total_channels": app_state["total_channels"],
        "cached_channels": len(cached) if cached else 0
    })

@app.get("/categories")
async def categories():
    channels = await get_cached_channels()
    if not channels:
        return JSONResponse({"categories": []})
    counts = {}
    for ch in channels:
        cat = ch.get("category", "General")
        counts[cat] = counts.get(cat, 0) + 1
    cats = [{"name": "All", "count": len(channels)}] + [{"name": k, "count": v} for k, v in sorted(counts.items())]
    return JSONResponse({"categories": cats})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
