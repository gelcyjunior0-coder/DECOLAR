"""db.py — conversa com o Supabase usando service_role (ignora RLS)."""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

import config

load_dotenv()
sb: Client = create_client(os.environ["SUPABASE_URL"],
                           os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def fetch_settings() -> dict:
    res = sb.table("app_settings").select("*").limit(1).execute()
    return res.data[0] if res.data else dict(config.DEFAULTS)


def fetch_active_competitors() -> list[dict]:
    res = (sb.table("hotels").select("id,name,url")
           .eq("active", True).eq("is_own_property", False).execute())
    return res.data or []


def create_run(trigger: str = "manual") -> str:
    return sb.table("scrape_runs").insert(
        {"status": "running", "trigger": trigger}).execute().data[0]["id"]


def finish_run(run_id: str, status: str, count: int, errors: list) -> None:
    sb.table("scrape_runs").update({
        "status": status,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "observations_count": count, "errors": errors,
    }).eq("id", run_id).execute()


def insert_observations(rows: list[dict]) -> None:
    if rows:
        sb.table("price_observations").upsert(
            rows, on_conflict="hotel_id,stay_date,category,scrape_run_id").execute()
