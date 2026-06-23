import json


def _btn(label, payload, color="primary"):
    return {"action": {"type": "callback", "label": label, "payload": json.dumps(payload, ensure_ascii=False)}, "color": color}


def _open_app_btn(label, app_id, hash=""):
    return {"action": {"type": "open_app", "label": label, "app_id": app_id, "hash": hash}}


def main_menu(app_id):
    return {"inline": False, "buttons": [
        [_open_app_btn("Открыть", app_id)],
    ]}


def back_to_menu():
    return {"inline": True, "buttons": [
        [_btn("⬅ Назад в меню", {"cmd": "main_menu"}, "secondary")],
    ]}


def faq_categories_kb(categories):
    buttons = [[_btn(c["name"], {"cmd": "faq_questions", "category_id": c["id"]})] for c in categories]
    buttons.append([_btn("⬅ Меню", {"cmd": "main_menu"}, "secondary")])
    return {"inline": True, "buttons": buttons}


def faq_questions_kb(questions, category_id):
    buttons = []
    for q in questions:
        label = q["question"][:40] + ("…" if len(q["question"]) > 40 else "")
        buttons.append([_btn(label, {"cmd": "faq_answer", "faq_id": q["id"]}, "secondary")])
    buttons.append([_btn("⬅ Категории", {"cmd": "faq_categories"}, "secondary"),
                    _btn("Меню", {"cmd": "main_menu"}, "secondary")])
    return {"inline": True, "buttons": buttons}


def back_to_questions(category_id):
    return {"inline": True, "buttons": [
        [_btn("⬅ Вопросы", {"cmd": "faq_questions", "category_id": category_id}),
         _btn("Меню", {"cmd": "main_menu"}, "secondary")],
    ]}


def category_list_kb(categories, item_type, extra_buttons=None):
    buttons = []
    for c in categories:
        cmd = f"{item_type}_by_category"
        buttons.append([_btn(c["name"][:30], { "cmd": cmd, "category_id": c["id"] })])
    nav = []
    if extra_buttons:
        for label, payload in extra_buttons:
            nav.append(_btn(label, payload, "positive"))
    nav.append(_btn("⬅ В меню", {"cmd": "main_menu"}, "secondary"))
    buttons.append(nav)
    return {"inline": True, "buttons": buttons}


def items_list_kb(items, page, total_pages, item_type, verified_mode=False):
    buttons = []
    id_key = f"{item_type}_id"
    cmd = "master_card" if item_type == "master" else "shop_card"
    for it in items:
        label = it["name"][:40] + ("…" if len(it["name"]) > 40 else "")
        b = "✅ " if it.get("verified") else ""
        buttons.append([_btn(b + label, { "cmd": cmd, id_key: it["id"] }, "secondary")])

    nav = []
    if page > 1:
        nav.append(_btn("⬅", { "cmd": f"{item_type}s_list", "page": page - 1 }, "secondary"))
    if page < total_pages:
        nav.append(_btn("➡", { "cmd": f"{item_type}s_list", "page": page + 1 }, "secondary"))
    if nav:
        buttons.append(nav)

    bottom = []
    if verified_mode:
        bottom.append(_btn("Проверенные", {"cmd": "masters_verified"}, "primary"))
    else:
        bottom.append(_btn("Категории", {"cmd": f"{item_type}_categories"}, "primary"))
    bottom.append(_btn("Меню", {"cmd": "main_menu"}, "secondary"))
    buttons.append(bottom)
    return {"inline": True, "buttons": buttons}


def item_card_kb(item_id, item_type, verified=False, is_owner=False):
    back_cmd = f"{item_type}s_list"
    back_label = "⬅ Назад"

    buttons = []
    if item_type == "master":
        buttons.append([_btn("⭐ Оценить и оставить отзыв", {"cmd": "start_review", "master_id": item_id}, "primary")])
        buttons.append([_btn("💬 Отзывы", {"cmd": "view_reviews", "master_id": item_id}, "secondary")])
        buttons.append([_btn("📞 Показать контакты", {"cmd": "show_master_contacts", "master_id": item_id}, "primary")])
        if is_owner and not verified:
            buttons.append([_btn("✅ Стать проверенным", {"cmd": "master_verify", "master_id": item_id}, "positive")])
    else:
        buttons.append([
            _btn("⭐ 1", { "cmd": "rate_shop", "shop_id": item_id, "rating": 1 }),
            _btn("⭐ 2", { "cmd": "rate_shop", "shop_id": item_id, "rating": 2 }),
            _btn("⭐ 3", { "cmd": "rate_shop", "shop_id": item_id, "rating": 3 }),
            _btn("⭐ 4", { "cmd": "rate_shop", "shop_id": item_id, "rating": 4 }),
            _btn("⭐ 5", { "cmd": "rate_shop", "shop_id": item_id, "rating": 5 }),
        ])

    buttons.append([_btn(back_label, {"cmd": back_cmd, "page": 1}, "secondary"),
                    _btn("Меню", {"cmd": "main_menu"}, "secondary")])
    return {"inline": True, "buttons": buttons}


def rating_kb(master_id):
    return {"inline": True, "buttons": [
        [_btn("⭐ 1", {"cmd": "set_review_rating", "master_id": master_id, "rating": 1}),
         _btn("⭐ 2", {"cmd": "set_review_rating", "master_id": master_id, "rating": 2}),
         _btn("⭐ 3", {"cmd": "set_review_rating", "master_id": master_id, "rating": 3}),
         _btn("⭐ 4", {"cmd": "set_review_rating", "master_id": master_id, "rating": 4}),
         _btn("⭐ 5", {"cmd": "set_review_rating", "master_id": master_id, "rating": 5})],
        [_btn("⬅ Отмена", {"cmd": "main_menu"}, "secondary")],
    ]}


def my_services_kb(items):
    buttons = [[_btn(it["name"][:40], {"cmd": "master_card", "master_id": it["id"]}, "secondary")] for it in items]
    buttons.append([_btn("⬅ В меню", {"cmd": "main_menu"}, "secondary")])
    return {"inline": True, "buttons": buttons}


def reg_cats_kb(categories):
    buttons = [[_btn(c["name"], {"cmd": "reg_select_cat", "category_id": c["id"]})] for c in categories]
    buttons.append([_btn("⬅ Отмена", {"cmd": "main_menu"}, "secondary")])
    if len(buttons) > 5:
        buttons[-2].append(_btn("⬅ Отмена", {"cmd": "main_menu"}, "secondary"))
        buttons.pop()
    return {"inline": True, "buttons": buttons}


def ad_offer_kb():
    return {"inline": True, "buttons": [
        [_btn("250₽ Объявление", {"cmd": "ad_request", "ad_type": "Обычное объявление — 250 ₽"}),
         _btn("300₽ Репост", {"cmd": "ad_request", "ad_type": "Репост из сообщества — 300 ₽"})],
        [_btn("400₽ Ссылка", {"cmd": "ad_request", "ad_type": "Объявление со ссылкой — 400 ₽"}),
         _btn("400₽ Сторис", {"cmd": "ad_request", "ad_type": "Реклама в сторис (24ч) — 400 ₽"})],
        [_btn("550₽ Сторис+Пост", {"cmd": "ad_request", "ad_type": "Сторис + пост — 550 ₽"})],
        [_btn("⬅ В меню", {"cmd": "main_menu"}, "secondary")],
    ]}


def performer_menu():
    return {"inline": True, "buttons": [
        [_btn("📝 Зарегистрировать услуги", {"cmd": "register_service"})],
        [_btn("📋 Мои услуги", {"cmd": "my_services"})],
        [_btn("🏪 Зарегистрировать магазин", {"cmd": "register_shop"})],
        [_btn("📋 Мои магазины", {"cmd": "my_shops"})],
        [_btn("⬅ В меню", {"cmd": "main_menu"}, "secondary")],
    ]}


def dosug_menu():
    return {"inline": True, "buttons": [
        [_btn("🏪 Магазины", {"cmd": "shop_categories"})],
        [_btn("🍔 Доставка еды", {"cmd": "food_categories"})],
        [_btn("⬅ В меню", {"cmd": "main_menu"}, "secondary")],
    ]}


def job_menu():
    return {"inline": True, "buttons": [
        [_btn("💼 Список вакансий", {"cmd": "job_list"})],
        [_btn("📝 Зарегистрировать работодателя", {"cmd": "register_employer"})],
        [_btn("⬅ В меню", {"cmd": "main_menu"}, "secondary")],
    ]}


def back_to_jobs():
    return {"inline": True, "buttons": [
        [_btn("⬅ К вакансиям", {"cmd": "job_list"}, "secondary"),
         _btn("Меню", {"cmd": "main_menu"}, "secondary")],
    ]}


def shop_item_card_kb(shop_id, shop_type, verified=False, is_owner=False):
    buttons = []
    buttons.append([
        _btn("⭐ 1", {"cmd": "write_shop_review", "shop_id": shop_id, "rating": 1, "shop_type": shop_type}),
        _btn("⭐ 2", {"cmd": "write_shop_review", "shop_id": shop_id, "rating": 2, "shop_type": shop_type}),
        _btn("⭐ 3", {"cmd": "write_shop_review", "shop_id": shop_id, "rating": 3, "shop_type": shop_type}),
        _btn("⭐ 4", {"cmd": "write_shop_review", "shop_id": shop_id, "rating": 4, "shop_type": shop_type}),
        _btn("⭐ 5", {"cmd": "write_shop_review", "shop_id": shop_id, "rating": 5, "shop_type": shop_type}),
    ])
    buttons.append([_btn("💬 Отзывы", {"cmd": "view_shop_reviews", "shop_id": shop_id}, "secondary")])
    if is_owner and not verified:
        buttons.append([_btn("✅ Стать проверенным", {"cmd": "shop_verify", "shop_id": shop_id}, "positive")])
    buttons.append([_btn("⬅ Назад", {"cmd": f"{shop_type}_categories"}, "secondary"),
                    _btn("Меню", {"cmd": "main_menu"}, "secondary")])
    return {"inline": True, "buttons": buttons}


def employers_list_kb(items, page, total_pages):
    buttons = []
    for it in items:
        label = it["company_name"][:40] + ("…" if len(it["company_name"]) > 40 else "")
        buttons.append([_btn("💼 " + label, {"cmd": "employer_card", "employer_id": it["id"]}, "secondary")])
    nav = []
    if page > 1:
        nav.append(_btn("⬅", {"cmd": "job_list", "page": page - 1}, "secondary"))
    if page < total_pages:
        nav.append(_btn("➡", {"cmd": "job_list", "page": page + 1}, "secondary"))
    if nav:
        buttons.append(nav)
    buttons.append([_btn("⬅ В меню", {"cmd": "main_menu"}, "secondary")])
    return {"inline": True, "buttons": buttons}


def shop_items_list_kb(items, page, total_pages, shop_type):
    buttons = []
    for it in items:
        label = it["name"][:40] + ("…" if len(it["name"]) > 40 else "")
        b = "✅ " if it.get("verified") else ""
        buttons.append([_btn(b + label, {"cmd": f"{shop_type}_card", f"{shop_type}_id": it["id"]}, "secondary")])
    nav = []
    if page > 1:
        nav.append(_btn("⬅", {"cmd": f"{shop_type}s_list", "page": page - 1}, "secondary"))
    if page < total_pages:
        nav.append(_btn("➡", {"cmd": f"{shop_type}s_list", "page": page + 1}, "secondary"))
    if nav:
        buttons.append(nav)
    buttons.append([_btn("Категории", {"cmd": f"{shop_type}_categories"}, "primary"),
                    _btn("Меню", {"cmd": "main_menu"}, "secondary")])
    return {"inline": True, "buttons": buttons}
