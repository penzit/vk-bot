import random
import time

from .database import get_db
from .config import ADMIN_VK_ID


def notify_admin_vk(text):
    if not ADMIN_VK_ID:
        return
    try:
        import requests as _req
        token = ""
        try:
            from .database import get_bot_setting
            token = get_bot_setting("vk_token") or ""
        except Exception:
            pass
        if not token:
            return
        _req.post("https://api.vk.com/method/messages.send", data={
            "user_id": ADMIN_VK_ID,
            "message": text,
            "random_id": 0,
            "access_token": token,
            "v": "5.131",
        }, timeout=5)
    except Exception:
        pass


AD_TRIGGER_KEYWORDS = [
    "реклама", "разместить", "купить рекламу", "объявление",
    "продвижение", "прайс", "сколько стоит реклама",
    "реклам", "размещ", "продвиж",
]

AD_OFFER_TEXT = (
    "📌 Обычное рекламное объявление - 250 ₽\n"
    "✅ Продвижение услуг, товаров, акций, вакансий и постов, предназначенных для определенных категорий в разделе \"обсуждения\".\n\n"
    "📢 Репост из вашего сообщества/страницы - 300₽\n"
    "🔗 Продвижение услуг, товаров, акций и вакансий с переходом трафика к вам.\n\n"
    "📲 Объявление со ссылкой на Телеграм-канал или на другие источники - 400 ₽\n"
    "📎 Продвижение услуг, товаров, акций и вакансий с переходом трафика к вам в канал или на ваш внешний источник.\n\n"
    "📲 Реклама в сторис (24 часа) - 400 ₽\n"
    "Ваше объявление в формате сторис: фото или видео с текстом и активной кнопкой.\n"
    "Отлично подходит для акций и срочных предложений.\n\n"
    "📲 Сторис + пост - 550 ₽ (выгоднее!)\n"
    "Комбинированное размещение: ваш пост в ленте + реклама в сторис для большего охвата.\n\n"
    "Работаем по системе НПД, можем выставить счет для ИП/юр.лица.\n"
    "После оплаты также высылаем чек для отчетности в организации.\n\n"
    "🎁 Скидки на пакетные размещения, уточняйте у админа.\n"
    "❗ Все посты публикуются навсегда и опускаются вниз по мере публикации новых записей.\n\n"
    "💳 Реквизиты:\n"
    "Сбербанк - 2202 2063 3271 2038\n"
    "Альфа-банк - 2200 1545 3229 7719\n"
    "Озон банк - 2204 3210 8798 2542\n\n"
    "❗После оплаты необходимо прислать скриншот или файл чека.\n\n"
    "Нажмите «Оставить заявку», чтобы начать."
)

SESSION_TTL = 12 * 3600


def contains_ad_keywords(text):
    text_lower = text.lower()
    for kw in AD_TRIGGER_KEYWORDS:
        if kw in text_lower:
            return True
    return False


def is_new_session(session):
    if not session:
        return True
    return (time.time() - session["last_interaction"]) > SESSION_TTL


# ─── FAQ ──────────────────────────────────────────────

def get_categories():
    with get_db() as db:
        return [{"id": r[0], "name": r[1]} for r in db.execute("SELECT id, name FROM categories ORDER BY name")]


def get_faq_by_category(category_id):
    with get_db() as db:
        return [{"id": r[0], "question": r[1]} for r in db.execute(
            "SELECT id, question FROM faq WHERE category_id=? ORDER BY id", (category_id,))]


def get_faq_by_id(faq_id):
    with get_db() as db:
        r = db.execute("SELECT id, question, answer, category_id FROM faq WHERE id=?", (faq_id,)).fetchone()
        if r:
            return {"id": r[0], "question": r[1], "answer": r[2], "category_id": r[3]}
        return None


def search_faq_by_keywords(text):
    keywords = text.lower().split()
    with get_db() as db:
        rows = db.execute("SELECT id, question, answer, keywords, category_id FROM faq").fetchall()
    results = []
    for r in rows:
        faq_kw = (r[3] + " " + r[1]).lower()
        match_count = sum(1 for kw in keywords if kw in faq_kw)
        if match_count > 0:
            results.append({"id": r[0], "question": r[1], "answer": r[2], "category_id": r[4], "relevance": match_count})
    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:5]


# ─── MASTER CATEGORIES ────────────────────────────────

def get_master_categories():
    with get_db() as db:
        return [{"id": r[0], "name": r[1]} for r in db.execute("SELECT id, name FROM master_categories ORDER BY name")]


def get_shop_categories():
    with get_db() as db:
        return [{"id": r[0], "name": r[1]} for r in db.execute("SELECT id, name FROM shop_categories ORDER BY name")]


def get_food_categories():
    with get_db() as db:
        return [{"id": r[0], "name": r[1]} for r in db.execute("SELECT id, name FROM food_categories ORDER BY name")]


# ─── MASTERS ──────────────────────────────────────────

def get_masters(category_id=None, verified_only=False, page=1, per_page=5):
    offset = (page - 1) * per_page
    where = []
    params = []

    if category_id:
        where.append("m.category_id = ?")
        params.append(category_id)
    if verified_only:
        where.append("m.verified = 1")

    where_clause = (" WHERE " + " AND ".join(where)) if where else ""

    with get_db() as db:
        total = db.execute(f"SELECT COUNT(*) FROM masters m{where_clause}", params).fetchone()[0]
        rows = db.execute(
            f"SELECT m.id, m.name, m.description, m.contacts, m.photo, m.verified, m.rating, m.votes_count, m.owner_vk_id "
            f"FROM masters m{where_clause} ORDER BY m.verified DESC, m.rating DESC, m.id LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            "items": [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                       "photo": r[4], "verified": bool(r[5]), "rating": r[6], "votes_count": r[7], "owner_vk_id": r[8]}
                      for r in rows],
            "total": total, "page": page, "total_pages": total_pages,
        }


def get_master_by_id(master_id):
    with get_db() as db:
        r = db.execute(
            "SELECT id, name, description, contacts, photo, verified, rating, votes_count, views_count, owner_vk_id "
            "FROM masters WHERE id=?", (master_id,)
        ).fetchone()
        if r:
            return {"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                    "photo": r[4], "verified": bool(r[5]), "rating": r[6], "votes_count": r[7],
                    "views_count": r[8], "owner_vk_id": r[9]}
        return None


def record_master_view(master_id):
    with get_db() as db:
        db.execute("UPDATE masters SET views_count = views_count + 1 WHERE id=?", (master_id,))
        return db.execute("SELECT views_count FROM masters WHERE id=?", (master_id,)).fetchone()[0]


def get_master_stats():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, views_count, rating, votes_count FROM masters ORDER BY views_count DESC"
        ).fetchall()
        return [{"id": r[0], "name": r[1], "views_count": r[2], "rating": r[3], "votes_count": r[4]} for r in rows]


def get_masters_by_owner(user_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, description, contacts, photo, verified, rating, votes_count "
            "FROM masters WHERE owner_vk_id=? ORDER BY id", (user_id,)
        ).fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                 "photo": r[4], "verified": bool(r[5]), "rating": r[6], "votes_count": r[7]} for r in rows]


def create_master(name, description, contacts, category_id, owner_vk_id=None):
    with get_db() as db:
        db.execute(
            "INSERT INTO masters (name, description, contacts, category_id, owner_vk_id) VALUES (?, ?, ?, ?, ?)",
            (name, description, contacts, category_id, owner_vk_id)
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


# ─── SHOPS ────────────────────────────────────────────

def get_shops(category_id=None, page=1, per_page=5):
    offset = (page - 1) * per_page
    where = " WHERE category_id=?" if category_id else ""
    params = [category_id] if category_id else []
    with get_db() as db:
        total = db.execute(f"SELECT COUNT(*) FROM shops{where}", params if category_id else []).fetchone()[0]
        rows = db.execute(
            f"SELECT id, name, description, contacts, photo, rating, votes_count FROM shops{where} ORDER BY rating DESC, id LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            "items": [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                       "photo": r[4], "rating": r[5], "votes_count": r[6]} for r in rows],
            "total": total, "page": page, "total_pages": total_pages,
        }


def get_shops_by_type(shop_type, category_id=None, page=1, per_page=5):
    offset = (page - 1) * per_page
    where = ["s.shop_type = ?"]
    params = [shop_type]
    if category_id:
        where.append("s.category_id = ?")
        params.append(category_id)
    where_clause = " WHERE " + " AND ".join(where)
    with get_db() as db:
        total = db.execute(f"SELECT COUNT(*) FROM shops s{where_clause}", params).fetchone()[0]
        rows = db.execute(
            f"SELECT s.id, s.name, s.description, s.contacts, s.photo, s.verified, s.rating, s.votes_count, s.owner_vk_id, s.shop_type "
            f"FROM shops s{where_clause} ORDER BY s.verified DESC, s.rating DESC, s.id LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            "items": [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                       "photo": r[4], "verified": bool(r[5]), "rating": r[6], "votes_count": r[7],
                       "owner_vk_id": r[8], "shop_type": r[9]} for r in rows],
            "total": total, "page": page, "total_pages": total_pages,
        }


def get_shop_by_id(shop_id):
    with get_db() as db:
        r = db.execute(
            "SELECT id, name, description, contacts, photo, rating, votes_count, owner_vk_id, verified, shop_type "
            "FROM shops WHERE id=?", (shop_id,)
        ).fetchone()
        if r:
            return {"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                    "photo": r[4], "rating": r[5], "votes_count": r[6], "owner_vk_id": r[7],
                    "verified": bool(r[8]), "shop_type": r[9]}
        return None


def get_shops_by_owner(user_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, description, contacts, photo, rating, votes_count, verified, shop_type "
            "FROM shops WHERE owner_vk_id=? ORDER BY id", (user_id,)
        ).fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                 "photo": r[4], "rating": r[5], "votes_count": r[6], "verified": bool(r[7]), "shop_type": r[8]}
                for r in rows]


# ─── REVIEWS ──────────────────────────────────────────

MIN_MSG_TO_REVIEW = 2


def create_review(master_id, user_id, user_name, text, rating):
    with get_db() as db:
        db.execute(
            "INSERT INTO reviews (target_type, target_id, user_id, user_name, text, rating, status) VALUES ('master', ?, ?, ?, ?, ?, 'pending')",
            (master_id, user_id, user_name, text, rating)
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def create_shop_review(shop_id, user_id, user_name, text, rating, target_type='shop'):
    with get_db() as db:
        db.execute(
            "INSERT INTO reviews (target_type, target_id, user_id, user_name, text, rating, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (target_type, shop_id, user_id, user_name, text, rating)
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def approve_review(review_id):
    with get_db() as db:
        r = db.execute("SELECT target_type, target_id FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not r:
            return
        target_type, target_id = r[0], r[1]
        db.execute("UPDATE reviews SET status='approved' WHERE id=?", (review_id,))
        stat = db.execute(
            "SELECT AVG(CAST(rating AS REAL)), COUNT(*) FROM reviews WHERE target_type=? AND target_id=? AND status='approved'",
            (target_type, target_id)
        ).fetchone()
        rating = round(float(stat[0] or 0), 1)
        votes = int(stat[1] or 0)
        if target_type == 'master':
            db.execute("UPDATE masters SET rating=?, votes_count=? WHERE id=?", (rating, votes, target_id))
        else:
            db.execute("UPDATE shops SET rating=?, votes_count=? WHERE id=?", (rating, votes, target_id))

def reject_review(review_id):
    with get_db() as db:
        db.execute("UPDATE reviews SET status='rejected' WHERE id=?", (review_id,))


def approve_shop_review(review_id):
    approve_review(review_id)


def reject_shop_review(review_id):
    reject_review(review_id)


def get_reviews_for_master(master_id, status="approved"):
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, user_name, text, rating, created_at FROM reviews WHERE target_type='master' AND target_id=? AND status=? ORDER BY created_at DESC",
            (master_id, status)
        ).fetchall()
        return [{"id": r[0], "user_id": r[1], "user_name": r[2], "text": r[3], "rating": r[4],
                 "created_at": str(r[5])[:16] if r[5] else ""} for r in rows]


def get_reviews_for_shop(shop_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, user_name, text, rating, created_at FROM reviews WHERE target_type IN ('shop','food') AND target_id=? AND status='approved' ORDER BY created_at DESC",
            (shop_id,)
        ).fetchall()
        return [{"id": r[0], "user_id": r[1], "user_name": r[2], "text": r[3], "rating": r[4],
                 "created_at": str(r[5])[:16] if r[5] else ""} for r in rows]


def get_pending_reviews():
    with get_db() as db:
        rows = db.execute(
            "SELECT r.id, r.target_type, r.target_id, r.user_id, r.user_name, r.text, r.rating, r.created_at, "
            "COALESCE(m.name, s.name) as target_name "
            "FROM reviews r "
            "LEFT JOIN masters m ON r.target_type='master' AND r.target_id=m.id "
            "LEFT JOIN shops s ON r.target_type IN ('shop','food') AND r.target_id=s.id "
            "WHERE r.status='pending' ORDER BY r.created_at DESC"
        ).fetchall()
        return [{"id": r[0], "target_type": r[1], "target_id": r[2], "user_id": r[3], "user_name": r[4],
                 "text": r[5], "rating": r[6],
                 "created_at": str(r[7])[:16] if r[7] else "", "target_name": r[8]} for r in rows]


def get_pending_shop_reviews():
    with get_db() as db:
        rows = db.execute(
            "SELECT r.id, r.target_type, r.target_id, r.user_id, r.user_name, r.text, r.rating, r.created_at, s.name as target_name "
            "FROM reviews r JOIN shops s ON r.target_id=s.id "
            "WHERE r.target_type IN ('shop','food') AND r.status='pending' ORDER BY r.created_at DESC"
        ).fetchall()
        return [{"id": r[0], "target_type": r[1], "target_id": r[2], "user_id": r[3], "user_name": r[4],
                 "text": r[5], "rating": r[6],
                 "created_at": str(r[7])[:16] if r[7] else "", "target_name": r[8]} for r in rows]


def get_all_reviews():
    with get_db() as db:
        rows = db.execute(
            "SELECT r.id, r.target_type, r.target_id, r.user_id, r.user_name, r.text, r.rating, r.status, r.created_at, "
            "COALESCE(m.name, s.name) as target_name "
            "FROM reviews r "
            "LEFT JOIN masters m ON r.target_type='master' AND r.target_id=m.id "
            "LEFT JOIN shops s ON r.target_type IN ('shop','food') AND r.target_id=s.id "
            "ORDER BY r.created_at DESC"
        ).fetchall()
        return [{"id": r[0], "target_type": r[1], "target_id": r[2], "user_id": r[3], "user_name": r[4],
                 "text": r[5], "rating": r[6], "status": r[7],
                 "created_at": str(r[8])[:16] if r[8] else "", "target_name": r[9]} for r in rows]


def get_all_shop_reviews():
    with get_db() as db:
        rows = db.execute(
            "SELECT r.id, r.target_type, r.target_id, r.user_id, r.user_name, r.text, r.rating, r.status, r.created_at, s.name as target_name "
            "FROM reviews r JOIN shops s ON r.target_id=s.id "
            "WHERE r.target_type IN ('shop','food') ORDER BY r.created_at DESC"
        ).fetchall()
        return [{"id": r[0], "target_type": r[1], "target_id": r[2], "user_id": r[3], "user_name": r[4],
                 "text": r[5], "rating": r[6], "status": r[7],
                 "created_at": str(r[8])[:16] if r[8] else "", "target_name": r[9]} for r in rows]


# ─── RATINGS (legacy, kept for shops) ─────────────────

def rate_shop(user_id, shop_id, rating):
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM ratings WHERE user_id=? AND target_type='shop' AND target_id=?", (user_id, shop_id)
        ).fetchone()
        if existing:
            return False, "Вы уже оценили этот магазин"
        db.execute("INSERT INTO ratings (user_id, target_type, target_id, rating) VALUES (?, 'shop', ?, ?)",
                   (user_id, shop_id, rating))
        db.execute("""
            UPDATE shops SET
                rating = (SELECT ROUND(AVG(CAST(rating AS REAL)), 1) FROM ratings WHERE target_type='shop' AND target_id=?),
                votes_count = (SELECT COUNT(*) FROM ratings WHERE target_type='shop' AND target_id=?)
            WHERE id=?
        """, (shop_id, shop_id, shop_id))
        return True, f"Спасибо! Ваша оценка: {rating} ⭐"


# ─── ADS ──────────────────────────────────────────────

def create_ads_request(user_id, user_name, message_text, message_type="ad"):
    with get_db() as db:
        db.execute("INSERT INTO ads_requests (user_id, user_name, message_type, message_text) VALUES (?, ?, ?, ?)",
                   (user_id, user_name, message_type, message_text))
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_ads_requests(status=None):
    with get_db() as db:
        q = "SELECT id, user_id, user_name, message_type, message_text, status, created_at FROM ads_requests"
        params = []
        if status:
            q += " WHERE status=? ORDER BY created_at DESC"
            params.append(status)
        else:
            q += " ORDER BY created_at DESC"
        rows = db.execute(q, params).fetchall()
        return [{"id": r[0], "user_id": r[1], "user_name": r[2], "message_type": r[3],
                 "message_text": r[4], "status": r[5],
                 "created_at": str(r[6])[:16] if r[6] else ""} for r in rows]


# ─── VERIFICATION ─────────────────────────────────────

def create_verification_request(master_id, user_id, phone, documents_info):
    with get_db() as db:
        db.execute("INSERT INTO verification_requests (master_id, user_id, phone, documents_info) VALUES (?, ?, ?, ?)",
                   (master_id, user_id, phone, documents_info))
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def approve_verification(master_id):
    with get_db() as db:
        db.execute("UPDATE masters SET verified=1 WHERE id=?", (master_id,))
        db.execute("UPDATE verification_requests SET status='approved' WHERE master_id=? AND status='pending'", (master_id,))


def reject_verification(master_id):
    with get_db() as db:
        db.execute("UPDATE verification_requests SET status='rejected' WHERE master_id=? AND status='pending'", (master_id,))


def get_all_verification_requests():
    with get_db() as db:
        rows = db.execute(
            "SELECT vr.id, vr.master_id, vr.user_id, vr.phone, vr.documents_info, vr.status, vr.created_at, m.name "
            "FROM verification_requests vr JOIN masters m ON vr.master_id=m.id ORDER BY vr.created_at DESC"
        ).fetchall()
        return [{"id": r[0], "master_id": r[1], "user_id": r[2], "phone": r[3],
                 "documents_info": r[4], "status": r[5],
                 "created_at": str(r[6])[:16] if r[6] else "", "master_name": r[7]} for r in rows]


# ─── MASTER REGISTRATION ──────────────────────────────

def create_registration(user_id, user_name, name, description, contacts, category_id, photo=""):
    with get_db() as db:
        db.execute(
            "INSERT INTO master_registrations (user_id, user_name, name, description, contacts, category_id, photo) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, user_name, name, description, contacts, category_id, photo)
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def approve_registration(reg_id):
    with get_db() as db:
        r = db.execute(
            "SELECT user_id, user_name, name, description, contacts, category_id, COALESCE(photo, '') FROM master_registrations WHERE id=?",
            (reg_id,)
        ).fetchone()
        if not r:
            return
        db.execute("UPDATE master_registrations SET status='approved' WHERE id=?", (reg_id,))
        db.execute("INSERT INTO masters (owner_vk_id, name, description, contacts, category_id, photo) VALUES (?, ?, ?, ?, ?, ?)",
                   (r[0], r[2], r[3], r[4], r[5], r[6]))


def reject_registration(reg_id):
    with get_db() as db:
        db.execute("UPDATE master_registrations SET status='rejected' WHERE id=?", (reg_id,))


def get_pending_registrations():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, user_name, name, description, contacts, category_id, created_at, COALESCE(photo, '') "
            "FROM master_registrations WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
        return [{"id": r[0], "user_id": r[1], "user_name": r[2], "name": r[3],
                 "description": r[4], "contacts": r[5], "category_id": r[6],
                 "created_at": str(r[7])[:16] if r[7] else "", "photo": r[8] if len(r) > 8 else ""} for r in rows]


# ─── SHOP REGISTRATION ────────────────────────────────

def create_shop_registration(user_id, user_name, shop_type, name, description, contacts, category_id, photo=""):
    with get_db() as db:
        db.execute(
            "INSERT INTO shop_registrations (user_id, user_name, shop_type, name, description, contacts, category_id, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, user_name, shop_type, name, description, contacts, category_id, photo)
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def approve_shop_registration(reg_id):
    with get_db() as db:
        r = db.execute(
            "SELECT user_id, user_name, shop_type, name, description, contacts, category_id, COALESCE(photo, '') FROM shop_registrations WHERE id=?",
            (reg_id,)
        ).fetchone()
        if not r:
            return
        db.execute("UPDATE shop_registrations SET status='approved' WHERE id=?", (reg_id,))
        db.execute(
            "INSERT INTO shops (owner_vk_id, name, description, contacts, category_id, shop_type, photo) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r[0], r[3], r[4], r[5], r[6], r[2], r[7])
        )


def reject_shop_registration(reg_id):
    with get_db() as db:
        db.execute("UPDATE shop_registrations SET status='rejected' WHERE id=?", (reg_id,))


def get_pending_shop_registrations():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, user_name, shop_type, name, description, contacts, category_id, created_at, COALESCE(photo, '') "
            "FROM shop_registrations WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
        return [{"id": r[0], "user_id": r[1], "user_name": r[2], "shop_type": r[3], "name": r[4],
                 "description": r[5], "contacts": r[6], "category_id": r[7],
                 "created_at": str(r[8])[:16] if r[8] else "", "photo": r[9] if len(r) > 9 else ""} for r in rows]


# ─── SHOP VERIFICATION ────────────────────────────────

def create_shop_verification_request(shop_id, user_id, phone, documents_info):
    with get_db() as db:
        db.execute(
            "INSERT INTO shop_verification_requests (shop_id, user_id, phone, documents_info) VALUES (?, ?, ?, ?)",
            (shop_id, user_id, phone, documents_info)
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def approve_shop_verification(shop_id):
    with get_db() as db:
        db.execute("UPDATE shops SET verified=1 WHERE id=?", (shop_id,))
        db.execute("UPDATE shop_verification_requests SET status='approved' WHERE shop_id=? AND status='pending'", (shop_id,))


def reject_shop_verification(shop_id):
    with get_db() as db:
        db.execute("UPDATE shop_verification_requests SET status='rejected' WHERE shop_id=? AND status='pending'", (shop_id,))


def get_all_shop_verification_requests():
    with get_db() as db:
        rows = db.execute(
            "SELECT svr.id, svr.shop_id, svr.user_id, svr.phone, svr.documents_info, svr.status, svr.created_at, s.name "
            "FROM shop_verification_requests svr JOIN shops s ON svr.shop_id=s.id ORDER BY svr.created_at DESC"
        ).fetchall()
        return [{"id": r[0], "shop_id": r[1], "user_id": r[2], "phone": r[3],
                 "documents_info": r[4], "status": r[5],
                 "created_at": str(r[6])[:16] if r[6] else "", "shop_name": r[7]} for r in rows]


# ─── EMPLOYERS ────────────────────────────────────────

def create_employer(user_id, user_name, company_name, description, phone, vk_page, contacts, vacancy_text, photo=""):
    with get_db() as db:
        db.execute(
            "INSERT INTO employers (user_id, user_name, company_name, description, phone, vk_page, contacts, vacancy_text, photo, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
            (user_id, user_name, company_name, description, phone, vk_page, contacts, vacancy_text, photo)
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_employers(page=1, per_page=5):
    offset = (page - 1) * per_page
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM employers WHERE status='approved'").fetchone()[0]
        rows = db.execute(
            "SELECT id, user_id, user_name, company_name, description, phone, vk_page, contacts, vacancy_text, created_at, COALESCE(photo, '') "
            "FROM employers WHERE status='approved' ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            "items": [{"id": r[0], "user_id": r[1], "user_name": r[2], "company_name": r[3],
                       "description": r[4], "phone": r[5], "vk_page": r[6], "contacts": r[7],
                       "vacancy_text": r[8], "created_at": str(r[9])[:16] if r[9] else "", "photo": r[10]} for r in rows],
            "total": total, "page": page, "total_pages": total_pages,
        }


def get_employer_by_id(emp_id):
    with get_db() as db:
        r = db.execute(
            "SELECT id, user_id, user_name, company_name, description, phone, vk_page, contacts, vacancy_text, created_at, COALESCE(photo, '') "
            "FROM employers WHERE id=?", (emp_id,)
        ).fetchone()
        if r:
            return {"id": r[0], "user_id": r[1], "user_name": r[2], "company_name": r[3],
                    "description": r[4], "phone": r[5], "vk_page": r[6], "contacts": r[7],
                    "vacancy_text": r[8], "created_at": str(r[9])[:16] if r[9] else "", "photo": r[10]}
        return None


def get_pending_employers():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, user_name, company_name, description, phone, vk_page, contacts, vacancy_text, created_at, COALESCE(photo, '') "
            "FROM employers WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
        return [{"id": r[0], "user_id": r[1], "user_name": r[2], "company_name": r[3],
                 "description": r[4], "phone": r[5], "vk_page": r[6], "contacts": r[7],
                 "vacancy_text": r[8], "created_at": str(r[9])[:16] if r[9] else "", "photo": r[10]} for r in rows]


def approve_employer(emp_id):
    with get_db() as db:
        db.execute("UPDATE employers SET status='approved' WHERE id=?", (emp_id,))


def reject_employer(emp_id):
    with get_db() as db:
        db.execute("DELETE FROM employers WHERE id=?", (emp_id,))


# ─── KEYWORD SEARCH ────────────────────────────────


def search_employers_by_keyword(text):
    keywords = text.lower().split()
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, user_name, company_name, description, phone, vk_page, contacts, vacancy_text, created_at, COALESCE(photo, '') "
            "FROM employers WHERE status='approved'"
        ).fetchall()
    results = []
    for r in rows:
        searchable = (r[3] + " " + r[4] + " " + r[8]).lower()
        match_count = sum(1 for kw in keywords if kw in searchable)
        if match_count > 0:
            results.append({"id": r[0], "user_id": r[1], "user_name": r[2], "company_name": r[3],
                           "description": r[4], "phone": r[5], "vk_page": r[6], "contacts": r[7],
                           "vacancy_text": r[8], "created_at": r[9], "photo": r[10], "relevance": match_count})
    results.sort(key=lambda x: -x["relevance"])
    return results


def search_masters_by_keyword(text):
    keywords = text.lower().split()
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, description, contacts, photo, verified, rating, votes_count, owner_vk_id "
            "FROM masters"
        ).fetchall()
    results = []
    for r in rows:
        searchable = (r[1] + " " + r[2]).lower()
        match_count = sum(1 for kw in keywords if kw in searchable)
        if match_count > 0:
            results.append({"id": r[0], "name": r[1], "description": r[2], "contacts": r[3],
                           "photo": r[4], "verified": bool(r[5]), "rating": r[6], "votes_count": r[7],
                           "owner_vk_id": r[8], "relevance": match_count})
    # Masters with votes first (by rating), then masters without votes (shuffled)
    results.sort(key=lambda x: (-x["relevance"], 0 if x["votes_count"] > 0 else 1, -x["rating"], random.random()))
    return results[:20]



def get_recommended_masters(limit=10):
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, description, contacts, photo, verified, rating, votes_count, owner_vk_id FROM masters WHERE COALESCE(recommended, 0)=1 ORDER BY rating DESC, id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3], "photo": r[4], "verified": bool(r[5]), "rating": r[6], "votes_count": r[7], "owner_vk_id": r[8]} for r in rows]


def get_recommended_shops(shop_type="shop", limit=10):
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, description, contacts, photo, verified, rating, votes_count, owner_vk_id, shop_type "
            "FROM shops WHERE COALESCE(recommended, 0)=1 AND shop_type=? ORDER BY rating DESC, id DESC LIMIT ?",
            (shop_type, limit)
        ).fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3], "photo": r[4],
                 "verified": bool(r[5]), "rating": r[6], "votes_count": r[7], "owner_vk_id": r[8], "shop_type": r[9]} for r in rows]


def get_recommended_employers(limit=10):
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, company_name, description, phone, vk_page, contacts, vacancy_text, photo "
            "FROM employers WHERE status='approved' AND COALESCE(recommended, 0)=1 ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"id": r[0], "user_id": r[1], "company_name": r[2], "description": r[3],
                 "phone": r[4], "vk_page": r[5], "contacts": r[6], "vacancy_text": r[7], "photo": r[8]} for r in rows]


def update_master(master_id, owner_vk_id, name=None, description=None, contacts=None, photo=None, category_id=None):
    with get_db() as db:
        m = db.execute("SELECT owner_vk_id FROM masters WHERE id=?", (master_id,)).fetchone()
        if not m or m[0] != owner_vk_id:
            return False
        fields, params = [], []
        if name is not None:
            fields.append("name=?"); params.append(name)
        if description is not None:
            fields.append("description=?"); params.append(description)
        if contacts is not None:
            fields.append("contacts=?"); params.append(contacts)
        if photo is not None:
            fields.append("photo=?"); params.append(photo)
        if category_id is not None:
            fields.append("category_id=?"); params.append(category_id if category_id else None)
        if not fields:
            return False
        params.append(master_id)
        db.execute(f"UPDATE masters SET {', '.join(fields)} WHERE id=?", params)
        return True


def update_shop(shop_id, owner_vk_id, name=None, description=None, contacts=None, photo=None, category_id=None):
    with get_db() as db:
        s = db.execute("SELECT owner_vk_id FROM shops WHERE id=?", (shop_id,)).fetchone()
        if not s or s[0] != owner_vk_id:
            return False
        fields, params = [], []
        if name is not None:
            fields.append("name=?"); params.append(name)
        if description is not None:
            fields.append("description=?"); params.append(description)
        if contacts is not None:
            fields.append("contacts=?"); params.append(contacts)
        if photo is not None:
            fields.append("photo=?"); params.append(photo)
        if category_id is not None:
            fields.append("category_id=?"); params.append(category_id if category_id else None)
        if not fields:
            return False
        params.append(shop_id)
        db.execute(f"UPDATE shops SET {', '.join(fields)} WHERE id=?", params)
        return True


def update_employer(emp_id, user_id, description=None, phone=None, vk_page=None, contacts=None, vacancy_text=None, photo=None):
    with get_db() as db:
        e = db.execute("SELECT user_id FROM employers WHERE id=?", (emp_id,)).fetchone()
        if not e or e[0] != user_id:
            return False
        fields, params = [], []
        if description is not None:
            fields.append("description=?"); params.append(description)
        if phone is not None:
            fields.append("phone=?"); params.append(phone)
        if vk_page is not None:
            fields.append("vk_page=?"); params.append(vk_page)
        if contacts is not None:
            fields.append("contacts=?"); params.append(contacts)
        if vacancy_text is not None:
            fields.append("vacancy_text=?"); params.append(vacancy_text)
        if photo is not None:
            fields.append("photo=?"); params.append(photo)
        if not fields:
            return False
        params.append(emp_id)
        db.execute(f"UPDATE employers SET {', '.join(fields)} WHERE id=?", params)
        return True
