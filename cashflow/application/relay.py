import json
import logging

from cashflow.application.ports import EventTransport, Outbox, PermanentDeliveryError

logger = logging.getLogger(__name__)


def deliver_batch(outbox: Outbox, transport: EventTransport) -> int:
    delivered = 0
    for row in outbox.due():
        try:
            transport.send(json.loads(row["payload"]))
        except PermanentDeliveryError:
            outbox.failed(row["id"], row["attempts"], permanent=True)
            logger.error("event_quarantined event_id=%s", row["id"])
        except Exception:
            outbox.failed(row["id"], row["attempts"])
            logger.warning("delivery_retry event_id=%s attempt=%s", row["id"], row["attempts"] + 1)
        else:
            outbox.delivered(row["id"])
            delivered += 1
    return delivered
