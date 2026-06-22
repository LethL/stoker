from httpx import ASGITransport, AsyncClient

from stoker_server import __version__
from stoker_server.main import app


async def test_healthz() -> None:
    # learn: ASGITransport бьёт прямо в приложение, без поднятия сети/порта —
    # быстро и детерминированно (паттерн из research 0005).
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok", "service": "stoker-server", "version": __version__}
