# A76 — Micro Shadow, Liquidity Evidence and Log Root-Cause Closure (2026-11-17)

**Active supplemental feature revision:** `A76-MICRO-SHADOW-ALERT-FAIR-ROTATION-LIQUIDATION-EVIDENCE-CONTRACT-2026-11-17`  
**Canonical distribution identity:** A66/A70 lineage retained.  
**Archive ceiling:** 99 files; no files added or removed.  
**Production disposition:** `MONITOR_ONLY_NO_NEW_BUYS` / `NO_GO_UNATTENDED_LIVE`.

## A76 root-cause findings from the supplied operator digests

1. The primary MSE candidate funnel is blocked before Selection, Builder and Telegram in the supplied bearish-BTC windows. The 30-minute windows show `DISC/RANK/PRE` progress but `PASS=0`, `SEL=0`, `BUILDER=0`, `QUEUE=0`, `TG=0`. The dominant rejection is `family_regime_disallowed.macro` (examples in the supplied digest: 170/178, 186/219, 212/232 and 350/370 reject records); `policy_ctx_top=PULLBACK@BEARISH[allow=BULLISH+NEUTRAL]` confirms the explicit family policy. This is not a Telegram transport failure: the canonical candidate never reaches the handoff stages. The policy has not been loosened.
2. `MICRO_TREND_CONTINUATION` is a core LONG strategy governed by strategy-family and higher-timeframe policy. In the current `BEARISH` BTC regime its BULLISH/NEUTRAL eligibility can correctly reject it. A76 does not add a bearish bypass or turn this core strategy into an always-on long entry.
3. The separate A9 `MICRO_*_1M` engines were `SHADOW_ONLY`: their samples were persisted to SQLite, but there was no independent Telegram alert handoff. Consequently a valid 1m research pattern could exist without an operator message.
4. The A9 rotating cohort had a confirmed allocation defect: top relative-strength leaders were prepended to the combined selection and the list was truncated at the batch ceiling. This could consume reserved places and starve the micro-liquidity pool. A76 confines RS preference to core slots and preserves the rotating micro quota when eligible micro symbols exist.
5. The supplied digest also shows a measured spread rejection at `0.5269%` above the configured ceiling. That is a real cost/liquidity rejection, not a reason to lower the spread gate. A76 keeps observed spread, conservative fallback costs, fee coverage and post-cost target checks unchanged.

## A76 changes implemented

- **Fair Micro cohort:** balanced core/micro selection, independent rotation offsets, a bounded RS leader preference that cannot displace micro slots, and explicit `core_selected`, `micro_selected`, and `rs_leaders` telemetry. If one pool is under-filled, unused places can be supplied from the other pool only after its reserved allocation is attempted.
- **Micro Shadow Telegram path:** every newly persisted eligible 1m `MICRO_MOMENTUM_1M`, `MICRO_SWEEP_RECLAIM_1M`, or `MICRO_PULLBACK_RECLAIM_1M` sample may create a durable SQLite alert record. A bounded scanner batch reads fresh records and calls the existing `TelegramDispatcher` outbox. The message says `MICRO SHADOW 1M — MONITOR ONLY`, includes reference Entry/Stop/Target, modeled round-trip cost and a post-cost viability label. Symbol cooldown, TTL expiry and per-batch cap bound message volume. A successful enqueue means durable queue admission, not Telegram delivery ACK.
- **Strict execution isolation:** the 1m lane remains outside `_MSE_ENGINES`, Selector, Builder, order sizing and exchange order APIs. `V702_INTRADAY_SHADOW_LIVE_ENABLE` remains hard-set to `False`; the global monitor-only entry policy is not changed. No alert is represented as a canonical confirmed opportunity or a live trade.
- **LSA evidence contract:** added `LSA_V1` validation for source, symbol, timestamp freshness, long liquidation burst, OI change, funding-rate decrease, Spot buy/sell flow and support reclaim. Defaults require a 2.5x liquidation burst, OI contraction of at least 2% over 15m, Spot buy share of at least 55%, falling funding and an explicit reclaim. Incomplete/stale/mismatched data is `UNAVAILABLE`; complete but failing evidence is `NOT_CONFIRMED`.
- **Provider limitation:** the A75 source package is Spot-only and contains no actual Futures liquidation, Open Interest, Funding or Spot CVD provider. A76 therefore adds the evidence contract and truthful `UNAVAILABLE` reporting only; it does not fabricate these observations, infer Smart Money identity, fetch an unconfigured data source or grant a new trading gate. A real provider and exchange-specific field mapping remain future integration work.
- **Strategy architecture:** the existing `LIQUIDITY_ACCEPTANCE_RECLAIM` is retained as the technical baseline; a duplicate LTR engine is not added. Narrative/Smart-Money wallet tracking, news/Parrondo switching and cash-secured Puts remain separate systems because they require on-chain labels, event feeds or options support that this Spot scalper does not have.

## A76 verification status

- Build-tree `python -m pytest -q`: **570 passed, 1 skipped, 0 failed**; 571 collected; one-process run completed in 31.06 seconds after syncing the canonical source digests. The one skip is `test_release_contracts.py:375`, which requires a historical A51 runtime log not included in the clean source archive.
- Clean-extracted ZIP test coverage: all **58 test modules** were run in non-overlapping batches; combined totals were **570 passed, 1 skipped, 0 failed**. A monolithic clean-extract attempt timed out at 63% before a summary and is not counted as a pass; modular batch coverage completed with zero failures.
- Targeted `python -m pytest -q test_v702_intraday_shadow.py`: **20 passed, 0 failed**. This includes balanced core/micro rotation, independent research alert persistence and queue-state handling, expiry/deduplication, LSA evidence freshness/schema validation, and missing-provider `UNAVAILABLE` behavior.
- `python -m compileall -q .`: PASS for all 73 packaged Python files.
- `python -u main.py --validate-only` from the clean-extracted ZIP: **PASS, exit code 0**; the validator returned `pass=true`, `bot_started=false`, and `live_threads=[]`. This is a one-shot offline validation, not a persistent deployment test.
- Final ZIP integrity: **99/99 unique paths**, CRC test PASS, exact manifest inventory PASS, and **98/98 SHA-256 entries matched** (`A66_SHA256SUMS.txt` excludes itself by design).
- The 5 intermediate test failures in the first final rerun were all the same stale `main.py` SHA-256 value in the two release manifests. Both manifests were synchronized and the subsequent full single-process suite completed with 570 passed, 1 skipped, and 0 failed.
- No live MEXC order/API test, Telegram network delivery ACK, configured Futures liquidation/OI/Funding/Spot-CVD provider, options/on-chain/news integration, Docker build, Railway deployment, or out-of-sample profitability test is claimed.

## Operating decision

A76 improves the visibility and sampling coverage of the independent 1m research lane. It does **not** fix the intentionally blocked bearish macro family policy by bypassing it, and it does not prove that the micro patterns are profitable. Continue monitor-only and evaluate the new research samples after modeled costs. A successful Telegram outbox enqueue is not an actual delivery ACK, and Shadow reference levels are not executable trade instructions.

---

# A71 — Integrated corrective production audit (2026-11-16)

**Active corrective layer:** `A71-BOOT-MEMORY-PM-COVERAGE-RESEARCH-RETENTION-2026-11-16`
**Canonical distribution tag:** `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL` (A70 package lineage retained)
**Archive ceiling:** 99 files; this integration edits existing package files only.
**Production disposition:** `NO_GO_UNATTENDED_LIVE` / `MONITOR_ONLY_NO_NEW_BUYS`.

## A71 integrated changes

- Replaced whole-file source introspection in startup contracts with bounded function-source extraction; LONG_ONLY is checked behaviorally and still rejects SHORT.
- Fixed frozen candidate diversification through immutable replacement and repaired the fallback ranked-candidate construction.
- Replaced the undefined Universe fallback reference with an explicit bounded cached-Universe recovery contract and a visible degraded-empty state.
- Made observability self-test exceptions unconditionally fail the check.
- Tightened PositionManager health to exact open-position identity coverage and per-position protection-cycle completion; this is fail-closed for new-entry health and does not disable existing position management.
- Changed shadow retention to remove terminal rows only, retaining unresolved `PENDING` rows even when the configured cap is reached.
- Added bounded Telegram Outbox retention for terminal `DELIVERED`/`DEAD_LETTER` rows only; pending/retry/sending rows are preserved.
- Centralized legacy/current validate-only environment aliases and added explicit `[V702-VALIDATE-EXIT]` diagnostics.

## A71 verification snapshot

- `py_compile` passed for the changed runtime, healthcheck, shadow and test modules.
- `python -u main.py --validate-only`: PASS, exit 0, 23 checks, 22.60 seconds; peak RSS measured at 551,132 KiB (about 538 MiB); `bot_started=false`.
- Targeted A71 regression suite: 9 passed. Position-health coverage regression: 1 passed.
- Full `pytest -q` completed after the final source/manifest refresh: **535 passed, 1 skipped, 0 failed**, in 64.72 seconds. The one skip is the historical A51-log test; the clean source archive does not package that historical log.
- The new peak memory is substantially below the ~1001 MiB measurement stated in the supplied audit, but remains above 512 MiB. Railway's actual memory limit and termination reason were not available; Railway OOM is therefore not confirmed.
- No real MEXC order, real Telegram delivery, exchange-native stop, or profitability test was performed.

## Railway deployment gates still requiring operator verification

Use the persistent worker start command `python -u main.py` (not `--validate-only`). Confirm that all validate-only variables are absent/disabled, mount a persistent Railway Volume at `/data`, and set `SCALPER_DB=/data/unified_scalper.db`. Keep `UNIFIED_LIVE_PILOT_ENABLE=0` and `UNIFIED_A55_LIVE_ARM=0`; keep monitor/paper flags as intended. Allow sufficient memory headroom (the measured validation peak is already about 538 MiB; a 512 MiB limit is insufficient for that measured path). Confirm the actual Railway healthcheck mode and grace period; do not configure an HTTP health path for a worker that does not serve HTTP. Obtain the deployment exit code, memory graph, and full logs before attributing a crash to OOM.

**Release decision remains NO-GO for unattended live trading.** A successful one-shot validator proves only the validation path. Monitor/Paper operation still requires stable Railway deployment, persistent DB verification, and real integration checks before a separate human-approved live decision.

---

# A66 — التقرير النهائي المدمج للتدقيق والإغلاق الإنتاجي

**التوزيعة المرجعية:** `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL`  
**مراجعة الدمج:** `A66-PRODUCTION-AUDIT-MERGED-CLOSURE-2026-11-15`  
**الملف التنفيذي الوحيد:** `main.py`  
**قرار التشغيل:** `NO_GO_UNATTENDED_LIVE`  
**سياسة الدخول الفعالة:** `MONITOR_ONLY_NO_NEW_BUYS`  
**القيود:** Spot / LONG_ONLY، لا Futures ولا short، لا تخفيف للبوابات، لا صلاحية تنفيذ لمسارات Shadow.

## 1. الحكم النهائي

تم استخدام أرشيف A66 الذي رفعه المستخدم باعتباره الـCanonical baseline، ثم دمج الإصلاحات التي أمكن تطبيقها واختبارها في الملفات الموجودة، دون إضافة ملفات جديدة أو حذف محرك استراتيجية أو وظيفة تداول/حماية أساسية. ظلت التوزيعة عند حد 99 ملفًا.

هذه النسخة **أكثر صلابة من A66 الأصلية في العيوب التي أُغلقت أدناه**، لكنها لا تحصل على اعتماد تشغيل حي غير مراقب. لم يحدث اتصال MEXC موثّق بالمفتاح الحقيقي، ولم تُرسل أوامر حقيقية، ولم يُتحقق من Native Stop على حساب فعلي، ولم يُختبر تسليم Telegram الحقيقي، ولم يُثبت أي Edge ربحي من تعبئات سوق فعلية.

## 2. التحقق الذي أُعيد تشغيله

- الأرشيف المرجعي: 99 ملفًا؛ لم تتم إضافة ملف رابع أو مئة.
- تم تعديل `main.py` وملفات الاختبارات والتوثيق والـWorkflow وملفات Manifest/Checksums داخل الأرشيف، مع الاحتفاظ بعدد الملفات.
- `python -m py_compile main.py`: ناجح بعد آخر تعديل.
- `python main.py --validate-only`: نجح بعد إدخال 19 فحص مصدر A66؛ `bot_started=false` ولا يبدأ تداولًا.
- مجموعة pytest الكاملة بعد تثبيت تغييرات الكود وهوية الإصدار: **497 PASS، اختبار واحد SKIPPED، و0 FAIL** في إعادة التشغيل النهائية استغرقت 30.29 ثانية. الاختبار المتخطّى تاريخي ويحتاج سجل A51 غير موجود في توزيعة المصدر النظيفة.
- فحوص `py_compile` و`compileall` ناجحة على بيئة Python 3.13.5 المحلية. بيئة Python 3.12/Linux amd64 وDocker لم تُشغّل هنا.
- نتائج الاختبار Offline/Mock لا تثبت التكامل الحقيقي مع MEXC أو Telegram ولا ربحية التداول.

## 3. الإصلاحات المدمجة والمنفذة

### 3.1 سلطة التحقق عند الإقلاع

أُصلح ترتيب الدمج في مدقق A66: تُدمج بيانات التقرير أولًا، ثم تُحسب `pass` النهائية على أنها تقاطع نجاح المدقق السابق ونجاح فحوص A66. لا يستطيع حقل `pass=True` في تقرير A66 إخفاء فشل السلسلة الموروثة. أضيف اختبار يعيد حالة المدقق السابق `False` مع تدقيق A66 ناجحًا، ويتأكد أن النتيجة النهائية تظل `False`.

### 3.2 حماية المراكز وصحة Health Lease

- أصبحت دورة PositionManager تُصدر نتيجة منظمة لكل مركز، فيها حالة الرمز وسبب الفشل.
- لا تتجدد `last_healthy_ts` ولا عدادات صحة الحماية لمجرد أن Task ما زالت حية أو أن الدالة عادت؛ لا بد من دورة مكتملة مع تقييم كل مركز مفتوح أو إغلاقه المؤكد.
- فشل Ticker/Mark أو مصالحة الأمر أو تقييم الحماية يبقي الـHealth Lease غير صالح، ويمنع الدخول الجديد وفق البوابات القائمة، مع استمرار محاولات الخروج/الحماية.
- فُصل مفهوم `task_alive` عن `protection_healthy` في منطق الدورة.

### 3.3 وقف التعادل وقفل الربح واستعادة TP1

- لا يُرفض وقف BE أو Trailing عند/فوق سعر الدخول لمجرد أنه لم يعد وقف خسارة أصليًا أسفل الدخول.
- تم تطبيق الاتساق على فحص صحة الوقف والاستعادة بعد Restart؛ وتظل صحة الوقف مرتبطة بوجود وقف Native مؤكد أو Software SL معتمد وفق الإعدادات.
- يلتقط مسار TP1 قيمة الوقف السابق داخل نطاق الصفقة نفسها وقبل محاولة BE؛ لا يعتمد الاسترداد على متغير غير مهيأ أو قيمة متبقية من رمز آخر.
- أضيف اختبار Regression لوقف ربح موجب فوق الدخول.

### 3.4 أولوية طلبات الحماية وحداثة بيانات الأسعار

- صُنّفت طلبات `protected_fetch_ticker_*` وعمليات PM/SL/TP والمصالحة قبل المطابقة العامة لكلمة `ticker`؛ فلا تسقط تلقائيًا في فئة SCAN بسبب اسم API.
- أصبح كاش Ticker يستخدم Timestamp مستقلًا لكل رمز. تحديث B لا يجدد TTL الخاص بـ A، والصفوف القديمة لا تُعاد على أنها حديثة.
- هذا يصلح تصنيف الأولوية والكاش داخل طبقة التطبيق؛ لا يثبت وحده عدم وجود ازدحام في طابور CCXT الداخلي عند حمل حي كثيف.

### 3.5 شفافية بيانات الأوامر والإلغاء

- فشل قراءة الأوامر المفتوحة يعرض حالة `UNKNOWN` بدل إرجاع `[]` بما يوحي بعدم وجود أوامر.
- الإلغاء العادي مقيد بأرقام الأوامر التي يتتبعها البوت. الإلغاء الشامل يظل مسارًا منفصلًا وصريحًا. تُستخدم أقفال الرمز لتقليل تعارض تعديل الأوامر والمصالحة.

### 3.6 Telegram Digest وOutbox

- استعادة Snapshot للـDigest عند إلغاء المهمة أو الفشل النهائي أصبحت صريحة، مع إعادة رفع `CancelledError` بدل ابتلاع إشارة الإلغاء.
- أضيف SQLite Outbox دائم قبل إدخال الرسالة إلى الطابور، مع حالات `QUEUED / SENDING / RETRY_PENDING / DELIVERED / DEAD_LETTER`، ومعرّف/مفتاح للرسالة، وdedup/coalescing، واستعادة الرسائل المعلقة بعد Restart.
- ACK الحقيقي من Telegram هو وحده ما ينقل الرسالة إلى `DELIVERED`; قبولها في الطابور ليس تسليمًا.
- تم دعم `retry_after` من استجابة 429 وتأخير تصاعدي محدود.
- **دلالة التسليم At-least-once وليست Exactly-once**: إذا قبل Telegram الرسالة ثم تعطلت العملية قبل حفظ ACK محليًا فقد تُعاد الرسالة بعد Restart. والـsemantic callbacks التي تعتمد على كائنات Python داخل العملية لا تُستعاد بعد Restart؛ هذا مصرح به في Manifest ولا يُدّعى أنها دائمة.
- لم يُنفذ اختبار Telegram حي. Outbox الدائم لا يضيف أي صلاحية تنفيذ ولا يجعل التداول تابعًا لنجاح Telegram.

### 3.7 اقتصاديات TP1 والرسوم

أضيف فصل واضح في نتائج `fee_viability_detail` بين:

- `TP1_FULL_CLOSE_NET_*`: صافي الربح النموذجي لو أُغلقت كامل التذكرة عند TP1.
- `TP1_PARTIAL_REALIZED_*`: صافي الربح/التكلفة النموذجيان على نسبة TP1 التي تُباع فعلًا من حجم الصفقة الأصلية، وفق أوزان TP1/TP2/Runner المضبوطة.

هذه الحسابات تفصل المقاييس ولا تغيّر حدود القبول القديمة: لم يُخفض Score أو صافي الربح أو صافي RR أو نسبة تغطية الرسوم. القيم الجزئية هنا نموذج توزيع للتكلفة/العائد، وليست بديلًا عن حساب VWAP ورسوم وكمية التعبئة الفعلية بعد تنفيذ حقيقي.

### 3.8 تكلفة التنفيذ والتحقق من القيم العددية

- مدخلات التكلفة المقاسة والرسوم والسبريد يجب أن تكون finite وغير سالبة.
- لا تتحول قيمة `NaN` للرسوم إلى صفر، ولا تُقص قيمة Spread/Cost مقاسة مرتفعة إلى حد أصغر متفائل.
- القياس الصريح يبقى `measured + buffer`؛ وعند غياب القياس يستخدم النموذج الاحتياطي المحافظ. أي مدخل غير صالح يسبب رفضًا/تأجيلًا بدل التظاهر بأن الصفقة رخيصة.

### 3.9 Edge / Paper / الإحصاء

- تمت ترقية Edge schema إلى `V702-KNOWLEDGE-EDGE-SHADOW-8-A66-AUDIT-CLOSURE` مع `A66_PARTIAL_EXIT_COST_AND_FDR_V1`.
- أصبح مفتاح/أهلية Edge مرتبطًا ببصمة اقتصادية تشمل إعدادات الرسوم والسبريد والانزلاق وحد الربح وRR وتقسيم TP1/TP2/Runner وسياسة الشموع؛ فتُعزل الأدلة التي جُمعت تحت افتراضات اقتصادية مختلفة.
- تم جعل `entries` في منتج التقرير عدد المشاهدات/العناقيد المستقلة، مع إبقاء `train_samples`, `validation_samples`, `holdout_samples` منفصلة.
- أصبح مستهلك Edge يطلب الحد الأدنى للمشاهدات المستقلة وحجم التدريب والتحقق والـHoldout، Purged Walk-Forward، توقعًا موجبًا في validation/holdout، وفحص Benjamini–Hochberg عند q=0.10، إضافة إلى الحدود السابقة للتوقع والثبات.
- لا تعتبر عبارة `VALIDATED_POSITIVE` وحدها دليلًا. ولا تُرقى استراتيجيات Shadow أو أي وصفة تلقائيًا إلى Live من دون اجتياز البوابات كلها.

### 3.10 شموع Shadow والفجوات والـTimeout

- الشموع غير المنطقية OHLC، أو ذات قيم غير finite، أو timestamps مكررة/غير مرتبة، أو حجم سالب، تُرفض.
- الفجوة الزمنية غير المرصودة تُعلّم صراحة، ولا تُحسم خلالها نتيجة TP/SL كما لو أن المسار كان معروفًا؛ تصبح العينة ملتبسة `AMBIGUOUS_DATA_GAP` وتُستبعد من الدليل الربحي.
- تم تطبيق Timeout لمسار Adaptive قبل TP1 وبعد TP1، مع حساب الجزء المتبقي بصورة منفصلة.
- تم فصل متابعة الشموع الصحيحة عن افتراض أن كل فجوة تعني عدم لمس وقف الخسارة.

### 3.11 تشخيص الأصفار في اللوج

أضيفت حقول Universe/Scan الأساسية في Digest لتوضيح حالة مصدر الأسواق وحجم القائمة وعمر آخر بيانات ومحاولة الاسترداد وعدد الرموز/الصفوف السعرية. ويظل منع الدخول منفصلًا عن المسح. لا تزال اللوجات التاريخية التي أرسلها المستخدم غير كافية لإثبات هل كانت أصفار DISC ناتجة عن Universe فارغ أو فشل جلب أو غياب إعدادات فنية؛ يلزم تسجيل تشغيل جديد بهذه الحقول حتى يُعرف السبب التشغيلي الفعلي.

### 3.12 هوية الإصدار

تم توحيد `V702_PACKAGE_AUDIT_REVISION` بلاحقة مراجعة الدمج، وإظهار `active_post_audit_patch_revision` ونسخة Edge والنموذج الاقتصادي في بيانات Runtime وManifest. يبقى `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL` اسم التوزيعة المرجعية.

## 4. خريطة طلبات التدقيق الـ30

| # | الحالة في هذه الحزمة | النتيجة |
|---:|---|---|
| 01 | مغلق | فشل المدقق الموروث لا يمكن إخفاؤه بنتيجة A66. |
| 02 | مغلق | صحة PM مبنية على تقييم كل مركز وHealth Lease. |
| 03 | مغلق | إصلاح `prev_sl` في مسار TP1/BE. |
| 04 | مغلق | وقف BE/Profit-lock فوق الدخول مقبول كوقف حماية جارٍ. |
| 05 | مفتوح | لم يُنفذ فصل كامل بين CCXT Public Market Data وPrivate Account/Execution clients. |
| 06 | غير محسوم | `defaultType=spot` موجود، لكن سلوك metadata الخاص بالمشتقات في CCXT لم يُختبر بمكتبة الإصدار الفعلية على الهدف؛ لا أدعي أنه أُغلق. |
| 07 | جزئي | أُضيفت Telemetry للـUniverse/Scan، لكنها لا تقدم حتى الآن كل أعمدة `symbols_attempted/snapshots_valid/scan_completed` لكل مسار في Digest. |
| 08 | جزئي | استمرار الحماية مع فشل Universe الأصلي قائم، لكن جميع أشكال فشل Preflight/الهوية/المصالحة أثناء الإقلاع لم تُختبر تكامليًا. |
| 09 | مغلق | Ticker TTL مستقل لكل رمز. |
| 10 | جزئي | تصنيف طلبات الحماية صار أعلى من Scan، لكن لا يوجد اختبار ضغط يثبت عدم تجويعها داخل طابور CCXT. |
| 11 | مفتوح | يلزم تطابق معرفات المراكز المستعادة مع تغطية PM، وليس عددًا فقط؛ لم يُغلق هذا العقد بالكامل. |
| 12 | مفتوح | لم يُغلق بالكامل تمييز FRESH عن STALE_FALLBACK في كل مسارات تجديد Universe القديمة. |
| 13 | مغلق | إلغاء Flush يعيد ملكية Snapshot ثم يعيد رفع الإلغاء. |
| 14 | مغلق ضمن Outbox/Recovery | فشل إرسال Digest يعيد الرسالة/النافذة للمحاولة؛ ACK لا يساوي admission. |
| 15 | جزئي | Outbox دائم للرسائل؛ التسليم At-least-once والـcallbacks الدلالية ليست دائمة. |
| 16 | مغلق على مستوى المعالجة | احترام 429 `retry_after` مع backoff محدود؛ يلزم اختبار Telegram حي. |
| 17 | مغلق | فشل قراءة الأوامر يعرض UNKNOWN وليس Empty. |
| 18 | مغلق جزئيًا | الإلغاء الافتراضي مقيد بأوامر البوت؛ الإلغاء الشامل مسار صريح، لكن التزامن الحي على المنصة غير مختبر. |
| 19 | مغلق | لا قصّ متفائل للتكلفة المقاسة ولا تحويل NaN إلى رسوم صفر. |
| 20 | مغلق | فحص finite/range لسياق HTF قبل إنشاء مفتاح Edge. |
| 21 | جزئي | Schema وFDR وValidation/Holdout أصبحوا مطلوبين؛ لم تُستكمل كل اختبارات FDR/Walk-forward المتعددة عبر ترابط العملات والتجارب. |
| 22 | مغلق من ناحية الفصل الاقتصادي | بصمة كاملة للنموذج الاقتصادي تعزل الإصدارات المختلفة؛ ما زال يلزم توثيق إعادة استخدام Holdout طويل المدى وحمايته من التكرار. |
| 23 | مغلق | Timeout لـAdaptive قبل وبعد TP1. |
| 24 | مغلق جزئيًا | تحقق OHLC/الترتيب/التكرار وبيانات الفجوة؛ يظل الاختبار الحي/مصدر شموع السوق الفعلي خارج التحقق. |
| 25 | مفتوح | لم يُبن Scheduler مستقل مضمون لكل عينة Shadow Pending بغض النظر عن عودة الرمز إلى Universe. |
| 26 | مفتوح | سياسة retention/archival تزايدية شاملة مع حفظ كل Pending واختبار restore طويل الأمد غير مكتملة. |
| 27 | مفتوح جزئيًا | الاختبارات الجديدة تغطي العيوب المؤكدة أعلاه؛ لم يُغلق كامل تصنيف F821/NameError ومسارات Ranking البديلة المذكورة في تقرير المستخدم. |
| 28 | جزئي | أضيفت فحوص مصدر/عقود رئيسية؛ تبسيط 435 مسار `except: pass` وسلطة مركزية واحدة لجميع Wrappers يحتاج إعادة هيكلة أوسع ولم يُدّع إغلاقه. |
| 29 | مغلق | هوية إصدار واحدة مع لاحقة الدمج وحقول Runtime/Manifest. |
| 30 | جزئي | سُمّيت Workflow/A66 artifacts وDocker tags A66؛ لم يتم تشغيل Python 3.12/Linux amd64 CI أو Docker build محليًا، ولا يزال قفل الاعتماديات المتعدية غير متحقق. |

## 5. عناصر التدقيق الأولي المدمجة

- تحسين تفسير `DISC=0` بإظهار حالة Universe/Scan؛ لا يُفسَّر `MONITOR_ONLY` كسبب لعدم المسح، ولا يُفسَّر `ENG=18` على أنه 18 فرصة.
- الاحتفاظ بمسارات الاستراتيجيات الـ18 وخمس استراتيجيات بحثية Shadow، دون تحويل البحث إلى سلطة تداول.
- الإبقاء على حدود Score والسيولة والرسوم وصافي الربح وصافي RR والحجم/عدد المراكز والخسارة اليومية كما هي.
- فصل ربح TP1 على كامل الصفقة عن ربح شريحة TP1 المنفذة.
- Telegram مستقل عن سلطة التنفيذ، مع Outbox دائم ودلالة تسليم معلنة.
- استمرار حماية المراكز أثناء فشل Universe، وعدم السماح للاستعادة بفتح BUY تلقائيًا.

## 6. ما لا يزال يمنع اعتمادًا حيًا

1. لا يوجد اتصال MEXC authenticated مُثبت بهذه الحزمة. خطأ `10072 / Api key info invalid` ورد في تقرير تاريخي داخل سلسلة التدقيق، وليس في مقتطف اللوج الحالي الذي أرسله المستخدم؛ يجب عدم نسبته إلى جلسة التشغيل الحالية قبل تأكيده.
2. لا يوجد تحقق Native Stop / OCO فعلي end-to-end على حساب ومنتج Spot ورمز محدد، مع Restart وPartial Fill وإعادة مصالحة.
3. لم يجر اختبار Telegram حقيقي؛ Outbox محليًا لا يساوي ACK من Telegram، والـcallbacks الدلالية لا تستمر عبر Restart.
4. لم يُنفذ فصل Public/Private CCXT بالكامل أو اختبار metadata Spot-only على نسخة CCXT المستهدفة.
5. لم يكتمل اختبار دورة حياة جميع أنواع فشل Startup/Preflight أو مطابقة هوية المراكز المستعادة.
6. لم يكتمل Scheduler متابعة Pending Shadow، ولا retention/restore طويل المدى لكل قواعد البيانات.
7. لم يُغلق كل فحص static F821/مسارات Ranking البديلة ولا جرى تقليل كامل لتعقيد الـWrappers والاستثناءات الصامتة.
8. `requirements-lock.txt` direct-pins وليس lock شاملًا لكل الاعتماديات transitive مع hashes. لم يتم تشغيل GitHub Actions أو Python 3.12/Linux amd64 أو Docker image build في البيئة الحالية.
9. لا توجد قاعدة تعبئات/رسوم/انزلاق حقيقية تثبت Expectancy موجبًا أو Profit Factor موجبًا أو أن الربح الصغير يتكرر بعد الرسوم. اختبارات الوحدة وPaper/Shadow ليست إثبات ربح.

## 7. ما يجب أن يظهر في أول تشغيل Monitor بعد النشر

يجب مراجعة مؤشرات صريحة قبل تحليل جودة الاستراتيجيات:

- Universe: الحالة، الحجم، آخر نجاح، العمر، المحاولة القادمة، سبب الخطأ، هل تستخدم قائمة قديمة.
- Scan: هل اكتملت الدورة، وعدد الرموز المطلوبة والمفحوصة والبيانات المقبولة والمرفوضة.
- Engine: Registered مقابل Invoked مقابل Generated، وأسباب عدم التوليد/الأخطاء لكل محرك.
- Candidate → Prequal → Score → Select → Builder → PreSend → Queue: عدادات فريدة وأسباب رفض متسقة مع المرشح والمرحلة.
- PositionManager: كل مركز مفتوح، عمر آخر mark، آخر تقييم حماية صالح، نوع الوقف وحالة الأمر، وسبب فشل محدد عند نقصه.
- Telegram: `QUEUED` منفصلة عن `DELIVERED`, وعدد المحاولات/ACK/Dead Letter.

لا تُرفع بوابة الدخول لمعالجة أصفار المسح. يجب أولًا ثبوت أن بيانات السوق وصلت للمحركات وأن المحركات استُدعيت بالفعل.

## 8. سياسة التشغيل والربح المتكرر الصغير

النهج المعتمد هو **التقاط عدد أكبر من الفرص المؤهلة الصافية، لا زيادة عدد الصفقات بأي ثمن**. لذلك:

- لا تخفيض Score Floor أو السيولة أو TP1 fee ratio أو صافي الربح/RR.
- لا تُعامل رسوم مجهولة أو Spread مرتفع كأنها منخفضة.
- لا يُحسب Edge على نتائج من نموذج تكلفة مختلف.
- لا تُمنح العينة ذات فجوة بيانات غير محلولة ربحًا افتراضيًا.
- لا يُفعّل محرك Shadow للشراء الحقيقي.
- يبقى الحد الأقصى للحجم والمراكز والصفقات اليومية وحد الخسارة كما في A66.

لا يوجد تعهد بربح متكرر، ولا توجد استراتيجية قادرة على ضمان فرص ربح صغيرة متتابعة. قد يؤدي رفض الصفقات مرتفعة التكلفة إلى فرص أقل لكنه يحمي صافي العائد من أن تلتهمه الرسوم.

## 9. قرار الاعتماد

**A66 + Merged Audit Closure هي النسخة المرجعية النهائية لهذه الجولة من التعديلات والاختبارات المحلية، وليست شهادة Production Live.**

`NO_GO_UNATTENDED_LIVE` و`MONITOR_ONLY_NO_NEW_BUYS` ما زالا نافذين. لا يُفتح BUY تلقائيًا عند نجاح Universe أو validate-only. يجب عدم تشغيلها على حساب حقيقي غير مراقب، وعدم اعتبار نجاح الاختبارات أو `Telegram ONLINE` دليلًا على صحة حماية المنصة أو ربحية الاستراتيجية.


## 10. سجل التحقق النهائي للحزمة المسلّمة

- `pytest`: **497 passed, 1 skipped, 0 failed** في 30.29 ثانية؛ الاختبار المتخطّى هو سجل A51 تاريخي غير معبأ.
- `python main.py --validate-only`: **PASS**، 19/19 فحص مصدر، `bot_started=false`، و`live_threads=[]`.
- `python -m py_compile` و`python -m compileall -q .`: **PASS** على Python 3.13.5.
- عدد ملفات الأرشيف: **99 بالضبط**، دون مجلدات caches أو قواعد بيانات تشغيلية.
- هذه اختبارات محلية Offline/Mock؛ لم يجر اتصال MEXC حقيقي أو إرسال Telegram فعلي أو بناء Docker أو اختبار Native Stop أو تداول حي.


## 11. A67 — Intelligent Opportunity Hunter (إضافة رصد مستقلة)

### الهدف والنطاق

أضيفت طبقة اكتشاف ومتابعة فرص مستقلة عن صلاحية الشراء. مصدرها أحد مسارين: (1) مرشحو الاستراتيجيات الفعليون الذين أصدرتهم المحركات الموجودة، وعددها 18، و(2) فحص محدود للقطات `market_data_map` الموجودة بالفعل. لا تنشئ الطبقة استدعاءات Exchange إضافية ولا تنفذ أوامر ولا تغيّر صلاحيات أي مسار تنفيذ.

### حالات الفرصة ومعناها

| الحالة | المعنى الدقيق |
|---|---|
| `WATCH` | إعداد فني تحت التكوين مع أدلة مقاسة وشروط ناقصة معلنة |
| `CONFIRMED` | إما Trigger فني من شمعة مغلقة وموسوم بأنه فني فقط، أو اجتياز `PREQUAL_PASS` / `SCORE_PASS` من المسار القانوني |
| `TRADEABLE` | اجتياز `PRESEND_PASS` القانوني فقط؛ لا يعني إرسال أمر أو قبوله أو تعبئته |
| `INVALIDATED` | السعر المغلق كسر مستوى إبطال الفرضية المسجل |
| `EXPIRED` | انتهت مدة الفرصة المحددة دون استمرار صالح |

الحالات تتقدم ولا تتراجع، والحالات النهائية لا يعاد إحياؤها بواسطة أحداث اكتشاف قديمة. تحفظ السجلات في جدول SQLite باسم `opportunity_hunter`. وتعرض رسائل Telegram سبب الرصد والأدلة والشروط المتبقية، والإطار الزمني، ومرجع الدخول التحليلي، ومستوى الإبطال، ومستويات TP1/TP2/TP3 المرجعية مع تحذير واضح أنها ليست أوامر أو ضمان ربح، وحالة التنبيه.

### أنماط البحث والحدود

- `BREAKOUT_CONTINUATION`: قرب/اختراق مقاومة 20 شمعة، مع اتجاه وحجم تداول.
- `PULLBACK_RECLAIM`: اتجاه 15m قائم واختبار EMA20، مع مراقبة استعادة قمة 5m.
- `MEAN_REVERSION`: ضعف/تشبع بيعي على 15m؛ RSI وحده لا يعد إشارة شراء، ويظل تأكيد الانعكاس مطلوبًا.
- `RELATIVE_STRENGTH_LEADER`: أداء 15m أعلى من BTC عند توفر Snapshot حديث صالح لـBTC.

تُستخدم شموع 5m/15m المغلقة فقط، مع التحقق من علاقات OHLC، وتكرار الطوابع الزمنية، والحد الأدنى للتاريخ وحداثته. الحدود: 240 حد إعداد أعلى وليس عدد الرموز الممسوحة فعليًا؛ التغطية الفعلية لا تتجاوز الرموز الموجودة في `market_data_map` بعد اختيار المسح العميق. كذلك 6 تنبيهات نمطية في المسح، وحد Hunter صارم قدره 3 تنبيهات في الدقيقة مع الحفاظ على callbacks، وHunter score لا يقل عن 55/100، عمر فرصة 3,600 ثانية، و1,200 سجل نشط. درجة Hunter مقياس ترتيب داخلي وليست احتمال ربح أو دليل Edge.

### فصل الرصد عن التنفيذ

`WATCH` و`CONFIRMED` يمكن أن يظهرا حتى مع منع الشراء. `TRADEABLE` ليس إلا وصفًا لاجتياز بوابات PreSend القائمة. لم تُخفّض عتبة Score أو السيولة أو الرسوم أو المخاطر، ولم تتم إضافة أي استدعاء لـBUY أو OrderExecutor داخل Hunter. السياسة ما زالت `MONITOR_ONLY_NO_NEW_BUYS`، وقرار التشغيل ما زال `NO_GO_UNATTENDED_LIVE`.

### اختبارات الإضافة

أضيفت اختبارات انحدار لحالات التقدم الرتيب، وعدم استخدام الشمعة غير المكتملة، ورفض OHLC غير المتسق والطوابع المكررة، وحفظ WATCH والإبطال/الانتهاء، ومنع إحياء الحالة النهائية، وترقية التأكيد الفني إلى Prequal قانوني، وعدم الكتابة فوق ACK متزامن من Telegram. نتيجة المجموعة الكاملة بعد إغلاق Manifest: **506 PASS، اختبار واحد SKIPPED، و0 FAIL**. الاختبار المتخطّى تاريخي ويخص سجل A51 غير المعبأ في التوزيعة النظيفة. كما نجحت اختبارات Hunter المركزة **8/8**.

### حدود الإثبات

هذه الإضافة تزيد قدرة الرصد وإظهار المرشحين، لكنها لا تثبت أن عدد الفرص الفعلية سيزيد في كل سوق أو أن الفرص مربحة. إرسال Telegram الحقيقي، تكامل MEXC، صورة Docker المستهدفة، الحماية الحية، والربحية لم تُختبر في هذه البيئة.


### نتيجة التحقق النهائية لإصدار A66 + A67

- `pytest -q`: **506 passed, 1 skipped, 0 failed**. الاختبار الوحيد المتخطّى هو سجل A51 تاريخي غير موجود في حزمة المصدر النظيفة.
- اختبارات `OpportunityHunter` المركزة: **8/8 PASS**، بما فيها ترقية التأكيد الفني إلى Prequal، وحفظ ACK متزامن دون استبداله بحالة QUEUED.
- `py_compile` لجميع ملفات Python المعبأة و`compileall -q .`: **PASS** على Python 3.13.5.
- `python main.py --validate-only`: خروج 0؛ فحوص مصدر A66/A67 عددها **23/23 PASS**؛ `bot_started=false` و`live_threads=[]`؛ الزمن المقاس 11.12 ثانية وذروة الذاكرة 549,504 KiB في بيئة التدقيق.
- بقيت اختبارات MEXC الفعلية، وتسليم Telegram الفعلي، وNative Stop، وDocker/ Python 3.12 Linux، والربحية الحقيقية غير منفذة/غير مثبتة.
- لا تغيير في `MONITOR_ONLY_NO_NEW_BUYS` أو `NO_GO_UNATTENDED_LIVE`.


## إغلاق تدقيق الحزمة واللوج — 2026-11-15

### إصلاح تشخيص اختبارات الإقلاع الذاتية

- عزلت أحداث الاختبارات الذاتية التي تحاكي خسائر `DailyCB-R5`، واستثناءات `V455-PREQUAL`، ومحاولة جدولة Telegram بلا Event Loop، عن مستويات التحذير والخطأ التشغيلية. تبقى تفاصيلها متاحة في السجل عند مستوى INFO/DEBUG، بينما تظل الأحداث الحقيقية خارج سياق الاختبار على مستوياتها الأصلية.
- استخدمت `contextvars.ContextVar` بدل علم عالمي مشترك؛ سياق الاختبار لا يتسرب إلى خيط عامل متزامن. أضيف اختبار انحدار يثبت ذلك.
- هذا التغيير تشخيصي فقط: لا يبدل قرارات التداول، ولا يخفض Prequal/Score/PreSend أو شروط الرسوم والسيولة والمخاطر، ولا يمنح Hunter سلطة تنفيذ.

### مطابقة لقطات Railway مع الكود

- اللقطات تعرض تكرار تسلسل الإقلاع/الاختبارات مع طوابع سجل UTC تقريبية من `2026-11-15 22:28:12` إلى `22:30:33` (نحو `2026-11-16 00:28`–`00:30` بتوقيت القاهرة)، وحالة الخدمة `Crashed`. رأس Railway يعرض المعرّف القصير `f00fb90a`؛ لا يحتوي ZIP على `.git` أو إعدادات Railway لمطابقته بمصدر الحزمة.
- رسائل `MSE.selftest engine=__boom__` و`V455-PREQUAL-EXCEPTION ... stage=selftest` و`DailyCB-R5 realized loss ...` و`TG-LIFECYCLE-UNSCHEDULED ... TEST/USDT` تقع ضمن مسارات اختبار ذاتي/بيانات اصطناعية في المصدر، وليست وحدها دليلًا على خسارة سوق حقيقية أو فشل إرسال إشارة حقيقية. تم تحسين تصنيف سجلات هذه المسارات.
- المصدر يثبت أن `--validate-only` أو أي من `UNIFIED_V699_VALIDATE_ONLY=1` / `UNIFIED_V702_VALIDATE_ONLY=1` / `UNIFIED_VALIDATE_ONLY=1` يشغل مدققًا أحادي التشغيل ثم ينهي العملية عمدًا مع `bot_started=false`.
- الصورة لا تعرض علامة الإنهاء `[V702-VALIDATE-EXIT] one_shot=true bot_started=false` ولا traceback كاملًا من `[V702-CRASH]`. لذلك لا يمكن الجزم بأن إعداد Railway هو السبب النهائي؛ تطابق التكرار القصير مع عملية validator فرضية مرجحة قابلة للحسم من آخر سجل كامل وإعداد Start Command.
- أمر الخدمة الصحيح هو `python -u main.py`، مع تعطيل متغيرات validate-only الثلاثة. اللقطات لا تعرض أمر التشغيل الفعلي ولا نهاية validator ولا traceback كاملًا، لذلك لا تثبت أن سبب `Crashed` هو أمر تشغيل أحادي. كما أن `ENV-BOOT` يعرض غياب/عدم تحميل `.env` مع وجود مفاتيح MEXC وTelegram بحسب مؤشرات الحضور؛ غياب `.env` وحده ليس دليلًا على غياب أسرار Railway.

### قرار التشغيل ونطاق الإثبات

الحزمة بعد هذا الإغلاق تظل `MONITOR_ONLY_NO_NEW_BUYS` و`NO_GO_UNATTENDED_LIVE`. جرى التحقق محليًا على Python 3.13.5؛ لم يُنفذ اتصال حي بـMEXC أو تسليم Telegram حقيقي أو بناء Docker/Python 3.12/Linux amd64 في هذه البيئة، ولم تُثبت الربحية أو سلامة Native Stop على الحساب المستهدف. نجاح الاختبارات لا يعادل اعتماد التداول الحي.

## 12. A68 — إغلاق متابعة نتائج فرص Hunter (TP / SL)

### الفجوة التي أُغلقت

كانت A67 تحفظ مرجع الدخول ووقف الفرضية وTP1/TP2/TP3، لكنها لا تسجل لمس الأهداف؛ كانت تتابع الإبطال والانتهاء فقط. أضيفت طبقة A68 فوق الجدول نفسه، مع ترحيل SQLite إضافي لا يحذف الصفوف التاريخية.

### منطق المتابعة

- مراقبة الفرص المحفوظة بحالة نشطة مقابل شموع 5m المغلقة الموجودة مسبقًا في `market_data_map`؛ لا يوجد طلب إضافي للمنصة ولا صلاحية تنفيذ جديدة.
- تجاهل شمعة ظهور الفرصة والشمعة التي كانت ما تزال قيد التكوين عند رصدها، ثم حفظ طابع آخر شمعة أُغلقت وعولجت لمنع تكرار الحدث بعد إعادة التشغيل.
- حفظ أحداث `SHADOW_TP1_TOUCHED` و`SHADOW_TP2_TOUCHED` و`SHADOW_TP3_TOUCHED`، و`SHADOW_STOP_HIT` أو `SHADOW_STOP_AFTER_TP1/TP2`، وكذلك الانتهاء قبل الهدف النهائي.
- إذا لامست شمعة واحدة الهدف والوقف معًا، تسجل حالة غموض ويُحسب الوقف أولًا تحفظيًا؛ لا يمكن استنتاج ترتيب الحركة داخل الشمعة من OHLC وحده.
- الوصول إلى TP3 يغلق دورة الفرضية بحالة `COMPLETED` ويخرجها من عداد المراقبة النشطة، مع بقاء أحداثها في SQLite وملخص النتائج. الهدف الجزئي يبقى مسجلًا حتى الوصول إلى هدف لاحق أو وقف أو انتهاء المهلة.
- مستويات Entry/SL/TP ثابتة لكل `candidate_key`، ومفتاح المرشح يتضمن الرمز/النمط/شمعة الإشارة لمنع دمج إشارتين منفصلتين لنفس العملة والنمط.
- المراقبة تشمل الرموز التي لها فرص محفوظة حتى إن كانت خارج حصة اكتشاف رموز جديدة في الدورة، طالما أن لقطة الرمز موجودة في خريطة السوق الحالية.

هذه **نتيجة مرجعية افتراضية (Shadow Reference)** تعتمد على لمس السعر في شمعة مغلقة، وليست إثباتًا لتعبئة أوامر أو ربح/خسارة فعلية. سجل الصفقات المنفذة منفصل ويستمر `PositionManager` في إدارة TP1/TP2 ووقف الحماية ومصالحة الخروج. لا يجوز دمج إحصاءات Hunter مع نتائج الصفقات المنفذة.

### حالات A68

| الحالة / الحدث | المعنى |
|---|---|
| `SHADOW_TP1_TOUCHED` / `SHADOW_TP2_TOUCHED` / `SHADOW_TP3_TOUCHED` | شمعة مغلقة لامست المستوى المرجعي الثابت |
| `SHADOW_STOP_HIT` | الوقف المرجعي تحقق قبل أي هدف مسجل |
| `SHADOW_STOP_AFTER_TP1` / `SHADOW_STOP_AFTER_TP2` | الوقف تحقق بعد تسجيل الهدف السابق |
| `SHADOW_STOP_AMBIGUOUS_STOP_FIRST` | نفس الشمعة لمست الهدف والوقف؛ احتساب محافظ للوقف أولًا |
| `SHADOW_EXPIRED_WITHOUT_TARGET` / `SHADOW_EXPIRED_AFTER_TP1/TP2` | انتهاء نافذة المتابعة مع حفظ الأهداف الجزئية السابقة |
| `COMPLETED` | دورة Hunter المرجعية وصلت TP3 وأُغلقت من الطابور النشط |

### اختبارات A68 المضافة

- تسلسل TP1 ثم TP2 ثم TP3، بما في ذلك الإغلاق النهائي بعد TP3.
- لمس TP والوقف داخل الشمعة نفسها، مع اختيار الوقف أولًا.
- استبعاد شمعة الإشارة والشمعة غير المكتملة.
- حفظ TP1 ثم إضافة حالة انتهاء بعد TP1.
- ترحيل أعمدة outcome إلى SQLite قديمة دون إسقاط بيانات.
- تثبيت هندسة Entry/SL/TP ومنع تداخل candidate keys.
- تشغيل مسح كامل يثبت متابعة رمز محفوظ خارج حصة اكتشاف الرموز حتى إغلاق TP3 إلى `COMPLETED`.

### التشغيل والإثبات

- أمر التحقق `python main.py --validate-only` ينفذ دورة validator أحادية ثم يخرج عمدًا بـ`bot_started=false`؛ لا تستخدمه كـRailway Start Command. أمر الخدمة المستمر هو `python -u main.py` مع جعل متغيرات validate-only الثلاثة غائبة أو `0`.
- لقطات Railway المقدمة لا تتضمن علامة نهاية validator أو traceback كاملًا أو إعدادات الخدمة؛ لذلك لا يمكن نسبة `Crashed` إلى سبب واحد مؤكّد من الحزمة وحدها.
- يظل `MONITOR_ONLY_NO_NEW_BUYS` و`NO_GO_UNATTENDED_LIVE` نافذين. لم يُختبر MEXC أو Telegram الفعلي أو Docker/Python 3.12/Linux amd64 ولم تثبت الربحية.



### سجل التحقق النهائي بعد A68

- `pytest -q`: **512 passed, 1 skipped, 0 failed**؛ 513 اختبارًا جُمعت ونُفذت في عملية واحدة على Python 3.13.5. الاختبار المتخطّى سجل A51 تاريخي غير موجود في حزمة المصدر النظيفة.
- اختبارات A68 المركزة: **6/6 PASS**، وتشمل TP1/TP2/TP3، وغموض TP/SL داخل الشمعة، واستبعاد شمعة الإشارة، والانتهاء مع حفظ الهدف الجزئي، وترحيل SQLite، وثبات هندسة المرشح، وتكامل مسح TP3 النهائي.
- `python main.py --validate-only`: **PASS**، عدد فحوص A66 = **23/23**، الخروج `0`، `bot_started=false`، `live_threads=[]`؛ زمن القياس 11.40 ثانية وذروة الذاكرة 548,660 KiB في بيئة التدقيق. هذا وضع تحقق أحادي وليس Start Command للخدمة.
- `python -m compileall -q .`: **PASS**؛ و`py_compile` لكل **73/73** ملف Python: **PASS**.
- الأرشيف النهائي: **99 ملفًا بالضبط**؛ تطابقت قائمة المحتويات مع المانيفست **99/99**، واجتاز ZIP فحص CRC بلا أسماء مكررة، وتحققت بصمات **98/98** ملفًا (ملف checksum لا يشمل نفسه).
- لا يوجد اتصال MEXC حي أو إرسال Telegram فعلي أو Docker/Linux amd64/Python 3.12 أو إثبات ربحية في هذه البيئة. قرار التشغيل يبقى `NO_GO_UNATTENDED_LIVE` والسياسة `MONITOR_ONLY_NO_NEW_BUYS`.

## 13. A69 — إصلاح ترتيب تحميل إعدادات dotenv وتشخيص توقف الإقلاع

- كان `CONFIG` يُنشأ قبل تحميل `.env`، ولذلك كانت مفاتيح مثل `SCALPER_DB` وروابط/أسماء Telegram تُقرأ مبكرًا وتفوتها قيم `.env`، رغم أن بيانات اعتماد MEXC نفسها كانت تُقرأ بعد التحميل. أضيف تطبيق صريح لهذه الإعدادات بعد `load_dotenv(override=False)` وقبل التقاط `ENV` النهائي؛ متغيرات بيئة المضيف تحتفظ بالأولوية.
- أضيف اختبار انحدار يغطي مسار قاعدة البيانات وروابط/أسماء Telegram والـaliases مع إزالة `@` كما في العقد الأصلي.
- `ExchangeFactory` يحتاج مفتاح MEXC وسره في هذا الإصدار حتى مع `MONITOR_ONLY_NO_NEW_BUYS`؛ عند غيابهما يظهر الآن `[V702-BOOT-STOP]` وسبب `missing_exchange_secrets` بشكل مباشر، دون طباعة أي قيمة سرية. لم يتم تجاوز شرط المصادقة أو إنشاء عميل غير موثوق لحماية المراكز.
- لم تتغير بوابات التداول أو استراتيجياته أو صلاحيات التنفيذ: تظل `MONITOR_ONLY_NO_NEW_BUYS` و`NO_GO_UNATTENDED_LIVE` كما هما.
- تحقق الحزمة بعد دمج مراجعة A69: `pytest -q` = **520 passed, 1 skipped, 0 failed** (521 اختبارًا، 28.11 ثانية، Python 3.13.5، تشغيل كامل في عملية واحدة). الاختبار الوحيد المتخطّى سجل A51 تاريخي غير موجود في توزيع المصدر.
- `python -m compileall -q .` = **PASS**؛ و`py_compile` = **73/73 PASS**.
- `python main.py --validate-only` = **PASS / exit 0**؛ فحوص المصدر **23/23**؛ `bot_started=false` و`live_threads=[]`. هذا تشغيل تحقق أحادي ولا يصلح كأمر تشغيل مستمر.
- مراجعة A69 المدمجة أضافت **6 اختبارات انحدار** لمسار ExpansionShadow وHunter، وجميعها ضمن مجموعة الاختبارات الناجحة أعلاه. تحوّل تكلفة الجولة الموحدة إلى R على قيمة الدخول مرة واحدة، بما يطابق محاسبة بقية مسارات V702 ولا يضاعف أساس التكلفة.
- لا تزال علة Railway الفعلية غير محسومة دون آخر سجل كامل وإعدادات Start Command/Variables؛ لا يجوز اعتبار الفرضيات سببًا مؤكدًا.



## 14. مراجعة التدفق التشغيلي النهائي (Startup → Execution)

1. **Startup:** يهيئ مخطط SQLite، ويستعيد حالات Circuit Breaker والصفقات النشطة ونوايا التنفيذ غير المحسومة، ويصالح حماية الصفقات المستعادة. يبدأ `PositionManager` ومؤشر صحته قبل أول طلب لبناء السوق؛ وإذا فشل تكوين قائمة السيولة، يبقى الدخول محظورًا ويبدأ استردادًا محدود المحاولات بدل تمرير Universe فارغ إلى Preflight.
2. **Scan:** يجدد قائمة Spot عالية السيولة على جدول زمني محدود. يسمح `_v702_monitor_only_scan_authorized` بالمسح القرائي عند تعطيل الدخول إذا كان `UNIFIED_MONITOR_ONLY_SCAN_ENABLE` مفعّلًا؛ وهذا لا يفتح PreSend أو إرسال BUY.
3. **Candidate / Prequal:** المرشحون يمرون بمسار التحقق وإسناد أسباب الرفض. `CandidateLifecycle` سجل تتبع جنائي فقط ولا يمنح صلاحية تنفيذ. شروط الجودة والبيانات/الاقتصاد الصلبة تظل fail-closed.
4. **Score / Select:** يستخدم المحكم العالمي درجة مرجحة، ويرفض المرشحين ذوي الطابع الزمني غير القابل للتحقق أو المنتهي، ثم يطبق حد الدرجة العالمي وسياسات التنوع/الترابط والاختيار المحدود؛ هذه مرحلة ترتيب وليست تفويض تنفيذ.
5. **Queue / Telegram:** تحفظ رسائل التنبيه في SQLite Outbox قبل الطابور المتطاير، وتدعم إعادة المحاولة الدائمة بدلالة at-least-once. callbacks الدلالية لا تستمر عبر إعادة التشغيل، ولا يوجد إثبات إرسال Telegram حقيقي في هذا التدقيق.
6. **Execution:** عميل MEXC هو Spot موثّق ويحتاج المفتاح والسر. لكن السياسة النهائية للحزمة `MONITOR_ONLY_NO_NEW_BUYS`، وقرار `NO_GO_UNATTENDED_LIVE`؛ لذلك لا ينبغي أن تنتج النسخة شراءً حيًا جديدًا حتى مع عمل المسح والتنبيهات. حماية المراكز المستعادة تظل مهمة مستقلة عن السماح بدخول جديد.

**مطابقة السجلات بالكود:** سجل التدقيق المرفق يشرح أن بعض رسائل Prequal / Daily Circuit Breaker / Telegram ذات الوسم `selftest` مصطنعة من الاختبارات الذاتية وليست أحداث تداول فعلية؛ عزل `ContextVar` يمنع خلطها بسجل أخطاء التشغيل الحي. أما أدلة Railway المقدمة فهي لقطات مختصرة دون نهاية العملية أو traceback كامل أو إعدادات الخدمة، لذا لا يوجد أساس لتسمية سبب `Crashed` على أنه مؤكد. الشرطان القابلان للتحقق في إعداد الخدمة هما Start Command = `python -u main.py`، وعدم تفعيل أي متغير من متغيرات validate-only الثلاثة؛ وكذلك وجود مفتاحَي MEXC الإلزاميين.


## 15. نتيجة الدمج النهائي A69 — الحزمة المسلّمة

هذه الفقرة هي سجل التحقق الأحدث للحزمة بعد دمج إصلاحات المراجعة؛ وهي تتقدم على أي أرقام أقدم واردة في السجل التاريخي أعلاه.

- **الاختبارات:** `pytest -q` = **520 passed, 1 skipped, 0 failed**؛ 521 اختبارًا جُمعت، Python 3.13.5، 28.30 ثانية، بعملية واحدة. الاختبار المتخطّى هو fixture تاريخي لـA51 غير متوفر في الأرشيف النظيف.
- **الترجمة:** `python -m compileall -q .` = PASS، و`py_compile` = **73/73 PASS**.
- **التحقق الأحادي:** `python main.py --validate-only` = exit 0؛ فحوص المصدر 23/23؛ `bot_started=false` و`live_threads=[]`.
- **المحتويات:** 99 ملفًا بالضبط، ولا يتجاوز حد الحزمة. ملف البصمات يضم 98 إدخالًا لأن ملف SHA-256 لا يمكن أن يتضمن بصمته الذاتية؛ ستتم مطابقة كل الإدخالات وفحص CRC في ZIP النهائي.
- **هوية الإصدار:** لم تُنشأ هوية تشغيل بديلة. بقي `4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL` ووسم التوزيع الأساسي `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL` كما تقتضي اختبارات التوافق؛ أُلحقت مراجعات A67/A68/A69 بسلسلة مراجعة الحزمة. لم يُعدّل عقد `canonical_package_revision` التاريخي المثبت على A10.
- **سياسة الأمان:** لا تجاوز للبوابات، ولا تخفيف لها. القرار `NO_GO_UNATTENDED_LIVE` والسياسة `MONITOR_ONLY_NO_NEW_BUYS` كما كانا.
- **حدود الإثبات:** لا تزال اتصالات MEXC الحية، وNative Stop، وتسليم Telegram الحقيقي، وبناء Docker على Linux amd64/Python 3.12، وقفل hashes للاعتماديات المتعدية، والربحية الفعلية غير مختبرة في هذه البيئة. لا تعتبر نتائج Shadow تعبئات أو أرباحًا حقيقية.

## 16. إغلاق مراجعة Production Audit النهائية — توحيد الهوية وتشخيص Railway

### الإصلاحات المطبقة في المصدر

- فصل هويات الإصدار بدل دمجها قسرًا: بقي `V702_FINAL_CANONICAL_RELEASE` و`CONFIG.V702_FINAL_CANONICAL_RUNTIME_IDENTITY` على هوية التوافق التاريخية A64، وبقيت هوية التوزيعة النشطة `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL` (A66). ظل `SCRIPT_VERSION` العام `4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL` دون تغيير حتى لا تُكسر عقود التوافق.
- جعل سطر بدء الخدمة ومعلومة Post-audit التي يعرضها متحكم Telegram يقرآن `active_post_audit_patch_revision_current` أولًا. بقيت قيمة A51 في الحقل التاريخي القديم كما هي؛ لم تعد تُعرض بالخطأ بوصفها المراجعة النشطة.
- مطابقة حقول الحزمة والتدقيق مع سلسلة المراجعات A67/A68/A69. بقي `active_post_audit_patch_revision_current` على A66، وأضيف `active_audit_merge_revision_current=A69-MERGED-PRODUCTION-AUDIT-CLOSURES-2026-11-15` كحقل مستقل؛ لم يُستبدل بذلك عقد A66 التشغيلي.
- إضافة سجلات مراحل `validate_config_begin/end` و`runtime_epoch_armed` و`run_bot_enter`، مع تسجيل سبب `SystemExit` أثناء التحقق في `[V702-BOOT-STOP]`. هذه سجلات تشخيصية فقط ولا تغير قرار السماح بالتداول.

### التصحيح المعتمد لمطابقة لقطات Railway

- المعرّف الظاهر في رأس Railway هو `f00fb90a` وليس `9591cebf`.
- التوقيت المقروء من سطور السجل هو تقريبًا `22:28:12–22:30:33 UTC` بتاريخ 15 نوفمبر 2026، أي نحو `00:28–00:30` صباح 16 نوفمبر بتوقيت القاهرة.
- `ENV-BOOT` في اللقطات يعرض `dotenv_loaded=False` مع مؤشرات وجود مفتاح وسر MEXC وبيانات Telegram. لا يصح اعتبار عدم تحميل ملف `.env` سبب توقف مؤكدًا.
- علامات `selftest` والـsynthetic fault injection مثل `engine=__boom__` وخسائر `DailyCB-R5` ورفض T17/T18 هي نتائج اختبارات معزولة، لا صفقات أو خسائر حقيقية.
- لا تعرض اللقطات `V702-VALIDATE-EXIT` ولا نهاية `validate_config` ولا `run_bot_enter` ولا traceback كاملًا. لذلك لا يمكن حسم هل التوقف بسبب `validate-only` أو خطأ اعتماد/اتصال أو حد الذاكرة أو إعداد Railway. قراءة الأرشيف وحده لا تعطي حد ذاكرة الخدمة أو Start Command أو متغيراتها الفعلية.

### نتيجة التدفق والقرار

يبقى التدفق المنطقي Startup → Scan → Candidate → Prequal → Score → Select → Queue → Telegram → Execution محفوظًا، وتظل Hunter/Outcome للمراقبة فقط. لا توجد في هذا الإغلاق إزالة لوظيفة أساسية أو تخفيف لبوابة دخول أو تجاوز حماية. السياسة الفعالة `MONITOR_ONLY_NO_NEW_BUYS` وقرار الاعتماد `NO_GO_UNATTENDED_LIVE` محفوظان. عميل MEXC يحتاج مفتاحًا وسرًا صالحين حتى في هذا الوضع؛ Telegram اختياري للمسح/التنفيذ لكنه يلزم لوظيفة التنبيهات.

### نتيجة تشغيل الإقلاع المحلي بعد إضافة علامات المراحل

شُغّل مسار بدء الخدمة محليًا من دون أسرار أو اتصال خارجي: اجتاز `validate_config` (`passed=True`)، وسجّل `runtime_epoch_armed` مع `MONITOR_ONLY_NO_NEW_BUYS`، ثم وصل فعلًا إلى `run_bot_enter`. توقّف بعدها برسالة `SystemExit: ccxt_missing` لأن حزمة `ccxt` غير مثبتة في حاوية التدقيق هذه. هذا يثبت أن علامات المراحل الجديدة تعمل وأن التوقف المحلي حدث بعد التحقق؛ ولا يثبت أن `ccxt` مفقود في Railway، إذ إن `requirements.in` يثبّت `ccxt==4.5.81`.

### إعادة تشغيل مجموعة الاختبارات بعد إغلاق الهوية

النتيجة النهائية الأحدث: `pytest -q` = **521 passed, 1 skipped, 0 failed** خلال 30.13 ثانية. الاختبار الإضافي يثبت الفصل بين هوية التوافق A64، ووسم التوزيعة A66، ومراجعة الدمج A69، ويمنع تفسير حقل A51 التاريخي على أنه المراجعة النشطة. هذه النتيجة تحل محل عدد 520 اختبارًا الوارد في سجل الإغلاق السابق في القسم 15؛ ذلك العدد كان صحيحًا قبل إضافة اختبار الانحدار الجديد.

كما نجح `python -m compileall -q .` و`py_compile` لكل 73 ملف Python. إعادة `python main.py --validate-only` الأخيرة نجحت برمز خروج 0، مع 23/23 فحصًا و`bot_started=false` و`live_threads=[]`، واستغرقت 10.49 ثانية، وبلغ قياس RSS الأقصى 551,064 KiB (نحو 538.15 MiB) في هذه البيئة. هذا القياس محلي وليس قياسًا لذاكرة Railway.

### حدود التحقق

تم التحقق محليًا من اختبارات Offline وملفات المصدر فقط. لم يتم الاتصال بـMEXC الحقيقي، ولم يتم إرسال Telegram حقيقي، ولم تُبنَ صورة Docker على Python 3.12/Linux amd64، ولم تُختبر إعدادات Railway ذاتها. كما أن عدم وجود `ccxt` في بيئة التدقيق المحلية يمنع اختبار مسار إنشاء عميل MEXC هنا؛ المتطلب pinned في `requirements.in`، لذلك يجب أن يتم التحقق من تثبيته في صورة النشر لا افتراض غيابه على Railway. لا يُرفع قرار التشغيل الحي اعتمادًا على اختبارات Mock. سبب `Crashed` على Railway لا يزال غير محسوم من اللقطات لأن السجل الكامل وStart Command وحد الذاكرة وإعدادات الخدمة غير متاحة؛ علامات المراحل الجديدة ستساعد على تحديد موضع التوقف في النشر اللاحق، لكنها ليست إثباتًا أن العطل أُزيل.


## 17. مراجعة مستقلة وإعادة تحقق — 2026-11-16

### 17.1 النطاق والحصيلة

- الحزمة المستلمة: 99 ملفًا. فُك ضغطها بنجاح، واجتاز الأرشيف الأصلي فحص CRC (`testzip=None`).
- الحزمة النهائية المستهدفة: 99 ملفًا، دون حذف وحدات تشغيل أو استراتيجيات أو اختبارات. أُعيدت تسمية ملفين فقط مع تحديث كل المراجع: `LIVE_RELEASE_ENV.example` إلى `.env.example`، و`A66_FINAL_PRODUCTION_AUDIT_AR.md` إلى `FINAL_AUDIT_REPORT.md`.
- جرى تحليل 73 ملف Python، بإجمالي 119,183 سطرًا تقريبًا. `main.py` وحده 103,929 سطرًا؛ فُحصت البنية عبر AST، وأُجري compile شامل، وفحص Imports واختبارات الانحدار. هذا لا يعني مراجعة بشرية حرفية لكل سطر من الـ119 ألف سطر.
- عدد عيوب الحزمة/الإصدار المؤكدة: **3**. عدد الإصلاحات المطبقة: **3**. لم يظهر خطأ Compile أو فشل Regression في تشغيل الاختبارات النهائي.
- كشف فحص AST عن 12 إعادة تعريف top-level موزعة على 11 اسمًا في `main.py` (منها تعريف مكرر ثلاث مرات لـ`tier_spread_hard_ok_v410`). لم تُحذف هذه الطبقات آليًا: ترتيب تعريفاتها/تغليفها قد يكون جزءًا من مسار الـruntime، وإزالتها دون تفكيك تدرجي واختبارات parity مخصصة مخاطرة. هذا الإصدار يغلق عيوب التسليم المؤكدة، لكنه **ليس إعادة كتابة هيكلية كاملة** للملف الأحادي الضخم؛ تبقى هذه نقطة refactoring لاحقة.

### 17.2 العيوب المؤكدة والإصلاحات

1. **بصمة مصدر قديمة في `A66_RELEASE_MANIFEST.json`:** حقلا `canonical_main_sha256` و`canonical_source_sha256` لم يطابقا `main.py` الفعلي، مع أن `FINAL_MANIFEST.json` كان يحمل البصمة الصحيحة. أُعيد حساب الحقلين وتوحيدهما مع بصمة المصدر، وأُضيف اختبار يمنع تكرار الانحراف.
2. **التباس هوية مراجعة الإصدار:** كان `active_post_audit_patch_revision_current` في Manifest A66 يعلن A69، رغم أن A66 هو الإصدار التشغيلي النشط وA69 دمج تدقيق لاحق مستقل. أُعيد حقل A66 إلى `A66-PRODUCTION-AUDIT-MERGED-CLOSURE-2026-11-15` وأضيف `active_audit_merge_revision_current=A69-MERGED-PRODUCTION-AUDIT-CLOSURES-2026-11-15`. أُضيفت assertions لاختبار هذا الفصل.
3. **تباين اسم نموذج الإعدادات:** كانت قواعد `.gitignore` و`.dockerignore` تسمح صراحةً بـ`.env.example` بينما الملف الموجود والمستخدم في runtime وDocker يحمل اسمًا مختلفًا. أُعيدت تسمية الملف إلى `.env.example`، ووُحّدت جميع مراجع `main.py` وDocker والاختبارات وقواعد الاستبعاد. بقيت مفاتيح التداول الحي `0` والقيم الحساسة غير موجودة.

تم تحديث `A66_SHA256SUMS.txt` ليعكس النسخة المعبأة الحالية. لم يُحذف أي ملف مصدر أو اختبار؛ اسما الملفين القديمان أعلاه لم يعودا موجودين لأنهما أُعيدا تسميتهما، لا لأن محتواهما أُسقط.

### 17.3 نتائج الفحص البرمجي

| الفحص | النتيجة | التفاصيل |
|---|---|---|
| Python Compile | PASS | `python -m compileall -q .`؛ 73 ملف Python |
| AST / Source parse | PASS | لا أخطاء تحليل نحوي في ملفات Python الـ73 |
| Internal Imports | PASS | لا مراجع مفقودة لوحدات المشروع الداخلية؛ 14 وحدة تشغيلية جرى استيرادها دون اتصال خارجي |
| Unit / Regression suite (مجلد العمل) | PASS | `522 passed, 1 skipped, 0 failed` خلال 29.81 ثانية؛ رمز الخروج 0 |
| Unit / Regression suite (نسخة ZIP مستخرجة) | INCONCLUSIVE | تجاوزت مهلة 180 ثانية عند نحو 78% دون ملخص؛ اختبار A56 المنفرد وملفه الكامل نجحا، والتعليق المرتبط بسياق/ترتيب المجموعة لا يزال مفتوحًا |
| Integration subset | PASS | 76 اختبارًا مستهدفًا لمسار الاستراتيجية ونوايا التنفيذ الوهمية والتكلفة والسلامة وShadow |
| Offline startup validation | PASS | `python main.py --validate-only`؛ exit 0، وفحوص A66 عددها 23/23، و`bot_started=false`، و`live_threads=[]` |
| Test-process teardown | PASS | بقي `MainThread` وحده بعد الاختبارات؛ لا عامل خلفية متروك |

الاختبار الوحيد المتخطّى هو `test_release_contracts.py`: سجل التحقق التاريخي A51 غير موجود في حزمة المصدر النظيفة. لم يُختلق هذا السجل أو يُستبدل بنتيجة مصطنعة. تشغيل `python -X dev -m pytest -q` على بيئة Python 3.13.5 تجاوز مهلة خمس دقائق قبل إظهار ملخص؛ أما التشغيل العادي من مجلد العمل `python -m pytest -q` فاكتمل برمز خروج 0. إصدار Python المستهدف في المشروع هو 3.12، ولم تكن بيئة 3.12 متاحة لهذا التدقيق.

**ملاحظة إعادة التحقق من النسخة المستخرجة:** بعد بناء ZIP وفكّه في مجلد نظيف، أُعيد تشغيل المجموعة الكاملة على النسخة المستخرجة، لكنها تجاوزت مهلة 180 ثانية عند قرابة 78% دون ملخص نهائي (آخر موضع ظاهر كان قرب `test_v702_a56_final_hardening.py::test_a56_validator_contains_all_new_safety_closures`). أُعيد تشغيل هذا الاختبار منفردًا وملف الاختبارات A56 كاملًا في المجلد المستخرج، ونجحا؛ لذلك لم يُثبت فشل حتمي للاختبار، لكن يوجد احتمال تعليق يعتمد على ترتيب/سياق المجموعة لم يُعزل بعد. النتيجة 522/1 skip/0 fail أعلاه تخص التشغيل الكامل الناجح من مجلد العمل، ولا يجوز اعتبارها إثباتًا لاكتمال المجموعة كاملة من النسخة المستخرجة. هذا القيد مفتوح ويجب إغلاقه في CI على Python 3.12 قبل أي ترقية لسياسة النشر.

### 17.4 تكامل التدفق ومخاطر التنفيذ

- مجموعة التكامل الموجّهة شملت `test_sr_pipeline_integration.py`، واختبارات `execution_intent_reconciliation` و`mock_intent_isolation`، ونموذج تكلفة التنفيذ، واختبارات أمان A63، وShadow intraday/counterfactual. كما شغّل التحقق الذاتي سلسلة بوابات السياسات والـhandoff والـrisk/SL/TP وشفافية Telegram/Queue من خلال محاكاة دون حساب تداول.
- توجد اختبارات حقن لأخطاء timeout، واستجابة venue غير المؤكدة، وفشل Telegram، ومحدد المعدل، واستعادة حالة الرصيد/الأوامر. لا تعني هذه المحاكاة أن API حقيقيًا أو Telegram حقيقيًا اختُبر.
- لم تُضف فلاتر Trend/MTF/Volume/ATR جديدة ولم تُخفّض عتبات Score/Liquidity أو حدود المخاطر. الكود الحالي يحتوي بالفعل مسارات HTF/MTF وRS/Volume/order-book واحتساب تكلفة ومخاطر/وقف؛ ولا يوجد في الحزمة سجل OHLCV/دفتر أوامر تاريخي موثوق لإثبات أن فلترًا آخر يحسن العائد بدل أن يخنق الفرص. بقي Hunter ونتائج TP/SL في نطاق Shadow، وبقيت سلطة التنفيذ الأصلية وحدها.
- لم تُنفّذ دورة سوق حقيقية كاملة من Scan إلى أمر MEXC، ولم يُرسل طلب تداول أو Telegram حقيقي. لا توجد بيانات تعبئة حقيقية أو Walk-Forward تسمح بادعاء الربحية.

### 17.5 الأمان والاعتماديات وحدود بيئة التدقيق

- فحص الحزمة لم يعثر على مفاتيح PEM خاصة أو Telegram token صالح أو بيانات اعتماد حقيقية. ملف `.env.example` يحتوي مفاتيح التشغيل الحي على `0` وبيانات MEXC الحساسة كعناصر توضيحية معلّقة فقط. لم تُستخدم أسرار في أي اختبار.
- `requirements.in` يثبت الاعتماديات المباشرة، ومنها `ccxt==4.5.81` و`aiosqlite==0.22.1`، لكن هاتين الحزمتين لم تكونا مثبتتين في بيئة التدقيق. اجتاز `--validate-only` لأنه لا ينشئ عميل تداول ولا يبدأ البوت؛ لذلك لم يُشغّل `python -u main.py` في هذه البيئة ولم يُستخدم اتصال خارجي.
- `requirements-lock.txt` هو direct-pin seed وليس hash lock متعديًا مكتملًا؛ CI المعرّف في `.github/workflows/a65-production-audit.yml` هو الذي ينشئ القفل الكامل لمنصة Python 3.12/Linux amd64. لم يُنفذ CI هنا.
- `pip check` أظهر تعارضًا في الحاوية المحيطة لا في مدخلات المشروع: `moviepy 2.2.1` يتطلب `pillow<12` بينما البيئة تحتوي `pillow 12.3.0`. لا يظهر Pillow ضمن الاعتماديات المباشرة للمشروع. لم يُبنَ Docker لأن Docker CLI/Engine غير متاح في بيئة التدقيق.
- بلغت ذروة RSS لعملية `--validate-only` نحو 551,224 KiB (قرابة 538 MiB)، ولعملية الاختبارات نحو 819,040 KiB (قرابة 800 MiB). يجب مطابقة هذا القياس مع حد ذاكرة Railway الفعلي؛ لا تثبت الصور الحد المتاح أو أن OOM هو سبب الانهيار.

### 17.6 مطابقة صور Railway

تتضمن الصور حالة خدمة `Crashed` وتكرار أسطر self-test. أعاد التحقق المحلي إنتاج رسائل `engine=__boom__` وT17/T18 وحقن timeout وخسائر DailyCB التجريبية ضمن الاختبارات الذاتية؛ لذا لا يصح تصنيفها وحدها كصفقات أو خسائر سوقية حقيقية. كما أن `dotenv_loaded=False` لا يثبت غياب أسرار Railway عندما تسجل الصورة مؤشرات وجود مفاتيح MEXC وبيانات Telegram. لا تظهر في الصور علامة نهاية التحقق أو traceback نهائيًا أو حد الذاكرة أو Start Command، لذلك **سبب Crash على Railway غير محسوم**. يجب فحص آخر سجل كامل، وأمر البدء (استخدم `python -u main.py` لا `--validate-only` كخدمة دائمة)، وحد الذاكرة، وإصدار/اعتماديات صورة النشر.

### 17.7 الملفات التي تغيرت أو أعيدت تسميتها

- إعادة تسمية: `LIVE_RELEASE_ENV.example` ← `.env.example`، و`A66_FINAL_PRODUCTION_AUDIT_AR.md` ← `FINAL_AUDIT_REPORT.md`.
- ملفات محدثة: `main.py`، `Dockerfile`، `.gitignore`، `.dockerignore`، `README.md`، `CHANGELOG.md`، `HISTORICAL_AUDITS_INDEX_AR.md`، `test_a58_canonical_runtime_fixes.py`، `test_v702_a55_release_fixes.py`، `test_release_contracts.py`، `test_live_switch_documentation.py`، `A66_RELEASE_MANIFEST.json`، `FINAL_MANIFEST.json`، `A66_SHA256SUMS.txt`.
- الملفات المحذوفة: **لا يوجد**. لم تُضف نسخة تشغيل بديلة أو سكربت مبسط، ولم تُحذف وظيفة استراتيجية.

### 17.8 تعليمات Google Colab

1. ارفع `FINAL_PRODUCTION_RELEASE.zip` إلى جلسة Colab، ثم نفّذ:

   ```python
   !unzip -q /content/FINAL_PRODUCTION_RELEASE.zip -d /content/unified_scalper
   %cd /content/unified_scalper
   !python --version
   !pip install -r requirements.txt -r requirements-dev.in
   !python -m compileall -q .
   !python main.py --validate-only
   !python -m pytest -q
   ```

2. استخدم Python 3.12 كما هو محدد في Docker/CI. لا تضع مفاتيح API في Notebook أو ملف ZIP؛ استخدم Colab Secrets أو مدير أسرار المنصة عند الحاجة.
3. للتشغيل الدائم على Railway استخدم `python -u main.py` بعد تثبيت الاعتماديات وإعداد تخزين دائم لـSQLite. لا تستخدم `--validate-only` كأمر خدمة دائم.
4. قرار الإصدار يظل `NO_GO_UNATTENDED_LIVE` والسياسة `MONITOR_ONLY_NO_NEW_BUYS`. لا تفعّل مفاتيح live arm اعتمادًا على اختبارات Mock أو Shadow.

### 17.9 التحقق من ملف التسليم

اسم ملف التسليم `FINAL_PRODUCTION_RELEASE.zip`. تم بناؤه من قائمة الملفات المسجلة في `FINAL_MANIFEST.json` لا من مجلد العمل المفتوح؛ المطلوب في الفحص النهائي هو 99 إدخالًا فريدًا، تطابق inventory بالكامل، نجاح CRC وفك الضغط، والتحقق من 98 بصمة SHA-256 (جميع الملفات عدا ملف checksums نفسه). لا تتضمن الحزمة `.env` أو قاعدة بيانات تشغيل أو ملفات cache/bytecode أو Logs محلية.


## 18. إعادة التدقيق بعد إصلاح هندسة الأسعار — 2026-11-16

### 18.1 العيب المؤكد والإصلاح الفعلي

- في `SizingEngine.decide` داخل `main.py`، كانت قيم `NaN`/`Infinity` في `entry` أو `sl` أو `tp1`/`tp2` أو `tp3`/`spread_pct` تصل إلى حسابات الكمية والقيمة الاسمية قبل أن ترفضها بوابة الجدوى اللاحقة. إعادة إنتاج مستقلة لقيمة `entry=NaN` أظهرت قرارًا مرفوضًا في النهاية (`fee_unviable`) لكن مع `raw_position_value=NaN` و`quantity_asset=NaN` و`effective_risk_usdt=NaN`، كما حصلت قراءة الرصيد قبل الرفض. لم يثبت هذا المسار تنفيذ أمر؛ العيب المؤكد هو استمرار حساب المخاطر بمدخل غير صالح وتأخر الرفض.
- أُصلح ذلك بإضافة تحويل رقمي صريح وفحص `math.isfinite` وترتيب هندسة الأسعار والسبريد قبل `BalanceReconciler.fetch`. القيم غير الصالحة تُرفض الآن مباشرة بسبب `invalid_price_geometry`، مع عداد تشخيصي مستقل، ولا تنتج كمية أو قيمة اسمية غير منتهية ولا تنفذ قراءة رصيد.
- أضيفت ثلاثة اختبارات: رفض NaN/Infinity والسبريد السلبي قبل جلب الرصيد، رفض ترتيب سعر غير صالح قبل جلب الرصيد، وقبول حالة Paper سليمة مع التحقق من أن حجم المركز وسجل المخاطر محدودان ومنتهيان.
- استُكمل `.env.example` بأسماء متغيرات Telegram الاختيارية المقبولة في runtime، كقيم معلّقة فقط؛ لا توجد مفاتيح أو tokens فعلية.

**حصيلة هذا التدقيق:** عيب برمجي مؤكد جديد واحد، أُصلح بالكامل واختُبر. لا تُحسب إخفاقات الاختبار الخمسة المؤقتة الناتجة عن بصمات Manifest قديمة بعد تعديل `main.py` كعيوب runtime؛ تم تحديث البصمات وأُعيد تشغيل مجموعة الاختبارات كاملة بنجاح.

### 18.2 نتائج إعادة التحقق

| الفحص | النتيجة الفعلية |
|---|---|
| Python / AST | Python 3.13.5؛ 73 ملف Python قابلة للتحليل |
| Compile | `python -m compileall -q .` — PASS |
| Unit + Regression | **525 passed, 1 skipped, 0 failed**؛ 526 اختبارًا جُمعت؛ 32.37 ثانية |
| Integration / mock execution subset | **109 passed**؛ 9.27 ثانية؛ يتضمن تكامل SR، نوايا التنفيذ الوهمية، rate limiter، فشل/timeout، cost model، Telegram، وfault injection |
| SizingEngine focused tests | 3/3 PASS |
| `python main.py --validate-only` | PASS؛ exit 0؛ `bot_started=false` و`live_threads=[]`؛ 11.58 ثانية؛ ذروة RSS = 551,332 KiB |
| API / Telegram real delivery | NOT TESTED؛ اختبارات mock فقط |
| MEXC real account / order / native stop | NOT TESTED؛ لم يحدث اتصال تداول أو إرسال أمر |
| Python 3.12 / Linux amd64 / Docker | NOT TESTED في هذه البيئة |

الاختبار المتخطّى الوحيد هو عقد `test_release_contracts.py` الذي يتطلب سجل تشغيل تاريخيًا لـA51 غير موجود في توزيع المصدر. لم يُنشأ سجل بديل أو نتيجة مصطنعة.

### 18.3 الاعتماديات وقيود بيئة التحقق

- إصدار البيئة المحلية هو Python 3.13.5، بينما هدف النشر المحدد في المشروع Python 3.12 / Linux amd64.
- لم تكن `ccxt` و`aiosqlite` مثبتتين في بيئة التدقيق. محاولة تثبيت `requirements.in` تعذرت لأن DNS/الاتصال بمستودع PyPI غير متاح (`Temporary failure in name resolution`). بقيت الاعتماديات المباشرة مثبتة بالإصدارات المحددة في `requirements.in`؛ لم تُحذف أو تُخفف.
- `requirements-lock.txt` ما زال seed بإصدارات direct pins وليس lockfile شاملًا مع SHA-256 لكل الاعتماديات الانتقالية. لم تُخترع hashes. يتطلب إتمام ذلك تشغيل CI أو بيئة متصلة على Python 3.12/Linux amd64 كما هو موثق في workflow.
- `pip check` أظهر تعارضًا في بيئة التدقيق نفسها: `moviepy 2.2.1` يتطلب `pillow<12` بينما النسخة المثبتة هنا `Pillow 12.3.0`. لم ينشأ هذا التعارض من `requirements.in`، ولم تُعدّل اعتماديات المشروع لمعالجة تعارض حزم البيئة المشتركة.
- لم يُنفّذ Docker build أو اختبار منصة Railway؛ ولم يُختبر اتصال MEXC أو Telegram الحقيقي.

### 18.4 مطابقة الأمان والتسليم

- لم يعثر الفحص النصي على PEM private key أو نمط Telegram token صالح أو AWS access-key نمطي. لم تُستخدم أسرار في الاختبارات. ملف `.env.example` يحوي placeholders معلّقة فقط.
- أبقيت مفاتيح Live arm على 0، وحالة الإصدار `NO_GO_UNATTENDED_LIVE` والسياسة `MONITOR_ONLY_NO_NEW_BUYS`. كل اختبارات دورة التنفيذ التي شُغّلت كانت mock/paper أو validation-only.
- عدد ملفات المصدر في ZIP الأصلي: 99. عدد ملفات الحزمة النهائية: 99. لم يُحذف أي ملف أصلي؛ ولم تُضف وحدات تشغيل بديلة أو سكربت مبسط. أزيلت فقط artifacts محلية ولّدتها الاختبارات (SQLite/bytecode/cache) من مجلد البناء، ولم تكن ضمن الأرشيف الأصلي.
- الملفات التي عُدلت في هذا الإغلاق: `main.py`، `test_v702_production_audit_fixes.py`، `.env.example`، `README.md`، `CHANGELOG.md`، `FINAL_AUDIT_REPORT.md`، `A66_RELEASE_MANIFEST.json`، `FINAL_MANIFEST.json`، `A66_SHA256SUMS.txt`.

### 18.5 ما لم يُنفّذ ولماذا

- لم يُجرَ تقسيم شامل لـ`main.py`: الملف ما يزال نحو 103,962 سطرًا ويحتوي 1,471 تعريفًا علويًا، مع 11 اسمًا مكرر التعريف (12 إعادة تعريف إضافية). طبقات التوافق والـwrappers وتغيير bindings عبر ترتيب التنفيذ تجعل النقل الآلي خطرًا على سلطة التنفيذ؛ لم تُحذف أو تُدمج تلك التعريفات دون اختبارات parity مرحلية مستقلة. هذا دين صيانة مؤكد وخطة refactoring منفصلة، وليس إصلاحًا يُدّعى إنجازه هنا.
- لم تضاف فلاتر Trend/MTF/Volume/ATR جديدة أو تتغير الحدود: توجد بالفعل بوابات HTF/MTF وVolume/RS/order-book، وإدارة SL/TP/تكلفة ومخاطر؛ لا تتوافر بيانات سوق تاريخية موثوقة أو Walk-Forward لإثبات أن مضاعفة هذه القيود تحسن الأداء. لم تُخفّض عتبات الجودة أو السيولة أو المخاطر.
- لا تثبت الاختبارات ربحية، جودة fills، استقرار native stops على الحساب المستهدف، أو استلام Telegram على الإنترنت.
- صور Railway تثبت أن الواجهة أظهرت `Crashed` وأن السجل المقتطف يعرض رسائل self-test؛ لا تعرض traceback نهائيًا أو حد ذاكرة المنصة أو أمر البدء أو تطابق commit مع الحزمة. سبب الانهيار ما زال **غير محسوم**. قياس `--validate-only` المحلي (~539 MiB RSS) يستحق مقارنته بحد ذاكرة Railway، لكنه لا يثبت وقوع OOM.

**قرار الإصدار لا يتغير:** الحزمة صالحة لفحوص المصدر والاختبارات والمحاكاة المسجلة أعلاه، لكنها ليست اعتمادًا للتداول الحي غير المراقب. أبقِ live arms مغلقة حتى استكمال Python 3.12 CI وDocker والاعتماديات، وربط Railway بالإصدار نفسه، والتحقق من MEXC/Stops/Telegram ضمن بيئة مراقبة، ثم إجراء replay تاريخي وwalk-forward على بيانات موثوقة.

### 18.6 التحقق النهائي من ملف ZIP المستلَم

تم بناء `/mnt/data/FINAL_PRODUCTION_RELEASE.zip` من قائمة `FINAL_MANIFEST.json`، ثم فُكّ الأرشيف في مجلد تحقق جديد واختُبرت النسخة المفكوكة نفسها:

- ZIP: **99 إدخالًا فريدًا**؛ لا توجد إدخالات مكررة أو ملفات خارج القائمة.
- `ZipFile.testzip()` و`unzip -t`: **PASS**، ولا توجد أخطاء ضغط/CRC.
- فك الضغط: **PASS**؛ 99/99 ملفًا، مع تطابق كامل لقائمة Manifest.
- SHA-256: **PASS**؛ 98/98 ملفًا غير ذاتي التوقيع مطابقة لـ`A66_SHA256SUMS.txt`.
- Python AST: **PASS**؛ 73/73 ملف Python داخل الأرشيف.
- الاختبارات من المجلد المفكوك النهائي: **525 passed, 1 skipped, 0 failed** خلال 32.35 ثانية. التخطي الوحيد هو سجل A51 التاريخي غير المضمّن.
- `python main.py --validate-only` من النسخة المفكوكة: **exit 0**؛ `bot_started=false` و`live_threads=[]`؛ 10.97 ثانية وذروة RSS مقدارها 551,444 KiB.

موضع الإصلاح الجديد: `main.py:5714-5744`، والاختبارات المقابلة في `test_v702_production_audit_fixes.py:250-310`. يرفض المحرك هندسة السعر/السبريد غير الصالحة قبل جلب الرصيد أو حساب حجم الصفقة. لم تُستخدم مفاتيح حقيقية أو أي واجهة تداول حية خلال هذا التحقق.


## 19. مراجعة Production Audit النهائية للحزمة المستلمة — A70 — 2026-11-16

### 19.1 النتيجة التنفيذية والعيب المؤكد

- فُك الأرشيف المستلم وفُحصت قائمته: 99 ملفًا فريدًا، منها 73 ملف Python؛ لا توجد ملفات تشغيل بديلة لـ`main.py` ولا ملفات `.env` أو قاعدة بيانات/Cache تشغيلية ضمن التوزيعة.
- العيب المؤكد الوحيد الذي أُضيف إصلاحه في هذه الجولة هو **ترتيب إغلاق هوية التدقيق**: كتلة A69 كانت بعد استدعاء `main()` في نهاية `main.py`. لذلك كان تشغيل الخدمة كملف مباشر يدخل `main()` قبل تنفيذ الإغلاق، وقد لا يصل إليه مطلقًا أثناء عمر الخدمة؛ كما أن مسار `--validate-only` يستطيع إنهاء العملية قبله. كانت اختبارات الاستيراد ترى الكتلة بعد اكتمال الاستيراد، فغطّت على خلل ترتيب التنفيذ الفعلي.
- نُقلت كتلة الهوية إلى ما قبل فرع CLI ونقطة دخول `__main__`. أضيفت هوية A70 تكميلية إلى `V702_PACKAGE_AUDIT_REVISION` و`FINAL_CANONICAL_RUNTIME` و`STATS`، وأصبحت حقول A69/A70 متاحة قبل التحقق أحادي التشغيل وقبل دخول `main()`. أضيفت حقول السجل `[V702-BOOT]` و`[Main] Starting` لإظهار إصدار دمج التدقيق وإصدار إغلاق نقطة الدخول.
- أضيف اختبار انحدار يتحقق من الترتيب النصي الفعلي للكتل، ومن اتساق هوية A70/A69 وحقول runtime ووجود حقول الإصدار في سطر بدء التشغيل. كما حُدّث عقد إصدار A44 لاشتراط أن تنتهي هوية الحزمة بـA70.
- لم تُغيّر عتبات الاستراتيجيات أو النتيجة/الدرجة أو السيولة أو PreSend/Edge أو إدارة المخاطر أو سياسات Spot/Long-only أو منطق Queue/Telegram/Execution؛ ولم تُحذف أي وظيفة استراتيجية أو ملف مصدر.

### 19.2 مطابقة مسار التشغيل مع الكود

المسار الفعلي الذي جرت مطابقته مع الشيفرة هو:

1. **Startup / Config:** تحميل إعدادات البيئة مع إبقاء متغيرات المضيف/Railway أعلى أولوية؛ تشخيص وجود مفاتيح الاعتماد دون طباعة قيمها؛ تهيئة قاعدة البيانات والمخطط؛ استعادة حالة Daily Circuit Breaker والصفقات والأوامر/النوايا السابقة. النوايا التنفيذية غير المحسومة أو فشل إثبات حالة المصالحة يحجب إدخالات جديدة بدل التخمين.
2. **Protection before Scan:** إنشاء اتصال MEXC غير المختبر خارجيًا هنا، ثم مصالحة الحماية والخروج للصفقات المستعادة؛ تنفيذ دورة حماية أولية، كتابة heartbeat، وتشغيل PositionManager ومراقب runtime قبل طلب Universe/بدء المسح. فشل هذه الخطوة يقفل الإدخال الجديد.
3. **Universe / Scan:** بناء Universe السيولة؛ عند الفشل أو الفراغ تبقى الحماية/heartbeat حية ويُعاد المحاولة على cadence محدود، مع منع المسح والإدخال على Universe غير موثوق. عند توفر Universe تُجمع وتُتحقق snapshots وOHLCV متعددة الأطر وتُنشأ `market_data_map` محدودة؛ يجري prefetch محدود لدفاتر الأوامر المؤهلة ويعاد استخدام اللقطات المشتركة بدل مضاعفة الطلبات.
4. **Candidate / Rank / Prequal / Select:** تُشغّل محركات الاستراتيجيات على snapshot موحد لكل رمز، وتُدمج/تزال التكرارات، ثم يُنشأ ترتيب مركب محلي أولي. بعد ذلك تُطبق Prequal canonical على المرشحين قبل Global Arbitration؛ لا يختار الـarbiter إلا من مجموعة اجتازت Prequal، مع حدود الاحتفاظ/التنوع وRecall احتياطي محدود لا يتجاوز المجموعة المؤهلة. هذا يعني أن هناك ترتيبًا أوليًا لغرض فرز المرشحين قبل Prequal، لكن سلطة الاختيار النهائي تقع بعد Prequal.
5. **Builder / PreSend / Queue:** يظل `SignalBuilder.build_and_route` مسار تسليم المرشح النهائي إلى الفحوص النهائية؛ يُمنع اعتبار رجوع Builder بلا نتيجة نجاحًا. تخضع الحالة بعد ذلك لبوابات التنفيذ/الدرجة/السيولة/Edge/PreSend والرصيد والسلطة. قبول الرسالة في Telegram Queue ليس ACK ولا تنفيذًا.
6. **Telegram:** المرسل/الـoutbox يسجل الحالة الدائمة قبل الإدراج، ويستخدم dedup/coalescing وإعادة المحاولة المحدودة وحالات delivery صريحة. `QUEUED_NOT_DELIVERED_ACK` لا يُعرض كتسليم ناجح؛ تأكيد التسليم يتطلب ACK من Telegram. callbacks الدلالية داخل العملية لا تعادل تسليمًا مؤكدًا بعد إعادة تشغيل.
7. **Execution / Position Management:** تُمرر نية التنفيذ وسياق المرشح عبر `OrderExecutor.submit_entry`، مع reconciliation/idempotency للنتيجة غير المعروفة، وتبقى `PositionManager` مالكة لمتابعة المراكز الفعلية وإدارة مخارجها وحمايتها. A67 Hunter وA68 shadow outcomes طبقتان رصد/متابعة للمرجع فقط ولا تمتلكان مسار إرسال أوامر.

**تفسير ترتيب الدرجات:** `GlobalOpportunityBrain.rank_and_select` يبني ترتيبًا مركبًا أوليًا لمحركات كل رمز، لكنه ينفّذ Prequal canonical قبل `GlobalOpportunityArbiter.select` النهائي. لا يجوز قراءة رقم `ranked` أو `selected` أو `PRESEND_PASS` باعتباره أمرًا أُرسل أو fill تم.

### 19.3 مطابقة صور Railway مع السلوك الفعلي

- تظهر الصور حالة `Crashed` وتكرار boot/self-tests. رسائل `engine=__boom__`, وT17/T18، وأخطاء timeout وخسائر DailyCB الاصطناعية تظهر ضمن اختبارات عزل/حقن أعطال مقصودة وتُمسح/تُعزل قبل live epoch. لا تُثبت بذاتها خسارة سوقية أو انهيارًا من هذه الوظائف.
- `dotenv_file_present=False` و`dotenv_loaded=False` متوقعان في بيئة لا تضع ملف `.env` محليًا. وبالتزامن تعرض الصورة `mexc_api_key_present=True` و`mexc_api_secret_present=True` و`telegram_token_present=True` و`telegram_chat_present=True`؛ لذلك لا يُستنتج غياب الأسرار من علامتي dotenv. الأسرار لا تُطبع قيمها.
- لا يظهر في المقتطف traceback نهائي، أو رسالة OOM صريحة، أو حد ذاكرة Railway، أو أمر Start Command، أو سجل كامل يحدد سبب الخروج. لذلك **سبب Railway Crash غير مثبت**، وإصلاح A70 لا يدّعي أنه حل ذلك السبب.
- `python -u main.py --validate-only` نجح محليًا بعد التعديل: exit 0، و`bot_started=false`، و`live_threads=[]`، وزمن 11.15 ثانية، وذروة RSS = 550,428 KiB. القياس في بيئة Python 3.13.5 وبغير تشغيل حساب MEXC/Telegram حي؛ قد يكون مهمًا فقط إذا كان حد الخدمة أقل من هذا الاستهلاك، ولا يثبت OOM. لا يمكن استنتاج أداء وضع الخدمة الدائم من مسار validation-only.

### 19.4 نتائج التحقق المحلي لهذه الجولة

| الفحص | النتيجة |
|---|---|
| محتوى ZIP المستلم | 99 ملفًا فريدًا؛ القائمة تطابق Manifest قبل إعادة البناء |
| Python AST / Compile | 73 ملف Python؛ `compileall` و`py_compile` بعد إعادة الإغلاق |
| اختبارات المجموعة | **526 passed, 1 skipped, 0 failed؛ 527 collected؛ 30.24 ثانية (`pytest -vv -x`)** على استخراج النسخة canonical الأخيرة، إضافة إلى نجاحات الاستخراج النظيف السابقة. حالات الفشل الخمس في الجولة الوسيطة كانت عقود Manifest قديمة فقط، وأُغلقت بعد التحديث. |
| `--validate-only` | PASS؛ exit 0؛ لا بوت ولا خيوط تداول؛ 11.37 ثانية؛ RSS الأقصى 551,204 KiB |
| Regression A70 | PASS؛ يؤكد الترتيب قبل CLI و`__main__` وحقول الهوية الحالية |
| Python 3.12 / Linux amd64 / Docker | غير منفذ في بيئة التدقيق هذه |
| تثبيت الاعتماديات كاملة | غير مكتمل: `ccxt` و`aiosqlite` غير مثبتتين محليًا، ومحاولة PyPI لم تنجح بسبب DNS/شبكة البيئة |
| MEXC / Telegram الحقيقيان | لم يُجر اتصال مصادقة أو أمر أو تسليم Telegram حي |
| الربحية / Edge الإنتاجي | غير مثبتة؛ اختبارات Mock/Paper لا تثبت ربحًا أو جودة fills |

### 19.5 بنية المصدر والاختناقات

- `main.py` ما زال ملفًا كبيرًا (104,016 سطرًا)؛ 1,471 تعريفًا علويًا، و11 اسمًا مكرر التعريف مع 12 إعادة تعريف إضافية. هذا يجعل ترتيب الـwrappers والـglobals عاملًا جوهريًا ويزيد كلفة التتبع والاختبار، وهو ما كشف عيب ترتيب A69/A70. لم أنفذ تفكيكًا آليًا في هذه الجولة لأن نقل تعريفات واعتماديات متداخلة دون parity test مستقل قد يغيّر سلطة التنفيذ أو مسارات الحماية.
- مسح الرموز/الأطر ودفاتر الأوامر قد يخلق ضغط CPU/RAM/زمن استجابة؛ توجد حدود Universe/deep-scan وprefetch وretention/retry. القياس المحلي للـvalidation-only يقارب 537.5 MiB RSS (550,428 KiB). يلزم مطابقة ذلك مع حد ذاكرة Railway الفعلي وسجلات المنصة قبل نسب الانهيار إلى الذاكرة.
- Outbox queue admission وTelegram delivery ACK مرحلتان مختلفتان؛ لا تعِدّ `QUEUED` على أنه `SENT`. وتبقى دلالات callback داخل العملية غير مكافئة لـACK دائم بعد Restart.
- سجل Railway المقتطف يُظهر دورات إقلاع قريبة زمنيًا؛ لكنه لا يعرض مدة حياة كل عملية أو سبب إنهائها. قد تكون إعادة تشغيل من المنصة أو أمر بدء/اعتمادية/حد موارد، لكن لا يوجد دليل كافٍ لترجيح أحدها.

### 19.6 حالة الإصدار النهائية

- الإصدار التنفيذي الثابت يبقى `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL`؛ A69 يبقى merged-audit closure، وA70 هو إغلاق هوية/ترتيب نقطة الدخول الحالي. لا يتغير وسم التوزيعة التاريخي ولا يُنشأ executable ثانٍ.
- جميع مفاتيح live arms والبوابات تبقى كما هي؛ السياسة `MONITOR_ONLY_NO_NEW_BUYS` والقرار `NO_GO_UNATTENDED_LIVE`؛ لا يوجد أي ادعاء اعتماد Live أو ربحية.
- يجب اعتبار ملف ZIP المسلّم مرجع المصدر النهائي لهذه الجولة، مع أن صلاحية تشغيله كخدمة على Railway تتطلب Python 3.12/اعتماديات الهدف وDocker/CI ومقارنة حدود الموارد والسجلات الكاملة للـdeployment.


### 19.7 التحقق من الأرشيف النهائي بعد إعادة البناء

- بُني `FINAL_PRODUCTION_RELEASE.zip` من قائمة الملفات المسجلة في `FINAL_MANIFEST.json`، مع 99 مسارًا فريدًا ودون ضم `unified_scalper.db` أو `.pytest_cache` أو `__pycache__` أو `.env` أو أسرار.
- فُك الأرشيف في استخراجين جديدين؛ بدأ الاختبار الثاني دون قاعدة بيانات سابقة. طابقت قائمة الملفات 99/99، ونجح CRC، وتحققت 98/98 بصمة SHA-256، ونجح `compileall` و`py_compile` لـ73/73 ملف Python.
- من الاستخراج النظيف: `pytest -q` على النسخة canonical الأخيرة أظهر **526 passed, 1 skipped, 0 failed** خلال 30.24 ثانية (`pytest -vv -x`). التخطي الوحيد سجل A51 تاريخي غير مضمن. كما نجح `python -u main.py --validate-only` بخروج 0 خلال 11.37 ثانية وذروة RSS = 551,204 KiB؛ `bot_started=false` و`live_threads=[]`.
- ملاحظة تشغيلية: جولة أولى واحدة من Pytest بعد الاستخراج انتهت بمهلة أداة التنفيذ قبل إظهار النتيجة، لكن إعادة تشغيل verbose على الاستخراج ذاته ثم تشغيل استخراج جديد نظيف أكملا المجموعة بالنتيجة نفسها؛ واختبار النسخة canonical الأخيرة اكتمل أيضًا دون إخفاق. لا أخفي هذه المحاولة؛ سجل الاستخراج النظيف الثاني هو النتيجة الحاسمة التي اعتمدت هنا.


## 20. إعادة تدقيق الحزمة المستلمة وصورة Railway الجديدة — 2026-11-16

### 20.1 النتيجة التنفيذية

- الحزمة الأصلية `FINAL_PRODUCTION_RELEASE(2).zip` قابلة للقراءة؛ `ZipFile.testzip()` أعاد `None`، وبداخلها **99 إدخالًا فريدًا** تمامًا، مطابقًا لقائمة `A66_RELEASE_MANIFEST.json` و`FINAL_MANIFEST.json`. لم توجد أسماء مكررة أو مسارات خارجية في الأرشيف.
- إجمالي ملفات المشروع المفكوكة: **99**، منها **73 ملف Python** (58 ملف اختبار و15 ملف تشغيل/مساعدة). الحجم المفكوك نحو 7.23 MB. `main.py` حجمه نحو 5.84 MB وبه 104,016 سطرًا؛ AST وجد 1,471 تعريفًا على المستوى العلوي و11 اسمًا مكرر التعريف (12 إعادة تعريف إضافية). الإعادات جزء من طبقات التوافق/الـwrappers المتتابعة، ولم تُنقل آليًا.
- **لم يُكتشف عيب منطقي/تشغيلي جديد قابل لإعادة الإنتاج في هذه الجولة، ولذلك لم أغيّر منطق التداول أو التنفيذ أو الاستراتيجية ولم أجرِ refactor تخمينيًا**. هذا لا ينفي وجود سبب تعطل في حساب Railway؛ فاللقطة لا تحتوي بيانات كافية لتحديده.

### 20.2 نتائج الاختبارات التي نُفذت

| الفحص | النتيجة المسجلة فعليًا |
|---|---|
| `py_compile` لكل المصادر | **73/73 PASS** |
| `python -m compileall -q .` | **PASS** |
| مجموعة Pytest الكاملة | **526 passed, 1 skipped, 0 failed**؛ 527 جُمعت؛ 35.39 ثانية في آخر استخراج نظيف (ظهر الملخص الكامل، لكن غلاف التنفيذ لم يُرجع رمز الخروج بسبب انتهاء مهلته بعد الملخص). إعادة كاملة سابقة مكافئة انتهت برمز 0 خلال 31.92 ثانية. |
| مجموعة تكامل/محاكاة مركزة: pipeline + execution intent + mock isolation + cost + shadows + A70/A705 | **71 passed**؛ 9.49 ثانية |
| مجموعة guardrails / retry / Telegram / safety / startup | **110 passed**؛ 17.18 ثانية |
| `python -u main.py --validate-only` | **exit 0**؛ `bot_started=false`؛ `live_threads=[]`؛ 11.58 ثانية؛ ذروة RSS = **551,408 KiB** |
| `main.validate_config()` مباشرة بعد import | **True**؛ نحو 1.05 ثانية؛ لم يبدأ `run_bot` ولم يتصل بسوق |
| ZIP الأصلي | `testzip()` = `None`؛ 99/99 إدخالًا قابلًا للفحص |
| A66 SHA-256 قبل تحديث وثائق هذه الجولة | **98/98 PASS**؛ الملف نفسه مستثنى من توقيع نفسه |

الاختبار المتخطّى الوحيد هو `test_release_contracts.py:375` لاحتياجه سجل A51 تاريخيًا غير موجود في التوزيعة النظيفة. لا يوجد تخمين أو ملف سجل مصطنع بدلًا منه. مجموعتا الاختبارات المركزة تتداخلان مع مجموعة الاختبارات الكاملة؛ أُدرجتا لإظهار تشغيل مسارات التكامل ووسائل الحماية صراحةً، وليس لجمعها كعدد اختبارات فريد إضافي.

ملاحظة تشغيل الاختبارات: محاولة `pytest -q` الأولى من الاستخراج انتهت بمهلة أداة التنفيذ عند نحو 54% دون ملخص؛ لم أحتسبها نجاحًا أو فشلًا. إعادة `pytest -vv -x` كاملة سابقة اكتملت بخروج 0 (526 نجاحًا و1 تخطٍ و0 إخفاقات، 31.92 ثانية). بعد تحديث وثائق/بيانات الإصدار وإعادة بناء ZIP، أظهرت إعادة كاملة من استخراج نظيف آخر الملخص الكامل نفسه (526/1/0 خلال 35.39 ثانية)، لكن أداة التنفيذ انتهت بمهلة بعد طباعة الملخص ولم تسجل رمز خروج العملية. على الأرشيف الأخير نفسه اجتازت اختبارات عقود الإصدار والإغلاق 56 اختبارًا مع تخطٍ واحد وبخروج 0، واجتاز `--validate-only` بخروج 0.

### 20.3 مراجعة صورة Railway المرفقة

- رأس الخدمة يعرض `Unified-Scalper / 9d951f72` وحالة `Crashed`. السجل الظاهر يعيد مقاطع الإقلاع في توقيت يقارب 14:56:17 إلى 14:56:30. لا يحتوي ZIP على `.git` أو إعدادات Railway، لذلك لا يمكن إثبات أن commit `9d951f72` يطابق `main.py` المرفق أو الـSHA في Manifest.
- `MSE.selftest engine=__boom__ isolated exception: boom` **خطأ مُفتعل عمدًا** في اختبار عزل المحرك؛ الكود يتوقع إرجاع قائمة فارغة للمحرك المعطوب مع تسجيله، ثم تظهر `all 8 self-tests PASSED`. لا تُفسر هذه الرسالة على أنها crash للمحرك الحقيقي.
- `T17/USDT` و`T18/USDT` مع `stage=selftest` رسائل اختبارات مُصطنعة لتسجيل رفض Prequal واستثناء قيمة؛ و`DailyCB-R5` بخسائر `-1.000R` و`-1.050R` ثم reset إلى `+1.200R` جزء من اختبار استعادة حالة القاطع اليومي. لا تمثل تداولًا حيًا أو خسارة فعلية. كما أن `DB` المؤقت باسم `/tmp/v702_r4_streak_*.db` سجل اختبار معزول، وليس إثباتًا لمسار قاعدة بيانات الخدمة الدائم.
- `ENV-BOOT` الظاهر يبيّن `dotenv_loaded=False` بالتزامن مع `api_secret_present=True` ووجود Telegram token/chat. هذا متسق مع حقن الأسرار من Railway Variables؛ عدم وجود ملف `.env` ليس بحد ذاته سبب الانهيار، ولا يظهر أي محتوى سرّي في السجل المعروض.
- المقتطف لا يعرض نهاية التشغيل أو traceback أو `[V702-CRASH]` أو marker كاملًا لمرحلة `run_bot_enter`. لذلك **سبب Crashed غير مثبت**. الاحتمالات التي ينبغي فحصها بالترتيب: أمر بدء الخدمة (يجب أن يكون `python -u main.py` لا `--validate-only`)، متغيرات `UNIFIED_V699_VALIDATE_ONLY` و`UNIFIED_V702_VALIDATE_ONLY` و`UNIFIED_VALIDATE_ONLY` (يجب غيابها أو أن تكون `0`)، ثم آخر traceback كامل وقياس ذاكرة Railway. ذروة RSS المحلية في مسار `--validate-only` كانت 551,512 KiB؛ هذه قيمة للمقارنة بحد ذاكرة الخدمة فقط ولا تثبت OOM.

### 20.4 الاعتماديات وحدود البيئة

- بيئة التدقيق هي Python **3.13.5**، في حين أن الهدف المعلن هو Python **3.12 / Linux amd64**.
- `ccxt` و`aiosqlite` غير مثبتتين في بيئة التدقيق؛ الكود يتعامل مع غياب `ccxt` على أنه غياب اعتماد اختياري عند import، لكن إنشاء عميل MEXC الفعلي يتوقف صراحةً عندما لا تتوفر `ccxt`. الحزمتان مثبتتان في `requirements.in` (والحزمة تُبنى وفق ملف الاعتماديات المباشر). لذلك لم يُنفّذ اتصال MEXC أو `run_bot` ضد الشبكة.
- لم يتوفر Docker في بيئة التنفيذ؛ لم يتم بناء Docker image أو اختبار Railway نفسه أو إرسال Telegram حقيقي. `pip check` يعرض تعارضًا خارجيًا في البيئة العامة فقط: `moviepy 2.2.1` يطلب `Pillow<12` بينما المثبت `Pillow 12.3.0`؛ هذه الحزم ليست من اعتماديات المشروع المباشرة.
- `requirements-lock.txt` ملف direct-pin seed لا lock شاملًا لكل الاعتماديات الانتقالية مع hashes. الـworkflow يولّد lock كاملًا على Python 3.12/Linux amd64 في CI؛ لم أشغّل هذا الـCI أو أختلق hashes.

### 20.5 الأمان وحساب نتائج الإصلاح

- فحص ملفات النص/الكود/الإعدادات لم يجد قيمًا فعلية واضحة لمفاتيح MEXC أو Telegram؛ `.env.example` يحتوي أسماء ومتغيرات نموذجية فقط. لم تُستخدم أسرار في الاختبارات أو في `--validate-only`، ولم يُرسل أي أمر تداول حقيقي.
- عدد الملفات الأصلي داخل ZIP المستلم: **99**. العدد بعد إعادة البناء: **99**. المحذوف: **0**. الملفات الأساسية والاختبارات والاعتماديات بقيت داخل الأرشيف.
- عدد عيوب الكود الجديدة المثبتة في هذه الجولة: **0**؛ عدد إصلاحات منطق التطبيق الجديدة في هذه الجولة: **0**. السبب هو عدم وجود عطل يمكن ربطه يقينًا بالمقتطف، ونجاح الاختبارات ومسار التحقق. لم أغيّر استراتيجية أو عتبات/بوابات مخاطر لمجرد التجربة. الإصلاحات المصدرية التاريخية (ومنها هندسة الأسعار وإغلاق هوية A70) باقية كما هي وموثقة في الأقسام السابقة.
- ملفات التوثيق/الإصدار التي تم تحديثها في إعادة التدقيق: `README.md`، `CHANGELOG.md`، `FINAL_AUDIT_REPORT.md`، `A66_RELEASE_MANIFEST.json`، `FINAL_MANIFEST.json`، `A66_SHA256SUMS.txt`. **لم يعدّل `main.py` أو أي ملف تشغيل Python في هذه الجولة**، ولم يُحذف ملف.

### 20.6 تعليمات Colab

1. ارفع `FINAL_PRODUCTION_RELEASE.zip` عبر `files.upload()` ثم فكّه إلى `/content/unified-scalper`.
2. ادخل المجلد، وتحقق من Python؛ الهدف المعتمد 3.12.
3. نفّذ `python -m pip install -r requirements.txt`، ثم `python -m compileall -q .` و`python -m pytest -q`.
4. شغّل `python -u main.py --validate-only` أولًا؛ يجب أن يظهر `bot_started=false` ويخرج برمز 0.
5. للتشغيل المراقب فقط، مرّر `MEXC_API_KEY` و`MEXC_API_SECRET` من Colab Secrets باستخدام مفتاح MEXC بصلاحيات قراءة فقط، ودون تداول/سحب، وأبقِ مفاتيح Live-arm على `0`. Telegram اختياري. جلسة Colab قابلة للانقطاع وليست مضيفًا دائمًا.

### 20.7 نتيجة التسليم

بُني `FINAL_PRODUCTION_RELEASE.zip` من قائمة `FINAL_MANIFEST.json` بعدد **99 ملفًا فريدًا**، ثم اجتاز اختبار CRC وفك الضغط ومطابقة قائمة الملفات. كما اجتازت ملفات الحزمة الـ98 غير الذاتية فحص SHA-256 مقابل `A66_SHA256SUMS.txt`، واجتاز الاستخراج النظيف فحوصات Python والاختبارات و`--validate-only` الموضحة في هذا التقرير. يبقى قرار التشغيل **`NO_GO_UNATTENDED_LIVE`**. لا يمكن اعتبار رسالة Crash محلولة حتى تتوفر نهاية Deploy Logs وأمر Start Command وذاكرة Railway أو traceback من نفس revision `9d951f72`.


## 21. A72 — Public market discovery without private MEXC credentials and independent macro reporting (2026-11-16)

### 21.1 Executive decision

Applied the A72 correction directly to the existing `main.py`. In the release's hard-locked `MONITOR_ONLY_NO_NEW_BUYS` / `NO_GO_UNATTENDED_LIVE` mode, public MEXC Spot market-data discovery no longer depends on API key/secret, a private account session, or wallet balance. A separate authenticated MEXC client is optional and is created only when recovered open positions or unresolved execution intents require private reconciliation/protection. No order authority was added.

BTC Macro is now an observational stream. When closed BTC data is available it reports `BULLISH`, `BEARISH`, or `NEUTRAL`; when the data is insufficient/unavailable it reports `UNKNOWN`. Macro classification/notification is performed before the empty-Universe defer, so an empty or unavailable trading universe does not prevent the BTC macro attempt. This does **not** remove strategy-specific regime/crash filters, local confirmations, cost/risk gates, or other canonical admission rules.

### 21.2 Confirmed defects and fixes

| # | Confirmed issue in the supplied source | Impact | Applied correction |
|---:|---|---|---|
| 1 | Read-only startup called the authenticated MEXC client factory even when no private state required it. | Missing/invalid MEXC keys could stop public discovery and Telegram opportunities before scanning. | Added `create_mexc_public_async()` with no `apiKey`/`secret`; monitor-only startup uses this public client. |
| 2 | Monitor-only boot still ran private balance/TruthSeal preflight. | A zero wallet balance or private-account/API failure could prevent read-only idea discovery even though balance is not needed to scan. | Skipped private balance preflight only for the hard-locked read-only release; live authority remains blocked. |
| 3 | Empty-Universe `continue` occurred before the shared BTC macro fetch/classification. | A MEXC Universe failure also suppressed BTC Macro, making the operator blind to the broader market context. | Moved BTC 5m/15m/1h/4h context processing and macro notification before the empty-Universe defer. Symbol-specific scanning remains deferred if Universe is empty. |

**Confirmed logic defects corrected in this round: 3.** No strategy threshold, score floor, family regime allow-list, crash policy, risk cap, or execution authorization was relaxed.

### 21.3 Runtime behavior and important boundaries

- No MEXC key/secret and no wallet balance are required for public market scanning in monitor-only mode. This assumes the public MEXC endpoints are reachable and CCXT is installed.
- Invalid/missing private credentials no longer terminate public discovery. If an old position or unresolved order intent exists, its private reconciliation/protection cannot be claimed without valid account access; the runtime sets an explicit unverified state, blocks new execution, and does not emit a false healthy PositionManager lease.
- Telegram delivery still requires a valid bot token and destination chat ID. Public scanning can continue without Telegram configuration, but no Telegram notification can be delivered without those values. A real Telegram delivery was not attempted in this offline audit.
- Opportunity messages still depend on actual data and the existing candidate/Hunter lanes producing a real measured idea. The changes do not fabricate a signal when the market data is unavailable, Universe is empty, or no pattern qualifies.
- Macro `BEARISH`/`NEUTRAL` reporting does not itself authorize a trade or bypass each strategy's family/macro/crash requirements. It merely removes a global requirement for a bullish macro label to continue observation/discovery.
- The public-only runtime does not start private Telegram command controls or the private PositionManager. If recovered positions exist while private account access is missing/invalid, their protection status is explicitly unverified. The release is still `MONITOR_ONLY_NO_NEW_BUYS` and `NO_GO_UNATTENDED_LIVE`.

### 21.4 Files changed / archive accounting

| File | Change |
|---|---|
| `main.py` | Public-vs-private exchange-client separation; read-only startup and preflight separation; conditional private recovery/PM/Supervisor operations; descriptive Macro classifier and Telegram notifier; Macro fetch before empty-Universe defer; A72 source-audit checks. |
| `test_v705_production_audit_closure.py` | Regression tests for public-client credential isolation, all four Macro states, bearish Macro Telegram notification under monitor-only policy, empty-Universe Macro ordering, and unchanged live authority. |
| `README.md` | Corrected credential requirements, Macro semantics, Telegram requirements, and Colab instructions. |
| `CHANGELOG.md` | Added A72 release notes. |
| `FINAL_AUDIT_REPORT.md` | Added this audit and verification section. |
| `FINAL_MANIFEST.json` | Updated main-source digest, A72 read-only/macro scope, and final verification claims. |
| `A66_RELEASE_MANIFEST.json` | Synced A72 revision/verification metadata and source digest. |
| `A66_SHA256SUMS.txt` | Regenerated hashes for all 98 other packaged files. |

- Modified files total: **8** (2 Python files, 3 documentation files, 2 manifests, 1 checksum ledger). Original archive: **99 regular files**. Final archive: **99 regular files**.
- Files added: **0**. Files removed: **0**. No required functionality was deleted to meet the 99-file limit. `unified_scalper.db`, caches, bytecode, and any `.env` secret file are excluded from the ZIP.
- Python source/operational files modified in this round: `main.py` plus one existing test module; documentation files modified: three.

### 21.5 Verification performed for A72

| Test / check | Result |
|---|---|
| A72 targeted regression module + existing missing-private-credentials + empty-Universe protection regressions | **19 passed, 0 failed** (9.02s) after adding the invalid-private-key case. |
| `main._v702_a66_startup_recovery_source_check()` | PASS (asserted by regression). |
| `main._v702_a72_read_only_runtime_source_check()` | PASS (asserted by regression). |
| No-key public-client config | PASS in mocked factory test; captured config contains no `apiKey` or `secret`. |
| BTC macro regime classifier | PASS in unit test for `BULLISH`, `BEARISH`, `NEUTRAL`, `UNKNOWN`; all declare `discovery_direction_gate=False`. |
| Bearish macro Telegram enqueue | PASS in mocked dispatcher test; message states macro does not turn discovery off and live entry remains monitor-only. |
| Real MEXC/Telegram calls or real orders | **Not performed**. All execution remains test/mock/read-only; no trading account was used. |
| Full pytest suite | **540 passed, 1 skipped, 0 failed; 541 collected**. All 58 test modules ran in four batches (89 + 111 + 171 + 169 passed; one historical A51-log fixture skipped); summed batch runtime 59.14s. Monolithic pytest exceeded tool timeout, so the full collection was completed in four bounded runs. The monolithic one-process run exceeded the tool time limit, so no single-process full-suite pass is claimed. |
| Compileall | **PASS**; explicit per-file `py_compile` passed for **73/73** Python files. |
| `python -u main.py --validate-only` with MEXC and Telegram secrets removed | **PASS**, exit 0, `bot_started=false`, `live_threads=[]`, and MEXC/Telegram secrets were absent from the environment; no real MEXC/Telegram network calls or orders. |

### 21.6 Google Colab operation

1. Upload and unzip `FINAL_PRODUCTION_RELEASE.zip`, then `cd /content/unified-scalper`.
2. Install `requirements.txt`; run `python -m compileall -q .`, `python -m pytest -q`, and `python -u main.py --validate-only`.
3. To receive Telegram notifications, set `TELEGRAM_BOT_TOKEN` (or `TELEGRAM_TOKEN`) and `TELEGRAM_CHAT_ID` (or `TELEGRAM_CHAT`) securely in the Colab process environment. The README demonstrates `getpass` so the bot token is not stored in notebook code.
4. Start `python -u main.py` in a foreground cell. No MEXC API key/secret or balance is required for public read-only market scanning; the machine still needs Internet access to MEXC public endpoints. Colab may disconnect and is not a persistent production host.
5. Keep `UNIFIED_LIVE_PILOT_ENABLE=0` and `UNIFIED_A55_LIVE_ARM=0`. This release does not authorize real orders.

### 21.7 Remaining limitations

- Public data discovery depends on MEXC's public endpoints, their current symbol metadata, network availability, and rate limits. If these fail, a candidate opportunity cannot be measured; the Macro notifier may report `UNKNOWN` if Telegram is available.
- Actual Telegram delivery, deployment-platform uptime, target Python 3.12/Linux amd64, Docker build, account recovery with a real MEXC account, and profitability remain unverified.
- The full test run and final archive-level checks are only called PASS in this report after the final output shows their exact results.


### 21.8 Final ZIP extraction verification

The final artifact `/mnt/data/FINAL_PRODUCTION_RELEASE.zip` was extracted into a clean directory and the exact extracted copy was validated:

- ZIP inventory: **99 unique entries**, exact match to `FINAL_MANIFEST.json`; CRC test returned no corrupt member; clean extraction passed.
- SHA-256 ledger: **98/98 non-self files passed** against `A66_SHA256SUMS.txt`.
- `compileall`: PASS; explicit `py_compile`: **73/73 Python files passed**.
- Full tests from the final ZIP extraction: **540 passed, 1 skipped, 0 failed; 541 collected** across all 58 test modules in four batches (89 + 111 + 171 + 169; 58.47s combined runtime). The single skip is the historical A51 log test because the historical log is not included in the clean release.
- `python -u main.py --validate-only` from the final extraction with MEXC and Telegram secret variables removed: PASS, exit 0, `bot_started=false`, `live_threads=[]`; A66 validation reported 25 checks PASS.
- No database, `.env`, credentials, caches or bytecode were packed.

The complete one-process pytest invocation exceeded the execution tool timeout; the test suite was therefore run by all 58 test modules in four separate batches, all of which completed successfully. No single-process full-suite pass is claimed.

---

# A73 — Final confirmed-opportunity delivery and multi-timeframe follow-up audit (2026-11-16)

**Audited source:** the user-uploaded `FINAL_PRODUCTION_RELEASE(3).zip`, extracted as the source baseline.  
**Canonical distribution identity:** `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL` (kept for compatibility).  
**Supplemental corrective revision:** `A73-CONFIRMED-ONLY-TRADINGVIEW-AND-MULTI-TF-OUTCOMES-2026-11-16`.  
**Final operating authority:** `MONITOR_ONLY_NO_NEW_BUYS`; distribution decision remains `NO_GO_UNATTENDED_LIVE`.

## A73.1 User-facing behavioral requirements

The Opportunity Hunter now distinguishes a stored/forming candidate from an alert-worthy opportunity:

- `WATCH` is retained in SQLite for internal observation and diagnostics, but is not delivered to Telegram.
- `PREQUAL_PASS` is an internal pipeline milestone only. It cannot, by itself, trigger a Telegram `CONFIRMED` alert because final score and cost/execution gates may still reject it.
- A `CONFIRMED` alert is permitted for a named closed-candle technical trigger (explicitly labelled technical-only), or after the canonical `SCORE_PASS`. `TRADEABLE` still requires canonical `PRESEND_PASS`; it is not a submitted order or a fill.
- Every Hunter alert includes a MEXC Spot TradingView chart URL, analytical entry, invalidation, reference targets, and its follow-up candle interval.
- Existing strategy-engine candidates marked `SWING` retain their style/timeframe metadata. Repeated discovery cycles anchor identity to the relevant closed candle rather than a changing per-cycle generation timestamp, preventing duplicate rows for the same family/setup/timeframe/candle.
- Intraday outcome tracking uses closed 5m OHLC candles; Swing outcome tracking uses closed 1h OHLC candles and defaults to a seven-day tracking lifetime. Existing discovery pattern logic remains 5m/15m; Swing coverage comes from existing strategy engines rather than a newly invented Swing signal engine.
- Outcome updates are shadow/reference observations only. If one OHLC candle touches a stop and target, the stop is counted first conservatively because bar data cannot prove intrabar ordering. A TP/SL touch does not prove entry, order submission, fill, fees, or realized PnL.

## A73.2 Confirmed defects and actual corrections

| # | Location in `main.py` | Confirmed defect | Effect | Applied correction |
|---:|---|---|---|---|
| 1 | `OpportunityHunter._queue_alert` / `scan_market_map` (around lines 103127–103380) | `WATCH` rows could reach the Telegram queue through the Hunter's generic state path. | Telegram could present a still-forming setup as an opportunity worth following. | Added one shared alert-eligibility policy and applied it both before queueing and again before delivery. `WATCH` is persisted but suppressed. |
| 2 | `OpportunityHunter.on_pipeline_event` (around line 102700) | `PREQUAL_PASS` was treated as an externally confirmed milestone even though Score and PreSend gates were still pending. | Premature notification of candidates that could later fail downstream gates. | `PREQUAL_PASS` only updates internal evidence/state. `SCORE_PASS` produces the canonical scored confirmation; `PRESEND_PASS` alone produces `TRADEABLE`. |
| 3 | `OpportunityHunter.observe_strategy_candidate` (around line 102622) | Strategy observation identity depended on the pipeline-generated key, which changes with generated time/cycle. | The same market setup could create repeated Hunter rows/alerts across scan cycles. | Added a stable key from symbol, family, pattern, timeframe profile and last closed anchor candle; preserved the original pipeline key only as provenance evidence. |
| 4 | `OpportunityTelegramNotifier._tradingview_link` and `OpportunityHunter._message` (around lines 13460 and 103197) | Hunter alert messages lacked an actionable chart link. | The user could not jump directly from a signal to the relevant TradingView market chart. | Added a URL-encoded MEXC Spot TradingView chart link and included strategy style and the outcome-monitoring interval in the message. |
| 5 | `observe_strategy_candidate` / `_outcome_interval_sec` (around lines 102622–102678 and 102971) | Strategy style/timeframe and observation horizon were not preserved consistently for the Hunter's non-5m candidates. | A non-scalping/Swing strategy could be treated as an intraday candidate or deduplicated/expired too quickly. | Preserve `strategy_style` and `timeframe_profile`; add a 604,800-second default Swing TTL, and bind Swing tracking to 1h closed bars. |
| 6 | `_advance_shadow_outcome` / `scan_market_map` (around lines 102985–103400) | Outcome advancement and labels were fixed to a 5m horizon. | Swing TP/SL progress could be evaluated on the wrong cadence or reported with the wrong interval. | Resolve the interval per idea, cache the corresponding already-provided 5m/1h frame, advance only closed candles, and label stop/target/expiry events with the actual horizon. |
| 7 | `.env.example` | A stale comment incorrectly stated that MEXC private credentials are required even for monitor-only scanning. | Operators could unnecessarily expose private keys or think public discovery would stop without them. | Corrected the example: public market scanning needs no keys; private read-only credentials are only relevant when recovered positions or unresolved intents require reconciliation/protection. |

**Confirmed defects in this A73 scope: 7 (6 runtime/logic + 1 configuration-documentation inconsistency). Fixes applied: 7.** This count refers only to the independently confirmed A73 issues above, not to every historical issue documented in earlier release sections. No core strategy engine was deleted; no score floor, entry gate, cost gate, risk cap, or order-execution authority was relaxed.

## A73.3 Changed files and archive accounting

| File | Change |
|---|---|
| `main.py` | Confirmed-only notification policy; Prequal/Score/PreSend state separation; stable strategy-candidate identity; TradingView message link; style-aware TTL and 5m/1h shadow outcome tracking; runtime revision metadata. |
| `test_v702_production_audit_fixes.py` | Updated confirmation-state/ACK/message tests; added WATCH suppression, 1h Swing outcome, stable Swing deduplication/TTL and scan-level alert-policy tests. |
| `test_production_guardrails.py` | Updated the rate-limit contract test to use a valid formed/confirmed alert instead of the now-suppressed WATCH state. |
| `README.md` | Corrected the confirmation contract, documented confirmed-only alerts, TradingView, Swing tracking and Colab steps. |
| `CHANGELOG.md` | Added the A73 corrective release notes. |
| `FINAL_AUDIT_REPORT.md` | Added this final A73 defect/fix/verification record. |
| `.env.example` | Corrected stale MEXC private-credential guidance for monitor-only public scanning. |
| `FINAL_MANIFEST.json` | Refreshed canonical source digest and A73 verification metadata; retained compatibility identity fields. |
| `A66_RELEASE_MANIFEST.json` | Synchronized A73 source digest and release-evidence metadata while preserving A66 lineage. |
| `A66_SHA256SUMS.txt` | Regenerated the current package checksum ledger. |

- Original ZIP inventory: **99 entries**.
- Final ZIP inventory: **99 entries** (within the 99-file ceiling).
- Python source files in the package: **73**.
- Files modified: **10**. Files added: **0**. Files removed: **0**. No required component was deleted to satisfy the file ceiling.
- The generated SQLite runtime database, `.env`, bytecode, caches, and virtual environments are excluded from the release archive. `.env.example` remains included with placeholders only.

## A73.4 Verification boundary

The final report records exact results after the release archive has been built and extracted for a clean-room verification. The following distinctions are mandatory:

- Offline unit/integration tests use synthetic candles, temporary SQLite databases, mocks and dry-run/validate-only controls. They do not represent live market observations.
- `--validate-only` must exit with `bot_started=false` and no live worker startup. No account keys or Telegram token are required for that validation path.
- No live exchange order, actual account execution, Telegram network delivery, or live profitability test is part of this audit.
- Public market discovery and TradingView link format can be tested locally, but current symbol availability, a user's TradingView access, MEXC data stability, network behavior and real Telegram delivery require a separate supervised environment check.
- Colab is suitable for validation or supervised monitoring, not durable unattended monitoring: its runtime may disconnect and lose local database state unless external persistent storage is explicitly configured.

## A73.5 Google Colab runbook

1. Upload `FINAL_PRODUCTION_RELEASE.zip` and extract it into `/content/unified-scalper`.
2. Install `requirements.txt`, then run `python -m compileall -q .`, `python -m pytest -q`, and `python -u main.py --validate-only` before starting the monitor.
3. To receive Telegram messages, supply `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` using Colab Secrets or `getpass`; never write credentials into a notebook cell, source file, or ZIP.
4. Keep `UNIFIED_LIVE_PILOT_ENABLE=0` and `UNIFIED_A55_LIVE_ARM=0`. Start `python -u main.py` only for supervised monitor-only operation. Public MEXC market discovery does not require private exchange keys; Telegram delivery requires a valid token and chat ID.
5. The first signal message is sent only when the technical trigger or canonical score milestone is reached. Its TradingView link opens the MEXC Spot chart. Follow-up messages report closed-bar TP1/TP2/TP3/SL reference touches at 5m for intraday ideas and 1h for Swing ideas. These are not live trade fills.
6. Colab is not an always-on host. Use durable external storage and a continuously supervised host for persistent monitoring; do not interpret this package as approval for unattended live trading.


## A73.6 Final verification from clean extracted release (2026-11-16)

The checks below were executed against the exact extracted copy that is being packaged, not against a separate working tree:

| Check | Observed result |
|---|---|
| Original archive inventory | 99 entries; CRC test returned `None`. |
| Final release inventory | 99 unique files; exact match to `FINAL_MANIFEST.json`; no added or removed paths. |
| A73 change accounting | 7 confirmed issues corrected (6 runtime/logic and 1 stale `.env.example` instruction); 10 modified files including the regenerated checksum ledger; 0 files added; 0 files removed. |
| Compile | `python -m compileall -q .` passed; explicit `py_compile` passed for 73/73 Python files. |
| Full unit/regression suite | `python -m pytest -q`: **544 passed, 1 skipped, 0 failed; 545 collected; 58 test modules; pytest time 32.53s; process exit 0**. |
| Skipped test | `test_release_contracts.py:375` requires a historical A51 log that is not part of the clean source release. No substitute log or synthetic pass was created. |
| Runtime validation | `python -u main.py --validate-only`: **PASS, exit 0**, `bot_started=false`, `live_threads=[]`; no MEXC or Telegram credentials were present. Wall time 11.13s; peak RSS 554,056 KiB. |
| Real exchange / messaging | No authenticated MEXC request, order, native stop, or real Telegram delivery was performed. |
| Target deployment | Python 3.12/Linux amd64, Docker, Railway, full dependency installation and profitability remain unverified. The audit runtime was Python 3.13.5. |

The single-process full pytest run above supersedes the earlier historical note that the one-process run exceeded the tool timeout. The historical A51 fixture remains the only skip.

### A73.7 Refactoring boundary and unresolved engineering work

The confirmed A73 fixes were applied in the existing source modules without replacing the original system. A broad decomposition of `main.py` was **not** represented as completed: it remains 104,647 lines with 1,480 top-level definitions and 11 multiply-defined names (12 extra redefinitions). These order-sensitive wrappers and shared runtime globals are part of the current compatibility chain; moving them without staged parity tests would risk changing execution/protection authority. The release therefore includes targeted corrective refactoring and regression coverage, not a full modular rewrite.

No profitability edge is certified. The system remains Spot / LONG_ONLY and `MONITOR_ONLY_NO_NEW_BUYS`; the package decision remains `NO_GO_UNATTENDED_LIVE`.

### A73.8 Final ZIP re-extraction and release verification (2026-11-16)

The following checks were executed against the last release source tree and ZIP contents after clean extraction into `/mnt/data/final_delivery_extract`. The only packaging edits after these code checks were this report/manifest evidence and the regenerated checksum ledger; no Python source or test module changed.

| Check | Final release result |
|---|---|
| ZIP extraction / CRC | PASS; `ZipFile.testzip()` returned `None` and the final archive extracted successfully. |
| Inventory | PASS; 99 unique entries, exactly matching `FINAL_MANIFEST.json`; no duplicate paths, added files or missing files. |
| SHA-256 ledger | PASS; all 98 non-self package entries match `A66_SHA256SUMS.txt`. |
| Python compile | PASS; `compileall` and explicit `py_compile` completed for 73/73 Python files. |
| Unit / integration regression suite | PASS across four non-overlapping batches covering all 58 test modules: 89 + 111 + 171 + 173 = **544 passed, 1 skipped, 0 failed** (545 total). Every batch exited 0; combined pytest-reported time was 54.40 seconds on Python 3.13.5. |
| Skipped test | `test_release_contracts.py:375` requires a historical A51 log not packaged in the clean source release. No substitute log or synthetic pass was created. |
| Validate-only / internal self-test | PASS; `python -u main.py --validate-only` exited 0 (11.09 seconds in the recorded run; peak RSS 553,964 KiB), returned `pass=true`, `bot_started=false`, `live_threads=[]`, and no MEXC / Telegram secrets were present. |
| Live exchange / messaging | NOT TESTED live: no authenticated MEXC session, real orders, native stops, actual Telegram delivery, target-platform Docker/Railway validation or profitability claim. |

A monolithic pytest invocation in the final packaging pass was interrupted by the execution timeout before emitting a summary; to avoid counting an incomplete run, the entire suite was rerun as four non-overlapping batches. The grouped results above cover every packaged test module. An earlier one-process suite also completed 544 passed / 1 skipped / 0 failed against the same Python source. This report does not claim that a full modular decomposition of `main.py` was completed.

---

# A74 — Quality-first alerts, stablecoin hard exclusion, independent Swing discovery and net Shadow outcomes (2026-11-17)

**Audited source:** user-uploaded `FINAL_PRODUCTION_RELEASE(5).zip`; extracted and modified in place as the working release source.  
**Canonical package identity:** A70/A66 compatibility identity deliberately retained.  
**Active Opportunity Hunter feature revision:** `A74-QUALITY-FIRST-STABLECOIN-FILTER-SWING-AND-NET-SHADOW-OUTCOMES-2026-11-17`.  
**Effective order authority:** `MONITOR_ONLY_NO_NEW_BUYS`; no authenticated exchange calls or live orders were used.

## A74.1 Requested behavior and applied changes

1. **Stablecoin hard exclusion.** The shared `_v531_is_stablecoin` predicate now enforces the base-asset denylist regardless of the legacy optional filter switch. The list covers major USD/EUR stable assets and bridged variants including USDC, USDT, USDS, USDE, FDUSD, TUSD, DAI, USDD, USDP, GUSD, PYUSD, FRAX, LUSD, CRVUSD, USD0, USD1, USDG, USDGO, EURC, EURS, EUROC, EURT, EURI, AEUR, RLUSD and others. The Hunter fails closed for malformed/unsupported symbols. Gold-backed assets such as XAUT/PAXG are not classified as stablecoins by this denylist.
2. **Strong-only initial Telegram opportunities.** WATCH remains stored for internal diagnostics but is suppressed from external alerts. Initial CONFIRMED alerts require independent technical, execution and market-regime quality, sufficient liquidity/turnover, acceptable spread, measured pattern-specific relative volume, appropriate absolute/relative momentum, a non-chased entry and cost-adjusted TP1 Net R:R. `TRADEABLE` remains tied to the existing canonical PreSend pass and is not a fill claim.
3. **Separate quality dimensions.** Technical quality, execution quality and 1H/4H regime fit are stored and displayed separately; the composite ranking is not represented as a win probability.
4. **Pattern-specific quality gates.** Pullback requires measured volume confirmation; Mean Reversion requires stronger reversal volume; Relative Strength requires positive absolute momentum as well as outperformance vs BTC; breakout requires a closed-bar trigger, volume and a maximum chase distance of 0.65 ATR. Unknown/engine-specific patterns require measured generic volume evidence rather than receiving an automatic pass.
5. **Independent Swing discovery.** In addition to preserving existing MSE strategy-engine candidates tagged SWING, the Hunter now builds independent closed-1H Swing Breakout, Pullback Reclaim and Relative Strength ideas with closed-4H direction confirmation. Swing monitoring uses closed 1H bars with a seven-day default tracking horizon. Intraday remains on closed 5m bars. This scans the existing bounded `market_data_map`; it does not claim to cover every exchange listing or invent short-side strategies absent from the Spot-long design.
6. **Cost-aware reference targets.** Read-only Hunter setups rebase TP1/TP2/TP3 to risk multiples that account for the estimated round-trip spread, two taker fees and two per-side slippage assumptions. TP1 is capped at 3R; if the cost model would require more, the idea is not eligible for a strong alert. These are research/reference levels, not exchange orders.
7. **Outcome tracking for every observed idea.** Existing SQLite outcome lifecycle is extended with estimated net return, net R, assumed cost and exited fraction. TP1/TP2/TP3, stop, post-target stop and expiry are modeled using the project's configured exit weights. A missing-data expiry is `UNKNOWN`, never silently a loss or a win. When one closed OHLC candle touches both target and stop, stop-first remains the conservative rule.
8. **Restart-safe alert deduplication.** Initial per-symbol alert cooldown state is persisted after Telegram delivery ACK in SQLite; outcome follow-up messages are not throttled by this initial-alert cooldown. A DB read failure fails closed rather than producing duplicate alerts.
9. **Swing relative-strength edge correction.** A final test pass found a stale-local-variable path in the Swing Relative Strength branch that could duplicate an earlier Swing setup when the relative-strength predicate was not met. The append now occurs only after a qualifying Swing RS idea has been constructed; a regression test covers the non-qualification path.

## A74.2 Applied thresholds (initial conservative operating values)

| Gate | Default |
|---|---:|
| Minimum technical score | 82/100 |
| Minimum execution score | 65/100 |
| Minimum 1H/4H regime score | 50/100 |
| Maximum spread | 0.15% |
| Minimum 24h quote turnover | 2,000,000 USDT |
| Pullback relative volume | 1.05x |
| Mean-Reversion relative volume | 1.15x |
| Breakout relative volume | 1.20x intraday / 1.25x Swing |
| Maximum breakout chase | 0.65 ATR |
| Relative-Strength absolute return | +0.15% minimum, plus relative outperformance >=0.30% |
| Minimum cost-adjusted TP1 Net R:R | 0.80 |
| Initial per-symbol alert cooldown | 900 seconds |
| Swing default lifetime / evaluation cadence | 7 days / closed 1H candles |

These are conservative first-pass filters, not statistically optimized values. They must be recalibrated only against out-of-sample historical or forward Paper data. Thresholds were not relaxed to increase alert frequency.

## A74.3 Outcome semantics and limits

`outcome_net_return_pct` and `outcome_net_r` are **hypothetical Shadow estimates**, not realized PnL. The model uses the existing configured TP exit weights (default 50% / 30% / 20%) and fee, spread and slippage assumptions. Because monitor-only ideas have no exchange-confirmed entry or fill, real execution differences, funding, queue position, order-book impact and actual fee tier cannot be known. Telegram wording distinguishes a partial contribution from a completed scenario, and data-gap expiry is explicitly UNKNOWN. Profitability has not been established by this code review.

The independent Swing scanner consumes the same bounded market snapshots as the existing Hunter. It does not issue extra market-data requests, does not make the entire exchange universe available, and does not add Futures/Short authority. Existing MSE Swing engine candidates continue to be observed with their strategy metadata.

## A74.4 Files changed in this release pass

- `main.py` — shared stablecoin hard filter; quality scoring and strong-only gating; separate execution/regime scores; 1H/4H Swing discovery; cost-aware reference targets; fee-aware Shadow outcomes; SQLite-persisted initial-alert cooldown; Swing RS stale-append correction; runtime feature-revision metadata.
- `test_v702_production_audit_fixes.py` — regression coverage for stablecoin exclusions, quality filters, Swing discovery and non-qualification, net outcomes, persistence, and data gaps.
- `test_production_guardrails.py` — alert-rate contract now uses strong eligible test alerts under the new policy.
- `README.md` — A74 behavior, thresholds, limitations and run instructions.
- `CHANGELOG.md` — A74 release notes.
- `FINAL_AUDIT_REPORT.md` — this A74 audit record and final verification.
- `FINAL_MANIFEST.json` — synchronized source digest, current Hunter contract and test/verification record.
- `A66_RELEASE_MANIFEST.json` — synchronized source digest and supplemental feature evidence while preserving historical release lineage.
- `A66_SHA256SUMS.txt` — regenerated SHA-256 ledger for all other package files.

No package file is added or deleted. The release remains within the **99-file ceiling**.

## A74.5 Verification status

The final `FINAL_PRODUCTION_RELEASE.zip` was built from the 99 paths in `FINAL_MANIFEST.json`, extracted into a clean directory, and verified there. Results from that extracted release:

- ZIP inventory: **99/99 unique files**, exact match to the manifest; `ZipFile.testzip()` returned `None` (CRC PASS).
- SHA-256 ledger: **98/98 non-self package files matched** `A66_SHA256SUMS.txt`.
- Python compilation: `compileall` PASS and explicit `py_compile` **73/73** PASS.
- Full regression suite: **557 passed, 1 skipped, 0 failed (558 collected), across all 58 test modules**. To avoid a single-process test-runner hang, all modules were executed in four non-overlapping batches; every command exited 0: batch 1 = 89 passed (15 modules), batch 2 = 111 passed (15 modules), batch 3 = 171 passed / 1 skipped (15 modules), batch 4 = 186 passed (13 modules). The single skip is `test_release_contracts.py:375`, which requires a historical A51 runtime log not bundled in the source release. An earlier all-in-one invocation stopped at the tool timeout without a final report; it is not counted as a successful run.
- Focused Hunter + production-guardrail regression set: **105 passed**. The dedicated A74 Hunter test file: **82 passed**.
- `python -u main.py --validate-only`: **PASS, process exit 0** from the final clean extraction, with an empty environment (`active_env_aliases=[]`), `pass=true`, `bot_started=false`, and `live_threads=[]`. The internal validator exercises mock self-tests only; no authenticated exchange request, real Telegram delivery or real order was sent.
- A74 runtime self-test: all checks true, including mandatory stablecoin denial, independent Swing scanner wiring, hourly follow-up horizon, fee-aware Shadow outcome callable, read-only authority and `MONITOR_ONLY_NO_NEW_BUYS`.

No test run establishes profitability. The modeled Shadow net return/R uses assumed costs and configured exit fractions; it is not account PnL or a broker-confirmed fill. Actual MEXC connectivity, Telegram delivery, order fills, exchange-native stop behavior, target Python 3.12/Docker/Railway deployment and live profitability remain unverified. The production decision remains **NO_GO_UNATTENDED_LIVE**.


# A75 — إعادة تدقيق الحزمة المستلمة ومطابقة سجلات التشغيل (2026-11-17)

## 22.1 حدود العمل والحكم التنفيذي

- ملف الإدخال: `FINAL_PRODUCTION_RELEASE(6).zip`؛ SHA-256: `6f5a911762e68ea5c4379f4a3fce2522858ad870b049e3755015fd3c76d386ec`.
- الحزمة الأصلية: **99 ملفًا فريدًا**، CRC سليم؛ ملفات Python: **73**؛ وحدات الاختبار: **58**.
- لم يُعثر في هذه الجولة على عيب برمجي جديد قابل لإعادة الإنتاج في مسار التداول أو على سبب يبرر تعديل بوابات التنفيذ. لذلك **لم أغيّر منطق التداول أو عتبات الاستراتيجية** ولم أخترع إصلاحًا شكليًا.
- الملفات البرمجية `main.py` والوحدات المساعدة بقيت كما هي؛ لا يعني اجتياز الاختبارات أن الربحية مثبتة أو أن التشغيل الحي آمن.
- قرار التشغيل يبقى `MONITOR_ONLY_NO_NEW_BUYS` و`NO_GO_UNATTENDED_LIVE`.

## 22.2 مطابقة سجلات المستخدم مع السياسة الفعلية

1. **سبب توقف مسار اختيار الفرص في السوق الهابط:** إعداد `FAMILY_POLICY_PULLBACK` يسمح بـ `BULLISH` و`NEUTRAL` فقط. اختبار `test_a9_regime_matrix_matches_canonical_policy_and_does_not_open_bearish_pullback` يثبت أن `PULLBACK@BEARISH` يُرفض بالسبب `macro`. هذا قيد مقصود لحماية صفقات Spot-long وليس خللًا في Queue أو Telegram. لا يجوز تحويله إلى سماح عام أثناء هبوط BTC.
2. **الأرقام تؤكد موضع الرفض:** إحدى نافذات 30 دقيقة الواردة في السجل سجلت `DISC/RANK/PRE/PASS/PRE_REJ = 277/165/165/0/165`، وكان السبب المسيطر `family_regime_disallowed.macro` (226 مرة في سجل الرفض المجمّع). في لقطات أخرى ظهرت قيم مماثلة: `290/134/134/0/134` و`320/236/236/0/236`. ومع `SEL/Q/TG/EXEC = 0` لا يوجد دليل على أن المرشحين وصلوا أصلًا إلى مرحلة الإرسال أو التنفيذ.
3. **رفض السيولة صحيح:** قيم السبريد المسجلة `0.3928%` و`0.4362%` و`5.2280%` تتجاوز سقف الفحص الظاهر في السجل `0.30%`. فتح البوابة لهذه القيم بغرض زيادة الإشارات يعرض ربح TP صغيرًا للاستهلاك بالسبريد والانزلاق والرسوم.
4. **حالة ASTER/USDT ليست صفقة خاسرة:** `Hunter score 92.6` ترتيب داخلي، لا احتمال ربح. التنبيه نفسه قال `MONITOR ONLY` ولم يصدر BUY. Net RR المرجعي عند TP1 كان نحو `0.80195`، أي قريبًا جدًا من أرضية Hunter البالغة `0.80`. ثم أعلن متعقب الشموع المغلقة `SHADOW_STOP_HIT` وصافي نتيجة ظلّية تقديرية `-0.666%` وفق افتراضات التكلفة. ذلك ليس Fill أو PnL محققًا. ويمكن لذيل شمعة 5m أن يلمس الوقف مع إغلاق أعلى منه؛ لا تكفي قيمة الإغلاق وحدها لنفي ملامسة الوقف.
5. **لا توجد مشكلة Queue مثبتة من هذه السجلات:** لأن `PREQUAL_PASS=0` و`SEL/Q/TG/EXEC=0`، فإن غياب الإرسال يتسق مع توقف المرشحين قبل الاختيار. لا يمكن اتهام Telegram أو Queue بالفشل استنادًا إلى هذه اللقطات.

## 22.3 نتائج الفحص والاختبارات المنفذة

| الفحص | النتيجة الفعلية |
|---|---|
| `py_compile` لجميع المصادر | **73/73 PASS**؛ صفر أخطاء ترجمة |
| مجموعة pytest الكاملة | **557 passed, 1 skipped, 0 failed** من 558 اختبارًا في 58 وحدة، عبر تشغيل مجزأ إلى أربع مجموعات |
| أحجام مجموعات الاختبار | 89 passed؛ 111 passed؛ 171 passed و1 skipped؛ 186 passed |
| مجموعة التكامل/المسار/الحارس المركّزة | **141 passed** (مجموعة فرعية من الإجمالي، وليست اختبارات إضافية) |
| `python -u main.py --validate-only` | **PASS، exit=0**؛ `bot_started=false`؛ `live_threads=[]`؛ `active_env_aliases=[]` |
| Imports المحلية | لا توجد إحالات محلية مفقودة حسب فحص AST؛ جميع الاختبارات استوردت المسارات التي تستخدمها |
| فحص أسرار ثابت | لم تظهر مفاتيح أو Tokens فعلية في الملفات وفق أنماط الفحص؛ لا يوجد `.env` داخل الحزمة، و`.env.example` يحتوي أسماء ومتغيرات فارغة فقط |
| SHA-256 ledger في الحزمة الواردة | **98/98 PASS** للملفات غير ملفّ checksum نفسه |
| أدوات التحليل الإضافي | `ruff` و`bandit` و`pyflakes` و`pip-audit` غير مثبتة في بيئة التدقيق؛ لم أزعم تشغيلها |

التخطي الوحيد هو `test_release_contracts.py:375` لاحتياجه سجل A51 تاريخيًا غير مرفق بالحزمة. لا يُحتسب التخطي نجاحًا لذلك الاختبار.

## 22.4 نتائج مراجعة البنية والمخاطر المتبقية

- `main.py` يحتوي **105,327 سطرًا** وحجمه **5,920,383 بايت**. فحص AST وجد 1,493 تعريفًا علويًا من دوال/فئات و1,481 اسمًا فريدًا، أي 11 اسمًا معاد التعريف في طبقات الإصدارات. هذا نمط ترقيعات توافق متراكمة ومصدر مخاطرة صيانة، وليس دليلًا وحده على عطل وقت التشغيل.
- لم يُنفّذ تقسيم شامل لـ `main.py` في هذه الجولة؛ فصل هذه الطبقات أو حذف التعريفات المتكررة دون خريطة اعتماد ديناميكية قد يكسر ترتيب الـ wrappers والتوافق الذي تغطيه الاختبارات. ذلك يحتاج مرحلة Refactor مستقلة تدريجية مع اختبارات parity لكل طبقة، ولا يصح تسميته «تم» هنا.
- بيئة التدقيق هي Python **3.13.5**، بينما Dockerfile يستهدف Python **3.12**. أمر Docker غير متاح في البيئة، لذلك لم أبنِ صورة Docker.
- مكتبتا `ccxt` و`aiosqlite` غير مثبتتين في بيئة التدقيق؛ `python-dotenv` و`aiohttp` الموجودتان لا تطابقان pins المحددة في `requirements.in`. نجح `--validate-only` والاختبارات باستخدام المسارات غير المتصلة والمحاكاة، لكن لم تُختبر جلسة MEXC حقيقية أو مسار Telegram حقيقي.
- `pip check` على بيئة الحاوية العامة أعاد تعارضًا خارجيًا: `moviepy 2.2.1` يتطلب `pillow<12` بينما البيئة تحتوي `pillow 12.3.0`. هذا التعارض لا يأتي من `requirements.in` ولا يثبت تعارضًا بين اعتماديات البوت، لكنه يمنع وصف بيئة التدقيق العامة بأنها نظيفة.
- `requirements-lock.txt` المضمّن هو seed بالنسخ المباشرة وليس قفلًا كاملًا لكل الاعتماديات الانتقالية مع hashes. ملف CI يملك خطوات توليد lock خاص بـ Python 3.12/Linux amd64، لكن تشغيل CI لم يُنفذ في هذه البيئة.
- لا يمكن إثبات ربح يومي أو معدل نجاح أو أفضلية استراتيجية من مراجعة الكود والاختبارات الاصطناعية وحدها. يلزم Forward Paper capture مع أسعار تنفيذ واقعية وتكاليف فعلية وعينة إحصائية قبل تعديل العتبات.

## 22.5 سجل التغييرات والحصر

| البند | العدد/الحالة |
|---|---:|
| الملفات الأصلية | 99 |
| الملفات النهائية داخل ZIP | 99 |
| ملفات Python | 73 |
| ملفات أُضيفت | 0 |
| ملفات حُذفت | 0 |
| أخطاء مصدر جديدة مؤكدة في هذه الجولة | 0 |
| إصلاحات مصدر كود جديدة | 0؛ لم يُجرَ تعديل غير مدعوم بدليل |
| ملفات توثيق/Manifest/Checksum ستُحدّث | 6 |

الملفات الستة التي توثق هذه الجولة: `README.md` و`CHANGELOG.md` و`FINAL_AUDIT_REPORT.md` و`FINAL_MANIFEST.json` و`A66_RELEASE_MANIFEST.json` و`A66_SHA256SUMS.txt`. لا يوجد حذف، ولا تغيير في API أو أسماء إعدادات، ولا تخفيف للمخاطر.

## 22.6 قرار زيادة الفرص والدخل

المشروع Spot-long؛ إضافة Shorts/Futures ليست «استراتيجية إضافية بسيطة» بل تتطلب نموذج مارجن وتصفية وتمويل وحماية أوامر ومخاطر مستقلًا، لذا لم تُضف. كما أن فتح PULLBACK في BEARISH بلا إثبات ارتداد محلي أو تخفيف سقف السبريد لم يُدمج. مسار Hunter القائم يتضمن رصدًا مستقلًا للـ Swing وقواعد قوة نسبية وMean-Reversion/Recovery ضمن حدود الجودة الحالية. تكرار الفرص هدف بحثي؛ لا يُحوّل تلقائيًا إلى أوامر.

الطريقة الصحيحة لزيادة الفرص بأمان هي جمع نتائج Shadow/Paper لكل عائلة واستراتيجية على حدة، مع تكلفة الدخول والخروج وقياس Net R والانزلاق، ثم تعديل عتبة واحدة فقط عند ثبوت تحسن خارج العينة. لا توجد بيانات كافية في السجلات المرسلة لإثبات أن استراتيجية جديدة أو تخفيف فلتر سيزيد صافي الربح.

## 22.7 تعليمات Google Colab

1. ارفع `FINAL_PRODUCTION_RELEASE.zip` إلى Colab ثم فكّه في `/content/unified-scalper`.
2. نفّذ `!pip install -r requirements.txt` داخل بيئة Colab، ثم `!python -m compileall -q .` و`!python -m pytest -q`.
3. نفّذ `!python -u main.py --validate-only` أولًا. لا تبدأ المراقبة قبل نجاح التحقق.
4. اترك `UNIFIED_LIVE_PILOT_ENABLE=0` و`UNIFIED_A55_LIVE_ARM=0`. للمراقبة فقط استخدم `!python -u main.py` بعد تثبيت الاعتماديات؛ لا توفّر مفاتيح MEXC الخاصة لمسح السوق العام. Telegram يحتاج Token وChat ID من Colab Secrets فقط، لا داخل ZIP أو Notebook محفوظ.
5. ثبّت قاعدة SQLite على Google Drive عند الحاجة إلى الاستمرارية. Colab قد ينقطع، لذلك ليس مضيفًا دائمًا ولا يصلح للتداول الآلي غير المراقب.

**الحكم النهائي:** الحزمة قابلة للفك، مترجمة، واجتازت الاختبارات غير المتصلة المحددة أعلاه. لكنها ليست اعتمادًا للتداول الحي أو وعدًا بدخل يومي؛ كما أن refactor المونوليث الكبير، واختبار Python 3.12/Docker، وتكامل MEXC/Telegram الحقيقي، وإثبات الربحية ما زالت خارج ما أمكن إثباته في هذه الجولة.


# A75 — merged audit implementation and release status (2026-11-17)

The A75 integration is applied to the canonical source package in-place. The historical A66 lineage and strategy inventory are retained; the active additive runtime closure is `A75-FINAL-PRODUCTION-AUDIT-CLOSURES-2026-11-17`. The release stays `NO_GO_UNATTENDED_LIVE` / `MONITOR_ONLY_NO_NEW_BUYS`.

## Implemented in this package

1. Final validation now requires the inherited/base checks, A66 checks and A72 read-only source checks to all pass. A non-empty A72 failure list cannot coexist with a PASS decision.
2. The `--validate-only` exit is deferred until the A74/A75 effective runtime wrappers and self-tests are installed.
3. Private account recovery now retries recovered-position and exit-state reconciliation with bounded exponential backoff when a private client was created but startup reconciliation failed. It starts PositionManager only after a successful healthy protection cycle. It does not make missing private credentials appear, nor does it permit new BUYs.
4. The Telegram command poller starts in Monitor-only when enabled. Read-only commands are allowed; commands that mutate account/order state are rejected without the verified private client / authorized runtime.
5. Hunter SQLite work in the asynchronous scan path is moved to worker threads; strategy-candidate observation also uses a worker thread when invoked from an active event loop.
6. Closed-candle parsing uses the actual timestamp of the last retained row, excludes forming bars, rejects stale bars and recent internal gaps, and retains sufficient history for 7-day hourly replay.
7. Hunter RSI edge cases are explicit: 100 for positive gains with zero losses, 0 for positive losses with zero gains, and 50 for a flat series.
8. The policy Regime source is the last closed BTC 4H candle, and confirmation increments only once per unique closed candle. Descriptive macro and candidate policy Regime remain separately identified in diagnostics.
9. `COMPLETED`, `INVALIDATED`, and `EXPIRED` opportunity IDs are terminal. Setup entry/SL/invalidation/targets/cost assumptions are frozen in the initial setup snapshot rather than silently rewritten by repeated scans.
10. Shadow outcomes are clipped at `expires_at`; data gaps are pending/unknown, and a gap at expiry is not labelled as a realized or assumed loss. Active-row scanning uses a rotating keyset cursor.
11. Observation, confirmation, delivery and simulated-entry timestamps are represented separately. Hunter score semantics and floor names distinguish technical, execution, regime-fit and composite ranking. A normalized `volume_quality` is not converted into a measured volume ratio.
12. Explicit zero cost inputs remain zero; negative/non-finite fee, slippage or spread inputs fail closed. Frozen setup costs are used for the later Shadow outcome estimate.
13. `/digest` now reports Hunter and MTF-D1 lane coverage and distinguishes descriptive BTC macro from candidate policy Regime. `/opportunities` lists persisted active observations without execution authority.
14. Hunter notification state is marked delivered only after dispatcher success ACK. Pending and failed states remain separate; this is at-least-once delivery, not an exactly-once guarantee.

## Explicit residual gates (not represented as completed)

- **Telegram durability:** process-kill proof of semantic Outbox state, idempotent replay and durable deferral of every rate-limited terminal event is still required. A failed or rate-limited terminal event must be checked under kill/restart integration before claiming durable delivery.
- **Storage:** Hunter I/O is offloaded from the event loop, but the entire application does not yet use one global SQLite writer actor; WAL backup/restore, disk-full and concurrent-process recovery require dedicated tests.
- **Data contract:** the shared market-data map is still upstream-filtered. A full per-strategy snapshot-quality contract and a proof that no independent 1D/4H lane is starved by the shared map need additional instrumented replay. A74/A75 diagnostic visibility does not manufacture missing candles.
- **Large-file maintenance:** broad extraction of the 105k-line `main.py`, full classification of 3,402 exception handlers and all undefined-name warnings were not safely completed. Existing wrappers were kept rather than removed without parity evidence.
- **Build/runtime:** no Docker executable or Python 3.12 target environment was available here. The installed interpreter is Python 3.13.5. The complete transitive hash lock, target image build, pip check, healthcheck-in-container and deployment-specific memory/soak tests remain required. A previous validate-only memory measurement around 583 MiB remains above a 512 MiB budget; no evidence here proves a past OOM.
- **Exchange proof:** no authenticated MEXC account, real order, partial fill, real native SL/OCO, Telegram API delivery, crash/restart protection or live PnL was tested in this environment. Code presence is not proof of exchange support or live protection.
- **Income/performance:** no profitability or recurring trading income is claimed. Existing strategy gates remain unchanged; additional strategies are not added until the current engines' out-of-sample and net-of-cost performance can be measured.

## Validation report

A75 regression suite: 8 targeted regression tests pass. The existing offline suite baseline before A75 test additions was 557 passed, 1 skipped; the full suite must be rerun on the final tree and its final count recorded in the release manifest. `python main.py --validate-only` passed after A75 installation with `exit_code=0`, `bot_started=false`, `live_threads=[]`, and `active_env_aliases=[]`. Docker/Python 3.12 and MEXC/Telegram live checks were not run.

**Release decision remains NO_GO_UNATTENDED_LIVE.** The package is for monitoring, offline validation and supervised Paper/Shadow research. Do not enable live trading based on this audit alone.
