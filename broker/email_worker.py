import logging

from broker.worker import Worker
from auth.email_verification import EmailSender
from infra.email_verification import RedisEmailQueue
from services.email_verification import EMAIL_VERIFICATION_SUBJECT

logger = logging.getLogger(__name__)


class EmailWorker(Worker):
    def __init__(
        self,
        queue: RedisEmailQueue,
        sender: EmailSender,
        interval_seconds: float,
        dequeue_timeout_seconds: int = 5,
    ) -> None:
        super().__init__(interval_seconds)
        self._queue = queue
        self._sender = sender
        self._dequeue_timeout_seconds = dequeue_timeout_seconds

    async def execute(self) -> None:
        message = await self._queue.dequeue(
            timeout_seconds=self._dequeue_timeout_seconds
        )
        if message is None:
            return
        try:
            await self._sender.send(message)
        except Exception:
            logger.exception("Не удалось отправить письмо на %s", message.to)
            raise
        if message.subject == EMAIL_VERIFICATION_SUBJECT:
            logger.info("Код подтверждения отправлен на %s", message.to)
        else:
            logger.info("Письмо отправлено на %s", message.to)
