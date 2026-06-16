import asyncio
from datetime import date, datetime

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import UKMTOEvent, ShippingIndex, CollectionLog
from app.collectors.collector_manager import collector_manager
from app.services.risk_engine import get_risk_engine
from app.scheduler import run_all_collectors
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/collect")
async def trigger_collection(collector_name: str | None = Body(None, embed=True)):
    if collector_name:
        result = await collector_manager.collect_one(collector_name)
        return {
            "collector": collector_name,
            "status": result.status.value,
            "records": result.records_count,
            "errors": result.errors,
        }
    else:
        results = await collector_manager.collect_all()
        return {
            name: {
                "status": r.status.value,
                "records": r.records_count,
                "errors": r.errors,
            }
            for name, r in results.items()
        }


@router.post("/ukmto/events")
def add_ukmto_event(
    event_date: str = Body(...),
    event_type: str = Body(...),
    description: str = Body(...),
    severity: str = Body(default="medium"),
    area_name: str = Body(default="Strait of Hormuz"),
    latitude: float | None = Body(default=None),
    longitude: float | None = Body(default=None),
    advisory_number: str | None = Body(default=None),
    source_url: str | None = Body(default=None),
    db: Session = Depends(get_db),
):
    event = UKMTOEvent(
        event_date=datetime.fromisoformat(event_date),
        event_type=event_type,
        description=description,
        severity=severity,
        area_name=area_name,
        latitude=latitude,
        longitude=longitude,
        advisory_number=advisory_number,
        source_url=source_url,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "message": "Event added successfully"}


@router.post("/shipping")
def add_shipping_index(
    record_date: str = Body(...),
    bdti: float | None = Body(default=None),
    td3c: float | None = Body(default=None),
    td8: float | None = Body(default=None),
    bcti: float | None = Body(default=None),
    source: str = Body(default="manual"),
    db: Session = Depends(get_db),
):
    row = ShippingIndex(
        record_date=date.fromisoformat(record_date),
        bdti=bdti,
        td3c=td3c,
        td8=td8,
        bcti=bcti,
        source=source,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "message": "Shipping index added"}


@router.post("/ukmto/scrape")
async def submit_ukmto_scrape(
    html: str = Body(default="", embed=True),
    db: Session = Depends(get_db),
):
    """Accept UKMTO HTML from frontend or fetch directly via proxy."""
    from bs4 import BeautifulSoup

    # If frontend couldn't fetch (CORS blocked), try backend proxy
    if not html or len(html) < 100:
        try:
            import httpx
            proxy = settings.HTTP_PROXY or settings.HTTPS_PROXY or None
            if proxy and not proxy.startswith(("http://", "https://", "socks5://")):
                proxy = None

            async with httpx.AsyncClient(proxy=proxy, timeout=30) as client:
                resp = await client.get(
                    "https://www.ukmto.org/recent-incidents",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "text/html",
                    }
                )
                if resp.status_code == 200:
                    html = resp.text
                elif resp.status_code == 403 and not proxy:
                    return {
                        "message": "UKMTO 被 Cloudflare 拦截。浏览器建议：直接打开 ukmto.org 复制页面内容，粘贴到下方输入框提交。",
                        "events": [],
                    }
                else:
                    return {
                        "message": f"UKMTO HTTP {resp.status_code}" + (" (代理已配置但被拦截)" if proxy else " (需配置代理)"),
                        "events": [],
                    }
        except Exception as e:
            return {
                "message": f"后端抓取失败: {str(e)[:100]}",
                "events": [],
            }

    soup = BeautifulSoup(html, "html.parser")

    # Extract text from HTML (if it's HTML), or use as-is (if plain text)
    body = soup.get_text("\n", strip=True)
    if len(body) < len(html) * 0.5:
        body = html  # Not really HTML, use as plain text

    # Parse incidents — match date patterns that START a new entry
    # Line-beginning dates: "2026年6月13日" or "2026年6月13日 攻击："
    # Avoid matching embedded dates inside descriptions
    events = []
    now = datetime.utcnow()
    import re

    # Split by date that appears at start of a logical segment
    # Match date preceded by newline or start-of-string
    date_pattern = r'(?:^|\n)\s*(2026\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)'
    chunks = re.split(date_pattern, body)

    # Re-combine date + content pairs
    for i in range(1, len(chunks) - 1, 2):
        date_str = chunks[i].strip().replace(" ", "")
        content = chunks[i + 1].strip()

        if len(content) < 20:
            continue

        # Stop parsing at footer/site navigation
        if any(kw in content for kw in ['© 英国皇家版权', '条款及细则', 'Royal Navy and UKMTO logos']):
            break

        # Extract event type from the beginning of content
        content_lower = content.lower()
        event_type = "other"
        severity = "low"

        # Check for type labels at start
        if content.startswith("攻击") or "attack" in content_lower[:20]:
            event_type, severity = "attack", "critical"
        elif content.startswith("劫持") or "hijack" in content_lower[:20]:
            event_type, severity = "hijack", "critical"
        elif "可疑" in content[:20] or "suspicious" in content_lower[:20]:
            event_type, severity = "suspicious_activity", "medium"
        elif "警告" in content[:20] or "advisory" in content_lower[:20] or "warning" in content_lower[:20]:
            event_type, severity = "advisory", "low"

        # If type not in header, check full text
        if event_type == "other":
            if any(w in content_lower for w in ["missile", "drone", "uas", "explosion", "fired", "shot", "attack", "袭击", "开火", "击中", "爆炸"]):
                event_type, severity = "attack", "critical"
            elif any(w in content_lower for w in ["hijack", "boarding", "pirates", "劫持", "登船"]):
                event_type, severity = "hijack", "critical"
            elif any(w in content_lower for w in ["suspicious", "approach", "loitering", "可疑", "靠近", "接近"]):
                event_type, severity = "suspicious_activity", "medium"
            elif any(w in content_lower for w in ["warning", "advisory", "警告", "公告"]):
                event_type, severity = "advisory", "low"

        # Parse date (Chinese format: "2026年6月13日" or English: "12 March 2026")
        try:
            date_clean = date_str.replace("年", "-").replace("月", "-").replace("日", "")
            parts = date_clean.split("-")
            if len(parts) == 3:
                event_date = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            else:
                event_date = now
        except Exception:
            try:
                event_date = datetime.strptime(date_str, "%d %B %Y")
            except Exception:
                event_date = now

        # Extract UKMTO advisory number if present
        ukmto_num = None
        num_match = re.search(r'(?:UKMTO|警告|warning)\s*[#]?\s*(\d{1,4}[\-]?\d{0,4})', content, re.IGNORECASE)
        if num_match:
            ukmto_num = f"UKMTO-{num_match.group(1)}"

        # Dedup by first 80 chars
        desc_key = content[:80].strip()
        existing = (
            db.query(UKMTOEvent)
            .filter(UKMTOEvent.description.startswith(desc_key))
            .first()
        )
        if not existing:
            db.add(UKMTOEvent(
                event_date=event_date,
                event_type=event_type,
                severity=severity,
                area_name="Strait of Hormuz",
                description=content[:1000],
                advisory_number=ukmto_num,
                source_url="https://www.ukmto.org/recent-incidents",
                source="ukmto",
            ))
            events.append(event_type)

    db.commit()
    return {
        "message": f"从 UKMTO 页面解析到 {len(events)} 个事件",
        "events": events,
    }


@router.get("/logs")
def get_collection_logs(days: int = 7, db: Session = Depends(get_db)):
    logs = (
        db.query(CollectionLog)
        .order_by(CollectionLog.started_at.desc())
        .limit(days * 4)
        .all()
    )
    return {
        "data": [
            {
                "collector": l.collector_name,
                "status": l.status,
                "started": l.started_at.isoformat() if l.started_at else None,
                "completed": l.completed_at.isoformat() if l.completed_at else None,
                "records": l.records_inserted,
                "error": l.error_message,
            }
            for l in logs
        ]
    }
