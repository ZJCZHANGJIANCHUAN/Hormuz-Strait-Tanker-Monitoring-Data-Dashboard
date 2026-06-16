import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from app.collectors.base import BaseCollector, CollectResult, CollectorStatus
from app.config import settings
from app.database import SessionLocal
from app.models import CollectionLog

logger = logging.getLogger(__name__)


class CollectorManager:
    def __init__(self):
        self.collectors: dict[str, BaseCollector] = {}
        self.http_client: Optional[httpx.AsyncClient] = None

    def register(self, collector: BaseCollector):
        self.collectors[collector.source_name] = collector
        logger.info(f"Registered collector: {collector.source_name}")

    async def _get_client(self) -> httpx.AsyncClient:
        if self.http_client is None:
            proxy = settings.HTTP_PROXY or settings.HTTPS_PROXY or None
            if proxy and not proxy.startswith(("http://", "https://", "socks5://")):
                proxy = None  # ignore invalid proxy strings
            self.http_client = httpx.AsyncClient(
                timeout=30,
                proxy=proxy,
                follow_redirects=True,
            )
        return self.http_client

    async def collect_all(self) -> dict[str, CollectResult]:
        if not self.collectors:
            logger.warning("No collectors registered")
            return {}

        client = await self._get_client()
        tasks = []
        for name, collector in self.collectors.items():
            tasks.append(self._collect_with_log(name, collector, client))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = {}
        for name, result in zip(self.collectors.keys(), results):
            if isinstance(result, Exception):
                output[name] = CollectResult(
                    status=CollectorStatus.FAILED,
                    errors=[str(result)],
                )
            else:
                output[name] = result
        return output

    async def collect_one(self, name: str) -> CollectResult:
        collector = self.collectors.get(name)
        if not collector:
            return CollectResult(status=CollectorStatus.FAILED, errors=[f"Unknown collector: {name}"])

        client = await self._get_client()
        return await self._collect_with_log(name, collector, client)

    async def _collect_with_log(
        self, name: str, collector: BaseCollector, client: httpx.AsyncClient
    ) -> CollectResult:
        started_at = datetime.utcnow()
        retry_count = 0
        result = None

        try:
            collector.http_client = client
            result = await collector.collect()
        except Exception as e:
            result = CollectResult(status=CollectorStatus.FAILED, errors=[str(e)])
            logger.error(f"Collector {name} failed: {e}")

        self._save_log(name, started_at, result, retry_count)
        return result

    def _save_log(self, name: str, started_at: datetime, result: CollectResult, retry_count: int):
        try:
            db = SessionLocal()
            log = CollectionLog(
                collector_name=name,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                status=result.status.value,
                records_inserted=result.records_count,
                error_message="; ".join(result.errors) if result.errors else None,
                retry_count=retry_count,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save collection log: {e}")
        finally:
            db.close()

    async def close(self):
        if self.http_client:
            await self.http_client.aclose()


collector_manager = CollectorManager()
