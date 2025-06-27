from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.status import HTTP_302_FOUND
import httpx
import asyncio

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User
from auth_utils import hash_password, verify_password

print("📦 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables should now exist.")

app = FastAPI()

package_cache = {}
search_history = []
MAX_HISTORY = 5


templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "history": search_history
    })

@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
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



@app.get("/compare", response_class=HTMLResponse)
async def compare_form(request: Request):
    return templates.TemplateResponse("compare.html", {"request": request})


@app.post("/compare", response_class=HTMLResponse)
async def compare_packages(request: Request, package1: str = Form(...), package2: str = Form(...)):

    async def get_package_info_async(package_name):
        if package_name in package_cache:
            return package_cache[package_name][0]

        url = f"https://pypi.org/pypi/{package_name}/json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        if response.status_code != 200:
            return None

        data = response.json()
        info_data = data["info"]
        releases = data.get("releases", {})
        versions = sorted(releases.keys(), reverse=True)
        latest_version = info_data.get("version")
        latest_release_info = releases.get(latest_version)
        last_upload_time = None
        if latest_release_info:
            last_upload_time = latest_release_info[0].get("upload_time")

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

        package_cache[package_name] = (info, versions, last_upload_time)
        return info

    # ⏱️ Run both in parallel
    info1, info2 = await asyncio.gather(
        get_package_info_async(package1),
        get_package_info_async(package2)
    )

    if not info1 or not info2:
        return templates.TemplateResponse("compare.html", {
            "request": request,
            "error": "One or both packages were not found.",
        })

    return templates.TemplateResponse("compare.html", {
        "request": request,
        "info1": info1,
        "info2": info2,
    })



@app.get("/signup", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Username already exists"
        })
    hashed = hash_password(password)
    user = User(username=username, email=email, hashed_password=hashed)
    db.add(user)
    db.commit()
    return RedirectResponse("/login", status_code=HTTP_302_FOUND)


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })
    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": user.username
    })