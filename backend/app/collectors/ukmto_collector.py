"""
UKMTO Collector — Maritime Security Incidents near Strait of Hormuz.
Uses proxy if configured for Cloudflare bypass.
"""
import logging
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, CollectResult, CollectorStatus
from app.config import settings
from app.database import SessionLocal
from app.models import UKMTOEvent

logger = logging.getLogger(__name__)

UKMTO_URL = "https://www.ukmto.org/recent-incidents"


class UKMTOCollector(BaseCollector):
    source_name = "ukmto"
    update_frequency = timedelta(hours=6)

    async def collect(self, target_date: datetime | None = None) -> CollectResult:
        try:
            resp = await self.http_client.get(
                UKMTO_URL,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-GB,en;q=0.9",
                },
            )

            if resp.status_code == 403:
                proxy_used = bool(settings.HTTP_PROXY or settings.HTTPS_PROXY)
                msg = (
                    "UKMTO blocked (403 Cloudflare). "
                    + ("Proxy is configured but still blocked." if proxy_used
                       else "No proxy configured. Set HTTP_PROXY in .env.")
                )
                logger.warning(msg)
                return CollectResult(status=CollectorStatus.BLOCKED, errors=[msg])

            if resp.status_code != 200:
                return CollectResult(
                    status=CollectorStatus.FAILED,
                    errors=[f"UKMTO HTTP {resp.status_code}"],
                )

            events = self._parse_page(resp.text)
            if not events:
                return CollectResult(
                    status=CollectorStatus.PARTIAL,
                    records_count=0,
                    errors=["No events found on UKMTO page"],
                )

            inserted = self._save_events(events)
            logger.info(f"UKMTO: {len(events)} events parsed, {inserted} new")
            return CollectResult(
                status=CollectorStatus.SUCCESS if inserted > 0 else CollectorStatus.PARTIAL,
                records_count=inserted,
            )

        except Exception as e:
            logger.error(f"UKMTO failed: {e}")
            return CollectResult(status=CollectorStatus.FAILED, errors=[str(e)])

    def _parse_page(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        events = []

        for tag in soup.find_all(["article", "tr", "div"]):
            text = tag.get_text(" ", strip=True)
            if len(text) < 30:
                continue

            event_type = "other"
            severity = "low"
            text_lower = text.lower()

            if any(w in text_lower for w in ["attack", "missile", "drone", "uas", "explosion"]):
                event_type, severity = "attack", "critical"
            elif any(w in text_lower for w in ["hijack", "boarding", "pirates"]):
                event_type, severity = "hijack", "critical"
            elif any(w in text_lower for w in ["suspicious", "approach", "loitering"]):
                event_type, severity = "suspicious_activity", "medium"
            elif any(w in text_lower for w in ["warning", "advisory"]):
                event_type, severity = "advisory", "low"

            events.append({
                "event_date": datetime.utcnow(),
                "event_type": event_type,
                "severity": severity,
                "area_name": "Strait of Hormuz",
                "description": text[:500],
                "source_url": UKMTO_URL,
                "source": "ukmto",
            })

        return events

    def _save_events(self, events: list[dict]) -> int:
        if not events:
            return 0
        db = SessionLocal()
        try:
            inserted = 0
            for evt in events:
                existing = (
                    db.query(UKMTOEvent)
                    .filter(UKMTOEvent.description == evt["description"][:100])
                    .first()
                )
                if not existing:
                    db.add(UKMTOEvent(**evt))
                    inserted += 1
            db.commit()
        finally:
            db.close()
        return inserted
