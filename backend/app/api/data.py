from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    StraitPassage, PortLoading, OilPrice, ShippingIndex,
    FireHotspot, UKMTOEvent,
)

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/strait")
def get_strait_data(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    rows = (
        db.query(StraitPassage)
        .filter(StraitPassage.record_date >= start_date)
        .order_by(StraitPassage.record_date.asc())
        .all()
    )
    return {
        "data": [
            {
                "date": str(r.record_date),
                "tanker_vessels": r.tanker_vessels,
                "total_vessels": r.total_vessels,
                "lng_vessels": r.lng_vessels,
                "tanker_capacity_tons": r.tanker_capacity_tons,
                "total_capacity_tons": r.total_capacity_tons,
                "source": r.source,
            }
            for r in rows
        ]
    }


@router.get("/ports")
def get_port_data(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    rows = (
        db.query(PortLoading)
        .filter(PortLoading.record_date >= start_date)
        .order_by(PortLoading.record_date.desc(), PortLoading.port_name)
        .all()
    )
    return {
        "data": [
            {
                "date": str(r.record_date),
                "port_name": r.port_name,
                "port_code": r.port_code,
                "loaded_tankers": r.loaded_tankers,
                "ballast_tankers": r.ballast_tankers,
                "loading_ratio": r.loading_ratio,
                "estimated_exports_7d": r.estimated_exports_7d,
            }
            for r in rows
        ]
    }


@router.get("/prices")
def get_price_data(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    rows = (
        db.query(OilPrice)
        .filter(OilPrice.record_date >= start_date)
        .order_by(OilPrice.record_date.asc())
        .all()
    )
    return {
        "data": [
            {
                "date": str(r.record_date),
                "brent_close": r.brent_close,
                "wti_close": r.wti_close,
                "spread": r.spread,
            }
            for r in rows
        ]
    }


@router.get("/shipping")
def get_shipping_data(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    rows = (
        db.query(ShippingIndex)
        .filter(ShippingIndex.record_date >= start_date)
        .order_by(ShippingIndex.record_date.asc())
        .all()
    )
    return {
        "data": [
            {
                "date": str(r.record_date),
                "bdti": r.bdti,
                "td3c": r.td3c,
                "td8": r.td8,
                "bcti": r.bcti,
            }
            for r in rows
        ]
    }


@router.get("/fires")
def get_fire_data(
    days: int = Query(default=7, ge=1, le=90),
    facility: str = Query(default=None),
    db: Session = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    query = (
        db.query(FireHotspot)
        .filter(FireHotspot.detection_time >= start_date)
    )
    if facility:
        query = query.filter(FireHotspot.facility_name == facility)
    rows = query.order_by(FireHotspot.detection_time.desc()).limit(500).all()

    return {
        "data": [
            {
                "detection_time": r.detection_time.isoformat() if r.detection_time else None,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "brightness": r.brightness,
                "frp": r.frp,
                "confidence": r.confidence,
                "facility_name": r.facility_name,
                "facility_type": r.facility_type,
                "country": r.country,
            }
            for r in rows
        ]
    }


@router.get("/ukmto")
def get_ukmto_data(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    rows = (
        db.query(UKMTOEvent)
        .filter(UKMTOEvent.event_date >= start_date)
        .order_by(UKMTOEvent.event_date.desc())
        .all()
    )
    return {
        "data": [
            {
                "event_date": r.event_date.isoformat() if r.event_date else None,
                "event_type": r.event_type,
                "severity": r.severity,
                "area_name": r.area_name,
                "description": r.description,
                "advisory_number": r.advisory_number,
            }
            for r in rows
        ]
    }
