from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    StraitPassage, PortLoading, OilPrice, ShippingIndex,
    FireHotspot, UKMTOEvent, RiskAssessment, CollectionLog,
)
from app.services.risk_engine import get_risk_engine

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Latest risk assessment
    risk = (
        db.query(RiskAssessment)
        .order_by(RiskAssessment.assessment_date.desc())
        .first()
    )

    # Strait passage: both IMF PortWatch (AIS detected) and IEA baseline (estimated total)
    strait_portwatch = (
        db.query(StraitPassage)
        .filter(StraitPassage.source == "portwatch")
        .order_by(StraitPassage.record_date.desc())
        .first()
    )
    strait_iea = (
        db.query(StraitPassage)
        .filter(StraitPassage.source == "iea_baseline")
        .order_by(StraitPassage.record_date.desc())
        .first()
    )

    # 30-day baselines for both sources
    pw_baseline = (
        db.query(func.avg(StraitPassage.tanker_vessels))
        .filter(
            StraitPassage.record_date >= today - timedelta(days=30),
            StraitPassage.record_date < today,
            StraitPassage.source == "portwatch",
            StraitPassage.tanker_vessels > 0,
        )
        .scalar()
    )
    iea_baseline = (
        db.query(func.avg(StraitPassage.tanker_vessels))
        .filter(
            StraitPassage.record_date >= today - timedelta(days=30),
            StraitPassage.record_date < today,
            StraitPassage.source == "iea_baseline",
            StraitPassage.tanker_vessels > 0,
        )
        .scalar()
    )

    # Primary display: IEA (authoritative total estimate)
    strait = strait_iea or strait_portwatch
    baseline_30d = iea_baseline or pw_baseline

    # Port loading: use IEA baseline (authoritative) over PortWatch AIS sample
    recent_ports = (
        db.query(PortLoading)
        .filter(
            PortLoading.record_date >= today - timedelta(days=7),
            PortLoading.source == "iea_baseline",
        )
        .all()
    )
    if not recent_ports:
        recent_ports = (
            db.query(PortLoading)
            .filter(PortLoading.record_date >= today - timedelta(days=7))
            .all()
        )
    avg_loading_ratio = (
        sum(p.loading_ratio for p in recent_ports if p.loading_ratio) / max(len([p for p in recent_ports if p.loading_ratio]), 1)
        if recent_ports else None
    )

    # Latest oil price
    oil = (
        db.query(OilPrice)
        .order_by(OilPrice.record_date.desc())
        .first()
    )

    # Latest shipping index
    shipping = (
        db.query(ShippingIndex)
        .order_by(ShippingIndex.record_date.desc())
        .first()
    )

    # Fire hotspots count (last 3 days)
    fire_count = (
        db.query(func.count(FireHotspot.id))
        .filter(FireHotspot.detection_time >= today - timedelta(days=3))
        .scalar()
    )

    # UKMTO events count (last 7 days)
    ukmto_count = (
        db.query(func.count(UKMTOEvent.id))
        .filter(UKMTOEvent.event_date >= today - timedelta(days=7))
        .scalar()
    )

    # Data source statuses
    source_status = _get_source_statuses(db)

    return {
        "risk": {
            "level": risk.risk_level if risk else 0,
            "label": risk.risk_level_label if risk else "未知",
            "confidence": risk.confidence_score if risk else 0,
            "date": str(risk.assessment_date) if risk else None,
        },
        "strait": {
            "tanker_vessels": strait.tanker_vessels if strait else None,
            "total_vessels": strait.total_vessels if strait else None,
            "baseline_30d": round(baseline_30d, 1) if baseline_30d else None,
            "change_pct": (
                round((strait.tanker_vessels - baseline_30d) / baseline_30d * 100, 1)
                if strait and strait.tanker_vessels and baseline_30d else None
            ),
            "record_date": str(strait.record_date) if strait else None,
            "source": strait.source if strait else None,
            # IMF PortWatch AIS satellite data (real detected vessels)
            "portwatch": {
                "tanker_vessels": strait_portwatch.tanker_vessels if strait_portwatch else None,
                "total_vessels": strait_portwatch.total_vessels if strait_portwatch else None,
                "record_date": str(strait_portwatch.record_date) if strait_portwatch else None,
                "baseline_30d": round(pw_baseline, 1) if pw_baseline else None,
                "source": "portwatch (AIS satellite)",
            } if strait_portwatch else None,
        },
        "ports": {
            "avg_loading_ratio": round(avg_loading_ratio, 3) if avg_loading_ratio else None,
            "ports_count": len(recent_ports),
        },
        "oil": {
            "brent": round(oil.brent_close, 2) if oil and oil.brent_close else None,
            "wti": round(oil.wti_close, 2) if oil and oil.wti_close else None,
            "spread": round(oil.spread, 2) if oil and oil.spread else None,
            "record_date": str(oil.record_date) if oil else None,
            "source": "sina_finance" if oil and oil.source == "yahoo_finance"
                else ("real" if oil and oil.source == "real" else (oil.source if oil else None)),
        },
        "shipping": {
            "bdti": shipping.bdti if shipping else None,
            "td3c": shipping.td3c if shipping else None,
            "record_date": str(shipping.record_date) if shipping else None,
            "source": shipping.source if shipping else None,
        },
        "fires": {
            "count_3d": fire_count or 0,
        },
        "ukmto": {
            "count_7d": ukmto_count or 0,
        },
        "source_status": source_status,
        "updated_at": today.isoformat(),
    }


@router.get("/sources")
def get_source_status(db: Session = Depends(get_db)):
    return _get_source_statuses(db)


def _get_source_statuses(db: Session) -> list[dict]:
    """Check actual data freshness for all monitoring sources."""
    today = date.today()
    result = []

    # Define sources with display names and their data tables
    sources = [
        {
            "name": "IMF PortWatch",
            "key": "portwatch",
            "table": StraitPassage,
            "date_field": "record_date",
            "source_filter": "portwatch",
            "description": "海峡AIS卫星数据",
        },
        {
            "name": "IEA/EIA 基准",
            "key": "iea_baseline",
            "table": StraitPassage,
            "date_field": "record_date",
            "source_filter": "iea_baseline",
            "description": "海峡通行权威估算",
        },
        {
            "name": "布伦特/WTI油价",
            "key": "oil_price",
            "table": OilPrice,
            "date_field": "record_date",
            "source_filter": None,
            "description": "实时行情+历史数据",
        },
        {
            "name": "NASA FIRMS",
            "key": "nasa_firms",
            "table": FireHotspot,
            "date_field": "detection_time",
            "source_filter": "nasa_firms",
            "description": "卫星火点监测",
        },
        {
            "name": "UKMTO",
            "key": "ukmto",
            "table": UKMTOEvent,
            "date_field": "event_date",
            "source_filter": "ukmto",
            "description": "海上安全事件",
        },
        {
            "name": "BDTI 运价",
            "key": "shipping",
            "table": ShippingIndex,
            "date_field": "record_date",
            "source_filter": None,
            "description": "运价指数(估算)",
        },
        {
            "name": "IEA 港口",
            "key": "port_iea",
            "table": PortLoading,
            "date_field": "record_date",
            "source_filter": "iea_baseline",
            "description": "港口装载数据",
        },
    ]

    for src in sources:
        date_col = getattr(src["table"], src["date_field"])
        query = db.query(func.max(date_col))
        if src["source_filter"]:
            query = query.filter(getattr(src["table"], "source") == src["source_filter"])
        latest = query.scalar()

        latest_date = None
        if latest:
            if isinstance(latest, datetime):
                latest_date = latest.date()
            elif isinstance(latest, date):
                latest_date = latest
            elif isinstance(latest, str):
                try:
                    latest_date = date.fromisoformat(latest[:10])
                except ValueError:
                    pass

        if latest_date:
            days_ago = (today - latest_date).days
            if days_ago <= 1:
                status = "healthy"
            elif days_ago <= 3:
                status = "degraded"
            elif days_ago <= 7:
                status = "warning"
            else:
                status = "stale"
        else:
            days_ago = None
            status = "unknown"

        # Also check collection logs
        last_log = (
            db.query(CollectionLog)
            .filter(CollectionLog.collector_name == src["key"])
            .order_by(CollectionLog.completed_at.desc())
            .first()
        )

        result.append({
            "name": src["name"],
            "key": src["key"],
            "status": status,
            "description": src["description"],
            "latest_data": str(latest_date) if latest_date else None,
            "days_ago": days_ago,
            "last_collection": last_log.completed_at.isoformat() if last_log and last_log.completed_at else None,
            "collector_error": last_log.error_message if last_log and last_log.status not in ("success", "partial") else None,
        })
    return result
