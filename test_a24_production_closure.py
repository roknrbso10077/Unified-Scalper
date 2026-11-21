"""A24 regressions: truthful starvation clock, stage labels, exact attribution, and frozen release seal."""
from collections import deque
import main as bot


def test_a24_logic_is_preserved_under_a26_startup_closure_and_never_relaxes_live_floor():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A25_CANONICAL_REVISION)
    assert bot.V702_A24_CANONICAL_REVISION in bot.V702_PACKAGE_AUDIT_REVISION
    assert "A24-TRUTHFUL-STARVATION-TELEMETRY-EXACT-ATTRIBUTION-CLOSURE" in bot.V702_A24_CANONICAL_REVISION
    assert "A25-STARTUP-VALIDATION-ORDER-DIAGNOSTICS-CLOSURE" in bot.V702_A25_CANONICAL_REVISION
    assert "A26-MONOTONIC-VALIDATION-REVISION-COMPATIBILITY-CLOSURE" in bot.V702_PACKAGE_AUDIT_REVISION
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["MIN_PAPER_SCORE"] < bot.CONFIG["MIN_LIVE_SCORE"]
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert bot.CONFIG.get("ENABLE_FUTURES", False) is False
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_no_send_clock_uses_most_recent_available_source_not_maximum():
    old_stats = {k: bot.STATS.get(k) for k in ("last_signal_sent_ts", "v45_no_send_sec")}
    old_last = getattr(bot.V422StarvationAlerter, "_last_send_ts", None)
    old_wall_provider, old_mono_provider = bot.WALL_NOW, bot.MONO_NOW
    wall_now, mono_now = 1_800_000_000.0, 10_000.0
    try:
        bot.WALL_NOW = lambda: wall_now
        bot.MONO_NOW = lambda: mono_now
        bot.STATS["last_signal_sent_ts"] = wall_now - 5400
        bot.STATS["v45_no_send_sec"] = 4200.0
        bot.V422StarvationAlerter._last_send_ts = mono_now - 180.0
        ages = bot._v704_no_send_age_sources()
        assert ages
        assert abs(bot._v704_no_send_age_sec() - min(ages.values())) < 1e-4
        assert bot._v704_no_send_age_sec() < 300.0
        assert bot._v704_starvation_state()["age_rule"] == "MIN_AVAILABLE_SOURCE_AGE_FAIL_CLOSED"
    finally:
        bot.WALL_NOW, bot.MONO_NOW = old_wall_provider, old_mono_provider
        for key, value in old_stats.items():
            if value is None:
                bot.STATS.pop(key, None)
            else:
                bot.STATS[key] = value
        if old_last is None:
            try:
                delattr(bot.V422StarvationAlerter, "_last_send_ts")
            except AttributeError:
                pass
        else:
            bot.V422StarvationAlerter._last_send_ts = old_last


def test_relief_can_remove_secondary_elite_floor_but_never_admits_score_below_70():
    saved = {k: bot.STATS.get(k) for k in ("last_signal_sent_ts", "v45_no_send_sec", "v681_runtime_cycle_ranked", "v681_runtime_cycle_selected")}
    old_last = getattr(bot.V422StarvationAlerter, "_last_send_ts", None)
    old_truth = getattr(bot, "_v699_truthful_starvation_snapshot", None)
    old_hazard = getattr(bot, "_v704_market_hazard", None)
    try:
        wall_now, mono_now = bot.WALL_NOW(), bot.MONO_NOW()
        bot.STATS["last_signal_sent_ts"] = wall_now - 4500
        bot.STATS["v45_no_send_sec"] = 4400.0
        bot.V422StarvationAlerter._last_send_ts = mono_now - 4300
        bot.STATS["v681_runtime_cycle_ranked"] = 4
        bot.STATS["v681_runtime_cycle_selected"] = 2
        bot._v699_truthful_starvation_snapshot = lambda: {"root": "SCORE", "detail": "score_starvation"}
        bot._v704_market_hazard = lambda: False
        allowed, meta = bot._v704_starvation_score_floor_override({"family": "PULLBACK"}, 74.0, 76.0)
        blocked, below = bot._v704_starvation_score_floor_override({"family": "PULLBACK"}, 69.99, 76.0)
        assert allowed is True and meta["effective_floor"] == 70.0
        assert blocked is False and below["reason"] == "score_below_hard_global_floor"
    finally:
        for key, value in saved.items():
            if value is None:
                bot.STATS.pop(key, None)
            else:
                bot.STATS[key] = value
        if old_last is None:
            try:
                delattr(bot.V422StarvationAlerter, "_last_send_ts")
            except AttributeError:
                pass
        else:
            bot.V422StarvationAlerter._last_send_ts = old_last
        if old_truth is None:
            bot.__dict__.pop("_v699_truthful_starvation_snapshot", None)
        else:
            bot._v699_truthful_starvation_snapshot = old_truth
        if old_hazard is None:
            bot.__dict__.pop("_v704_market_hazard", None)
        else:
            bot._v704_market_hazard = old_hazard


def test_long_reason_digest_tokens_do_not_merge_shared_prefixes():
    metrics = bot.V702PipelineMetrics
    old_events = metrics._events
    reasons = [
        "score_below_threshold:62.1ceil=0.2200%:tier=MID",
        "score_below_threshold:62.1ceil=0.2300%:tier=MID",
    ]
    try:
        metrics._events = deque([
            {"ts": 100.0, "stage": "REJECT", "candidate_key": f"A34-C{i}",
             "symbol": "TEST/USDT", "details": {"stage": "prequal", "reason": reason}}
            for i, reason in enumerate(reasons)
        ], maxlen=4096)
        line = metrics.window_line(interval_sec=900.0, now=101.0)
        tokens = [bot._v702_reason_summary_token(reason, 32) for reason in reasons]
        assert tokens[0] != tokens[1]
        assert all(len(token) <= 32 for token in tokens)
        assert "record_top=" in line
        assert all(token in line for token in tokens), line
        spread_reason = "liquidity.spread=0.4002%>ceil=0.3000%:tier=MICRO"
        spread_token = bot._v702_reason_summary_token(spread_reason, 40)
        assert spread_token == "spread:0.4002>0.3000:MICRO", spread_token
        assert "ceil=0" not in spread_token
    finally:
        metrics._events = old_events


def test_digest_classifier_splits_scorer_route_and_real_builder_block():
    classifier = bot._V702R28TelegramDigest.classify
    assert classifier("Selected → Builder BLOCK\nSOL/USDT\nroot=SCORE\nstage=scorer\nreason=score_below_threshold:65<70") == "scorer_block"
    assert classifier("Selected → Builder BLOCK\nSOL/USDT\nroot=POLICY\nstage=selected_preexec_policy\nreason=blocked") == "route_block"
    assert classifier("Selected → Builder BLOCK\nSOL/USDT\nroot=BUILDER\nstage=builder\nreason=builder_returned_none") == "builder_block"


def test_digest_buffers_and_headings_keep_block_stages_separate():
    digest = bot._V702R28TelegramDigest
    saved = (digest._events, digest._category_counts, digest._scorer_blocks, digest._route_blocks, digest._selected_blocks)
    try:
        digest._events = 3
        from collections import defaultdict
        digest._category_counts = defaultdict(int, {"scorer_block": 1, "route_block": 1, "builder_block": 1})
        digest._scorer_blocks = deque(["Selected → Builder BLOCK\nSOL/USDT\nroot=SCORE\nstage=scorer\nreason=score_below_threshold:66<70"], maxlen=20)
        digest._route_blocks = deque(["Selected → Builder BLOCK\nINJ/USDT\nroot=POLICY\nstage=selected_preexec_policy\nreason=blocked"], maxlen=20)
        digest._selected_blocks = deque(["Selected → Builder BLOCK\nTIA/USDT\nroot=BUILDER\nstage=builder\nreason=builder_returned_none"], maxlen=20)
        rendered = digest.build()
        assert "SELECTED → SCORER BLOCK" in rendered
        assert "SELECTED → ROUTE BLOCK" in rendered
        assert "SELECTED → BUILDER BLOCK" in rendered, f"len={len(rendered)} max={bot.CONFIG.get('V702_R28_TELEGRAM_DIGEST_MAX_CHARS')} content={rendered!r}"
    finally:
        digest._events, digest._category_counts, digest._scorer_blocks, digest._route_blocks, digest._selected_blocks = saved


def test_score_rejection_records_distinct_score_block_metric():
    metrics = bot.V702PipelineMetrics
    old_enabled = metrics._enabled
    old_cycle = metrics._cycle_id
    old_counts = metrics._epoch_counts
    old_keys = metrics._cycle_keys
    old_events = metrics._events
    old_context = bot._V702_PIPELINE_CONTEXT.get()
    from collections import defaultdict, deque
    try:
        metrics._enabled = True
        metrics._cycle_id = metrics._cycle()
        metrics._epoch_counts = defaultdict(int)
        metrics._cycle_keys = defaultdict(set)
        metrics._events = deque(maxlen=4096)
        bot._V702_PIPELINE_CONTEXT.set({"candidate_key": "A24|SOL/USDT|PULLBACK|TEST|1", "symbol": "SOL/USDT", "family": "PULLBACK"})
        bot._v702_record_rejection_with_metrics("trace-a24", "SOL/USDT", "score", "score_below_threshold:66<70", "scorer", None, {"score": 66, "min_score": 70})
        assert metrics.snapshot()["cycle_counts"].get("SCORE_BLOCK", 0) == 1
        assert "SCORE_BLOCK" in metrics.STAGES
    finally:
        metrics._enabled = old_enabled
        metrics._cycle_id = old_cycle
        metrics._epoch_counts = old_counts
        metrics._cycle_keys = old_keys
        metrics._events = old_events
        bot._V702_PIPELINE_CONTEXT.set(old_context)


def test_stale_candidate_reason_is_not_reused_as_current_builder_reason():
    key = f"{bot.V702PipelineMetrics._cycle()}|A24TEST/USDT|PULLBACK|UNKNOWN|stale"
    now = bot.WALL_NOW()
    store = bot.STATS.setdefault("v702_builder_rejection_by_candidate", {})
    prior = store.get(key)
    store[key] = {"candidate_key": key, "symbol": "A24TEST/USDT", "stage": "builder", "reason": "stale", "ts": now - 10, "cycle_id": bot.V702PipelineMetrics._cycle()}
    try:
        assert bot._v702_builder_rejection_reason_for_candidate(key, now) is None
    finally:
        if prior is None:
            store.pop(key, None)
        else:
            store[key] = prior


def test_a23_and_a24_runtime_closures_pass():
    a23 = bot._v702_a23_terminal_self_test()
    a24 = bot._v702_a24_terminal_self_test()
    assert a23["pass"], a23
    assert a24["pass"], a24
