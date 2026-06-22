import logging
import threading

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import ADMIN_PANEL_PORT, ADMIN_USERNAME, ADMIN_PASSWORD
from .database import get_db, init_db, seed_data, get_bot_setting, set_bot_setting
from .api import router as api_router

logger = logging.getLogger(__name__)

app = FastAPI(title="VK Bot Admin Panel")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
templates = Jinja2Templates(directory="app/templates")

app.mount("/grabovo", StaticFiles(directory="miniapp", html=True), name="grabovo")

_bot_thread = None
_bot_stop_event = None


async def verify_auth(request: Request):
    username = request.cookies.get("username")
    password = request.cookies.get("password")
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


@app.on_event("startup")
def startup():
    logging.basicConfig(level=logging.INFO)
    init_db()
    seed_data()
    logger.info("Admin panel database initialized")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        faq_count = db.execute("SELECT COUNT(*) FROM faq").fetchone()[0]
        master_count = db.execute("SELECT COUNT(*) FROM masters").fetchone()[0]
        shop_count = db.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
        new_ads = db.execute("SELECT COUNT(*) FROM ads_requests WHERE status='new'").fetchone()[0]
        ratings_count = db.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "faq_count": faq_count, "master_count": master_count,
        "shop_count": shop_count, "ads_count": new_ads,
        "ratings_count": ratings_count,
        "bot_running": bot_status(),
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(key="username", value=username)
        resp.set_cookie(key="password", value=password)
        return resp
    return templates.TemplateResponse("login.html", {
        "request": request, "error": "\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 \u043b\u043e\u0433\u0438\u043d \u0438\u043b\u0438 \u043f\u0430\u0440\u043e\u043b\u044c"
    })


@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("username")
    resp.delete_cookie("password")
    return resp


def get_cats(table):
    with get_db() as db:
        rows = db.execute(f"SELECT id, name FROM {table} ORDER BY name").fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]


# ─── FAQ ──────────────────────────────────────────────

@app.get("/faq", response_class=HTMLResponse)
async def faq_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        rows = db.execute(
            "SELECT f.id, f.question, f.answer, f.keywords, c.name as category "
            "FROM faq f JOIN categories c ON f.category_id = c.id ORDER BY f.id"
        ).fetchall()
    faqs = [{"id": r[0], "question": r[1], "answer": r[2], "keywords": r[3], "category": r[4]} for r in rows]
    return templates.TemplateResponse("faq.html", {
        "request": request, "faqs": faqs, "categories": get_cats("categories")
    })


@app.post("/faq/add")
async def faq_add(request: Request, category_id: int = Form(...), question: str = Form(...), answer: str = Form(...), keywords: str = Form("")):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("INSERT INTO faq (category_id, question, answer, keywords) VALUES (?, ?, ?, ?)",
                   (category_id, question, answer, keywords))
    return RedirectResponse(url="/faq", status_code=303)


@app.post("/faq/edit/{faq_id}")
async def faq_edit(request: Request, faq_id: int, category_id: int = Form(...), question: str = Form(...), answer: str = Form(...), keywords: str = Form("")):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("UPDATE faq SET category_id=?, question=?, answer=?, keywords=? WHERE id=?",
                   (category_id, question, answer, keywords, faq_id))
    return RedirectResponse(url="/faq", status_code=303)


@app.post("/faq/delete/{faq_id}")
async def faq_delete(request: Request, faq_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("DELETE FROM faq WHERE id=?", (faq_id,))
    return RedirectResponse(url="/faq", status_code=303)


# ─── MASTERS ──────────────────────────────────────────

@app.get("/masters", response_class=HTMLResponse)
async def masters_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        rows = db.execute(
            "SELECT m.id, m.name, m.description, m.contacts, m.photo, m.rating, m.votes_count, m.views_count, m.verified, COALESCE(m.recommended, 0), "
            "COALESCE(mc.name, '') as cat_name "
            "FROM masters m LEFT JOIN master_categories mc ON m.category_id = mc.id ORDER BY m.id"
        ).fetchall()
    items = [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
              "photo": r[4], "rating": r[5], "votes_count": r[6], "views_count": r[7], "verified": bool(r[8]), "recommended": bool(r[9]), "category": r[10]} for r in rows]
    cats = [{"id": None, "name": "\u2014"}]
    for c in get_cats("master_categories"):
        cats.append(c)
    return templates.TemplateResponse("items.html", {
        "request": request, "items": items, "type": "masters", "title": "\u041c\u0430\u0441\u0442\u0435\u0440\u0430",
        "categories": cats, "cat_type": "master_categories"
    })


@app.get("/masters/stats/{master_id}", response_class=HTMLResponse)
async def master_stats(request: Request, master_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_master_by_id, get_master_stats
    with get_db() as db:
        r = db.execute(
            "SELECT m.id, m.name, m.description, m.contacts, m.photo, m.verified, "
            "m.rating, m.votes_count, m.views_count, m.owner_vk_id, "
            "COALESCE(mc.name, '') as cat_name "
            "FROM masters m LEFT JOIN master_categories mc ON m.category_id = mc.id WHERE m.id=?",
            (master_id,)
        ).fetchone()
    if not r:
        return HTMLResponse("Мастер не найден", status_code=404)
    m = {"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
         "photo": r[4], "verified": bool(r[5]), "rating": r[6], "votes_count": r[7],
         "views_count": r[8], "owner_vk_id": r[9], "category": r[10]}
    all_stats = get_master_stats()
    return templates.TemplateResponse("master_stats.html", {
        "request": request, "m": m, "all_stats": all_stats,
    })


@app.post("/masters/add")
async def masters_add(request: Request, name: str = Form(...), description: str = Form(""), contacts: str = Form(""), photo: str = Form(""), category_id: int = Form(None), recommended: int = Form(0)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        cat_val = category_id if category_id and category_id > 0 else None
        db.execute("INSERT INTO masters (name, description, contacts, photo, category_id, recommended) VALUES (?, ?, ?, ?, ?, ?)",
                   (name, description, contacts, photo, cat_val, recommended))
    return RedirectResponse(url="/masters", status_code=303)


@app.post("/masters/edit/{item_id}")
async def masters_edit(request: Request, item_id: int, name: str = Form(...), description: str = Form(""), contacts: str = Form(""), photo: str = Form(""), category_id: int = Form(None), recommended: int = Form(0)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        cat_val = category_id if category_id and category_id > 0 else None
        db.execute("UPDATE masters SET name=?, description=?, contacts=?, photo=?, category_id=?, recommended=? WHERE id=?",
                   (name, description, contacts, photo, cat_val, recommended, item_id))
    return RedirectResponse(url="/masters", status_code=303)


@app.post("/masters/delete/{item_id}")
async def masters_delete(request: Request, item_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("DELETE FROM masters WHERE id=?", (item_id,))
        db.execute("DELETE FROM ratings WHERE target_type='master' AND target_id=?", (item_id,))
    return RedirectResponse(url="/masters", status_code=303)


# ─── SHOPS ────────────────────────────────────────────

@app.get("/shops", response_class=HTMLResponse)
async def shops_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        rows = db.execute(
            "SELECT s.id, s.name, s.description, s.contacts, s.photo, s.rating, s.votes_count, s.verified, COALESCE(s.recommended, 0), "
            "COALESCE(sc.name, '') as cat_name "
            "FROM shops s LEFT JOIN shop_categories sc ON s.category_id = sc.id ORDER BY s.id"
        ).fetchall()
    items = [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
              "photo": r[4], "rating": r[5], "votes_count": r[6], "verified": bool(r[7]), "recommended": bool(r[8]), "category": r[9]} for r in rows]
    cats = [{"id": None, "name": "\u2014"}]
    for c in get_cats("shop_categories"):
        cats.append(c)
    return templates.TemplateResponse("items.html", {
        "request": request, "items": items, "type": "shops", "title": "\u041c\u0430\u0433\u0430\u0437\u0438\u043d\u044b",
        "categories": cats, "cat_type": "shop_categories"
    })


@app.post("/shops/add")
async def shops_add(request: Request, name: str = Form(...), description: str = Form(""), contacts: str = Form(""), photo: str = Form(""), category_id: int = Form(None)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        cat_val = category_id if category_id and category_id > 0 else None
        db.execute("INSERT INTO shops (name, description, contacts, photo, category_id) VALUES (?, ?, ?, ?, ?)",
                   (name, description, contacts, photo, cat_val))
    return RedirectResponse(url="/shops", status_code=303)


@app.post("/shops/edit/{item_id}")
async def shops_edit(request: Request, item_id: int, name: str = Form(...), description: str = Form(""), contacts: str = Form(""), photo: str = Form(""), category_id: int = Form(None)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        cat_val = category_id if category_id and category_id > 0 else None
        db.execute("UPDATE shops SET name=?, description=?, contacts=?, photo=?, category_id=? WHERE id=?",
                   (name, description, contacts, photo, cat_val, item_id))
    return RedirectResponse(url="/shops", status_code=303)


@app.post("/shops/delete/{item_id}")
async def shops_delete(request: Request, item_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("DELETE FROM shops WHERE id=?", (item_id,))
        db.execute("DELETE FROM ratings WHERE target_type='shop' AND target_id=?", (item_id,))
    return RedirectResponse(url="/shops", status_code=303)


# ─── CATEGORIES MANAGEMENT ────────────────────────────

@app.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    cats = {
        "faq": get_cats("categories"),
        "master": get_cats("master_categories"),
        "shop": get_cats("shop_categories"),
        "food": get_cats("food_categories"),
    }
    return templates.TemplateResponse("categories.html", {"request": request, "cats": cats})


@app.post("/categories/add")
async def categories_add(request: Request, table: str = Form(...), name: str = Form(...)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        try:
            db.execute(f"INSERT OR IGNORE INTO {table} (name) VALUES (?)", (name,))
        except Exception:
            pass
    return RedirectResponse(url="/categories", status_code=303)


@app.post("/categories/delete")
async def categories_delete(request: Request, table: str = Form(...), cat_id: int = Form(...)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute(f"DELETE FROM {table} WHERE id=?", (cat_id,))
    return RedirectResponse(url="/categories", status_code=303)


# ─── ADS ──────────────────────────────────────────────

@app.get("/ads", response_class=HTMLResponse)
async def ads_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, user_name, message_type, message_text, status, created_at "
            "FROM ads_requests ORDER BY created_at DESC"
        ).fetchall()
    ads = [{"id": r[0], "user_id": r[1], "user_name": r[2], "message_type": r[3],
             "message_text": r[4], "status": r[5], "created_at": str(r[6])[:16] if r[6] else ""} for r in rows]
    return templates.TemplateResponse("ads.html", {"request": request, "ads": ads})


@app.post("/ads/status/{ad_id}")
async def ads_status(request: Request, ad_id: int, status: str = Form(...)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("UPDATE ads_requests SET status=? WHERE id=?", (status, ad_id))
    return RedirectResponse(url="/ads", status_code=303)


# ─── VERIFICATION ─────────────────────────────────────

@app.get("/verification", response_class=HTMLResponse)
async def verification_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_all_verification_requests
    reqs = get_all_verification_requests()
    return templates.TemplateResponse("verification.html", {"request": request, "reqs": reqs})


@app.post("/verification/approve/{master_id}")
async def verification_approve(request: Request, master_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import approve_verification
    approve_verification(master_id)
    return RedirectResponse(url="/verification", status_code=303)


@app.post("/verification/reject/{master_id}")
async def verification_reject(request: Request, master_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import reject_verification
    reject_verification(master_id)
    return RedirectResponse(url="/verification", status_code=303)


# ─── MASTER VERIFY TOGGLE (direct from master edit) ───

@app.post("/masters/verify/{item_id}")
async def master_verify_toggle(request: Request, item_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("UPDATE masters SET verified = 1 - verified WHERE id = ?", (item_id,))
    return RedirectResponse(url="/masters", status_code=303)


@app.post("/masters/recommend/{item_id}")
async def master_recommend_toggle(request: Request, item_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("UPDATE masters SET recommended = 1 - recommended WHERE id = ?", (item_id,))
    return RedirectResponse(url="/masters", status_code=303)


@app.post("/employers/recommend/{emp_id}")
async def employer_recommend_toggle(request: Request, emp_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("UPDATE employers SET recommended = 1 - recommended WHERE id = ?", (emp_id,))
    return RedirectResponse(url="/employers", status_code=303)


# ─── REVIEWS MODERATION ───────────────────────────────

@app.get("/reviews", response_class=HTMLResponse)
async def reviews_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_all_reviews
    revs = get_all_reviews()
    return templates.TemplateResponse("reviews.html", {"request": request, "revs": revs})


@app.post("/reviews/approve/{review_id}")
async def reviews_approve(request: Request, review_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    try:
        from .services import approve_review
        approve_review(review_id)
    except Exception as e:
        logger.error(f"Review approve error: {e}")
    return RedirectResponse(url="/reviews", status_code=303)


@app.post("/reviews/reject/{review_id}")
async def reviews_reject(request: Request, review_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    try:
        from .services import reject_review
        reject_review(review_id)
    except Exception as e:
        logger.error(f"Review reject error: {e}")
    return RedirectResponse(url="/reviews", status_code=303)


# ─── MASTER REGISTRATIONS ─────────────────────────────

@app.get("/registrations", response_class=HTMLResponse)
async def registrations_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_pending_registrations
    regs = get_pending_registrations()
    return templates.TemplateResponse("registrations.html", {"request": request, "regs": regs})


@app.post("/registrations/approve/{reg_id}")
async def registrations_approve(request: Request, reg_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import approve_registration
    approve_registration(reg_id)
    return RedirectResponse(url="/registrations", status_code=303)


@app.post("/registrations/reject/{reg_id}")
async def registrations_reject(request: Request, reg_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import reject_registration
    reject_registration(reg_id)
    return RedirectResponse(url="/registrations", status_code=303)


# ─── SHOP REVIEWS MODERATION ───────────────────────────

@app.get("/shop_reviews", response_class=HTMLResponse)
async def shop_reviews_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_all_shop_reviews
    revs = get_all_shop_reviews()
    return templates.TemplateResponse("shop_reviews.html", {"request": request, "revs": revs})


@app.post("/shop_reviews/approve/{review_id}")
async def shop_reviews_approve(request: Request, review_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import approve_shop_review
    approve_shop_review(review_id)
    return RedirectResponse(url="/shop_reviews", status_code=303)


@app.post("/shop_reviews/reject/{review_id}")
async def shop_reviews_reject(request: Request, review_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import reject_shop_review
    reject_shop_review(review_id)
    return RedirectResponse(url="/shop_reviews", status_code=303)


# ─── SHOP REGISTRATIONS ─────────────────────────────

@app.get("/shop_registrations", response_class=HTMLResponse)
async def shop_registrations_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_pending_shop_registrations
    regs = get_pending_shop_registrations()
    return templates.TemplateResponse("shop_registrations.html", {"request": request, "regs": regs})


@app.post("/shop_registrations/approve/{reg_id}")
async def shop_registrations_approve(request: Request, reg_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import approve_shop_registration
    approve_shop_registration(reg_id)
    return RedirectResponse(url="/shop_registrations", status_code=303)


@app.post("/shop_registrations/reject/{reg_id}")
async def shop_registrations_reject(request: Request, reg_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import reject_shop_registration
    reject_shop_registration(reg_id)
    return RedirectResponse(url="/shop_registrations", status_code=303)


# ─── SHOP VERIFICATION ─────────────────────────────

@app.get("/shop_verification", response_class=HTMLResponse)
async def shop_verification_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_all_shop_verification_requests
    reqs = get_all_shop_verification_requests()
    return templates.TemplateResponse("shop_verification.html", {"request": request, "reqs": reqs})


@app.post("/shop_verification/approve/{shop_id}")
async def shop_verification_approve(request: Request, shop_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import approve_shop_verification
    approve_shop_verification(shop_id)
    return RedirectResponse(url="/shop_verification", status_code=303)


@app.post("/shop_verification/reject/{shop_id}")
async def shop_verification_reject(request: Request, shop_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import reject_shop_verification
    reject_shop_verification(shop_id)
    return RedirectResponse(url="/shop_verification", status_code=303)


# ─── EMPLOYERS ─────────────────────────────────────

@app.get("/employers", response_class=HTMLResponse)
async def employers_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_employers
    data = get_employers(page=1, per_page=100)
    return templates.TemplateResponse("employers.html", {"request": request, "emps": data["items"]})


@app.post("/employers/delete/{emp_id}")
async def employers_delete(request: Request, emp_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("DELETE FROM employers WHERE id=?", (emp_id,))
    return RedirectResponse(url="/employers", status_code=303)


# ─── STATISTICS ─────────────────────────────────────

@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_master_stats
    stats = get_master_stats()
    return templates.TemplateResponse("stats.html", {"request": request, "stats": stats})


# ─── EMPLOYER REGISTRATIONS ──────────────────────────

@app.get("/employer_registrations", response_class=HTMLResponse)
async def employer_registrations_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import get_pending_employers
    regs = get_pending_employers()
    return templates.TemplateResponse("employer_registrations.html", {"request": request, "regs": regs})


@app.post("/employer_registrations/approve/{emp_id}")
async def employer_registrations_approve(request: Request, emp_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import approve_employer
    approve_employer(emp_id)
    return RedirectResponse(url="/employer_registrations", status_code=303)


@app.post("/employer_registrations/reject/{emp_id}")
async def employer_registrations_reject(request: Request, emp_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .services import reject_employer
    reject_employer(emp_id)
    return RedirectResponse(url="/employer_registrations", status_code=303)


# ─── BOT SETTINGS ─────────────────────────────────────

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    vk_token = get_bot_setting("vk_token") or ""
    group_id = get_bot_setting("group_id") or ""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "vk_token": vk_token,
        "group_id": group_id,
        "bot_running": _bot_thread is not None and _bot_thread.is_alive(),
    })


@app.post("/settings")
async def settings_save(request: Request, vk_token: str = Form(...), group_id: str = Form(...)):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    set_bot_setting("vk_token", vk_token)
    set_bot_setting("group_id", group_id)
    logger.info("Bot settings saved")
    return RedirectResponse(url="/settings", status_code=303)


@app.post("/sessions/clear")
async def sessions_clear(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        db.execute("DELETE FROM user_sessions")
    logger.info("All user sessions cleared")
    return RedirectResponse(url="/settings", status_code=303)


# ─── BOT LIFECYCLE ────────────────────────────────────

@app.post("/bot/start")
async def bot_start(request: Request):
    global _bot_thread, _bot_stop_event
    if not await verify_auth(request):
        return RedirectResponse(url="/login")

    if _bot_thread and _bot_thread.is_alive():
        return RedirectResponse(url="/settings", status_code=303)

    from .bot import start_bot

    _bot_stop_event = threading.Event()

    def _run():
        try:
            start_bot(stop_event=_bot_stop_event)
        except Exception as e:
            logger.exception(f"Bot error: {e}")

    _bot_thread = threading.Thread(target=_run, daemon=True)
    _bot_thread.start()
    logger.info("Bot started from admin panel")
    return RedirectResponse(url="/settings", status_code=303)


@app.post("/bot/stop")
async def bot_stop(request: Request):
    global _bot_stop_event
    if not await verify_auth(request):
        return RedirectResponse(url="/login")

    if _bot_stop_event:
        _bot_stop_event.set()
        logger.info("Bot stop signal sent")
    return RedirectResponse(url="/settings", status_code=303)


def bot_status():
    return _bot_thread is not None and _bot_thread.is_alive()


# ─── ORDER BOARD MANAGEMENT ───────────────────────────

@app.get("/orders", response_class=HTMLResponse)
async def orders_list(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .order_services import get_active_orders, get_order_categories, get_order_stats
    page = int(request.query_params.get("page", 1))
    cat_id = request.query_params.get("category_id")
    cid = int(cat_id) if cat_id else None
    data = get_active_orders(category_id=cid, page=page)
    cats = get_order_categories()
    stats = get_order_stats()
    return templates.TemplateResponse("orders.html", {
        "request": request, "orders": data["items"], "total": data["total"],
        "page": page, "total_pages": data["total_pages"], "cats": cats,
        "selected_cat": cid, "stats": stats,
        "page_list": list(range(1, data["total_pages"] + 1)),
    })


@app.post("/orders/delete/{order_id}")
async def orders_delete(request: Request, order_id: int):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .order_services import delete_order
    delete_order(order_id)
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/expire")
async def orders_expire(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    from .order_services import expire_old_orders
    expire_old_orders()
    return RedirectResponse(url="/orders", status_code=303)


# ─── DB CLEANUP ───────────────────────────────────────

@app.post("/settings/clear_db")
async def clear_database(request: Request):
    if not await verify_auth(request):
        return RedirectResponse(url="/login")
    with get_db() as db:
        tables = [
            "order_reviews", "order_responses", "orders",
            "order_performer_categories", "order_performers", "order_categories",
            "reviews", "ratings", "ads_requests",
            "master_registrations", "shop_registrations",
            "verification_requests", "shop_verification_requests",
            "masters", "shops", "employers",
            "faq", "categories", "master_categories", "shop_categories", "food_categories",
            "user_sessions",
        ]
        for t in tables:
            try:
                db.execute(f"DELETE FROM {t}")
            except Exception:
                pass
        try:
            db.execute("DELETE FROM bot_settings WHERE key NOT IN ('vk_token', 'group_id')")
        except Exception:
            pass
    from .database import seed_data
    seed_data()
    return RedirectResponse(url="/settings?cleared=1", status_code=303)


# ─── RUN ──────────────────────────────────────────────

def run_admin():
    uvicorn.run(app, host="0.0.0.0", port=ADMIN_PANEL_PORT, log_level="info")
