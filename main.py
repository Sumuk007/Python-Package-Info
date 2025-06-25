from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

package_cache = {}
search_history = []
MAX_HISTORY = 5


templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "history": search_history
    })




@app.post("/search", response_class=HTMLResponse)
async def search_package(request: Request, package_name: str = Form(...)):
    # 1. Check cache first
    if package_name in package_cache:
        info, versions, last_upload_time = package_cache[package_name]
        print(f"🔁 Cache hit for {package_name}")
    else:
        # 2. If not in cache, fetch from PyPI
        url = f"https://pypi.org/pypi/{package_name}/json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        if response.status_code != 200:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": "Package not found",
                "history": search_history
            })

        data = response.json()
        info_data = data["info"]
        releases = data.get("releases", {})

        versions = sorted(releases.keys(), reverse=True)
        latest_version = info_data.get("version")
        latest_release_info = releases.get(latest_version)
        last_upload_time = None
        if latest_release_info:
            last_upload_time = latest_release_info[0].get("upload_time")

        # 3. Prepare info dict
        info = {
            "name": info_data.get("name"),
            "version": latest_version,
            "summary": info_data.get("summary"),
            "author": info_data.get("author"),
            "url": info_data.get("project_url") or info_data.get("home_page"),
            "requires": info_data.get("requires_dist"),
            "last_updated": last_upload_time,
            "versions": versions
        }

        # 4. Save to cache
        package_cache[package_name] = (info, versions, last_upload_time)
        print(f"✅ Cached {package_name}")

    # 5. Update search history
    if package_name not in search_history:
        search_history.insert(0, package_name)
        if len(search_history) > MAX_HISTORY:
            search_history.pop()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "info": info,
        "history": search_history
    })


