"""
scraper.py — captura de preços na Decolar.

Estratégia: o Playwright abre a página, aceita cookies, clica em "Veja mais opções"
(que carrega os quartos por JS) e então pega o HTML completo. O parser é o MESMO usado
no test_extract.py (offline), então o que você validar no sample vale para a captura real.
"""
import re
from collections import defaultdict
from datetime import date, timedelta

import config


# --------------------------------------------------------------------------- parse
def _strip(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&amp;", "&").replace("&#x27;", "'")
    s = re.sub(r"&#\d+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_price(text: str):
    m = re.search(r"R\$\s*([\d\.]+)", text or "")
    return float(m.group(1).replace(".", "")) if m else None


def classify(name: str) -> dict:
    n = " " + (name or "").lower() + " "
    return {
        "ocean": any(k in n for k in config.OCEAN_KEYWORDS),
        "suite": any(k in n for k in config.SUITE_KEYWORDS),
    }


def parse_rooms(html: str) -> dict:
    """Do HTML completo da página, devolve {nome_do_quarto: menor_preço}."""
    names = [(m.start(), _strip(m.group(1)))
             for m in re.finditer(r'class="[^"]*room-name[^"]*"[^>]*>(.*?)</', html, re.S)]
    prices = [(m.start(), parse_price(m.group(0)))
              for m in re.finditer(config.PRICE_MARKER + r":?\s*R\$\s*[\d\.]+", html)]
    room_min: dict = defaultdict(lambda: float("inf"))
    for ppos, val in prices:
        if val is None:
            continue
        preceding = [n for pos, n in names if pos < ppos]
        if preceding:
            room_min[preceding[-1]] = min(room_min[preceding[-1]], val)
    return dict(room_min)


def derive_categories(room_min: dict) -> dict:
    def cheapest(filter_fn=lambda n: True):
        vals = [v for n, v in room_min.items() if filter_fn(n)]
        if not vals:
            return None
        name = min(room_min.items(), key=lambda kv: kv[1] if filter_fn(kv[0]) else float("inf"))
        # garante que o nome escolhido satisfaz o filtro
        cand = {n: v for n, v in room_min.items() if filter_fn(n)}
        bn = min(cand, key=cand.get)
        return {"room_name": bn, "price": cand[bn]}
    return {
        "cheapest_overall": cheapest(),
        "ocean_view": cheapest(lambda n: classify(n)["ocean"]),
        "suite": cheapest(lambda n: classify(n)["suite"]),
    }


# --------------------------------------------------------------------------- live
def build_url(base_url: str, checkin: date, checkout: date, adults: int = 1) -> str:
    """
    Monta a URL da Decolar para a data-alvo, LIMPANDO o lixo de sessão.
    Formato: /accommodations/detail/{ID}/{checkin}/{checkout}/{hospedes}?currency=BRL
    - troca as duas datas AAAA-MM-DD do caminho;
    - ajusta o número de hóspedes para `adults`;
    - remove searchId, selected_room_pack, user_searched_gid, throughResults, etc.
    """
    from urllib.parse import urlparse, urlunparse

    parts = urlparse(base_url)
    segs = parts.path.split("/")
    date_idx = [i for i, s in enumerate(segs) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)]
    if len(date_idx) >= 2:
        segs[date_idx[0]] = checkin.isoformat()
        segs[date_idx[1]] = checkout.isoformat()
        g = date_idx[1] + 1                       # segmento de hóspedes vem após o checkout
        if g < len(segs) and segs[g].isdigit():
            segs[g] = str(adults)
        new_path = "/".join(segs)
        return urlunparse((parts.scheme, parts.netloc, new_path, "", "currency=BRL", ""))

    # fallback (URL fora do padrão esperado): só troca datas no texto
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", base_url)
    url = base_url
    if len(dates) >= 2:
        url = url.replace(dates[0], checkin.isoformat(), 1).replace(dates[1], checkout.isoformat(), 1)
    return url


def dismiss_cookies(page) -> None:
    for sel in config.SELECTORS["cookie_btns"]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click(timeout=4000)
                page.wait_for_timeout(800)
                return
        except Exception:
            continue


def expand_rooms(page) -> None:
    """Clica em 'Veja mais opções' (uma ou mais vezes) para carregar todos os quartos."""
    for _ in range(4):
        try:
            btn = page.locator(config.SELECTORS["view_more"]).first
            if btn.count() == 0 or not btn.is_visible():
                return
            btn.scroll_into_view_if_needed(timeout=3000)
            btn.click(timeout=4000)
            page.wait_for_timeout(2000)
        except Exception:
            return


_dumped = False


def scrape_hotel_date(page, hotel: dict, stay_date: date, run_id: str,
                      currency: str = "BRL", adults: int = 1) -> list[dict]:
    global _dumped
    checkin, checkout = stay_date, stay_date + timedelta(days=1)
    url = build_url(hotel["url"], checkin, checkout, adults)

    page.goto(url, timeout=config.PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
    dismiss_cookies(page)
    try:
        page.wait_for_selector(config.SELECTORS["room_name"], timeout=config.PAGE_TIMEOUT_MS)
    except Exception:
        pass
    expand_rooms(page)

    html = page.content()
    room_min = parse_rooms(html)

    # Diagnóstico: salva a 1ª página vista e loga por que não achou quartos
    if not _dumped:
        _dumped = True
        try:
            with open("debug_first_page.html", "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass
        title = ""
        try:
            title = page.title()
        except Exception:
            pass
        low = html.lower()
        challenge = [w for w in ("captcha", "robot", "verifique", "acesso negado",
                                 "denied", "unusual", "blocked") if w in low]
        print(f"  [diag] url={page.url[:90]}")
        print(f"  [diag] titulo='{title[:60]}' | tamanho={len(html)} | "
              f"room-name={html.count('room-name')} | '{config.PRICE_MARKER}'="
              f"{html.count(config.PRICE_MARKER)} | desafio={challenge or 'nao'}")

    cats = derive_categories(room_min)

    base = {"hotel_id": hotel["id"], "scrape_run_id": run_id,
            "stay_date": stay_date.isoformat(), "currency": currency, "source": "decolar"}

    def obs(category, pick):
        return {**base, "category": category,
                "price": pick["price"] if pick else None,
                "room_name": pick["room_name"] if pick else None,
                "available": pick is not None}

    return [obs("cheapest_overall", cats["cheapest_overall"]),
            obs("ocean_view", cats["ocean_view"]),
            obs("suite", cats["suite"])]
