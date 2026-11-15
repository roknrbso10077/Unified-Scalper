from collections import defaultdict, deque

import pytest

import main as bot


def _row(category, symbol):
    return {
        "category": category,
        "symbol": symbol,
        "root": "SCORE",
        "stage": "scorer",
        "reason": "score_below_threshold",
        "recorded_ts": 1.0,
        "raw": f"SELECTED → SCORER BLOCK {symbol}/USDT root=SCORE stage=scorer reason=score_below_threshold",
    }


def _seed_digest(monkeypatch, structured):
    digest = bot._V702R28TelegramDigest
    monkeypatch.setattr(bot, "_V702_A37_STRUCTURED_BLOCKS", structured)
    monkeypatch.setattr(digest, "_events", 3)
    monkeypatch.setattr(digest, "_category_counts", defaultdict(int, {"scorer_block": 1}))
    monkeypatch.setattr(digest, "_heartbeat", "heartbeat=test")
    monkeypatch.setattr(digest, "_starvation", "starvation=test")
    monkeypatch.setattr(digest, "_edge", "edge=test")
    monkeypatch.setattr(digest, "_latest_rejection", "reject=test")
    monkeypatch.setattr(digest, "_rejection_captured", 1)
    monkeypatch.setattr(digest, "_selected_blocks", deque(["legacy-builder"]))
    monkeypatch.setattr(digest, "_scorer_blocks", deque(["legacy-scorer"]))
    monkeypatch.setattr(digest, "_route_blocks", deque(["legacy-route"]))
    monkeypatch.setattr(digest, "_shadow_events", deque(["shadow"]))
    monkeypatch.setattr(digest, "_discovery_by_symbol", {})
    monkeypatch.setattr(digest, "_periodic_summary", "summary=test")
    monkeypatch.setattr(digest, "_last_flush_ts", 0.0)
    monkeypatch.setattr(digest, "_started_ts", 0.0)
    monkeypatch.setattr(digest, "build", classmethod(lambda cls: "A62 test digest"))
    return digest


@pytest.mark.asyncio
async def test_a62_successful_digest_delivery_clears_every_structured_block_queue(monkeypatch):
    structured = {
        "scorer_block": deque([_row("scorer_block", "AAA")]),
        "route_block": deque([_row("route_block", "BBB")]),
        "builder_block": deque([_row("builder_block", "CCC")]),
    }
    digest = _seed_digest(monkeypatch, structured)

    async def _successful_enqueue(*args, **kwargs):
        return True

    monkeypatch.setattr(bot, "_V702_R28_RAW_ENQUEUE", _successful_enqueue)
    delivered = await digest.flush(force=True)

    assert delivered is True
    assert all(not queue for queue in structured.values())
    assert digest._events == 0
    assert digest._periodic_summary == ""
    assert bot.STATS.get("v702_a62_structured_block_reset_wired") is True


@pytest.mark.parametrize("failure_mode", ["false", "exception"])
@pytest.mark.asyncio
async def test_a62_failed_digest_delivery_keeps_structured_rows_for_retry(monkeypatch, failure_mode):
    structured = {
        "scorer_block": deque([_row("scorer_block", "AAA")]),
        "route_block": deque([_row("route_block", "BBB")]),
        "builder_block": deque([_row("builder_block", "CCC")]),
    }
    digest = _seed_digest(monkeypatch, structured)

    async def _failed_enqueue(*args, **kwargs):
        if failure_mode == "exception":
            raise RuntimeError("simulated Telegram transport failure")
        return False

    monkeypatch.setattr(bot, "_V702_R28_RAW_ENQUEUE", _failed_enqueue)
    delivered = await digest.flush(force=True)

    assert delivered is False
    assert all(len(queue) == 1 for queue in structured.values())
    assert {queue[0]["symbol"] for queue in structured.values()} == {"AAA", "BBB", "CCC"}


def test_a62_release_self_test_keeps_live_entry_policy_fail_closed():
    report = bot._v702_a62_self_test()
    assert report["pass"] is True, report
    assert bot.V702_FINAL_CANONICAL_RELEASE == "UNIFIED-SCALPER-V702-A64-CANONICAL-FINAL"
    assert bot.FINAL_CANONICAL_RUNTIME["production_decision"] == "NO_GO_UNATTENDED_LIVE"
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.FINAL_CANONICAL_RUNTIME["live_gates_relaxed"] is False
