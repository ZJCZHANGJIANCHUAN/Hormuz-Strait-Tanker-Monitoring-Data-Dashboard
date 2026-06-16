"""
Seed script to populate database with realistic historical data.
Run: python seed.py
"""
import random
from datetime import date, datetime, timedelta, timezone

from app.database import engine, Base, SessionLocal
from app.models import (
    StraitPassage, PortLoading, OilPrice, ShippingIndex,
    FireHotspot, UKMTOEvent,
)


def seed_strait_passages(db):
    """Generate 90 days of strait passage data based on EIA baselines.

    EIA (2024-2025): Strait of Hormuz = ~20M bpd oil flow
    ~20-22 oil tankers/day, ~55-60 total vessels/day
    Reference: https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints
    """
    base_tanker = 21      # ~20-22 oil tankers/day (EIA)
    base_total = 58        # ~55-60 total vessels/day (EIA)
    base_lng = 3           # ~3-4 LNG carriers/day
    base_container = 13    # container ships
    base_dry_bulk = 11     # dry bulk carriers
    base_tanker_cap = 2800000   # ~2.8M deadweight tons tanker capacity
    base_total_cap = 6200000    # ~6.2M total deadweight tons

    inserted = 0
    for i in range(90, -1, -1):
        d = date.today() - timedelta(days=i)
        # Add some realistic daily variation
        noise = random.gauss(0, 2)
        tanker = max(5, round(base_tanker + noise))
        total = max(15, round(base_total + noise * 2.5))
        lng = max(1, round(base_lng + random.gauss(0, 0.5)))
        container = max(3, round(base_container + random.gauss(0, 1)))
        dry_bulk = max(2, round(base_dry_bulk + random.gauss(0, 1)))

        existing = db.query(StraitPassage).filter(
            StraitPassage.record_date == d,
            StraitPassage.source == "seed",
        ).first()
        if not existing:
            db.add(StraitPassage(
                record_date=d,
                total_vessels=total,
                tanker_vessels=tanker,
                lng_vessels=lng,
                container_vessels=container,
                dry_bulk_vessels=dry_bulk,
                tanker_capacity_tons=base_tanker_cap + random.uniform(-200000, 200000),
                total_capacity_tons=base_total_cap + random.uniform(-400000, 400000),
                avg_speed_knots=round(random.uniform(10, 14), 1),
                waiting_vessels=max(0, round(random.gauss(3, 2))),
                source="seed",
            ))
            inserted += 1
    db.commit()
    print(f"  StraitPassage: {inserted} records seeded")
    return inserted


def seed_port_loadings(db):
    """Generate 30 days of port loading data."""
    ports = [
        ("Kharg Island", "IRKHK"), ("Ras Tanura", "SARTA"), ("Fujairah", "AEFJR"),
        ("Das Island", "AEDAS"), ("Ras Laffan", "QARLF"), ("Mina al-Ahmadi", "KWMEA"),
        ("Basrah", "IQBSR"), ("Jubail", "SAJUB"), ("Ruwais", "AERUW"), ("Yanbu", "SAYNB"),
    ]
    base_loads = {
        "IRKHK": (12, 4), "SARTA": (18, 6), "AEFJR": (15, 8),
        "AEDAS": (8, 3), "QARLF": (10, 2), "KWMEA": (14, 5),
        "IQBSR": (16, 7), "SAJUB": (10, 4), "AERUW": (8, 3), "SAYNB": (12, 5),
    }

    inserted = 0
    for i in range(30, -1, -1):
        d = date.today() - timedelta(days=i)
        for port_name, port_code in ports:
            loaded_base, ballast_base = base_loads.get(port_code, (10, 4))
            loaded = max(1, round(loaded_base + random.gauss(0, 2)))
            ballast = max(0, round(ballast_base + random.gauss(0, 1.5)))
            total = loaded + ballast
            loading_ratio = round(loaded / total, 3) if total > 0 else 0.5

            existing = db.query(PortLoading).filter(
                PortLoading.record_date == d,
                PortLoading.port_code == port_code,
                PortLoading.source == "seed",
            ).first()
            if not existing:
                db.add(PortLoading(
                    record_date=d,
                    port_name=port_name,
                    port_code=port_code,
                    departing_tankers=loaded,
                    arriving_tankers=ballast,
                    loaded_tankers=loaded,
                    ballast_tankers=ballast,
                    loading_ratio=loading_ratio,
                    estimated_exports_7d=round(loaded * 7 * random.uniform(0.8, 1.2)),
                    estimated_exports_30d=round(loaded * 30 * random.uniform(0.8, 1.2)),
                    source="seed",
                ))
                inserted += 1
    db.commit()
    print(f"  PortLoading: {inserted} records seeded")
    return inserted


def seed_oil_prices(db):
    """Generate 90 days of oil price data using realistic current prices."""
    brent_base = 83.0   # Brent ~$83/bbl (June 2026, real Sina price)
    wti_base = 79.0     # WTI ~$79/bbl

    inserted = 0
    for i in range(90, -1, -1):
        d = date.today() - timedelta(days=i)
        # Mean-reverting random walk (Brent oscillates around $65)
        brent_mean = 65.0
        brent_base += random.gauss(0, 0.5) + (brent_mean - brent_base) * 0.02
        brent_base = max(55, min(75, brent_base))
        wti_mean = 61.0
        wti_base += random.gauss(0, 0.45) + (wti_mean - wti_base) * 0.02
        wti_base = max(51, min(71, wti_base))

        brent_close = round(brent_base, 2)
        wti_close = round(wti_base, 2)
        spread = round(brent_close - wti_close, 2)

        existing = db.query(OilPrice).filter(
            OilPrice.record_date == d,
            OilPrice.source == "seed",
        ).first()
        if not existing:
            db.add(OilPrice(
                record_date=d,
                brent_close=brent_close,
                brent_open=round(brent_close + random.uniform(-0.5, 0.5), 2),
                brent_high=round(brent_close + random.uniform(0.5, 1.5), 2),
                brent_low=round(brent_close - random.uniform(0.5, 1.5), 2),
                brent_volume=round(random.uniform(100000, 300000)),
                wti_close=wti_close,
                wti_open=round(wti_close + random.uniform(-0.5, 0.5), 2),
                wti_high=round(wti_close + random.uniform(0.5, 1.5), 2),
                wti_low=round(wti_close - random.uniform(0.5, 1.5), 2),
                wti_volume=round(random.uniform(200000, 500000)),
                spread=spread,
                source="seed",
            ))
            inserted += 1
    db.commit()
    print(f"  OilPrice: {inserted} records seeded")
    return inserted


def seed_shipping_indices(db):
    """Generate 60 days of shipping index data with realistic BDTI range."""
    bdti_base = 1150.0  # BDTI ~1150 (June 2026)

    inserted = 0
    for i in range(60, -1, -1):
        d = date.today() - timedelta(days=i)
        bdti_mean = 1150.0
        bdti_base += random.gauss(0, 20) + (bdti_mean - bdti_base) * 0.03
        bdti = round(max(800, min(1600, bdti_base)))
        td3c = round(bdti * random.uniform(0.8, 1.2))
        td8 = round(bdti * random.uniform(0.6, 0.9))
        bcti = round(random.uniform(500, 900))

        existing = db.query(ShippingIndex).filter(
            ShippingIndex.record_date == d,
            ShippingIndex.source == "seed",
        ).first()
        if not existing:
            db.add(ShippingIndex(
                record_date=d,
                bdti=bdti,
                td3c=td3c,
                td8=td8,
                bcti=bcti,
                source="seed",
            ))
            inserted += 1
    db.commit()
    print(f"  ShippingIndex: {inserted} records seeded")
    return inserted


def seed_fire_hotspots(db):
    """Generate recent fire hotspot data for key facilities."""
    facilities = [
        ("Kharg Island", "oil_terminal", "Iran", 50.30, 29.25),
        ("Ras Tanura", "oil_terminal", "Saudi Arabia", 50.15, 26.70),
        ("Asaluyeh SouthPars", "gas_plant", "Iran", 52.61, 27.48),
        ("Fujairah", "oil_terminal", "UAE", 56.33, 25.12),
        ("Ruwais", "refinery", "UAE", 52.73, 24.12),
        ("Jubail", "refinery", "Saudi Arabia", 49.66, 27.01),
        ("Mina al-Ahmadi", "oil_terminal", "Kuwait", 48.17, 29.08),
        ("Basrah Terminal", "oil_terminal", "Iraq", 48.83, 29.67),
    ]

    inserted = 0
    for i in range(14):
        d = datetime.now(timezone.utc) - timedelta(days=i, hours=random.randint(0, 23))
        # Generate 0-3 hotspots per day
        for _ in range(random.randint(0, 3)):
            fac = random.choice(facilities)
            lat = fac[3] + random.uniform(-0.05, 0.05)
            lon = fac[4] + random.uniform(-0.05, 0.05)

            db.add(FireHotspot(
                detection_time=d,
                latitude=round(lat, 5),
                longitude=round(lon, 5),
                brightness=round(random.uniform(310, 380), 1),
                brightness_t31=round(random.uniform(290, 350), 1),
                frp=round(random.uniform(1, 15), 1),
                confidence=random.choice(["high", "nominal", "nominal", "high"]),
                satellite="VIIRS-SNPP",
                facility_name=fac[0],
                facility_type=fac[1],
                country=fac[2],
                is_anomaly=random.random() < 0.1,
                source="seed",
            ))
            inserted += 1
    db.commit()
    print(f"  FireHotspot: {inserted} records seeded")
    return inserted


def seed_ukmto_events(db):
    """Generate sample UKMTO events."""
    event_types = [
        ("suspicious_activity", "Suspicious approach reported in the area", "medium"),
        ("advisory", "Navigation warning issued for Strait of Hormuz", "low"),
        ("attack", "Unmanned aerial vehicle activity detected near merchant vessel", "high"),
        ("suspicious_activity", "Small craft loitering near tanker lane", "medium"),
        ("warning", "Increased military activity reported in Persian Gulf", "medium"),
        ("suspicious_activity", "AIS spoofing detected in Gulf of Oman", "medium"),
    ]

    inserted = 0
    for i in range(15):
        d = datetime.now(timezone.utc) - timedelta(days=i * random.uniform(0.3, 2.5), hours=random.randint(0, 23))
        evt = random.choice(event_types)
        lat = random.uniform(24.5, 27.5)
        lon = random.uniform(55.0, 57.5)

        db.add(UKMTOEvent(
            event_date=d,
            event_type=evt[0],
            description=evt[1],
            severity=evt[2],
            area_name=random.choice(["Strait of Hormuz", "Gulf of Oman", "Persian Gulf"]),
            latitude=round(lat, 5),
            longitude=round(lon, 5),
            advisory_number=f"UKMTO-{random.randint(100, 999)}",
            source_url="https://www.ukmto.org/indian-ocean/recent-incidents",
            source="seed",
        ))
        inserted += 1
    db.commit()
    print(f"  UKMTOEvent: {inserted} records seeded")
    return inserted


def main():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding data...")
        seed_strait_passages(db)
        seed_port_loadings(db)
        seed_oil_prices(db)
        seed_shipping_indices(db)
        seed_fire_hotspots(db)
        seed_ukmto_events(db)
        print("\nSeed completed successfully!")
        print("Run the app and trigger a risk assessment to populate risk data.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
