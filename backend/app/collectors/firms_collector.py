import logging
from datetime import datetime, timedelta, timezone

import httpx
from app.collectors.base import BaseCollector, CollectResult, CollectorStatus
from app.config import settings
from app.database import SessionLocal
from app.models import FireHotspot

logger = logging.getLogger(__name__)

FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Bounding boxes for key facilities: (lon_min, lat_min, lon_max, lat_max)
MONITOR_ZONES = {
    "Kharg_Island": (50.15, 28.95, 50.45, 29.35),
    "Asaluyeh_SouthPars": (52.45, 27.30, 52.75, 27.60),
    "Ras_Tanura": (49.90, 26.55, 50.35, 27.10),
    "Abqaiq": (49.55, 25.55, 49.95, 26.10),
    "Jubail": (49.50, 26.80, 49.90, 27.20),
    "Yanbu": (38.00, 23.75, 38.15, 24.15),
    "Fujairah": (56.15, 25.00, 56.45, 25.40),
    "Das_Island": (52.75, 25.05, 53.05, 25.35),
    "Ruwais": (52.60, 24.05, 52.90, 24.40),
    "Ras_Laffan": (51.50, 25.80, 51.75, 26.10),
    "Mina_al_Ahmadi": (48.05, 28.95, 48.35, 29.30),
    "Al_Zour": (48.30, 28.70, 48.55, 28.90),
    "Basrah_Terminal": (48.65, 29.55, 49.05, 29.85),
}

PERSIAN_GULF_BBOX = "48.0,24.0,58.0,30.5"


class FIRMSCollector(BaseCollector):
    source_name = "nasa_firms"
    update_frequency = timedelta(hours=24)

    async def collect(self, target_date: datetime | None = None) -> CollectResult:
        if not settings.FIRMS_API_KEY:
            return CollectResult(
                status=CollectorStatus.FAILED,
                errors=["FIRMS_API_KEY not configured. Get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/"],
            )

        try:
            # Path-based URL format: /api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}
            url = (
                f"{FIRMS_URL}/{settings.FIRMS_API_KEY}"
                f"/VIIRS_SNPP_NRT/{PERSIAN_GULF_BBOX}/3"
            )
            resp = await self.http_client.get(url)
            resp.raise_for_status()

            csv_text = resp.text
            records = self._parse_csv(csv_text)

            inserted = self._save_hotspots(records)
            logger.info(f"FIRMS: fetched {len(records)} hotspots, inserted {inserted}")

            return CollectResult(
                status=CollectorStatus.SUCCESS,
                records_count=inserted,
            )

        except Exception as e:
            logger.error(f"FIRMS collection error: {e}")
            return CollectResult(
                status=CollectorStatus.FAILED,
                errors=[str(e)],
            )

    def _parse_csv(self, csv_text: str) -> list[dict]:
        lines = csv_text.strip().split("\n")
        if len(lines) < 2:
            return []

        headers = [h.strip() for h in lines[0].split(",")]
        records = []

        for line in lines[1:]:
            values = [v.strip() for v in line.split(",")]
            if len(values) != len(headers):
                continue

            row = dict(zip(headers, values))
            try:
                lat = float(row.get("latitude", 0))
                lon = float(row.get("longitude", 0))
                brightness = float(row.get("bright_ti4", 0) or 0)
                frp = float(row.get("frp", 0) or 0)
                acq_date = row.get("acq_date", "")
                acq_time = row.get("acq_time", "0000")

                dt_str = f"{acq_date} {acq_time}"
                detection_time = datetime.strptime(dt_str, "%Y-%m-%d %H%M")

                facility = self._match_facility(lat, lon)

                # Map VIIRS confidence codes to readable labels
                conf_map = {"h": "high", "n": "nominal", "l": "low"}
                raw_conf = row.get("confidence", "n")
                confidence = conf_map.get(raw_conf, "nominal")

                records.append({
                    "detection_time": detection_time,
                    "latitude": lat,
                    "longitude": lon,
                    "brightness": brightness,
                    "frp": frp,
                    "confidence": confidence,
                    "satellite": row.get("satellite", "VIIRS-SNPP"),
                    "facility_name": facility["name"],
                    "facility_type": facility["type"],
                    "country": facility["country"],
                    "raw_daynight": row.get("daynight", "D"),
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"FIRMS parse error: {e} for line: {line[:100]}")
                continue

        return records

    def _match_facility(self, lat: float, lon: float) -> dict:
        for name, (lon_min, lat_min, lon_max, lat_max) in MONITOR_ZONES.items():
            if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
                country_map = {
                    "Kharg_Island": "Iran", "Asaluyeh_SouthPars": "Iran",
                    "Ras_Tanura": "Saudi Arabia", "Abqaiq": "Saudi Arabia",
                    "Jubail": "Saudi Arabia", "Yanbu": "Saudi Arabia",
                    "Fujairah": "UAE", "Das_Island": "UAE", "Ruwais": "UAE",
                    "Ras_Laffan": "Qatar",
                    "Mina_al_Ahmadi": "Kuwait", "Al_Zour": "Kuwait",
                    "Basrah_Terminal": "Iraq",
                }
                type_map = {
                    "Kharg_Island": "oil_terminal", "Asaluyeh_SouthPars": "gas_plant",
                    "Ras_Tanura": "oil_terminal", "Abqaiq": "processing",
                    "Jubail": "refinery", "Yanbu": "oil_terminal",
                    "Fujairah": "oil_terminal", "Das_Island": "oil_terminal",
                    "Ruwais": "refinery", "Ras_Laffan": "lng_terminal",
                    "Mina_al_Ahmadi": "oil_terminal", "Al_Zour": "refinery",
                    "Basrah_Terminal": "oil_terminal",
                }
                return {
                    "name": name,
                    "type": type_map.get(name, "unknown"),
                    "country": country_map.get(name, "Unknown"),
                }

        # Approximate offshore assignment
        if 48 <= lon <= 58 and 24 <= lat <= 30.5:
            return {"name": "Persian_Gulf_Offshore", "type": "offshore", "country": "Various"}
        return {"name": "Unmapped", "type": "unknown", "country": "Unknown"}

    def _save_hotspots(self, records: list[dict]) -> int:
        if not records:
            return 0

        db = SessionLocal()
        inserted = 0
        try:
            for rec in records:
                existing = (
                    db.query(FireHotspot)
                    .filter(
                        FireHotspot.detection_time == rec["detection_time"],
                        FireHotspot.latitude == rec["latitude"],
                        FireHotspot.longitude == rec["longitude"],
                    )
                    .first()
                )
                if not existing:
                    db.add(FireHotspot(**rec))
                    inserted += 1
            db.commit()
        finally:
            db.close()
        return inserted
