from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
async def search_package(request: Request, package_name: str = Form(...)):
    url = f"https://pypi.org/pypi/{package_name}/json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": f"Package '{package_name}' not found."
            })
        data = response.json()
        info = data["info"]

        return templates.TemplateResponse("index.html", {
            "request": request,
            "info": {
                "name": info.get("name"),
                "version": info.get("version"),
                "summary": info.get("summary"),
                "author": info.get("author"),
                "license": info.get("license"),
                "home_page": info.get("home_page"),
                "python": info.get("requires_python"),
            }
        })