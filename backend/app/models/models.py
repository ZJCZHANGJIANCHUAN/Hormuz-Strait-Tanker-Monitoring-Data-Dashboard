from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text, JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


class StraitPassage(Base):
    __tablename__ = "strait_passages"
    __table_args__ = (UniqueConstraint("record_date", "source"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_date = Column(Date, nullable=False, index=True)
    total_vessels = Column(Integer)
    tanker_vessels = Column(Integer)
    lng_vessels = Column(Integer)
    container_vessels = Column(Integer)
    dry_bulk_vessels = Column(Integer)
    tanker_capacity_tons = Column(Float)
    total_capacity_tons = Column(Float)
    avg_speed_knots = Column(Float)
    waiting_vessels = Column(Integer)
    source = Column(String(50), default="portwatch")
    created_at = Column(DateTime, default=datetime.utcnow)


class PortLoading(Base):
    __tablename__ = "port_loadings"
    __table_args__ = (UniqueConstraint("record_date", "port_code", "source"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_date = Column(Date, nullable=False, index=True)
    port_name = Column(String(100), nullable=False)
    port_code = Column(String(20), index=True)
    departing_tankers = Column(Integer)
    arriving_tankers = Column(Integer)
    loaded_tankers = Column(Integer)
    ballast_tankers = Column(Integer)
    loading_ratio = Column(Float)
    estimated_exports_7d = Column(Float)
    estimated_exports_30d = Column(Float)
    avg_waiting_time_hours = Column(Float)
    source = Column(String(50), default="portwatch")
    created_at = Column(DateTime, default=datetime.utcnow)


class OilPrice(Base):
    __tablename__ = "oil_prices"
    __table_args__ = (UniqueConstraint("record_date", "source"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_date = Column(Date, nullable=False, index=True)
    brent_close = Column(Float)
    brent_open = Column(Float)
    brent_high = Column(Float)
    brent_low = Column(Float)
    brent_volume = Column(Float)
    wti_close = Column(Float)
    wti_open = Column(Float)
    wti_high = Column(Float)
    wti_low = Column(Float)
    wti_volume = Column(Float)
    spread = Column(Float)
    diesel_price = Column(Float)
    jet_fuel_price = Column(Float)
    source = Column(String(50), default="yahoo_finance")
    created_at = Column(DateTime, default=datetime.utcnow)


class ShippingIndex(Base):
    __tablename__ = "shipping_indices"
    __table_args__ = (UniqueConstraint("record_date", "source"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_date = Column(Date, nullable=False, index=True)
    bdti = Column(Float)
    td3c = Column(Float)
    td8 = Column(Float)
    bcti = Column(Float)
    source = Column(String(50), default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)


class FireHotspot(Base):
    __tablename__ = "fire_hotspots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detection_time = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    brightness = Column(Float)
    brightness_t31 = Column(Float)
    frp = Column(Float)
    confidence = Column(String(10))
    satellite = Column(String(20))
    facility_name = Column(String(100), index=True)
    facility_type = Column(String(50))
    country = Column(String(50))
    is_anomaly = Column(Boolean, default=False)
    raw_daynight = Column(String(1))
    source = Column(String(50), default="nasa_firms")
    created_at = Column(DateTime, default=datetime.utcnow)


class UKMTOEvent(Base):
    __tablename__ = "ukmto_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="medium")
    latitude = Column(Float)
    longitude = Column(Float)
    area_name = Column(String(100))
    description = Column(Text)
    affected_vessels = Column(Integer)
    vessel_types = Column(String(200))
    advisory_number = Column(String(50))
    source_url = Column(String(500))
    source = Column(String(50), default="ukmto")
    created_at = Column(DateTime, default=datetime.utcnow)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (UniqueConstraint("assessment_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_date = Column(Date, nullable=False, index=True)
    risk_level = Column(Integer, nullable=False)
    risk_level_label = Column(String(50))
    confidence_score = Column(Float)
    strait_passage_score = Column(Float)
    port_loading_score = Column(Float)
    oil_price_score = Column(Float)
    shipping_index_score = Column(Float)
    fire_anomaly_score = Column(Float)
    ukmto_event_score = Column(Float)
    evidence_summary = Column(Text)
    raw_data_snapshot = Column(JSON)
    is_manual_override = Column(Boolean, default=False)
    manual_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collector_name = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(20))
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
