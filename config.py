"""config.py — parâmetros do scraper da Decolar."""
import os
from dotenv import load_dotenv

load_dotenv()

REQUEST_MIN_DELAY = float(os.getenv("REQUEST_MIN_DELAY", "4"))
REQUEST_MAX_DELAY = float(os.getenv("REQUEST_MAX_DELAY", "9"))
PAGE_TIMEOUT_MS   = int(os.getenv("PAGE_TIMEOUT_MS", "60000"))
HEADLESS          = os.getenv("HEADLESS", "true").lower() == "true"
MAX_RETRIES       = int(os.getenv("MAX_RETRIES", "3"))

DEFAULTS = {"window_start": "2026-10-01", "window_end": "2026-12-31",
            "los": 1, "adults": 1, "currency": "BRL"}

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Classificação de categoria pelos nomes reais da Decolar
# (ex.: "Quarto de Luxo com Vista ao Mar", "Suíte Dupla Júnior com Vista ao Mar")
OCEAN_KEYWORDS = ["vista ao mar", "vista para o mar", "frente ao mar", "oceano", " mar "]
SUITE_KEYWORDS = ["suíte", "suite"]

# Seletores calibrados a partir de um HTML real da Decolar (página do Fairmont)
SELECTORS = {
    "room_name":   ".room-name",                 # <p class="room-name">Quarto de Luxo com Vista ao Mar</p>
    "view_more":   ".view-more",                  # botão "Veja mais opções"
    "cookie_btns": [
        'button:has-text("Aceitar")',
        'button:has-text("Aceito")',
        'button:has-text("Concordo")',
        '#onetrust-accept-btn-handler',
    ],
}
# marcador de preço por noite no texto da página
PRICE_MARKER = "Final por noite"
