from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from openminion.base.channel import ChannelRegistry
from openminion.base.types import Message
from openminion.modules.storage.runtime.idempotency_store import IdempotencyStore
from openminion.modules.storage.runtime.migrations import migrate_database
from openminion.modules.storage.runtime.session_store import SessionStore
from openminion.modules.storage.runtime.sqlite import connect_database
from openminion.services.gateway.service import GatewayService
from openminion.services.runtime.run_status import RUN_CHECKPOINT_EVENT_TYPE
from openminion.services.runtime.verifier_binding import (
    TERMINAL_STATE_PROVENANCE_FIELD,
    TERMINAL_STATE_PROVENANCE_TYPED,
)

from tests.eval.integration.ameb_phase2_runner import (
    _coding_simple_spec,
    run_gateway_benchmark_turn,
)


class _SinkChannel:
    def __init__(self, *, name: str = "console") -> None:
        self.name = name
        self.sent: list[Message] = []

    def send(self, message: Message) -> None:
        self.sent.append(message)


class _StaticAgent:
    async def run_turn(self, message: Message, history=None, **_kwargs):
        del history, _kwargs
        return type(
            "_Response",
            (),
            {
                "text": f"ack::{message.body}",
                "channel": message.channel,
                "target": message.target,
                "metadata": {},
            },
        )()


def _build_gateway() -> tuple[GatewayService, SessionStore]:
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "state" / "openminion.db"
    migrate_database(db_path)
    connection = connect_database(db_path)
    sessions = SessionStore(connection)
    idempotency = IdempotencyStore(connection)
    gateway = GatewayService(
        agent=_StaticAgent(),  # type: ignore[arg-type]
        channels=ChannelRegistry([_SinkChannel()]),
        logger=logging.getLogger("gtgs-ameb-test"),
        sessions=sessions,
        idempotency=idempotency,
        agent_id="gtgs-agent",
    )
    gateway._gtgs_tmp = tmp  # type: ignore[attr-defined]
    gateway._gtgs_connection = connection  # type: ignore[attr-defined]
    return gateway, sessions


def _cleanup_gateway(gateway: GatewayService) -> None:
    gateway._gtgs_connection.close()  # type: ignore[attr-defined]
    gateway._gtgs_tmp.cleanup()  # type: ignore[attr-defined]


def test_ameb_harness_runs_benchmark_turn_through_gtgs_gateway_path() -> None:
    gateway, sessions = _build_gateway()
    try:
        response = asyncio.run(
            run_gateway_benchmark_turn(
                gateway=gateway,
                spec=_coding_simple_spec(),
                session_id="ameb-gtgs",
            )
        )
        session_id = response.metadata["session_id"]
        events = sessions.list_events(
            session_id=session_id,
            limit=100,
            newest_first=False,
        )
        event_types = [event.event_type for event in events]
        assert RUN_CHECKPOINT_EVENT_TYPE in event_types
        terminal_events = [
            event
            for event in events
            if event.event_type in {"run.completed", "run.failed", "run.blocked"}
        ]
        assert terminal_events
        terminal = terminal_events[-1]
        assert (
            terminal.payload[TERMINAL_STATE_PROVENANCE_FIELD]
            == TERMINAL_STATE_PROVENANCE_TYPED
        )
    finally:
        _cleanup_gateway(gateway)
