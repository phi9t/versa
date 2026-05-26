from __future__ import annotations

import pytest

pytest.importorskip("textual")

from versa.gather.factory import make_gather_session
from versa.gather.tui.app import GatherApp


@pytest.mark.asyncio
async def test_gather_app_pilot_loads():
    session = make_gather_session(mock=True)
    app = GatherApp(session, task_id="tui-pilot")
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        stats = app.query_one("#stats-bar")
        assert "Gathering" in str(stats.render())
        assert app.snapshot is not None
        assert app.snapshot.task_id == "tui-pilot"
