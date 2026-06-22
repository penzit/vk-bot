from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .database import get_db
from .services import (
    get_categories, get_faq_by_category, get_faq_by_id, search_faq_by_keywords,
    get_master_categories, get_masters, get_master_by_id,
    get_reviews_for_master, create_review,
    get_shop_categories, get_food_categories, get_shops_by_type, get_shop_by_id,
    get_reviews_for_shop, create_shop_review,
    create_registration, create_shop_registration,
    create_verification_request, create_shop_verification_request,
    record_master_view, search_masters_by_keyword,
    get_employers, get_employer_by_id, search_employers_by_keyword, create_employer,
    create_ads_request, get_ads_requests, notify_admin_vk, get_recommended_masters,
    get_recommended_shops, get_recommended_employers,
    update_master, update_shop, update_employer,
    AD_OFFER_TEXT,
)
from .order_services import (
    register_order_performer, get_order_performer, update_order_performer,
    toggle_accepts_requests, set_performer_categories, get_performer_by_id,
    get_order_categories, create_order, get_order, get_active_orders, get_my_orders,
    get_performer_orders, respond_to_order, decline_order_response,
    select_performer, complete_order, cancel_order, delete_order, expire_old_orders,
    leave_order_review, get_performer_reviews, get_order_stats,
    notify_performers_new_order, notify_customer_response, notify_performer_selected,
    send_vk_message, URGENCY_OPTIONS,
)

router = APIRouter(prefix="/api")


class ReviewCreate(BaseModel):
    master_id: int
    user_id: int
    user_name: str
    text: str
    rating: int


class RegistrationCreate(BaseModel):
    user_id: int
    user_name: str
    name: str
    description: str
    contacts: str
    category_id: Optional[int] = None
    photo: str = ""


class ShopRegistrationCreate(BaseModel):
    user_id: int
    user_name: str
    shop_type: str
    name: str
    description: str
    contacts: str
    category_id: Optional[int] = None
    photo: str = ""


class ShopReviewCreate(BaseModel):
    shop_id: int
    user_id: int
    user_name: str
    text: str
    rating: int
    target_type: str = "shop"


class VerificationCreate(BaseModel):
    target_id: int
    user_id: int
    phone: str
    documents_info: str


class EmployerCreate(BaseModel):
    user_id: int
    user_name: str
    company_name: str
    description: str = ""
    phone: str = ""
    vk_page: str = ""
    contacts: str = ""
    vacancy_text: str
    photo: str = ""


class AdsRequestCreate(BaseModel):
    user_id: int
    user_name: str = ""
    message_text: str
    message_type: str = "ad"


@router.get("/masters")
def api_masters(
    category_id: Optional[int] = None,
    verified_only: bool = False,
    search: Optional[str] = None,
    page: int = 1,
):
    if search:
        results = search_masters_by_keyword(search)
        return {"items": results, "total": len(results), "page": 1, "total_pages": 1}
    return get_masters(category_id=category_id, verified_only=verified_only, page=page)


@router.get("/masters/recommended")
def api_recommended_masters():
    return {"items": get_recommended_masters()}


@router.get("/masters/{master_id}")
def api_master_detail(master_id: int):
    m = get_master_by_id(master_id)
    if not m:
        raise HTTPException(404, "Master not found")
    record_master_view(master_id)
    m["views_count"] = get_master_by_id(master_id)["views_count"]
    return m


@router.get("/masters/{master_id}/reviews")
def api_master_reviews(master_id: int):
    return get_reviews_for_master(master_id)


@router.post("/reviews")
def api_create_review(review: ReviewCreate):
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(400, "Rating must be 1-5")
    rid = create_review(review.master_id, review.user_id, review.user_name, review.text, review.rating)
    return {"id": rid, "status": "pending"}


@router.get("/master_categories")
def api_master_categories():
    return get_master_categories()


@router.get("/shop_categories")
def api_shop_categories():
    return get_shop_categories()


@router.get("/shops")
def api_shops(
    shop_type: str = "shop",
    category_id: Optional[int] = None,
    page: int = 1,
):
    return get_shops_by_type(shop_type, category_id=category_id, page=page)


@router.get("/shops/recommended")
def api_recommended_shops(shop_type: str = "shop"):
    return {"items": get_recommended_shops(shop_type)}


@router.post("/register")
def api_register_master(reg: RegistrationCreate):
    rid = create_registration(reg.user_id, reg.user_name, reg.name, reg.description, reg.contacts, reg.category_id, reg.photo)
    return {"id": rid, "status": "pending"}


@router.post("/register_shop")
def api_register_shop(reg: ShopRegistrationCreate):
    from .services import create_shop_registration
    rid = create_shop_registration(
        reg.user_id, reg.user_name, reg.shop_type,
        reg.name, reg.description, reg.contacts, reg.category_id, reg.photo
    )
    return {"id": rid, "status": "pending"}


@router.get("/food_categories")
def api_food_categories():
    return get_food_categories()


@router.get("/shops/{shop_id}")
def api_shop_detail(shop_id: int):
    s = get_shop_by_id(shop_id)
    if not s:
        raise HTTPException(404, "Shop not found")
    return s


@router.get("/shops/{shop_id}/reviews")
def api_shop_reviews(shop_id: int):
    return get_reviews_for_shop(shop_id)


@router.post("/shop_reviews")
def api_create_shop_review(review: ShopReviewCreate):
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(400, "Rating must be 1-5")
    if review.target_type not in ("shop", "food"):
        raise HTTPException(400, "Invalid target_type")
    rid = create_shop_review(review.shop_id, review.user_id, review.user_name, review.text, review.rating, review.target_type)
    return {"id": rid, "status": "pending"}


@router.post("/verify_master")
def api_verify_master(req: VerificationCreate):
    rid = create_verification_request(req.target_id, req.user_id, req.phone, req.documents_info)
    return {"id": rid, "status": "pending"}


@router.post("/verify_shop")
def api_verify_shop(req: VerificationCreate):
    rid = create_shop_verification_request(req.target_id, req.user_id, req.phone, req.documents_info)
    return {"id": rid, "status": "pending"}


@router.get("/employers")
def api_employers(search: Optional[str] = None, page: int = 1):
    if search:
        results = search_employers_by_keyword(search)
        return {"items": results, "total": len(results), "page": 1, "total_pages": 1}
    return get_employers(page=page)


@router.get("/employers/recommended")
def api_recommended_employers():
    return {"items": get_recommended_employers()}


@router.get("/employers/{emp_id}")
def api_employer_detail(emp_id: int):
    emp = get_employer_by_id(emp_id)
    if not emp:
        raise HTTPException(404, "Employer not found")
    return emp


@router.post("/register_employer")
def api_register_employer(reg: EmployerCreate):
    rid = create_employer(
        reg.user_id, reg.user_name, reg.company_name, reg.description,
        reg.phone, reg.vk_page, reg.contacts, reg.vacancy_text, reg.photo,
    )
    return {"id": rid, "status": "pending"}


@router.get("/ads_offer")
def api_ads_offer():
    return {"text": AD_OFFER_TEXT}


@router.post("/ads_request")
def api_ads_request(req: AdsRequestCreate):
    if req.message_type not in ("ad", "contact"):
        raise HTTPException(400, "Invalid message_type")
    rid = create_ads_request(req.user_id, req.user_name, req.message_text, req.message_type)
    label = "\u0420\u0435\u043a\u043b\u0430\u043c\u0430" if req.message_type == "ad" else "\u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0430\u0434\u043c\u0438\u043d\u0443"
    notify_admin_vk(f"{label} #{rid}\n\u041e\u0442: {req.user_name or req.user_id}\nvk.com/id{req.user_id}\n\n{req.message_text}")
    return {"id": rid, "status": "new"}


@router.get("/sections")
def api_sections():
    return {
        "sections": [
            {"id": "guide", "title": "\u0421\u043f\u0440\u0430\u0432\u043e\u0447\u043d\u0438\u043a", "categories": get_categories()},
            {"id": "masters", "title": "\u0423\u0441\u043b\u0443\u0433\u0438", "categories": get_master_categories()},
            {"id": "leisure", "title": "\u0414\u043e\u0441\u0443\u0433", "categories": [
                {"id": "shops", "name": "\u041c\u0430\u0433\u0430\u0437\u0438\u043d\u044b", "children": get_shop_categories()},
                {"id": "food", "name": "\u0414\u043e\u0441\u0442\u0430\u0432\u043a\u0430 \u0435\u0434\u044b", "children": get_food_categories()},
            ]},
            {"id": "jobs", "title": "\u0420\u0430\u0431\u043e\u0442\u0430", "categories": []},
            {"id": "ads", "title": "\u0420\u0435\u043a\u043b\u0430\u043c\u0430", "categories": []},
            {"id": "admin", "title": "\u0410\u0434\u043c\u0438\u043d", "categories": []},
            {"id": "performers", "title": "\u0418\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u0438", "categories": [
                {"id": "master", "name": "\u0427\u0430\u0441\u0442\u043d\u044b\u0439 \u043c\u0430\u0441\u0442\u0435\u0440"},
                {"id": "shop", "name": "\u041c\u0430\u0433\u0430\u0437\u0438\u043d"},
                {"id": "food", "name": "\u0414\u043e\u0441\u0442\u0430\u0432\u043a\u0430"},
            ]},
        ]
    }


@router.get("/faq_categories")
def api_faq_categories():
    return get_categories()


@router.get("/faq")
def api_faq(category_id: Optional[int] = None, search: Optional[str] = None):
    if search:
        return search_faq_by_keywords(search)
    if category_id:
        items = get_faq_by_category(category_id)
        return [get_faq_by_id(item["id"]) for item in items]
    rows = []
    for cat in get_categories():
        for item in get_faq_by_category(cat["id"]):
            row = get_faq_by_id(item["id"])
            if row:
                row["category_name"] = cat["name"]
                rows.append(row)
    return rows


@router.get("/ads_banners")
def api_ads_banners():
    requests = get_ads_requests(status="new")[:5]
    return {
        "offer": AD_OFFER_TEXT,
        "items": [
            {
                "id": item["id"],
                "title": item["user_name"] or "\u0420\u0435\u043a\u043b\u0430\u043c\u0430",
                "text": item["message_text"],
                "status": item["status"],
                "created_at": item["created_at"],
            }
            for item in requests
        ],
    }


class MasterUpdate(BaseModel):
    owner_vk_id: int
    name: str = ""
    description: str = ""
    contacts: str = ""
    photo: str = ""
    category_id: Optional[int] = None


class ShopUpdate(BaseModel):
    owner_vk_id: int
    name: str = ""
    description: str = ""
    contacts: str = ""
    photo: str = ""
    category_id: Optional[int] = None


class EmployerUpdate(BaseModel):
    user_id: int
    description: str = ""
    phone: str = ""
    vk_page: str = ""
    contacts: str = ""
    vacancy_text: str = ""
    photo: str = ""


@router.put("/masters/{master_id}")
def api_update_master(master_id: int, data: MasterUpdate):
    ok = update_master(master_id, data.owner_vk_id, data.name or None, data.description or None,
                       data.contacts or None, data.photo if data.photo else None, data.category_id)
    if not ok:
        raise HTTPException(403, "Not authorized or not found")
    return {"status": "ok"}


@router.put("/shops/{shop_id}")
def api_update_shop(shop_id: int, data: ShopUpdate):
    ok = update_shop(shop_id, data.owner_vk_id, data.name or None, data.description or None,
                     data.contacts or None, data.photo if data.photo else None, data.category_id)
    if not ok:
        raise HTTPException(403, "Not authorized or not found")
    return {"status": "ok"}


@router.put("/employers/{emp_id}")
def api_update_employer(emp_id: int, data: EmployerUpdate):
    ok = update_employer(emp_id, data.user_id, data.description or None, data.phone or None,
                         data.vk_page or None, data.contacts or None, data.vacancy_text or None,
                         data.photo if data.photo else None)
    if not ok:
        raise HTTPException(403, "Not authorized or not found")
    return {"status": "ok"}


@router.get("/my_items")
def api_my_items(user_id: int):
    with get_db() as db:
        masters = db.execute(
            "SELECT id, name, description, contacts, photo, category_id FROM masters WHERE owner_vk_id=?",
            (user_id,)
        ).fetchall()
        shops = db.execute(
            "SELECT id, name, description, contacts, photo, category_id, shop_type FROM shops WHERE owner_vk_id=?",
            (user_id,)
        ).fetchall()
        employers_rows = db.execute(
            "SELECT id, company_name, description, phone, vk_page, contacts, vacancy_text, photo FROM employers WHERE user_id=? AND status='approved'",
            (user_id,)
        ).fetchall()
    return {
        "masters": [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3], "photo": r[4], "category_id": r[5]} for r in masters],
        "shops": [{"id": r[0], "name": r[1], "description": r[2], "contacts": r[3], "photo": r[4], "category_id": r[5], "shop_type": r[6]} for r in shops],
        "employers": [{"id": r[0], "company_name": r[1], "description": r[2], "phone": r[3], "vk_page": r[4], "contacts": r[5], "vacancy_text": r[6], "photo": r[7]} for r in employers_rows],
    }


@router.get("/moderation_status")
def api_moderation_status(user_id: int):
    with get_db() as db:
        masters = db.execute(
            "SELECT id, name, status, created_at FROM master_registrations WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        shops = db.execute(
            "SELECT id, name, shop_type, status, created_at FROM shop_registrations WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        employers = db.execute(
            "SELECT id, company_name, status, created_at FROM employers WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return {
        "items":
            [{"id": r[0], "type": "master", "name": r[1], "status": r[2], "created_at": r[3]} for r in masters] +
            [{"id": r[0], "type": r[2], "name": r[1], "status": r[3], "created_at": r[4]} for r in shops] +
            [{"id": r[0], "type": "job", "name": r[1], "status": r[2], "created_at": r[3]} for r in employers]
    }


# ─── ORDER BOARD (Биржа заявок) ────────────────────────

class OrderCreate(BaseModel):
    user_vk_id: int
    user_name: str = ""
    category_id: int
    description: str
    urgency: str = "Не срочно"
    address: str = ""
    contact: str
    photo_url: str = ""
    desired_time: str = ""
    comment: str = ""


class PerformerRegister(BaseModel):
    vk_id: int
    name: str
    contact: str = ""
    description: str = ""


class PerformerUpdate(BaseModel):
    vk_id: int
    name: str = ""
    contact: str = ""
    description: str = ""


class PerformerCategoriesUpdate(BaseModel):
    vk_id: int
    category_ids: List[int]


class OrderResponseCreate(BaseModel):
    performer_id: int
    message: str = ""


class OrderReviewCreate(BaseModel):
    customer_vk_id: int
    performer_id: int
    rating: int
    text: str = ""


@router.get("/order_categories")
def api_order_categories():
    return get_order_categories()


@router.get("/order_urgency_options")
def api_order_urgency():
    return URGENCY_OPTIONS


@router.post("/orders")
def api_create_order(order: OrderCreate):
    oid, err = create_order(order.user_vk_id, order.user_name, order.category_id,
                            order.description, order.urgency, order.address, order.contact,
                            order.photo_url, order.desired_time, order.comment)
    if err:
        raise HTTPException(400, err)
    try:
        expire_old_orders()
        notify_performers_new_order(oid)
    except Exception:
        pass
    return {"id": oid, "status": "new"}


@router.get("/orders")
def api_list_orders(category_id: Optional[int] = None, page: int = 1):
    return get_active_orders(category_id=category_id, page=page)


@router.get("/orders/my")
def api_my_orders(user_vk_id: int):
    return get_my_orders(user_vk_id)


@router.get("/orders/performer")
def api_performer_orders(vk_id: int):
    return get_performer_orders(vk_id)


@router.get("/orders/stats")
def api_order_stats():
    return get_order_stats()


@router.get("/orders/expire/run")
def api_expire_orders():
    expire_old_orders()
    return {"status": "ok"}


@router.get("/orders/{order_id}")
def api_order_detail(order_id: int):
    o = get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    return o


@router.post("/orders/{order_id}/respond")
def api_respond_order(order_id: int, data: OrderResponseCreate):
    ok, err = respond_to_order(order_id, data.performer_id, data.message)
    if not ok:
        raise HTTPException(400, err)
    try:
        notify_customer_response(order_id)
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/orders/{order_id}/decline")
def api_decline_order(order_id: int, performer_id: int):
    decline_order_response(order_id, performer_id)
    return {"status": "ok"}


@router.post("/orders/{order_id}/select")
def api_select_performer(order_id: int, response_id: int):
    ok = select_performer(order_id, response_id)
    if not ok:
        raise HTTPException(400, "Invalid")
    try:
        o = get_order(order_id)
        if o and o["selected_performer_id"]:
            p = get_performer_by_id(o["selected_performer_id"])
            if p:
                notify_performer_selected(order_id, p["vk_id"])
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/orders/{order_id}/complete")
def api_complete_order(order_id: int, user_vk_id: int):
    ok = complete_order(order_id, user_vk_id)
    if not ok:
        raise HTTPException(400, "Cannot complete")
    return {"status": "ok"}


@router.post("/orders/{order_id}/cancel")
def api_cancel_order(order_id: int, user_vk_id: int):
    ok = cancel_order(order_id, user_vk_id)
    if not ok:
        raise HTTPException(400, "Cannot cancel")
    return {"status": "ok"}


@router.delete("/orders/{order_id}")
def api_delete_order(order_id: int):
    delete_order(order_id)
    return {"status": "ok"}


@router.post("/orders/{order_id}/review")
def api_review_order(order_id: int, data: OrderReviewCreate):
    ok = leave_order_review(order_id, data.customer_vk_id, data.performer_id, data.rating, data.text)
    if not ok:
        raise HTTPException(400, "Cannot review")
    return {"status": "ok"}


# ─── PERFORMERS ─────────────────────────────────────────

@router.post("/performers/register")
def api_register_performer(data: PerformerRegister):
    pid = register_order_performer(data.vk_id, data.name, data.contact, data.description)
    return {"id": pid, "status": "ok"}


@router.get("/performers/me")
def api_my_performer_profile(vk_id: int):
    p = get_order_performer(vk_id)
    if not p:
        raise HTTPException(404, "Not registered")
    return p


@router.put("/performers/me")
def api_update_performer(data: PerformerUpdate):
    update_order_performer(data.vk_id, data.name or None, data.contact or None, data.description or None)
    return {"status": "ok"}


@router.put("/performers/me/categories")
def api_set_performer_categories(data: PerformerCategoriesUpdate):
    set_performer_categories(data.vk_id, data.category_ids)
    return {"status": "ok"}


@router.post("/performers/me/toggle")
def api_toggle_performer(vk_id: int):
    accepts = toggle_accepts_requests(vk_id)
    return {"accepts_requests": accepts}


@router.get("/performers/{performer_id}")
def api_get_performer(performer_id: int):
    p = get_performer_by_id(performer_id)
    if not p:
        raise HTTPException(404, "Not found")
    return p


@router.get("/performers/{performer_id}/reviews")
def api_performer_reviews(performer_id: int):
    return get_performer_reviews(performer_id)


@router.get("/performers")
def api_list_performers():
    from .order_services import get_pending_performers
    return get_pending_performers()


@router.post("/orders/notify")
def api_send_order_message(user_id: int, text: str):
    ok = send_vk_message(user_id, text)
    return {"sent": ok}
