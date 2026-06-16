import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.collectors.collector_manager import collector_manager
from app.collectors.portwatch_collector import PortWatchCollector
from app.collectors.firms_collector import FIRMSCollector
from app.collectors.oil_price_collector import OilPriceCollector
from app.collectors.ukmto_collector import UKMTOCollector
from app.collectors.shipping_index_collector import ShippingIndexCollector
from app.config import settings
from app.services.risk_engine import get_risk_engine
from app.services.data_validator import get_validator

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def register_collectors():
    collector_manager.register(PortWatchCollector())
    collector_manager.register(FIRMSCollector())
    collector_manager.register(OilPriceCollector())
    collector_manager.register(UKMTOCollector())
    collector_manager.register(ShippingIndexCollector())
    logger.info(f"Registered {len(collector_manager.collectors)} collectors")


async def run_all_collectors():
    logger.info("Scheduled collection started")
    results = await collector_manager.collect_all()
    for name, result in results.items():
        logger.info(f"  {name}: {result.status.value} ({result.records_count} records)")
    logger.info("Scheduled collection completed")

    # Validate data quality
    try:
        validator = get_validator()
        validation = validator.validate()
        validator.close()
        if not validation.is_valid:
            logger.warning(f"Data validation FAILED (score={validation.overall_score:.0%}): "
                           f"{validation.freshness_issues + validation.value_issues}")
        else:
            logger.info(f"Data validation OK (score={validation.overall_score:.0%})")
    except Exception as e:
        logger.error(f"Data validation error: {e}")

    # Run risk assessment after collection + validation
    try:
        engine = get_risk_engine()
        result = engine.assess()
        logger.info(f"Risk assessment: Level {result.level.value} ({result.label}), "
                     f"confidence={result.confidence:.0%}")
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")


def start_scheduler():
    register_collectors()

    # Hourly data collection (for real-time monitoring)
    scheduler.add_job(
        run_all_collectors,
        trigger=IntervalTrigger(hours=1),
        id="collect_hourly",
        name="Hourly data collection + risk assessment",
        replace_existing=True,
    )

    # Daily comprehensive risk assessment at configured hour
    scheduler.add_job(
        _run_risk_assessment,
        trigger=CronTrigger(hour=settings.RISK_ASSESSMENT_HOUR, minute=30),
        id="risk_assessment",
        name="Daily risk assessment",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: hourly collection + daily risk assessment at "
        f"{settings.RISK_ASSESSMENT_HOUR}:30"
    )


async def _run_risk_assessment():
    try:
        validator = get_validator()
        validation = validator.validate()
        validator.close()

        engine = get_risk_engine()
        result = engine.assess()
        logger.info(
            f"Daily risk assessment: Level {result.level.value} ({result.label}), "
            f"validation={validation.overall_score:.0%}"
        )
    except Exception as e:
        logger.error(f"Daily risk assessment failed: {e}")
