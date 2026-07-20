from __future__ import annotations

import json
import os
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("DATABASE_PATH", "deals.db"))
CATALOG_PATH = Path(os.getenv("CATALOG_PATH", "catalog.json"))


@dataclass(slots=True)
class Offer:
    source: str
    title: str
    price: float
    url: str
    item_id: str
    seller: str = ""
    shipping: float = 0.0

    @property
    def total(self) -> float:
        return self.price + self.shipping


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                total_price REAL NOT NULL,
                url TEXT NOT NULL,
                collected_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_item ON price_history(item_id, collected_at)"
        )


def load_catalog() -> list[dict[str, Any]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["products"]


def normalize(text: str) -> str:
    return " ".join(text.lower().replace("-", " ").split())


def matches_product(title: str, product: dict[str, Any]) -> bool:
    normalized = normalize(title)
    required = [normalize(term) for term in product.get("required_terms", [])]
    blocked = [normalize(term) for term in product.get("blocked_terms", [])]
    return all(term in normalized for term in required) and not any(
        term in normalized for term in blocked
    )


def fetch_mercado_livre(query: str, limit: int = 50) -> list[Offer]:
    url = "https://api.mercadolibre.com/sites/MLB/search"
    with httpx.Client(timeout=25, follow_redirects=True) as client:
        response = client.get(url, params={"q": query, "limit": limit})
        response.raise_for_status()
        payload = response.json()

    offers: list[Offer] = []
    for item in payload.get("results", []):
        shipping = item.get("shipping") or {}
        offers.append(
            Offer(
                source="Mercado Livre",
                title=item.get("title", ""),
                price=float(item.get("price") or 0),
                shipping=0.0 if shipping.get("free_shipping") else 0.0,
                url=item.get("permalink", ""),
                item_id=f"mlb:{item.get('id', '')}",
                seller=str(item.get("seller", {}).get("nickname", "")),
            )
        )
    return offers


def historical_prices(item_id: str, days: int = 30) -> list[float]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT total_price FROM price_history
            WHERE item_id = ?
              AND collected_at >= datetime('now', ?)
            ORDER BY collected_at DESC
            """,
            (item_id, f"-{days} days"),
        ).fetchall()
    return [float(row[0]) for row in rows]


def save_offer(offer: Offer) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO price_history
            (item_id, source, title, total_price, url, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                offer.item_id,
                offer.source,
                offer.title,
                offer.total,
                offer.url,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def deal_score(offer: Offer, target_price: float, history: list[float]) -> int:
    score = 0
    if offer.total <= target_price:
        score += 55
    if history:
        median = statistics.median(history)
        discount = max(0.0, (median - offer.total) / median)
        score += min(35, round(discount * 175))
        if offer.total <= min(history):
            score += 10
    return min(score, 100)


def should_alert(offer: Offer, product: dict[str, Any], history: list[float]) -> bool:
    target = float(product["target_price"])
    if offer.total <= target:
        return True
    if history:
        return offer.total <= statistics.median(history) * float(
            product.get("median_discount_trigger", 0.88)
        )
    return False


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(text)
        return

    response = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
        timeout=20,
    )
    response.raise_for_status()


def run() -> None:
    init_db()
    seen: set[str] = set()

    for product in load_catalog():
        for offer in fetch_mercado_livre(product["query"]):
            if offer.item_id in seen or not matches_product(offer.title, product):
                continue
            seen.add(offer.item_id)
            history = historical_prices(offer.item_id)
            alert = should_alert(offer, product, history)
            score = deal_score(offer, float(product["target_price"]), history)
            save_offer(offer)

            if alert:
                send_telegram(
                    "\n".join(
                        [
                            f"🔥 Oferta DNBB — score {score}/100",
                            product["name"],
                            offer.title,
                            f"Preço: R$ {offer.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            f"Fonte: {offer.source}",
                            offer.url,
                        ]
                    )
                )


if __name__ == "__main__":
    run()
