import asyncio
from threading import Event

from httpx import ASGITransport, AsyncClient

from app import main
from app.sample import SAMPLE


def test_health_responds_while_decode_is_waiting(monkeypatch):
    started = Event()
    release = Event()

    def slow_decode(image):
        started.set()
        if not release.wait(timeout=10):
            raise TimeoutError("decode was not released")
        return SAMPLE

    monkeypatch.setattr(main, "decode", slow_decode)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    async def scenario():
        async with AsyncClient(
            transport=ASGITransport(app=main.app), base_url="http://test"
        ) as client:
            decoding = asyncio.create_task(
                client.post("/decode", files={"file": ("a.jpg", b"fake", "image/jpeg")})
            )
            try:
                assert await asyncio.to_thread(started.wait, 3)
                health = await asyncio.wait_for(client.get("/health"), timeout=3)
                assert health.status_code == 200
                assert health.json() == {"ok": True, "sample_mode": True, "commit": main.COMMIT}
                assert not decoding.done()
            finally:
                release.set()
                decoded = await asyncio.wait_for(decoding, timeout=3)
            assert decoded.status_code == 200
            assert decoded.json() == SAMPLE.model_dump()

    asyncio.run(scenario())
