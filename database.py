import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import Optional

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

async def log_expense(phone: str, amount: float, category: str, description: str):
    try:
        supabase.table("expenses").insert({
            "phone": phone,
            "amount": amount,
            "category": category,
            "description": description,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print(f"DB error logging expense: {e}")

async def get_weekly_summary(phone: str) -> dict:
    try:
        since = (datetime.utcnow() - timedelta(days=7)).isoformat()
        result = supabase.table("expenses").select("amount, category").eq("phone", phone).gte("created_at", since).execute()
        return _build_summary(result.data)
    except Exception as e:
        print(f"DB error getting weekly summary: {e}")
        return {}

async def get_monthly_summary(phone: str) -> dict:
    try:
        now = datetime.utcnow()
        since = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
        result = supabase.table("expenses").select("amount, category").eq("phone", phone).gte("created_at", since).execute()
        return _build_summary(result.data)
    except Exception as e:
        print(f"DB error getting monthly summary: {e}")
        return {}

async def get_user_goal(phone: str) -> Optional[float]:
    try:
        result = supabase.table("user_goals").select("goal_amount").eq("phone", phone).execute()
        if result.data:
            return float(result.data[0]["goal_amount"])
        return None
    except Exception as e:
        print(f"DB error getting goal: {e}")
        return None

async def set_user_goal(phone: str, amount: float):
    try:
        existing = supabase.table("user_goals").select("id").eq("phone", phone).execute()
        if existing.data:
            supabase.table("user_goals").update({"goal_amount": amount, "updated_at": datetime.utcnow().isoformat()}).eq("phone", phone).execute()
        else:
            supabase.table("user_goals").insert({"phone": phone, "goal_amount": amount, "created_at": datetime.utcnow().isoformat()}).execute()
    except Exception as e:
        print(f"DB error setting goal: {e}")

async def get_user_language(phone: str) -> Optional[str]:
    try:
        result = supabase.table("user_preferences").select("language").eq("phone", phone).execute()
        if result.data:
            return result.data[0]["language"]
        return None
    except Exception as e:
        print(f"DB error getting language: {e}")
        return None

async def set_user_language(phone: str, language: Optional[str]):
    try:
        existing = supabase.table("user_preferences").select("id").eq("phone", phone).execute()
        if existing.data:
            supabase.table("user_preferences").update({"language": language, "updated_at": datetime.utcnow().isoformat()}).eq("phone", phone).execute()
        else:
            supabase.table("user_preferences").insert({"phone": phone, "language": language, "created_at": datetime.utcnow().isoformat()}).execute()
    except Exception as e:
        print(f"DB error setting language: {e}")

def _build_summary(data: list) -> dict:
    if not data:
        return {"total": 0, "count": 0, "by_category": {}}
    total = sum(row["amount"] for row in data)
    count = len(data)
    by_category = {}
    for row in data:
        cat = row["category"]
        by_category[cat] = round(by_category.get(cat, 0) + row["amount"], 2)
    by_category = dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True))
    return {"total": round(total, 2), "count": count, "by_category": by_category}
