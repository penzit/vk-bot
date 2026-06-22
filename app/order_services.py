import time
from datetime import datetime, timedelta
from .database import get_db, get_bot_setting
from .services import notify_admin_vk

ORDER_CATEGORIES = [
    "Электрик", "Сантехник", "Ремонт", "Грузчики", "Доставка",
    "Такси", "Помощь по дому", "Красота и здоровье", "Строительство",
    "Подработка", "Другое",
]

ORDER_STATUSES = ("new", "has_responses", "in_progress", "completed", "cancelled", "expired")
URGENCY_OPTIONS = ("Срочно, сегодня", "В ближайшие дни", "Не срочно", "По договорённости")
ORDER_TTL_DAYS = 5
MAX_ACTIVE_ORDERS = 3


# ─── PERFORMER ──────────────────────────────────────────

def register_order_performer(vk_id, name, contact="", description=""):
    with get_db() as db:
        existing = db.execute("SELECT id FROM order_performers WHERE vk_id=?", (vk_id,)).fetchone()
        if existing:
            db.execute("UPDATE order_performers SET name=?, contact=?, description=? WHERE vk_id=?",
                       (name, contact, description, vk_id))
            return existing[0]
        db.execute("INSERT INTO order_performers (vk_id, name, contact, description) VALUES (?, ?, ?, ?)",
                   (vk_id, name, contact, description))
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_order_performer(vk_id):
    with get_db() as db:
        r = db.execute("SELECT id, vk_id, name, description, contact, rating, reviews_count, accepts_requests FROM order_performers WHERE vk_id=?", (vk_id,)).fetchone()
        if r:
            cats = [row[0] for row in db.execute(
                "SELECT c.id, c.name FROM order_categories c JOIN order_performer_categories pc ON c.id=pc.category_id WHERE pc.performer_id=?",
                (r[0],)).fetchall()]
            return {"id": r[0], "vk_id": r[1], "name": r[2], "description": r[3], "contact": r[4],
                    "rating": r[5], "reviews_count": r[6], "accepts_requests": bool(r[7]), "categories": cats}
        return None


def update_order_performer(vk_id, name=None, contact=None, description=None):
    with get_db() as db:
        fields, params = [], []
        if name is not None:
            fields.append("name=?"); params.append(name)
        if contact is not None:
            fields.append("contact=?"); params.append(contact)
        if description is not None:
            fields.append("description=?"); params.append(description)
        if not fields:
            return
        params.append(vk_id)
        db.execute(f"UPDATE order_performers SET {', '.join(fields)} WHERE vk_id=?", params)


def toggle_accepts_requests(vk_id):
    with get_db() as db:
        db.execute("UPDATE order_performers SET accepts_requests = 1 - accepts_requests WHERE vk_id=?", (vk_id,))
        r = db.execute("SELECT accepts_requests FROM order_performers WHERE vk_id=?", (vk_id,)).fetchone()
        return bool(r[0]) if r else True


def set_performer_categories(vk_id, category_ids):
    with get_db() as db:
        r = db.execute("SELECT id FROM order_performers WHERE vk_id=?", (vk_id,)).fetchone()
        if not r:
            return
        pid = r[0]
        db.execute("DELETE FROM order_performer_categories WHERE performer_id=?", (pid,))
        for cid in category_ids:
            db.execute("INSERT OR IGNORE INTO order_performer_categories (performer_id, category_id) VALUES (?, ?)", (pid, cid))


def get_performer_by_id(pid):
    with get_db() as db:
        r = db.execute("SELECT id, vk_id, name, description, contact, rating, reviews_count, accepts_requests FROM order_performers WHERE id=?", (pid,)).fetchone()
        if r:
            cats = [row[0] for row in db.execute(
                "SELECT c.id, c.name FROM order_categories c JOIN order_performer_categories pc ON c.id=pc.category_id WHERE pc.performer_id=?",
                (r[0],)).fetchall()]
            return {"id": r[0], "vk_id": r[1], "name": r[2], "description": r[3], "contact": r[4],
                    "rating": r[5], "reviews_count": r[6], "accepts_requests": bool(r[7]), "categories": cats}
        return None


def get_performers_for_category(category_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT p.id, p.vk_id, p.name, p.contact FROM order_performers p "
            "JOIN order_performer_categories pc ON p.id=pc.performer_id "
            "WHERE pc.category_id=? AND p.accepts_requests=1",
            (category_id,)
        ).fetchall()
        return [{"id": r[0], "vk_id": r[1], "name": r[2], "contact": r[3]} for r in rows]


# ─── ORDERS ─────────────────────────────────────────────

def create_order(user_vk_id, user_name, category_id, description, urgency, address, contact, photo_url, desired_time, comment):
    with get_db() as db:
        active = db.execute(
            "SELECT COUNT(*) FROM orders WHERE user_vk_id=? AND status IN ('new','has_responses','in_progress')",
            (user_vk_id,)
        ).fetchone()[0]
        if active >= MAX_ACTIVE_ORDERS:
            return None, "Достигнут лимит активных заявок (макс. 3)"
        expires = (datetime.utcnow() + timedelta(days=ORDER_TTL_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO orders (user_vk_id, user_name, category_id, description, urgency, address, contact, photo_url, desired_time, comment, status, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)",
            (user_vk_id, user_name, category_id, description, urgency, address, contact, photo_url, desired_time, comment, expires)
        )
        oid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return oid, None


def get_order(order_id):
    with get_db() as db:
        r = db.execute(
            "SELECT o.id, o.user_vk_id, o.user_name, c.name, o.category_id, o.description, o.urgency, "
            "o.address, o.contact, o.photo_url, o.desired_time, o.comment, o.status, "
            "o.selected_performer_id, o.created_at, o.expires_at "
            "FROM orders o JOIN order_categories c ON o.category_id=c.id WHERE o.id=?",
            (order_id,)
        ).fetchone()
        if r:
            responses = db.execute(
                "SELECT rp.id, rp.performer_id, p.name, p.rating, p.reviews_count, p.contact, rp.message, rp.status, rp.created_at "
                "FROM order_responses rp JOIN order_performers p ON rp.performer_id=p.id WHERE rp.order_id=? ORDER BY rp.created_at DESC",
                (order_id,)
            ).fetchall()
            resp_list = [{"id": x[0], "performer_id": x[1], "performer_name": x[2], "rating": x[3],
                          "reviews_count": x[4], "contact": x[5], "message": x[6], "status": x[7], "created_at": str(x[8])[:16] if x[8] else ""} for x in responses]
            return {
                "id": r[0], "user_vk_id": r[1], "user_name": r[2], "category": r[3], "category_id": r[4],
                "description": r[5], "urgency": r[6], "address": r[7], "contact": r[8],
                "photo_url": r[9], "desired_time": r[10], "comment": r[11], "status": r[12],
                "selected_performer_id": r[13], "created_at": str(r[14])[:16] if r[14] else "",
                "expires_at": str(r[15])[:16] if r[15] else "", "responses": resp_list,
            }
        return None


def get_active_orders(category_id=None, page=1, per_page=20):
    offset = (page - 1) * per_page
    with get_db() as db:
        where = "WHERE o.status IN ('new','has_responses')"
        params = []
        if category_id:
            where += " AND o.category_id=?"
            params.append(category_id)
        total = db.execute(f"SELECT COUNT(*) FROM orders o {where}", params).fetchone()[0]
        rows = db.execute(
            f"SELECT o.id, o.user_vk_id, o.user_name, c.name, o.description, o.urgency, o.address, "
            f"o.status, o.created_at, "
            f"(SELECT COUNT(*) FROM order_responses WHERE order_id=o.id) as resp_count "
            f"FROM orders o JOIN order_categories c ON o.category_id=c.id {where} "
            f"ORDER BY CASE o.urgency WHEN 'Срочно, сегодня' THEN 0 WHEN 'В ближайшие дни' THEN 1 WHEN 'Не срочно' THEN 2 ELSE 3 END, o.created_at DESC "
            f"LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        return {
            "items": [{"id": r[0], "user_vk_id": r[1], "user_name": r[2], "category": r[3],
                       "description": r[4][:120], "urgency": r[5], "address": r[6],
                       "status": r[7], "created_at": str(r[8])[:16] if r[8] else "", "responses_count": r[9]} for r in rows],
            "total": total, "page": page, "total_pages": max(1, (total + per_page - 1) // per_page),
        }


def get_my_orders(user_vk_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT o.id, c.name, o.description, o.urgency, o.status, o.created_at, "
            "(SELECT COUNT(*) FROM order_responses WHERE order_id=o.id) as resp_count "
            "FROM orders o JOIN order_categories c ON o.category_id=c.id "
            "WHERE o.user_vk_id=? ORDER BY o.created_at DESC",
            (user_vk_id,)
        ).fetchall()
        return [{"id": r[0], "category": r[1], "description": r[2][:120], "urgency": r[3],
                 "status": r[4], "created_at": str(r[5])[:16] if r[5] else "", "responses_count": r[6]} for r in rows]


def get_performer_orders(vk_id):
    with get_db() as db:
        p = db.execute("SELECT id FROM order_performers WHERE vk_id=?", (vk_id,)).fetchone()
        if not p:
            return []
        pid = p[0]
        rows = db.execute(
            "SELECT o.id, c.name, o.description, o.urgency, o.status, o.created_at, o.user_name, o.address, o.contact, o.desired_time, "
            "rp.status as my_response, rp.message "
            "FROM orders o "
            "JOIN order_categories c ON o.category_id=c.id "
            "JOIN order_performer_categories pc ON o.category_id=pc.category_id AND pc.performer_id=? "
            "LEFT JOIN order_responses rp ON rp.order_id=o.id AND rp.performer_id=? "
            "WHERE o.status IN ('new','has_responses','in_progress') "
            "ORDER BY CASE o.urgency WHEN 'Срочно, сегодня' THEN 0 WHEN 'В ближайшие дни' THEN 1 WHEN 'Не срочно' THEN 2 ELSE 3 END, o.created_at DESC",
            (pid, pid)
        ).fetchall()
        return [{"id": r[0], "category": r[1], "description": r[2][:120], "urgency": r[3],
                 "status": r[4], "created_at": str(r[5])[:16] if r[5] else "", "user_name": r[6],
                 "address": r[7], "contact": r[8], "desired_time": r[9],
                 "my_response": r[10], "my_message": r[11]} for r in rows]


def respond_to_order(order_id, performer_id, message=""):
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM order_responses WHERE order_id=? AND performer_id=?",
            (order_id, performer_id)
        ).fetchone()
        if existing:
            return False, "Вы уже откликнулись"
        db.execute("INSERT INTO order_responses (order_id, performer_id, message) VALUES (?, ?, ?)",
                   (order_id, performer_id, message))
        db.execute("UPDATE orders SET status='has_responses' WHERE id=? AND status='new'", (order_id,))
        return True, None


def decline_order_response(order_id, performer_id):
    with get_db() as db:
        db.execute("UPDATE order_responses SET status='declined' WHERE order_id=? AND performer_id=?",
                   (order_id, performer_id))


def select_performer(order_id, response_id):
    with get_db() as db:
        r = db.execute("SELECT performer_id FROM order_responses WHERE id=? AND order_id=?", (response_id, order_id)).fetchone()
        if not r:
            return False
        db.execute("UPDATE orders SET status='in_progress', selected_performer_id=? WHERE id=?", (r[0], order_id))
        db.execute("UPDATE order_responses SET status='rejected' WHERE order_id=? AND id!=?", (order_id, response_id))
        db.execute("UPDATE order_responses SET status='accepted' WHERE id=?", (response_id,))
        return True


def complete_order(order_id, user_vk_id):
    with get_db() as db:
        o = db.execute("SELECT user_vk_id FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o or o[0] != user_vk_id:
            return False
        db.execute("UPDATE orders SET status='completed' WHERE id=? AND status='in_progress'", (order_id,))
        return True


def cancel_order(order_id, user_vk_id):
    with get_db() as db:
        o = db.execute("SELECT user_vk_id, status FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o or o[0] != user_vk_id:
            return False
        if o[1] not in ('new', 'has_responses'):
            return False
        db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
        return True


def delete_order(order_id):
    with get_db() as db:
        db.execute("DELETE FROM orders WHERE id=?", (order_id,))


def expire_old_orders():
    with get_db() as db:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "UPDATE orders SET status='expired' WHERE status IN ('new','has_responses') AND expires_at<?",
            (now,)
        )


def leave_order_review(order_id, customer_vk_id, performer_id, rating, text):
    with get_db() as db:
        o = db.execute("SELECT status, selected_performer_id FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o or o[0] != 'completed' or o[1] != performer_id:
            return False
        existing = db.execute("SELECT id FROM order_reviews WHERE order_id=? AND customer_vk_id=?", (order_id, customer_vk_id)).fetchone()
        if existing:
            return False
        db.execute("INSERT INTO order_reviews (order_id, customer_vk_id, performer_id, rating, text) VALUES (?, ?, ?, ?, ?)",
                   (order_id, customer_vk_id, performer_id, rating, text))
        stat = db.execute("SELECT AVG(CAST(rating AS REAL)), COUNT(*) FROM order_reviews WHERE performer_id=?", (performer_id,)).fetchone()
        db.execute("UPDATE order_performers SET rating=?, reviews_count=? WHERE id=?",
                   (round(float(stat[0] or 0), 1), int(stat[1] or 0), performer_id))
        return True


def get_performer_reviews(performer_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT r.id, r.customer_vk_id, r.rating, r.text, r.created_at, o.description "
            "FROM order_reviews r JOIN orders o ON r.order_id=o.id WHERE r.performer_id=? ORDER BY r.created_at DESC",
            (performer_id,)
        ).fetchall()
        return [{"id": r[0], "customer_vk_id": r[1], "rating": r[2], "text": r[3],
                 "created_at": str(r[4])[:16] if r[4] else "", "order_desc": r[5][:80]} for r in rows]


def get_order_categories():
    with get_db() as db:
        return [{"id": r[0], "name": r[1]} for r in db.execute("SELECT id, name FROM order_categories ORDER BY id")]


def get_pending_performers():
    with get_db() as db:
        rows = db.execute("SELECT id, vk_id, name, contact, description, created_at FROM order_performers ORDER BY created_at DESC").fetchall()
        return [{"id": r[0], "vk_id": r[1], "name": r[2], "contact": r[3], "description": r[4],
                 "created_at": str(r[5])[:16] if r[5] else ""} for r in rows]


def get_order_stats():
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        by_status = {}
        for s in ORDER_STATUSES:
            by_status[s] = db.execute("SELECT COUNT(*) FROM orders WHERE status=?", (s,)).fetchone()[0]
        by_cat = db.execute(
            "SELECT c.name, COUNT(*) FROM orders o JOIN order_categories c ON o.category_id=c.id GROUP BY c.name ORDER BY COUNT(*) DESC"
        ).fetchall()
        return {"total": total, "by_status": by_status, "by_category": [{"name": r[0], "count": r[1]} for r in by_cat]}


def send_vk_message(user_id, text, keyboard=None):
    token = get_bot_setting("vk_token") or ""
    if not token or not user_id:
        return False
    try:
        import requests as _req
        data = {"user_id": user_id, "message": text, "random_id": 0, "access_token": token, "v": "5.131"}
        if keyboard:
            data["keyboard"] = keyboard
        _req.post("https://api.vk.com/method/messages.send", data=data, timeout=5)
        return True
    except Exception:
        return False


def notify_performers_new_order(order_id):
    with get_db() as db:
        o = db.execute(
            "SELECT o.id, c.name, o.description, o.urgency, o.address, o.contact, o.desired_time "
            "FROM orders o JOIN order_categories c ON o.category_id=c.id WHERE o.id=?",
            (order_id,)
        ).fetchone()
        if not o:
            return
        cat_id = db.execute("SELECT category_id FROM orders WHERE id=?", (order_id,)).fetchone()
        if not cat_id:
            return
        performers = db.execute(
            "SELECT p.vk_id, p.name FROM order_performers p "
            "JOIN order_performer_categories pc ON p.id=pc.performer_id "
            "WHERE pc.category_id=? AND p.accepts_requests=1",
            (cat_id[0],)
        ).fetchall()
        text = (
            f"📋 Новая заявка в категории: {o[1]}\n\n"
            f"📝 Описание: {o[2]}\n"
            f"⏰ Срочность: {o[3]}\n"
            f"📍 Адрес: {o[4] or 'не указан'}\n"
            f"📞 Контакт: {o[5]}\n"
            f"🕐 Время: {o[6] or 'по договорённости'}\n\n"
            f"Откройте заявку, чтобы откликнуться."
        )
        for p in performers:
            send_vk_message(p[0], text)


def notify_customer_response(order_id):
    with get_db() as db:
        o = db.execute("SELECT user_vk_id, user_name FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o:
            return
        count = db.execute("SELECT COUNT(*) FROM order_responses WHERE order_id=?", (order_id,)).fetchone()[0]
        send_vk_message(o[0], f"👤 На вашу заявку #{order_id} откликнулся исполнитель. Всего откликов: {count}. Откройте заявку, чтобы посмотреть.")


def notify_performer_selected(order_id, performer_vk_id):
    send_vk_message(performer_vk_id, f"✅ Заказчик выбрал вас по заявке #{order_id}. Свяжитесь с ним для уточнения деталей.")
