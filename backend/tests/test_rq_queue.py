"""Medium test: needs the `redis` service from docker-compose running."""
import uuid

from redis import Redis
from rq import Queue

from app.core.config import settings
from app.services.queue import RQDocumentQueue


def test_enqueue_document_puts_process_job_on_queue():
    q = Queue(f"test-{uuid.uuid4().hex[:8]}", connection=Redis.from_url(settings.redis_url))
    doc_id = uuid.uuid4()

    RQDocumentQueue(q).enqueue_document(doc_id)

    [job] = q.get_jobs()
    assert job.func_name == "app.workers.process_document.process_document"
    assert job.args == (str(doc_id),)
    assert job.timeout == 180  # plan 7.2: 3-minute limit per document
    q.empty()


def test_enqueue_whatsapp_puts_handler_job_on_queue():
    q = Queue(f"test-{uuid.uuid4().hex[:8]}", connection=Redis.from_url(settings.redis_url))
    msg = {"from": "919812345210", "id": "wamid.A", "type": "text", "text": {"body": "hi"}}

    RQDocumentQueue(q).enqueue_whatsapp(msg)

    [job] = q.get_jobs()
    assert job.func_name == "app.workers.whatsapp.handle_whatsapp_message"
    assert job.args == (msg,)
    q.empty()
