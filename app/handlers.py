import json
import logging
import random

from .config import ADMIN_VK_ID, VK_MINI_APP_ID
from .keyboards import (
    main_menu, faq_categories_kb, faq_questions_kb, back_to_questions,
    category_list_kb, items_list_kb, item_card_kb,
    ad_offer_kb, back_to_menu, my_services_kb,
)
from .services import (
    get_categories, get_faq_by_category, get_faq_by_id, search_faq_by_keywords,
    get_master_categories, get_masters, get_master_by_id, get_masters_by_owner,
    get_shop_categories, get_shops, get_shop_by_id, get_shops_by_owner,
    create_review, create_ads_request, contains_ad_keywords, AD_OFFER_TEXT,
    create_verification_request, create_registration, is_new_session,
    rate_shop,
    create_shop_review, get_reviews_for_shop,
    create_shop_registration, get_shops_by_type, get_food_categories,
    create_shop_verification_request,
    get_employers, get_employer_by_id, create_employer, record_master_view, get_master_stats,
    search_employers_by_keyword, search_masters_by_keyword,
)
from .database import update_session, get_session
from .rate_limit import rate_limiter

logger = logging.getLogger(__name__)

user_states = {}
_processed_events = set()
_MAX_PROCESSED = 500


def _user_info(vk, user_id):
    try:
        u = vk.users.get(user_ids=user_id)[0]
        return f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
    except Exception:
        return f"id{user_id}"


def _send(vk, peer_id, message, keyboard=None, attachment=None):
    params = {"peer_id": peer_id, "message": message, "random_id": random.randint(0, 2**31)}
    if keyboard:
        params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
    if attachment:
        params["attachment"] = attachment
    vk.messages.send(**params)


def _edit(vk, peer_id, cmid, message, keyboard=None):
    params = {"peer_id": peer_id, "conversation_message_id": cmid, "message": message}
    if keyboard:
        params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
    vk.messages.edit(**params)


def _ack(vk, obj):
    try:
        vk.messages.sendMessageEventAnswer(
            event_id=obj.get("event_id"), user_id=obj.get("user_id"), peer_id=obj.get("peer_id"),
            event_data=json.dumps({"type": "show_snackbar", "text": "⏳"}),
        )
    except Exception:
        logger.debug("_ack failed (non-critical)")


def _notify(vk, label, rid, name, uid, text):
    aid = ADMIN_VK_ID
    if aid:
        try:
            _send(vk, int(aid),
                f"📩 {label} #{rid}\n👤 {name}\n🔗 vk.com/id{uid}\n💬 {text}")
        except Exception as e:
            logger.error(f"Admin notify fail: {e}")


def handle_message_new(vk, event):
    msg = event.object.get("message", {})
    peer_id = msg.get("peer_id")
    user_id = msg.get("from_id")
    text = (msg.get("text") or "").strip()
    pr = msg.get("payload")

    mid = msg.get("id") or msg.get("conversation_message_id")
    if mid:
        dk = f"msg_{peer_id}_{mid}"
        if dk in _processed_events:
            return
        _processed_events.add(dk)
        if len(_processed_events) > _MAX_PROCESSED:
            _processed_events.clear()

    payload = {}
    if isinstance(pr, str):
        payload = json.loads(pr) if pr else {}
    elif isinstance(pr, dict):
        payload = pr

    if not text and not payload:
        return
    if rate_limiter.is_limited(user_id):
        return

    user_name = _user_info(vk, user_id)
    session = get_session(user_id)
    update_session(user_id)
    msg_count = session["msg_count"] + 1 if session else 1
    new_sesh = is_new_session(session)
    state = user_states.get(user_id)

    # ─── State handlers ───
    if state:
        st = state.get("awaiting")
        if st == "ad_message":
            user_states.pop(user_id, None)
            ad_type = state.get("ad_type", "")
            msg = f"[{ad_type}] {text}" if ad_type else text
            rid = create_ads_request(user_id, user_name, msg, "ad")
            _send(vk, peer_id, "✅ Заявка принята! Администратор свяжется.", keyboard=back_to_menu())
            _notify(vk, "РЕКЛАМА", rid, user_name, user_id, msg)
            return
        if st == "contact_message":
            user_states.pop(user_id, None)
            rid = create_ads_request(user_id, user_name, text, "contact")
            _send(vk, peer_id, "✅ Сообщение передано администратору.", keyboard=back_to_menu())
            _notify(vk, "ОБРАЩЕНИЕ", rid, user_name, user_id, text)
            return
        if st == "verification_phone":
            user_states[user_id] = {"awaiting": "verification_docs", "master_id": state["master_id"], "phone": text}
            _send(vk, peer_id, "📄 Отправьте информацию о документах (паспорт, ИНН, самозанятость и т.д.)", back_to_menu())
            return
        if st == "verification_docs":
            user_states.pop(user_id, None)
            mid = state["master_id"]
            rid = create_verification_request(mid, user_id, state.get("phone", ""), text)
            _send(vk, peer_id, "✅ Документы отправлены на проверку.", keyboard=back_to_menu())
            _notify(vk, "ВЕРИФИКАЦИЯ", rid, user_name, user_id,
                    f"Мастер #{mid}\nТел: {state.get('phone', '')}\nДоки: {text}")
            return
        if st == "review_rating":
            from .keyboards import rating_kb
            _send(vk, peer_id, "⭐ Выберите оценку на кнопках выше:", rating_kb(state["master_id"]))
            return
        if st == "review_text":
            user_states.pop(user_id, None)
            mid = state["master_id"]
            rating = state["rating"]
            rid = create_review(mid, user_id, user_name, text, rating)
            _send(vk, peer_id,
                "✅ Ваш отзыв отправлен на модерацию администратору. После проверки он появится.",
                keyboard=back_to_menu())
            _notify(vk, "ОТЗЫВ", rid, user_name, user_id,
                    f"Мастер #{mid}\nОценка: {rating}\nТекст: {text}")
            return
        if st == "reg_name":
            user_states[user_id] = {"awaiting": "reg_desc", "name": text}
            _send(vk, peer_id, "📝 Напишите описание ваших услуг:", back_to_menu())
            return
        if st == "reg_desc":
            user_states[user_id] = {"awaiting": "reg_contacts", "name": state["name"], "description": text}
            _send(vk, peer_id, "📞 Напишите контакты (телефон, @username):", back_to_menu())
            return
        if st == "reg_contacts":
            user_states[user_id] = {"awaiting": "reg_cat", "name": state["name"], "description": state["description"], "contacts": text}
            cats = get_master_categories()
            from .keyboards import reg_cats_kb
            _send(vk, peer_id, "📂 Выберите категорию:", keyboard=reg_cats_kb(cats))
            return
        if st == "reg_cat":
            if payload.get("cmd") == "reg_select_cat":
                cid = payload.get("category_id")
                user_states.pop(user_id, None)
                rid = create_registration(user_id, user_name, state["name"], state["description"], state["contacts"], cid)
                _send(vk, peer_id,
                    "✅ Заявка отправлена! После одобрения вы появитесь в каталоге.",
                    keyboard=back_to_menu())
                _notify(vk, "РЕГИСТРАЦИЯ", rid, user_name, user_id,
                        f"Имя: {state['name']}\nОписание: {state['description']}\nКонтакты: {state['contacts']}")
                return
            _send(vk, peer_id, "❌ Выберите категорию из кнопок выше:", back_to_menu())
            return
        # ─── Shop registration states ───
        if st == "reg_shop_type":
            if text in ("1", "2"):
                shop_type = "shop" if text == "1" else "food"
                user_states[user_id] = {"awaiting": "reg_shop_name", "shop_type": shop_type}
                _send(vk, peer_id, "📝 Введите название:", back_to_menu())
                return
            _send(vk, peer_id, "❌ Напишите 1 (Магазин) или 2 (Доставка еды):", back_to_menu())
            return
        if st == "reg_shop_name":
            user_states[user_id] = {"awaiting": "reg_shop_desc", "shop_type": state["shop_type"], "name": text}
            _send(vk, peer_id, "📝 Введите описание:", back_to_menu())
            return
        if st == "reg_shop_desc":
            user_states[user_id] = {"awaiting": "reg_shop_contacts", "shop_type": state["shop_type"], "name": state["name"], "description": text}
            _send(vk, peer_id, "📞 Введите контакты:", back_to_menu())
            return
        if st == "reg_shop_contacts":
            user_states[user_id] = {"awaiting": "reg_shop_cat", "shop_type": state["shop_type"], "name": state["name"], "description": state["description"], "contacts": text}
            stype = state["shop_type"]
            cats = get_shop_categories() if stype == "shop" else get_food_categories()
            from .keyboards import reg_cats_kb
            _send(vk, peer_id, "📂 Выберите категорию:", keyboard=reg_cats_kb(cats))
            return
        if st == "reg_shop_cat":
            if payload.get("cmd") == "reg_select_cat":
                cid = payload.get("category_id")
                user_states.pop(user_id, None)
                rid = create_shop_registration(user_id, user_name, state["shop_type"], state["name"], state["description"], state["contacts"], cid)
                _send(vk, peer_id,
                    "✅ Заявка отправлена! После одобрения вы появитесь в каталоге.",
                    keyboard=back_to_menu())
                _notify(vk, "МАГАЗИН/ДОСТАВКА", rid, user_name, user_id,
                        f"Название: {state['name']}\nТип: {state['shop_type']}\nОписание: {state['description']}\nКонтакты: {state['contacts']}")
                return
            _send(vk, peer_id, "❌ Выберите категорию из кнопок выше:", back_to_menu())
            return
        # ─── Shop review ───
        if st == "shop_review_text":
            user_states.pop(user_id, None)
            sid = state["shop_id"]
            rating = state["rating"]
            stype = state.get("shop_type", "shop")
            rid = create_shop_review(sid, user_id, user_name, text, rating)
            _send(vk, peer_id, "✅ Отзыв отправлен на модерацию.", keyboard=back_to_menu())
            _notify(vk, "ОТЗЫВ НА МАГАЗИН", rid, user_name, user_id,
                    f"Магазин #{sid}\nТип: {stype}\nОценка: {rating}\nТекст: {text}")
            return
        # ─── Shop verification ───
        if st == "shop_verification_phone":
            user_states[user_id] = {"awaiting": "shop_verification_docs", "shop_id": state["shop_id"], "phone": text}
            _send(vk, peer_id, "📄 Отправьте информацию о документах (паспорт, ИНН и т.д.):", back_to_menu())
            return
        if st == "shop_verification_docs":
            user_states.pop(user_id, None)
            sid = state["shop_id"]
            rid = create_shop_verification_request(sid, user_id, state.get("phone", ""), text)
            _send(vk, peer_id, "✅ Документы отправлены на проверку.", keyboard=back_to_menu())
            _notify(vk, "ВЕРИФИКАЦИЯ МАГАЗИНА", rid, user_name, user_id,
                    f"Магазин #{sid}\nТел: {state.get('phone', '')}\nДоки: {text}")
            return
        # ─── Employer registration ───
        if st == "emp_company":
            user_states[user_id] = {"awaiting": "emp_description", "company_name": text}
            _send(vk, peer_id, "📝 Введите описание компании:", back_to_menu())
            return
        if st == "emp_description":
            user_states[user_id] = {"awaiting": "emp_phone", "company_name": state["company_name"], "description": text}
            _send(vk, peer_id, "📱 Введите номер телефона для связи:", back_to_menu())
            return
        if st == "emp_phone":
            user_states[user_id] = {"awaiting": "emp_vk_page", "company_name": state["company_name"], "description": state["description"], "phone": text}
            _send(vk, peer_id, "🔗 Введите ссылку на вашу страницу ВК (или @username):", back_to_menu())
            return
        if st == "emp_vk_page":
            user_states[user_id] = {"awaiting": "emp_contacts", "company_name": state["company_name"], "description": state["description"], "phone": state["phone"], "vk_page": text}
            _send(vk, peer_id, "📞 Введите дополнительные контакты (email, сайт и т.д.):", back_to_menu())
            return
        if st == "emp_contacts":
            user_states[user_id] = {"awaiting": "emp_vacancy", "company_name": state["company_name"], "description": state["description"], "phone": state["phone"], "vk_page": state["vk_page"], "contacts": text}
            _send(vk, peer_id, "💼 Введите текст вакансии:", back_to_menu())
            return
        if st == "emp_vacancy":
            try:
                rid = create_employer(user_id, user_name, state["company_name"], state["description"], state["phone"], state["vk_page"], state["contacts"], text)
                _send(vk, peer_id, "✅ Заявка отправлена на модерацию! После проверки она появится в списке.", keyboard=back_to_menu())
                _notify(vk, "ВАКАНСИЯ", rid, user_name, user_id,
                        f"Компания: {state['company_name']}\nТел: {state.get('phone', '')}\nВК: {state.get('vk_page', '')}\nКонтакты: {state.get('contacts', '')}\nВакансия: {text}")
            except Exception as e:
                logger.exception(f"Employer registration error: {e}")
                _send(vk, peer_id, "❌ Ошибка при сохранении. Попробуйте позже.", keyboard=back_to_menu())
            finally:
                user_states.pop(user_id, None)
            return

    # ─── Payload (from keyboard with text buttons) ───
    if payload.get("cmd"):
        handle_cmd(vk, payload, peer_id, user_id, user_name, msg_count=msg_count)
        return

    # ─── Ad keywords (always check) ───
    if contains_ad_keywords(text):
        _send(vk, peer_id, AD_OFFER_TEXT, keyboard=ad_offer_kb())
        return

    # ─── FAQ search (always check) ───
    faq_results = search_faq_by_keywords(text)
    if faq_results:
        resp = "🔍 Нашёл:\n\n"
        for r in faq_results:
            resp += f"❓ {r['question']}\n{r['answer']}\n\n"
        _send(vk, peer_id, resp.strip(), keyboard=back_to_menu())
        return

    # ─── Section context search (text while in a section) ───
    if state and not state.get("awaiting"):
        ctx = state.get("context", "")
        if ctx == "job":
            results = search_employers_by_keyword(text)
            if results:
                from .keyboards import employers_list_kb
                total_pages = max(1, (len(results) + 4) // 5)
                _send(vk, peer_id, f"💼 Найдено {len(results)} вакансий:",
                      employers_list_kb(results[:5], 1, total_pages))
            else:
                _send(vk, peer_id, "❌ Нет подходящих вакансий.", back_to_menu())
            return
        if ctx == "master":
            results = search_masters_by_keyword(text)
            if results:
                total_pages = max(1, (len(results) + 4) // 5)
                _send(vk, peer_id, f"🖍 Найдено {len(results)} мастеров:",
                      items_list_kb(results[:5], 1, total_pages, "master"))
            else:
                _send(vk, peer_id, "❌ Нет подходящих мастеров.", back_to_menu())
            return

    # ─── Smart intent routing (free text from main menu) ───
    if route_text_intent(vk, peer_id, user_id, user_name, text, None):
        return

    # ─── Active session → no response (suppress welcome for returning users) ───
    if not new_sesh:
        return

    # ─── First interaction → welcome ───
    _send(vk, peer_id,
        "Здравствуйте! Что хотите узнать?",
        keyboard=main_menu(VK_MINI_APP_ID))


def handle_callback(vk, event):
    obj = event.object
    peer_id = obj.get("peer_id")
    user_id = obj.get("user_id")
    cmid = obj.get("conversation_message_id")
    pr = obj.get("payload")

    payload = {}
    if isinstance(pr, str):
        payload = json.loads(pr) if pr else {}
    elif isinstance(pr, dict):
        payload = pr

    dk = f"cb_{peer_id}_{obj.get('event_id', '')}"
    if dk in _processed_events:
        return
    _processed_events.add(dk)
    if len(_processed_events) > _MAX_PROCESSED:
        _processed_events.clear()

    user_name = _user_info(vk, user_id)
    update_session(user_id)
    session = get_session(user_id)
    msg_count = session["msg_count"] if session else 1

    _ack(vk, obj)
    handle_cmd(vk, payload, peer_id, user_id, user_name, cmid, msg_count)


def stars(n):
    return "⭐" * int(n) + "☆" * (5 - int(n))


def _full_menu():
    from .keyboards import _btn
    return {"inline": True, "buttons": [
        [_btn("📚 Справочник", {"cmd": "faq_categories"}),
         _btn("🛠 Услуги", {"cmd": "master_categories"}),
         _btn("🏪 Магазины", {"cmd": "shop_categories"})],
        [_btn("💼 Работа", {"cmd": "job_menu"}),
         _btn("💰 Реклама", {"cmd": "ad_offer"}),
         _btn("📞 Админ", {"cmd": "contact_admin"}),
         _btn("👤 Исполнители", {"cmd": "performer_menu"})],
    ]}


def fmt_master(m, is_owner=False):
    badge = "✅ Проверенный\n\n" if m.get("verified") else ""
    rating_line = f"{stars(m['rating'])} {m['rating']} — {m['votes_count']} оценок" if m['votes_count'] > 0 else "⭐ Нет оценок"
    return (
        f"🖍 {m['name']}\n\n{badge}"
        f"{m['description']}\n\n"
        f"{rating_line}"
    )


def fmt_shop(s):
    return (
        f"🏪 {s['name']}\n\n{s['description']}\n\n"
        f"📞 {s['contacts']}\n\n"
        f"{stars(s['rating'])} {s['rating']} — {s['votes_count']} оценок"
    )


def handle_cmd(vk, payload, peer_id, user_id, user_name, cmid=None, msg_count=1):
    cmd = payload.get("cmd")
    if not cmd:
        return
    logger.info(f"cmd={cmd} user={user_id}")

    eos = lambda t, k=None, a=None: _edit_or_send(vk, peer_id, cmid, t, k, a)

    # ─── Menu ───
    if cmd == "main_menu":
        user_states.pop(user_id, None)
        eos("Выберите раздел:", _full_menu())

    elif cmd == "start_bot":
        user_states.pop(user_id, None)
        eos("Здравствуйте! Что хотите узнать?", _full_menu())

    # ─── FAQ ───
    elif cmd == "faq_categories":
        cats = get_categories()
        eos("📚 Категории:", faq_categories_kb(cats) if cats else back_to_menu())
    elif cmd == "faq_questions":
        cid = payload["category_id"]
        qs = get_faq_by_category(cid)
        cn = next((c["name"] for c in get_categories() if c["id"] == cid), "")
        eos(f"📚 {cn}", faq_questions_kb(qs, cid) if qs else back_to_menu())
    elif cmd == "faq_answer":
        faq = get_faq_by_id(payload.get("faq_id"))
        if not faq:
            eos("Не найдено.", back_to_menu()); return
        eos(f"❓ {faq['question']}\n\n{faq['answer']}", back_to_questions(faq["category_id"]))

    # ─── Master categories ───
    elif cmd == "master_categories":
        user_states[user_id] = {"context": "master"}
        cats = get_master_categories()
        cats.insert(0, {"id": None, "name": "📂 Все мастера"})
        eos("🖍 Категории мастеров:\n\nНапишите, кого вы ищете, и я найду подходящих мастеров:",
            category_list_kb(cats, "master", extra_buttons=[
                ("✅ Проверенные", {"cmd": "masters_verified"}),
            ]))

    elif cmd == "masters_verified":
        data = get_masters(verified_only=True, page=1)
        if not data["items"]:
            eos("🖍 Пока нет проверенных мастеров.", back_to_menu()); return
        eos(f"✅ Проверенные мастера:", items_list_kb(data["items"], 1, data["total_pages"], "master", verified_mode=True))

    elif cmd == "master_by_category":
        payload["cmd"] = "masters_list"
        handle_cmd(vk, payload, peer_id, user_id, user_name, cmid, msg_count)

    elif cmd == "masters_list":
        cid = payload.get("category_id")
        page = payload.get("page", 1)
        data = get_masters(category_id=cid, page=page)
        if not data["items"]:
            eos("Нет мастеров.", back_to_menu()); return
        eos(f"🖍 Мастера (стр.{page}/{data['total_pages']}):",
            items_list_kb(data["items"], page, data["total_pages"], "master"))

    elif cmd == "master_card":
        m = get_master_by_id(payload.get("master_id"))
        if not m:
            eos("Не найден.", back_to_menu()); return
        is_owner = m["owner_vk_id"] == user_id
        eos(fmt_master(m), item_card_kb(m["id"], "master", m["verified"], is_owner), m.get("photo") or None)

    elif cmd == "show_master_contacts":
        m = get_master_by_id(payload.get("master_id"))
        if not m:
            eos("Не найден.", back_to_menu()); return
        views = record_master_view(m["id"])
        text = f"📞 Контакты: {m['contacts']}\n\n👁 Просмотров: {views}"
        eos(text, back_to_menu())

    elif cmd == "master_verify":
        m = get_master_by_id(payload.get("master_id"))
        if not m:
            eos("Не найден.", back_to_menu()); return
        if m.get("verified"):
            eos("Уже верифицирован.", back_to_menu()); return
        user_states[user_id] = {"awaiting": "verification_phone", "master_id": m["id"]}
        eos("📞 Отправьте ваш номер телефона:", back_to_menu())

    # ─── Reviews (new flow: rate → review text) ───
    elif cmd == "start_review":
        m = get_master_by_id(payload.get("master_id"))
        if not m:
            eos("Не найден.", back_to_menu()); return
        if msg_count < 2:
            eos(f"Чтобы оставить отзыв, нужно отправить хотя бы 2 сообщения боту (у вас {msg_count}).", back_to_menu())
            return
        from .keyboards import rating_kb
        user_states[user_id] = {"awaiting": "review_rating", "master_id": m["id"]}
        eos("⭐ Оцените мастера от 1 до 5:", rating_kb(m["id"]))

    elif cmd == "set_review_rating":
        master_id = payload.get("master_id")
        rating = payload.get("rating")
        m = get_master_by_id(master_id)
        if not m:
            eos("Не найден.", back_to_menu()); return
        user_states[user_id] = {"awaiting": "review_text", "master_id": master_id, "rating": rating}
        eos(f"📝 Напишите ваше имя и расскажите, как прошла услуга.\n"
            f"Где выполнялись работы? Что делал мастер? Оцениваете на {rating} ⭐",
            back_to_menu())

    elif cmd == "view_reviews":
        mid = payload.get("master_id")
        from .services import get_reviews_for_master
        revs = get_reviews_for_master(mid)
        if not revs:
            eos("💬 У этого мастера пока нет отзывов.", back_to_menu()); return
        text = "💬 Отзывы:\n\n"
        for r in revs:
            text += f"{r['user_name']} — {stars(r['rating'])} {r['rating']}\n{r['text'][:100]}\n\n"
        eos(text.strip(), back_to_menu())

    # ─── Shop categories (updated) ───
    elif cmd == "shop_categories":
        cats = get_shop_categories()
        cats.insert(0, {"id": None, "name": "📂 Все магазины"})
        eos("🏪 Магазины:", category_list_kb(cats, "shop"))
    elif cmd == "shop_by_category":
        payload["cmd"] = "shops_list"
        handle_cmd(vk, payload, peer_id, user_id, user_name, cmid, msg_count)
    elif cmd == "shops_list":
        cid = payload.get("category_id")
        page = payload.get("page", 1)
        data = get_shops_by_type("shop", category_id=cid, page=page)
        if not data["items"]:
            eos("Нет магазинов.", back_to_menu()); return
        from .keyboards import shop_items_list_kb
        eos(f"🏪 Магазины (стр.{page}/{data['total_pages']}):",
            shop_items_list_kb(data["items"], page, data["total_pages"], "shop"))
    elif cmd == "shop_card":
        s = get_shop_by_id(payload.get("shop_id"))
        if not s:
            eos("Не найден.", back_to_menu()); return
        from .keyboards import shop_item_card_kb
        owner = s.get("owner_vk_id")
        is_owner = bool(owner and owner == user_id)
        eos(fmt_shop(s), shop_item_card_kb(s["id"], "shop", s.get("verified", False), is_owner), s.get("photo") or None)
    elif cmd == "rate_shop":
        ok, msg = rate_shop(user_id, payload["shop_id"], payload["rating"])
        s = get_shop_by_id(payload["shop_id"])
        if s:
            eos(fmt_shop(s) + f"\n\n_{msg}_", item_card_kb(s["id"], "shop"), s.get("photo") or None)
        else:
            eos(msg, back_to_menu())

    # ─── My services ───
    elif cmd == "my_services":
        items = get_masters_by_owner(user_id)
        if not items:
            eos("У вас пока нет зарегистрированных услуг. Хотите добавить?\n\n"
                "Нажмите «📝 Зарегистрировать услуги» в главном меню.",
                back_to_menu())
            return
        text = "🖍 Ваши услуги:\n\n"
        for i in items:
            tick = "✅" if i["verified"] else "❌"
            text += f"{tick} {i['name']} — {stars(i['rating'])} {i['rating']}\n"
        eos(text.strip(), back_to_menu())

    elif cmd == "register_service":
        user_states[user_id] = {"awaiting": "reg_name"}
        eos("📝 Введите название вашей услуги (например: «Иван — Мастер маникюра»):", back_to_menu())

    elif cmd == "reg_select_cat":
        state = user_states.get(user_id)
        if state and state.get("awaiting") == "reg_cat":
            cid = payload.get("category_id")
            user_states.pop(user_id, None)
            rid = create_registration(user_id, user_name, state["name"], state["description"], state["contacts"], cid)
            eos("✅ Заявка отправлена! После одобрения администратором вы появитесь в каталоге.", back_to_menu())
            _notify(vk, "РЕГИСТРАЦИЯ", rid, user_name, user_id,
                    f"Имя: {state['name']}\nОписание: {state['description']}\nКонтакты: {state['contacts']}")
        elif state and state.get("awaiting") == "reg_shop_cat":
            cid = payload.get("category_id")
            user_states.pop(user_id, None)
            rid = create_shop_registration(user_id, user_name, state["shop_type"], state["name"], state["description"], state["contacts"], cid)
            eos("✅ Заявка отправлена! После одобрения вы появитесь в каталоге.", back_to_menu())
            _notify(vk, "МАГАЗИН/ДОСТАВКА", rid, user_name, user_id,
                    f"Название: {state['name']}\nТип: {state['shop_type']}\nОписание: {state['description']}\nКонтакты: {state['contacts']}")
        else:
            eos("Сессия истекла. Начните заново.", back_to_menu())

    # ─── Ads ───
    elif cmd == "ad_offer":
        eos(AD_OFFER_TEXT + "\n\nВыберите формат:", ad_offer_kb())
    elif cmd == "ad_request":
        ad_type = payload.get("ad_type", "")
        user_states[user_id] = {"awaiting": "ad_message", "ad_type": ad_type}
        eos("📝 Напишите текст объявления:", back_to_menu())

    # ─── Contact ───
    elif cmd == "contact_admin":
        user_states[user_id] = {"awaiting": "contact_message"}
        eos("📩 Напишите ваш вопрос:", back_to_menu())

    # ─── Dosug (Leisure) ───
    elif cmd == "dosug_menu":
        user_states.pop(user_id, None)
        from .keyboards import dosug_menu
        eos("🎯 Выберите раздел:", dosug_menu())
    elif cmd == "food_categories":
        cats = get_food_categories()
        cats.insert(0, {"id": None, "name": "📂 Вся доставка"})
        eos("🍔 Доставка еды:", category_list_kb(cats, "food"))
    elif cmd == "food_by_category":
        payload["cmd"] = "foods_list"
        handle_cmd(vk, payload, peer_id, user_id, user_name, cmid, msg_count)
    elif cmd == "foods_list":
        cid = payload.get("category_id")
        page = payload.get("page", 1)
        data = get_shops_by_type("food", category_id=cid, page=page)
        if not data["items"]:
            eos("Нет доставок.", back_to_menu()); return
        from .keyboards import shop_items_list_kb
        eos(f"🍔 Доставка (стр.{page}/{data['total_pages']}):",
            shop_items_list_kb(data["items"], page, data["total_pages"], "food"))
    elif cmd == "food_card":
        s = get_shop_by_id(payload.get("shop_id"))
        if not s:
            eos("Не найдена.", back_to_menu()); return
        from .keyboards import shop_item_card_kb
        owner = s.get("owner_vk_id")
        is_owner = bool(owner and owner == user_id)
        eos(fmt_shop(s), shop_item_card_kb(s["id"], "food", s.get("verified", False), is_owner), s.get("photo") or None)

    # ─── Performer menu ───
    elif cmd == "performer_menu":
        from .keyboards import performer_menu
        eos("👤 Для исполнителей:", performer_menu())
    elif cmd == "register_shop":
        user_states[user_id] = {"awaiting": "reg_shop_type"}
        eos("Выберите тип:\n1 - Магазин\n2 - Доставка еды\n\nНапишите 1 или 2:", back_to_menu())
    elif cmd == "my_shops":
        items = get_shops_by_owner(user_id)
        if not items:
            eos("У вас пока нет магазинов.", back_to_menu()); return
        text = "🏪 Ваши магазины/доставки:\n\n"
        for i in items:
            tick = "✅" if i["verified"] else "❌"
            text += f"{tick} {i['name']} — {stars(i['rating'])} {i['rating']}\n"
        eos(text.strip(), back_to_menu())
    elif cmd == "write_shop_review":
        user_states[user_id] = {"awaiting": "shop_review_text", "shop_id": payload["shop_id"], "shop_type": payload.get("shop_type", "shop"), "rating": payload["rating"]}
        eos("✍️ Напишите текст отзыва:", back_to_menu())
    elif cmd == "view_shop_reviews":
        sid = payload.get("shop_id")
        revs = get_reviews_for_shop(sid)
        if not revs:
            eos("У этого магазина пока нет отзывов.", back_to_menu()); return
        text = "💬 Отзывы:\n\n"
        for r in revs:
            text += f"{r['user_name']} — {stars(r['rating'])} {r['rating']}\n{r['text'][:100]}\n\n"
        eos(text.strip(), back_to_menu())
    elif cmd == "shop_verify":
        sid = payload["shop_id"]
        s = get_shop_by_id(sid)
        if not s or s.get("owner_vk_id") != user_id:
            eos("Это не ваш магазин.", back_to_menu()); return
        if s.get("verified"):
            eos("Уже проверен.", back_to_menu()); return
        user_states[user_id] = {"awaiting": "shop_verification_phone", "shop_id": sid}
        eos("📞 Введите ваш номер телефона:", back_to_menu())

    # ─── Jobs ───
    elif cmd == "job_menu":
        user_states[user_id] = {"context": "job"}
        from .keyboards import job_menu
        data = get_employers(page=1)
        if data["items"]:
            from .keyboards import employers_list_kb
            eos("💼 Работа:\n\nНапишите, кем вы хотите работать, чтобы найти подходящие вакансии:",
                employers_list_kb(data["items"], 1, data["total_pages"]))
        else:
            eos("💼 Работа:\n\nНапишите, кем вы хотите работать, чтобы найти подходящие вакансии:", job_menu())
    elif cmd == "job_list":
        page = payload.get("page", 1)
        data = get_employers(page=page)
        if not data["items"]:
            eos("Нет вакансий.", back_to_menu()); return
        from .keyboards import employers_list_kb
        eos(f"💼 Вакансии (стр.{page}/{data['total_pages']}):",
            employers_list_kb(data["items"], page, data["total_pages"]))
    elif cmd == "employer_card":
        eid = payload.get("employer_id")
        emp = get_employer_by_id(eid)
        if not emp:
            eos("Не найдена.", back_to_menu()); return
        from .keyboards import back_to_jobs
        phone = emp.get("phone", "")
        vk_page = emp.get("vk_page", "")
        contacts = emp.get("contacts", "")
        text = (
            f"💼 {emp['company_name']}\n\n"
            f"{emp['description']}\n\n"
            f"📞 {contacts}\n"
        )
        if phone:
            text += f"📱 {phone}\n"
        if vk_page:
            text += f"🔗 {vk_page}\n"
        text += f"\n=== ВАКАНСИЯ ===\n{emp['vacancy_text']}"
        eos(text, back_to_jobs())
    elif cmd == "register_employer":
        user_states[user_id] = {"awaiting": "emp_company"}
        eos("🏢 Введите название компании:", back_to_menu())


def route_text_intent(vk, peer_id, user_id, user_name, text, cmid):
    """Smart keyword routing from free text. Returns True if handled."""
    text_lower = text.lower()
    eos = lambda t, k=None, a=None: _edit_or_send(vk, peer_id, cmid, t, k, a)

    # ─── Contact admin ───
    admin_kw = ["админ", "администратор", "связаться", "поддержка", "жалоба", "вопрос"]
    if any(kw in text_lower for kw in admin_kw):
        user_states[user_id] = {"awaiting": "contact_message"}
        eos("📩 Напишите ваш вопрос:", back_to_menu())
        return True

    # ─── Job keywords ───
    job_kw = ["работа", "ваканс", "подработк", "трудоустройств", "зарплат", "устроиться", "заработат"]
    if any(kw in text_lower for kw in job_kw):
        user_states[user_id] = {"context": "job"}
        data = get_employers(page=1)
        if data["items"]:
            from .keyboards import employers_list_kb
            eos("💼 Работа:\n\nНапишите, кем вы хотите работать, чтобы найти подходящие вакансии:",
                employers_list_kb(data["items"], 1, data["total_pages"]))
        else:
            from .keyboards import job_menu
            eos("💼 Работа:\n\nНапишите, кем вы хотите работать, чтобы найти подходящие вакансии:", job_menu())
        return True

    # ─── Master/service keywords ───
    master_kw = ["мастер", "услуг", "ремонт", "починит", "сделать", "отремонтиров",
                 "почин", "настроит", "собер", "установ", "визаж", "парикмахер",
                 "маникюр", "косметолог", "ногт", "бров", "ресниц", "чистк",
                 "шугер", "депиляци", "массаж", "покраск"]
    if any(kw in text_lower for kw in master_kw):
        from .services import search_masters_by_keyword, get_master_categories
        masters = search_masters_by_keyword(text)
        if masters:
            total_pages = max(1, (len(masters) + 4) // 5)
            eos(f"🖍 Найдено {len(masters)} мастеров:",
                items_list_kb(masters[:5], 1, total_pages, "master"))
        else:
            cats = get_master_categories()
            cats.insert(0, {"id": None, "name": "📂 Все мастера"})
            eos("🖍 Категории мастеров:", category_list_kb(cats, "master", extra_buttons=[
                ("✅ Проверенные", {"cmd": "masters_verified"}),
            ]))
        return True

    # ─── Shop keywords ───
    shop_kw = ["магазин", "купить", "товар", "покупк", "досуг", "отдых", "развлек"]
    food_kw = ["доставк", "еда", "покушат", "заказат", "пицц", "суши", "бургер"]
    if any(kw in text_lower for kw in shop_kw):
        cats = get_shop_categories()
        cats.insert(0, {"id": None, "name": "📂 Все магазины"})
        eos("🏪 Магазины:", category_list_kb(cats, "shop"))
        return True
    if any(kw in text_lower for kw in food_kw):
        cats = get_food_categories()
        cats.insert(0, {"id": None, "name": "📂 Вся доставка"})
        eos("🍔 Доставка еды:", category_list_kb(cats, "food"))
        return True

    return False


def _edit_or_send(vk, peer_id, cmid, text, keyboard=None, attachment=None):
    if cmid:
        try:
            _edit(vk, peer_id, cmid, text, keyboard)
            return
        except Exception as e:
            logger.warning(f"_edit failed (peer={peer_id}, cmid={cmid}): {e}")
    _send(vk, peer_id, text, keyboard, attachment)
