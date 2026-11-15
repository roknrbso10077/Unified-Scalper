# V702 A64 — المراجعة الإنتاجية النهائية Canonical Production Audit

**الإصدار:** `UNIFIED-SCALPER-V702-A64-CANONICAL-FINAL`  
**التاريخ:** 14 نوفمبر 2026  
**المرجع الذي بدأت منه المراجعة:** `UNIFIED_SCALPER_V702_A63_CANONICAL_FINAL.zip`  
**ملف التشغيل الوحيد:** `main.py`  
**قرار التشغيل:** `NO_GO_UNATTENDED_LIVE`  
**سياسة الدخول الفعلية:** `MONITOR_ONLY_NO_NEW_BUYS`

---

## 1. الخلاصة التنفيذية

تمت إعادة فتح حزمة A63 نفسها وفحص الكود المرجعي، طبقات الحماية والتنفيذ، Telegram/Digest، وحدات Shadow وPaper وEdge، اختبارات الانحدار، ملفات الإعداد والتبعيات، Dockerfile، Healthcheck، وGitHub Actions. لم أتعامل مع نصوص الـDigest باعتبارها دليلًا على أن المراحل اللاحقة عملت؛ تمت مطابقة أرقامها مع مسار الـPipeline.

**النتيجة:** A63 كانت تحمي Snapshot/Swap الخاص بالـDigest من سباق فقد الأحداث أثناء `await`، لكنها أسقطت callbacks الخاصة بعناصر Discovery عند فصل الجيل. لذلك كان من الممكن قبول أجزاء الـDigest في Queue دون أن تصل callbacks المسؤولة عن تسجيل Knowledge إلى نتيجة ACK الحقيقية. كما لم يكن `periodic_summary` جزءًا من لقطة الاستعادة، ودمج الأحداث ذات الرمز نفسه كان قادرًا على استبدال callback قديم بآخر جديد. أُغلقت هذه العيوب في A64 مع اختبارات سلوكية، وأُضيفت نتيجة A64 صراحةً إلى تقرير `--validate-only`.

لم أُخفف أي سياسة Macro/Family أو Score أو HTF أو Liquidity/Spread أو PreSend أو Risk أو Execution/Protection بغرض إجبار النظام على إرسال إشارات. كذلك لم أفتح Live أو أغيّر سلوك الشراء. **A64 هو الإصدار المرجعي النهائي للحزمة في نطاق الكود الذي أمكن تدقيقه Offline، وليس شهادة GO للتداول الحي غير المراقب.**

## 2. مطابقة اللوج مع الكود: ماذا حدث بالفعل؟

### 2.1 عنق الزجاجة قبل الاختيار

في نوافذ `PIPELINE[WINDOW_30M]` المتتابعة، تتكرر الصورة التالية مع اختلاف أعداد الاكتشاف حسب النافذة:

- `DISC` و`RANK` و`PRE` تسجل مرشحين؛
- `PASS=0` و`PRE_REJ` يساوي تقريبًا كل حالات `PRE`؛
- `SEL=0`؛
- `BUILDER / SCORE / PRESEND / QUEUE / TG / EXEC / ORDER / PROTECTED` جميعها صفر داخل النافذة.

إذن توقف التدفق في اللوج المعروض **قبل Selection**، وليس عند Telegram أو إرسال الأوامر. الصياغة الصحيحة للمشكلة هي أن مرشحي السوق لم يجتازوا Prequal/Arbiter، مع منع الشراء الجديد أصلًا بسياسة المراقبة. لا يوجد في هذه اللوجات دليل على أن Telegram فشل في إرسال تنبيه تداول أو أن Executor رفض أمرًا؛ لم يصل أي مرشح إلى هذه المراحل داخل نوافذ القياس المعروضة.

### 2.2 أسباب الرفض الأساسية متوافقة مع السياسة

الأسباب الأعلى ظهورًا هي:

1. `family_regime_disallowed.macro`.
2. `htf.family_htf_strength` / `htf.family_htf_strength_below_floor`.
3. حالات أقل مثل `sweep_bearish_confirmation_missing` و`liquidity.spread` أو `tier_spread_ceiling`.

يعرض اللوج `PULLBACK@BEARISH[allow=BULLISH+NEUTRAL]`. هذا ليس تناقضًا بذاته: Registry الخاص بهذه العائلة لا يسمح بـBearish، ولذلك يجب أن يرفضها في ذلك السياق. توسيع السياسة لقبول Bearish لمجرد رفع عدد `PASS` سيكون تجاوزًا للسياسة وليس إصلاحًا. كما أن ضعف HTF أو اتساع Spread يظلان أسباب رفض صحيحة عند عدم بلوغ Floor/Ceiling المعتمد.

### 2.3 تفسير مؤشرات التشغيل

- `state=FULL_LIVE_RUNNING` يثبت أن عملية المراقبة تعمل؛ لا يثبت وجود صفقة أو أمر حي.
- `trades=0` و`live_ready=0` متسقان مع اللوج.
- `exec_try=9` موسوم صراحةً بـ`scope=ROUTE_ATTEMPTS`؛ لا يجوز تفسيره على أنه تسع محاولات إنشاء أوامر.
- `exec_try_cycle=0` و`ORDER=0` لا يظهران محاولة أمر في الدورة المعروضة.
- `entry_policy=MONITOR_ONLY_NO_NEW_BUYS` و`bypass=0` يثبتان أن شراءً جديدًا غير مسموح في هذا الإعداد.
- أسطر `SELECTED → SCORER/BUILDER BLOCK` هي سجلات Block منفصلة عن عدادات الـWindow/Cycle؛ لا تُستخدم وحدها لإثبات أن هناك Selection في نفس نافذة الثلاثين دقيقة. مرجع المرحلة الكمي هو `PIPELINE[WINDOW_30M]` مع Scope كل Counter.

### 2.4 Shadow وPaper وEdge

- Counters الظاهرة في Counterfactual Shadow متوازنة حسابيًا في العينات المعروضة؛ مثل `attempted = stored + not_stored`. و`errors=0` و`backpressure_drops=0` في معظم اللقطات. `not_stored` لا يعني تلقائيًا فقدًا أو خطأ I/O؛ قد يشمل عدم الأهلية أو Dedupe أو عدم استيفاء شروط التسجيل.
- قيم `io_pending_all` غير الصفرية في لقطة واحدة لا تصاحبها في النص المرسل أخطاء تخزين أو Backpressure؛ لا تكفي وحدها لإثبات اختناق.
- Paper الاستكشافي المعروض: `n=5`، وجميع النتائج `SL` (`0/0/0/5`)، و`First-touch expectancy=-1.00R` و`Modeled realized=-1.59R`. العينة صغيرة جدًا وغير مؤهلة لتغيير استراتيجية أو سياسة.
- `Edge-eligible finalized rows=0` لأن شروط Builder completion وShadow PreSend eligibility وSchema/version الحالي غير متحققة في تلك السجلات. لا يجوز استخدام الخمس Paper rows الاستكشافية لتدريب Edge أو تخفيف بوابات الدخول.
- في بعض اللقطات، تظهر `cycle_dropped` أو `epoch_dropped_cumulative` رغم أن `window_dropped=0` و`window_covered=yes`. هذه Counters بنطاقات مختلفة، ولا تُجمع أو تُقارن كأنها Counter واحدة.

## 3. مراجعة التدفق من البداية إلى النهاية

| المرحلة | نتيجة المراجعة | ما يثبته اللوج الحالي |
|---|---|---|
| Startup / Config | مسار التحقق أحادي التنفيذ؛ أخطاء السياسة/البيانات الحرجة Fail-Closed. وضع `--validate-only` لا يبدأ البوت. | Heartbeat يثبت وجود Runtime عامل، وليس صحة اتصال MEXC أو تداول حي. |
| Scan / Discovery | يولد الكون المرشحين ويصنفهم؛ سجلات Discovery/Counterfactual لا تملك سلطة أمر. | أعداد DISC موجودة؛ لا دليل على أن Discovery نفسها اختنقت. |
| Candidate / Rank | يمر المرشح عبر ترتيب مرجعي ثم Arbiter/Prequal. لا يجوز الخلط بين ترتيب داخلي 0..1 وScore نهائي 0..100. | RANK وPRE موجودان. |
| Prequal / Family / HTF | السياسات الحالية تمنع Family/Regime غير المسموح، وتطبق HTF Floor وLiquidity/Spread. | هذه هي نقطة توقف المرشحين في اللوج؛ `PASS=0`. |
| Score / Select | Score النهائي والاختيار لا يعملان على مرشح رُفض قبل ذلك. حد Live Score الأدنى 70 محفوظ. | `SEL=0` في نافذة الـ30 دقيقة؛ لا يوجد Selection قابل للتنفيذ من هذه العينة. |
| Builder / PreSend | Builder وPreSend لا ينبغي تخطيهما أو إعادة تسميتهما كنجاح بسبب وجود Candidate فقط. | عدادات Builder وPreSend صفر داخل النافذة لأن Selection صفر. |
| Queue / Telegram | كل رسالة لها دلالتها: قبول Queue ليس ACK من Telegram. أجزاء Digest تقسم لأكثر من رسالة عند الحاجة. | Queue/TG صفر داخل النافذة لا يثبت عطل Telegram؛ لم تصل إشارات إلى تلك المرحلة. |
| Execution / Protection | إنشاء الأمر، مطابقة الهوية، المصالحة بعد UNKNOWN، والتحقق من SL/PositionManager تبقى سلطات منفصلة ومقفلة. | Orders/States/Protected صفر؛ لا يوجد دليل تشغيل حي أو حماية حية في هذه اللوجات. |

## 4. الإصلاحات المطبقة في A64

| العيب | الأثر المحتمل في A63 | إصلاح A64 |
|---|---|---|
| Discovery callbacks لا تُربط بأجزاء Digest بعد Snapshot/Swap | يمكن أن تُقبل الرسالة في Queue ولا يصل نجاح التسليم إلى Knowledge callbacks. | ربط `on_success` و`on_failure` بكل جزء مرسل، وتجميع النتيجة؛ لا يتم نجاح التسجيل إلا بعد ACK لجميع الأجزاء. |
| الخلط المحتمل بين Queue admission وTelegram delivery | اعتبار `enqueue=True` دليل تسليم، وهو غير صحيح. | تبقى الحالة `QUEUED_NOT_DELIVERED_ACK` حتى تأكيد التسليم؛ قبول Queue لا يشغّل Success callback. |
| Failure في جزء من Digest | احتمال فقد حالة Discovery أو إشعار Knowledge بصورة غير متسقة. | أول Failure نهائي يغلق مجموعة الإقرار مرة واحدة؛ أي ACK متأخر بعد ذلك يُهمل ولا يعكس النتيجة. |
| فشل Queue admission قبل قبول الرسالة | قد تُسجل Failure كأن Telegram رفض رسالة لم تدخل Queue أصلًا. | إخفاء callback الفوري قبل تأكيد القبول؛ إعادة Snapshot للمخزن حتى يمكن إعادة المحاولة. |
| `periodic_summary` غير محفوظ في Snapshot | اختفاء الملخص الدوري عند فشل Queue بعد فصل الجيل. | تضمين الملخص في Snapshot ودمجه مع الملخص الجديد عند الاستعادة. |
| نفس الرمز يظهر في الجيل القديم والجديد أثناء `await` | تحديث صف الرمز الجديد قد يستبدل callbacks القديمة. | دمج callback pairs القديمة والجديدة مع Dedupe بهوية callback، والاحتفاظ ببيانات الجيلين. |
| نتيجة فحص A64 لا تظهر في JSON النهائي | يصعب مراجعة الإصدار آليًا رغم أن Validator يمر على Wrapper A64. | أُضيف `v702_a64_validation` وRevision وعقد Digest إلى مخرجات `--validate-only`، وأصبح نجاح A64 شرطًا مباشرًا في نتيجة التحقق. |

### حدود إصلاح Telegram

هذا الإغلاق يعالج ملكية الـCallbacks وإقرار التسليم في مسار Digest الموجود. لكنه **لا ينشئ Durable Outbox**؛ Queue الحالية محدودة وذاكرية، ولا يمكن من هذه البيئة إثبات استعادة الرسائل بعد Restart أو ضمان تسليم Exactly-Once. كما أن ACK الحقيقي من Telegram لم يُختبر هنا باتصال خارجي؛ اختباراتنا تحققت من سلوك callbacks باستخدام Dispatcher mock. لذلك يظل أي اعتماد على الاستعادة بعد انقطاع العملية أو تسليم Telegram الحقيقي محظورًا حتى اختبار التكامل وOutbox دائم موثق.

## 5. ما لم يتغير عمدًا

- لم تُحذف استراتيجية أو عائلة من الـRegistry.
- لم تتغير شروط Macro/Family أو HTF أو السيولة أو Spread أو Structure أو Score أو Fee/RR أو PreSend.
- لم يتغير Score Floor الأدنى 70.
- Spot فقط وLONG-only؛ Futures وShort غير مفعّلين.
- لم تتغير حدود المخاطر أو KillSwitch أو مفاتيح Live أو سلطة Execution/Order reconciliation.
- لم يتم تحويل Paper أو Counterfactual Shadow إلى Live authority، ولم يُمنح Edge اعتمادًا على بيانات غير مؤهلة.
- لم يتم اعتبار Telegram تنبيهًا بمثابة Fill، أو Queue acceptance بمثابة Telegram ACK، أو إنشاء Stop بمثابة حماية مؤكدة.

## 6. نتائج التحقق في بيئة المراجعة

البيئة المتاحة هي Python 3.13.5. الهدف المعلن في الحزمة Python 3.12 و`linux/amd64`؛ لم يتم تشغيل Docker أو GitHub Actions أو الاتصال بحساب MEXC أو Telegram من هذه البيئة.

| الفحص | النتيجة | النطاق |
|---|---|---|
| `python -m compileall -q .` | PASS | Compile لجميع Python sources في الحزمة. |
| `python main.py --validate-only` | PASS | `pass=true`، هوية A64، `bot_started=false`، `live_threads=[]`. |
| A64 self-test | PASS — 8/8 | الهوية، Snapshot/Swap، callback ownership، ACK-only، restore، وعدم تخفيف السياسة. |
| اختبارات A64/A63/A62/A61 وA58/A55 المرتبطة | PASS — 44/44 | مجموعة رجوع مركزة على إصلاح ACK وSnapshot/Swap وعقود الإصدارات السابقة. |
| عقود الإصدار وWorkflow والهوية | PASS — 75 passed, 1 skipped | التخطي الوحيد سجل A51 تاريخي غير موجود في حزمة المصدر النظيفة. |
| مجموعة الانحدار الكاملة | PASS بالدفعات — 478 passed, 1 skipped | جُمعت 479 حالة فريدة من 57 ملف اختبار؛ غطتها التشغيلات المنفصلة كلها، دون فشل في التشغيلات النهائية. |
| Python 3.12 / Linux amd64 | NOT RUN | يحتاج CI المستهدف. |
| Docker strict hash-lock / Healthcheck container | NOT RUN | Docker غير متاح محليًا؛ Workflow ليس دليل نجاح حتى يُشغّل على GitHub. |
| MEXC Spot orders / UNKNOWN / partial fills / restart recovery | NOT RUN | لا توجد جلسة Exchange حية أو بيانات اعتماد. |
| Telegram delivery ACK الحقيقي | NOT RUN | الاختبارات المحلية تحاكي Dispatcher callbacks؛ لا تثبت Telegram network delivery. |
| Native/Software SL protection live | NOT RUN | لا يوجد مركز حي أو Exchange integration. |
| ربحية الاستراتيجيات | NOT PROVEN | 5 Paper outcomes استكشافية وكلها SL؛ لا تكفي لاستنتاج إحصائي. |

## 7. القيود التشغيلية التي تمنع GO حيًا

1. **لا يوجد إثبات تكامل حي:** يلزم اختبار MEXC Spot في بيئة مصرح بها لسيناريوهات Timeout بعد قبول الأمر، Partial Fill، Cancel UNKNOWN، Restart، Reconciliation، وSoftware-SL fallback، مع إثبات PositionManager حي.
2. **Telegram outbox:** لا يزال التخزين Durable لرسائل Telegram وحالات CREATED/QUEUED/ACK/RETRY/FAILED غير مكتمل؛ A64 لا يدعي ضمان عدم فقد رسالة بعد Restart.
3. **CI والمنصة:** Workflow A64 يستهدف Python 3.12/Linux amd64 ويولد Transitive Hash Locks أثناء CI، لكن لم يُشغّل هنا ولم تُحفظ Hash Locks نهائية معتمدة داخل الحزمة. `requirements-lock.txt` يظل Direct-pin seed وليس ملف `pip --require-hashes` مكتملًا.
4. **Paper/Edge:** لا تزال Parity بين Batch/Single-bar/Restart، التغطية التاريخية الكبيرة، Runner matching، ومهاجرات قاعدة البيانات التاريخية بحاجة لإثبات/تنفيذ أوسع. لا توجد عينة Edge مؤهلة في اللوج المرفق.
5. **قاعدة البيانات:** لا يوجد هنا قياس أداء على قاعدة تشغيل كبيرة/قرص بطيء أو خطة Archive/Rollup/Backup/Restore تم إثباتها عمليًا.
6. **الصيانة:** `main.py` ما زال Monolith كبيرًا؛ لا يجوز تقسيمه بحذف وظائف. أي Modularization لاحق يحتاج Golden/Parity tests تغطي كل المسارات قبل نقل السلطة.

ملاحظة منهجية للاختبارات: تشغيل `python -X dev -m pytest -q` كعملية واحدة تجاوز مهلة التنفيذ المتاحة (240 ثانية) قبل اكتماله؛ لذلك لا أقدمه على أنه تشغيل موحد ناجح. عُزل فشل مبكر في اختبار A26 كان يتوقع اسم Wrapper A63 حرفيًا بعد ترقية السلسلة إلى A64؛ عُدّل الاختبار ليفحص الاستدعاء الإضافي الصحيح A64→A63 ثم أُعيد بنجاح ضمن دفعة 16/16. بعد ذلك جرى جمع كل 479 حالة فريدة عبر دفعات مستقلة من 57 ملفًا: 478 نجاحًا، تخطٍ واحد، وصفر إخفاقات في آخر تشغيل لكل دفعة.

هذه البنود ليست تبريرًا لتخفيف السياسات؛ هي حدود إثبات/تشغيل حقيقية. ولا يمكن إغلاق اتصال MEXC أو Telegram أو Docker/CI أو الربحية من دون الوصول للبيئة والخدمات الفعلية.

## 8. القرار النهائي

**A64 هو الـCanonical Final Version لهذه الحزمة.** الإصلاحات التي أمكن تنفيذها والتحقق منها Offline أُدمجت الآن، مع الاحتفاظ بكل استراتيجيات التداول ووظائف المراقبة والحماية والـPaper/Shadow.

**لكن القرار التشغيلي يظل:**

- `production_decision = NO_GO_UNATTENDED_LIVE`
- `effective_entry_policy = MONITOR_ONLY_NO_NEW_BUYS`
- `hard_gate_bypass = false`
- `live_gates_relaxed = false`

نجاح Compile أو Validate أو Pytest لا يُعد إثبات ربحية ولا موافقة على تشغيل Live غير مراقب. لا تفعّل مفاتيح Live في هذه النسخة بناءً على هذا التقرير.
