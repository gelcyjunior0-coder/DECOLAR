"""
main.py — orquestra a captura na Decolar (pensado para rodar no GitHub Actions).

Uso:
  python main.py                 # captura a janela inteira
  python main.py --trigger cron  # marca como agendado
"""
import argparse
import random
import sys
import time
from datetime import date, timedelta

from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

import config
import db
import scraper


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trigger", choices=["manual", "cron"], default="manual")
    args = ap.parse_args()

    settings = db.fetch_settings()
    hotels = db.fetch_active_competitors()
    if not hotels:
        print("Nenhum concorrente ativo. Cadastre em hotels e preencha 'url' (Decolar).")
        sys.exit(1)

    start = date.fromisoformat(str(settings["window_start"]))
    end = date.fromisoformat(str(settings["window_end"]))
    currency = settings["currency"]

    run_id = db.create_run(trigger=args.trigger)
    print(f"Run {run_id} | {len(hotels)} hotéis | {start} -> {end}")

    total, errors = 0, []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=config.HEADLESS,
            args=["--disable-http2", "--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=config.USER_AGENT, locale="pt-BR",
            timezone_id="America/Sao_Paulo", viewport={"width": 1366, "height": 900},
            extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page = ctx.new_page()

        @retry(stop=stop_after_attempt(config.MAX_RETRIES),
               wait=wait_exponential(multiplier=2, min=2, max=30), reraise=True)
        def one(hotel, day):
            return scraper.scrape_hotel_date(page, hotel, day, run_id, currency)

        try:
            for hotel in hotels:
                if not hotel.get("url"):
                    errors.append({"hotel": hotel["name"], "date": None, "reason": "url vazia"})
                    continue
                for day in daterange(start, end):
                    try:
                        rows = one(hotel, day)
                        db.insert_observations(rows)
                        total += len(rows)
                        avail = sum(1 for r in rows if r["available"])
                        print(f"  ok  {hotel['name']:<34} {day}  ({avail}/3)")
                    except Exception as e:
                        errors.append({"hotel": hotel["name"], "date": day.isoformat(),
                                       "reason": str(e)[:300]})
                        print(f"  ERR {hotel['name']:<34} {day}  -> {str(e)[:70]}")
                    time.sleep(random.uniform(config.REQUEST_MIN_DELAY, config.REQUEST_MAX_DELAY))
        finally:
            browser.close()

    status = "failed" if total == 0 else ("partial" if errors else "success")
    db.finish_run(run_id, status, total, errors)
    print(f"Run {run_id} -> {status} | {total} observações | {len(errors)} erros")


if __name__ == "__main__":
    main()
