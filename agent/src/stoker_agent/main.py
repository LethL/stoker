import argparse
import asyncio
import contextlib
import signal
from collections.abc import Generator
from pathlib import Path

import uvicorn
from prometheus_client import make_asgi_app

from stoker_agent.config import AgentSettings, load_settings
from stoker_agent.metrics import update_fake_metrics


class _NoSignalServer(uvicorn.Server):
    """uvicorn.Server, не перехватывающий сигналы.

    learn: штатный Server в serve() оборачивается в capture_signals(): ставит свои
    обработчики SIGTERM/SIGINT и на выходе ПЕРЕподнимает пойманный сигнал — это
    убивало бы процесс до нашего чистого возврата. Здесь сигналами управляет наш
    stop-event (единая точка graceful-выхода), поэтому перехват отключаем.
    """

    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None]:
        yield


async def _run_metrics_server(settings: AgentSettings, stop: asyncio.Event) -> None:
    # learn: make_asgi_app() отдаёт текущий registry как ASGI-приложение —
    # сервим его на uvicorn в том же event loop (без отдельного потока).
    app = make_asgi_app()
    config = uvicorn.Config(
        app,
        host=settings.metrics_host,
        port=settings.metrics_port,
        log_level="warning",
    )
    server = _NoSignalServer(config)
    serve_task = asyncio.create_task(server.serve())
    await stop.wait()
    server.should_exit = True  # graceful: uvicorn дослуживает и выходит
    await serve_task


async def _run_poller(settings: AgentSettings, stop: asyncio.Event) -> None:
    tick = 0
    while not stop.is_set():
        update_fake_metrics(settings.rig_id, settings.fake_gpu_count, tick)
        tick += 1
        # learn: ждём интервал, но мгновенно просыпаемся при stop — не тормозим shutdown.
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=settings.poll_interval_s)


async def run(settings: AgentSettings) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    # learn: SIGTERM (от systemd) и SIGINT (Ctrl-C) ставят stop → graceful shutdown.
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    # learn: TaskGroup (3.11+) — structured concurrency: супервизит обе задачи,
    # при падении одной отменяет вторую. Обе штатно выходят по stop.
    async with asyncio.TaskGroup() as tg:
        tg.create_task(_run_metrics_server(settings, stop))
        tg.create_task(_run_poller(settings, stop))


def main() -> None:
    parser = argparse.ArgumentParser(prog="stoker-agent")
    parser.add_argument("--config", type=Path, required=True, help="путь к TOML-конфигу")
    args = parser.parse_args()
    settings = load_settings(args.config)
    asyncio.run(run(settings))
