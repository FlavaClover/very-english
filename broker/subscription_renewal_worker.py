import logging

from broker.worker import Worker
from billing.yookassa_client import YooKassaClient
from infra.payments import PaymentsPg
from infra.subscriptions import SubscriptionsPg
from services.subscription import SubscriptionService
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class SubscriptionRenewalWorker(Worker):
    def __init__(
        self,
        engine: AsyncEngine,
        gateway: YooKassaClient,
        interval_seconds: float,
    ) -> None:
        super().__init__(interval_seconds)
        self._engine = engine
        self._gateway = gateway

    async def execute(self) -> None:
        try:
            async with self._engine.begin() as conn:
                service = SubscriptionService(
                    payments=PaymentsPg(conn),
                    subscriptions=SubscriptionsPg(conn),
                    gateway=self._gateway,
                )
                await service.run_renewal_batch()
            logger.info("Renewal batch iteration completed")
        except Exception:
            logger.exception("Renewal batch failed")
