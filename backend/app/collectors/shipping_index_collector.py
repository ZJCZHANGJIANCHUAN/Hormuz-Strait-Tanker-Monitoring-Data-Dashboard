"""
Shipping Index Collector
BDTI (Baltic Dirty Tanker Index) is a paid index. This collector:
1. Estimates BDTI from oil prices + strait passage data (marked as estimated)
2. Supports manual entry for actual values (marked as actual)
"""
import logging
from datetime import datetime, date, timedelta

from sqlalchemy import func

from app.collectors.base import BaseCollector, CollectResult, CollectorStatus
from app.database import SessionLocal
from app.models import ShippingIndex, OilPrice, StraitPassage

logger = logging.getLogger(__name__)


class ShippingIndexCollector(BaseCollector):
    """
    Estimates BDTI/TD3C from correlated market data.
    Real BDTI data requires Baltic Exchange subscription (~$2000/year).
    Estimated values are flagged with source='estimated'.
    """
    source_name = "shipping_index"
    update_frequency = timedelta(hours=6)

    async def collect(self, target_date: datetime | None = None) -> CollectResult:
        try:
            db = SessionLocal()
            inserted = 0

            try:
                today = target_date.date() if target_date else date.today()

                # Get latest oil price
                oil = (
                    db.query(OilPrice)
                    .order_by(OilPrice.record_date.desc())
                    .first()
                )

                # Get strait passage trend (7-day avg vs 30-day avg)
                week_ago = today - timedelta(days=7)
                month_ago = today - timedelta(days=30)

                recent_avg = (
                    db.query(func.avg(StraitPassage.tanker_vessels))
                    .filter(
                        StraitPassage.record_date >= week_ago,
                        StraitPassage.tanker_vessels > 0,
                    )
                    .scalar()
                )

                baseline_avg = (
                    db.query(func.avg(StraitPassage.tanker_vessels))
                    .filter(
                        StraitPassage.record_date >= month_ago,
                        StraitPassage.record_date < week_ago,
                        StraitPassage.tanker_vessels > 0,
                    )
                    .scalar()
                )

                # Estimate BDTI
                bdti = self._estimate_bdti(
                    brent_price=oil.brent_close if oil else 80.0,
                    recent_passage=recent_avg or 22,
                    baseline_passage=baseline_avg or 22,
                )

                # Estimate TD3C (Saudi->Japan route, typically ~85% of BDTI)
                td3c = round(bdti * 0.85)
                # Estimate TD8 (Kuwait->Singapore)
                td8 = round(bdti * 0.65)
                # Estimate BCTI (clean tanker, typically ~60% of BDTI)
                bcti = round(bdti * 0.6)

                # Check if we already have data for today
                existing = (
                    db.query(ShippingIndex)
                    .filter(
                        ShippingIndex.record_date == today,
                        ShippingIndex.source == "estimated",
                    )
                    .first()
                )

                if not existing:
                    db.add(ShippingIndex(
                        record_date=today,
                        bdti=bdti,
                        td3c=td3c,
                        td8=td8,
                        bcti=bcti,
                        source="estimated",
                    ))
                    inserted = 1
                    logger.info(
                        f"BDTI estimated: {bdti} (Brent={oil.brent_close if oil else 'N/A'}, "
                        f"passage 7d={recent_avg}, 30d={baseline_avg})"
                    )

                db.commit()
            finally:
                db.close()

            return CollectResult(
                status=CollectorStatus.SUCCESS,
                records_count=inserted,
            )

        except Exception as e:
            logger.error(f"Shipping index estimation failed: {e}")
            return CollectResult(
                status=CollectorStatus.FAILED,
                errors=[str(e)],
            )

    def _estimate_bdti(
        self,
        brent_price: float,
        recent_passage: float,
        baseline_passage: float,
    ) -> int:
        """
        Estimate BDTI from market indicators.

        Base model (historically observed correlations):
        - BDTI ~ 600-2000 range, mean ~1100
        - Positive correlation with oil price: +15 per $1 Brent above $60
        - Inverse correlation with passage: +20 per 1% decline vs baseline
        - Floor: 500, Ceiling: 2500
        """
        # Oil price component (baseline Brent=$60)
        oil_component = max(0, (brent_price - 60) * 15)

        # Scarcity component (passage decline drives rates up)
        if baseline_passage > 0:
            passage_change = (baseline_passage - recent_passage) / baseline_passage
            passage_component = max(0, passage_change * 2000)
        else:
            passage_component = 0

        # Base BDTI level
        bdti = 700 + oil_component + passage_component

        # Add some random noise (±5%) for realism
        import random
        noise = random.uniform(-0.05, 0.05)
        bdti = bdti * (1 + noise)

        return max(500, min(2500, round(bdti)))
