# تقرير التدقيق النهائي Production Audit — UNIFIED SCALPER V702 A58.1

**هوية التوزيعة:** `UNIFIED-SCALPER-V702-A58-CANONICAL-FINAL`  
**مراجعة الإصدار:** `V702-A58.1-PRODUCTION-AUDIT-CANONICAL-FINAL-2026-11-13`  
**القرار التشغيلي:** `NO_GO_UNATTENDED_LIVE`  
**النطاق المسموح حاليًا:** Offline Validation / Monitor / Supervised Paper فقط.

## 1. الخلاصة التنفيذية

تم فحص الأرشيف المرفق وملفات التشغيل والبناء والاعتماديات ووحدات Shadow والحماية، وإضافة إصلاحات لبناء الصورة وتوحيد سياسة الحظر وقفل SQLite ونقل أعمال Shadow المتزامنة خارج حلقة asyncio. بقيت قواعد الاستراتيجية ودرجة الدخول الحية الدنيا 70 وحدود المخاطر دون تخفيف مقصود.

**سبب فشل صورة Railway الأصلي مؤكد من ملفات الحزمة:** ملف `requirements-lock.txt` كان يحتوي قيودًا مباشرة مثبتة فقط، بلا `--hash=sha256:`، بينما Dockerfile كان يفرض وجود hash ثم يستخدم `pip --require-hashes`. لذلك كان البناء يتوقف عند مرحلة بناء الصورة قبل تشغيل البوت.

الحزمة المرفقة الآن تتضمن Workflow تحت `.github/workflows/`، خلافًا للاعتقاد الأولي بأنه غير موجود في ZIP. لكن الفحص الحالي للملفات المنشورة على فرع GitHub `main` ما زال يُظهر Dockerfile القديم الذي يفرض hash lock، وملف lock القديم غير المحتوي على بصمات. هذا يعني أن إصلاحات الأرشيف لم تُرفع بعد إلى الفرع الذي يسحبه Railway. لا أملك صلاحية/اتصالًا لنشر commits إلى مستودعك من هذه الجلسة.

## 2. الإصلاحات المدمجة في المصدر

| المجال | ما تم تغييره | الأثر المقصود |
|---|---|---|
| اعتماديات Python | إنشاء `requirements.in` كمصدر واحد للحزم الست ذات الإصدارات المحددة، وتغيير `requirements.txt` ليشير إليه | إنهاء الدورة المرجعية القديمة بين ملفات المتطلبات |
| Docker | إضافة `STRICT_HASH_LOCK=0` افتراضيًا لمسار Railway، مع مسار `STRICT_HASH_LOCK=1` صارم يتطلب hashes فعلية؛ تثبيت إصدار pip في الصورة | منع فشل البناء الحتمي بسبب ملف lock غير مكتمل، مع إبقاء بوابة CI الصارمة |
| GitHub Actions | Workflow يحل الاعتماديات الانتقالية لهدف Python 3.12 / Linux amd64 باستخدام `uv pip compile --generate-hashes`، ثم يثبت بـ `--require-hashes` ويبني Docker بالوضع الصارم وينشر lock كـ Artifact | إثبات إمكانية البناء الصارم على هدف النشر عند تشغيل Workflow |
| سياسة الأصول | نقل قائمة الأصول المحظورة إلى `v702_core__policy__forbidden_assets.py` واستيرادها في main وShadow والحماية | إزالة مصادر السياسة التشغيلية المتنافسة؛ CAKE لا تزال محظورة |
| SQLite | إنشاء `SQLITE_WRITER_LOCK` موحد واستخدامه عبر KnowledgeOutcomeLedger وPortfolioDrawdownGuard وExpansionShadow وShadow modules | تسلسل الوصول المحلي إلى قاعدة البيانات المشتركة وتقليل تصادمات الكتابة |
| asyncio / Shadow | نقل عمليات Intraday Shadow وCounterfactual Shadow والقراءات/التقارير والكتابات البطيئة إلى `asyncio.to_thread`؛ تحديد الأعمال المعلقة الافتراضي 16 وبحد أقصى 64 | منع عمليات SQLite المتزامنة من حجب scanner event loop؛ عند الضغط تُسقط عينة Shadow الرصدية ولا توقف قرار التداول |
| Score floor | إبقاء دالة `effective_live_floor` بحد نهائي 70 أو أكثر | لا يسمح بمسارات الإنقاذ أو relief بخفض بوابة الدخول الحية |
| CAKE التاريخية | توضيح أن اختبارات/تعليقات fee-rescue القديمة سياق تاريخي لا يمنح سماحًا للأصل | CAKE تبقى ضمن hard denylist |
| تشغيل Railway | توثيق `RAILWAY_RUN_UID=0` للـ Volume، وسياسة Restart `Always`، وعدم تعيين HTTP Healthcheck Path لبوت لا يقدم HTTP | معالجة ملكية Volume والتمييز بين فحص بدء النشر والمراقبة المستمرة |
| سجل المصدر | نقل سرد الـ patches القديم من رأس `main.py` إلى `CHANGELOG.md` ووضع shebang في أول الملف | تحسين قابلية قراءة الملف وتنفيذ shebang الصحيح |
| اختبار الإغلاق | إضافة فحوص Lifecycle للـ pytest؛ بعد انتهاء الاختبارات يُثبت test object graph فقط، مع التأكد من عدم بقاء خيوط عمل | حل تعليق إغلاق مشغّل الاختبارات دون تغيير GC الخاص بتشغيل البوت |

## 3. مراجعة تدفق Startup → Scan → Candidate → Prequal → Score → Select → Queue → Telegram → Execution

هذا مخطط ساكن مستند إلى نقاط الدخول والواجهات الموجودة في المصدر. لا يمثل إعادة تشغيل إنتاجية كاملة؛ لم تُرفق سجلات Build/Deploy نصية تسمح بمطابقة كل حدث فعلي مع السطر المقابل.

| المرحلة | موضع/واجهة المصدر | ما أمكن إثباته ساكنًا |
|---|---|---|
| Startup | `main()` ثم `run_bot()` | تهيئة قاعدة البيانات، فحص execution intents غير المحسومة، استعادة المراكز، إنشاء Exchange، reconciliations للحماية والخروج، ثم كتابة نبضات PM/runtime قبل أول مسح |
| Preflight | `BootOrchestrator.run_preflight()` | بوابة بدء fail-closed قبل دخول حلقة المسح |
| Scan | حلقة المسح داخل `run_bot()` | جلب universe/بيانات السوق، استخدام BTC context مشترك، حدود زمنية/تغطية، ومنع إدخال أصول القائمة المحظورة في المسح/الـ prefetch |
| Candidate | `SignalBuilder` | بناء المرشحين من بيانات الشموع والسوق؛ تبقى SignalBuilder جزءًا من main.py |
| Prequal | `_v453_prequalify()` مع wrappers تاريخية | يوجد أكثر من تعريف/طبقة monkey-patch؛ الاختبارات الحالية تغطي عقود parity المحددة، لكن لا توجد trace سجلات إنتاج تثبت كل فرع runtime |
| Score | `CompositeRankingEngine` وطبقات scoring داخل `main.py` | فصل score/quality عن أهلية الدخول النهائية؛ الحد الأدنى الحي النهائي لا يقل عن 70 |
| Select | `GlobalOpportunityBrain.rank_and_select()` | ترتيب المرشحين واختيار finalists بعد التصفية/الإسناد |
| Telegram queue | `TelegramDispatcher.enqueue()` و`run_forever()` | Queue نقل رسائل فقط؛ Telegram إشعار غير مخوّل للتداول ولا يمنح سلطة تنفيذ |
| Execution | `OrderExecutor.submit_entry()` وwrapper `_v587_submit_entry()` | سياق intent إلزامي في مسارات التنفيذ، مع حفظ execution intent قبل الإرسال وتحديث حالته بعد الرد/التعبئة؛ استعادة intents غير المحسومة تحجب الدخول الجديد عند الإقلاع |
| Protection | `PositionManager` | استعادة الحماية قبل المسح، ونبضة PM مستقلة مرتبطة بعملية التشغيل والمراكز المفتوحة |

**ملاحظة بنيوية مهمة:** `main.py` ما زال ملفًا كبيرًا (نحو 99 ألف سطر) ويحتوي طبقات wrappers تاريخية. تم فصل سياسات مشتركة ومكوّنات مساعدة محددة، لكن لم أنقل مراحل Scan/Prequal/Score/Select/Queue/Telegram/Execution السبع إلى ملفات مستقلة بالكامل؛ القيام بذلك آليًا في هذه المراجعة مع هذا العدد من overrides قد يغيّر ترتيب تطبيق الـ patches أو قرارات التداول. لذلك لم أُجرِ إعادة هيكلة واسعة غير مثبتة بتطابق runtime. هذا الجزء من طلب التفكيك المعماري الكامل **لم يُنجز**، ولا أصف التدفق بأنه اختُبر تشغيلًا طرفًا لطرف.

## 4. إعداد البناء والاعتماديات بعد الإصلاح

### مسار Railway الافتراضي

- Docker يترك `STRICT_HASH_LOCK=0` افتراضيًا.
- يثبت الحزم المباشرة المثبتة الإصدارات من `requirements.in`.
- لا يدّعي هذا المسار أن الاعتماديات الانتقالية مغلقة بـ SHA-256، ولا يضمن إعادة بناء byte-for-byte متطابقة.

### مسار GitHub Actions الصارم

- يستهدف Python 3.12 و`x86_64-unknown-linux-gnu`.
- يحل الشجرة الانتقالية ويولّد `requirements-lock.txt` حقيقيًا مع hashes.
- يتحقق من وجود بصمات SHA-256، ويثبت باستخدام `pip --require-hashes`، ثم يبني صورة Docker مع `STRICT_HASH_LOCK=1`.
- يرفع ملف lock المحلول كـ Artifact لمدة 30 يومًا.
- لا يكتب ملف lock الناتج تلقائيًا إلى الفرع. النسخة الموجودة في ZIP تظل ملف قيود مباشرة seed حتى ينجح CI؛ لا توجد بصمات مصطنعة مضافة يدويًا.

**حالة المستودع البعيد وقت هذا الفحص:** الملفات الخام المنشورة على GitHub ما زالت تحتوي Dockerfile القديم الذي يشترط hashes في ملف lock، و`requirements-lock.txt` غير المحتوي على hashes. لذلك تنزيل الكود من الفرع الحالي لا يعطي إصلاحات هذه الحزمة بعد. يجب رفع التوزيعة بما فيها المجلد المخفي `.github/workflows/` باستخدام Git، لا الاعتماد على رفع الملفات المرئية فقط.

## 5. إعداد Railway التشغيلي

- Volume دائم مركّب في `/data`، مع مسار قاعدة البيانات `SCALPER_DB=/data/unified_scalper.db`.
- متغير `RAILWAY_RUN_UID=0` بحسب متطلبات ملكية Volume الموثقة في Railway.
- Restart Policy = `Always`.
- لا تضبط `Healthcheck Path` على endpoint HTTP؛ التطبيق لا يشغّل خادم HTTP.
- حد النبضة العامة 2100 ثانية هو نبضة تشخيصية بطيئة، وليس watchdog. نبضة runtime السريعة 60 ثانية، وPositionManager 30 ثانية عند وجود مراكز هي الأدلة التشغيلية الأهم.
- Railway Healthcheck يخص نجاح مرحلة النشر ولا يُستخدم كـ watchdog مستمر بعد استقرار النشر؛ استخدم تنبيهًا خارجيًا/Telegram لمراقبة النبضات واستمرارية العملية.

## 6. نتائج الاختبارات والحدود

النتائج الرقمية النهائية مثبتة في `A58_RELEASE_MANIFEST.json`. الاختبارات التي أُجريت محليًا على Python 3.13.5:

- `python -m compileall -q .` — **PASS**، ونجح تجميع ملفات Python الـ68.
- `python -m pytest -q` على جميع اختبارات الحزمة — **435 passed, 1 skipped, 0 failed** خلال 31.17 ثانية، ورمز خروج 0. الاختبار المتجاوز الوحيد يحتاج سجل A51 تاريخيًا غير موجود في الأرشيف.
- `python -u main.py --validate-only` — **PASS**، رمز الخروج 0؛ سجل النهاية يثبت `bot_started=false` و`live_threads=[]`. تهيئة الاختبارات استخدمت محاكاة داخلية فقط ولم ترسل طلبًا حقيقيًا إلى MEXC أو Telegram.
- اختبارات A58/V705 تغطي مركزية denylist، هوية قفل SQLite، توافق قواعد بيانات Shadow، حدود offload من event loop، عقد Docker/Workflow، وترتيب/ثبات حد الدرجة النهائي 70. بعد اكتمال pytest لم يبقَ سوى `MainThread`، وخرج مشغّل الاختبارات برمز 0.

البيئة المحلية المستخدمة Python 3.13.5. لم يتوفر Docker CLI في بيئة التدقيق، ولذلك لم يُبنَ Docker محليًا ولم يُختبر هدف Python 3.12/linux/amd64 عمليًا هنا. ملف Workflow مهيأ لتشغيل هذا الاختبار عند رفع الحزمة إلى GitHub، لكن نجاحه لم يُثبت بعد. لم يتم نشر التطبيق إلى Railway من هذه الجلسة.

لم يتم إجراء طلب تداول MEXC حقيقي، أو إرسال Telegram فعلي، أو اختبار partial fills / cancel / restart reconciliation على حساب حقيقي، أو التحقق من native stop على المنصة. نجاح validate-only والاختبارات لا يثبت هذه السلوكيات الحية. لم تثبت ربحية أي استراتيجية. كما لم تُرفق Build Logs أو Deploy Logs نصية؛ الصورة المرفقة تثبت فشل مرحلة Build image فقط، ولا يمكن مقارنتها بحدث تنفيذ محدد بعد إصلاح الكود.

## 7. الحكم النهائي

**القرار يظل `NO_GO_UNATTENDED_LIVE`.** اجتياز الاختبارات المحلية لا يثبت سلامة التداول الحي أو حماية المراكز أو الربحية. لا تُفعّل مفاتيح التداول الحي ولا تترك البوت يتداول دون إشراف حتى ينجح Workflow الفعلي على Python 3.12/linux/amd64، ثم ينجح نشر Railway، وتُراجع سجلات التشغيل الحقيقية لأول 10 دقائق، وتُختبر المصالحة والحماية والإرسال على بيئة تداول مراقبة.

## 8. ملفات الإصدار

- `main.py`: الملف التنفيذي الوحيد.
- `requirements.in`: مصدر الاعتماديات المباشرة.
- `requirements-lock.txt`: seed مباشر غير hash-locked، وسيُستبدل بمخرج resolver داخل CI عند تشغيله.
- `.github/workflows/a58-production-audit.yml`: بوابة التدقيق والبناء المستهدف.
- `A58_RELEASE_MANIFEST.json`: بيانات الإصدار والتحقق.
- `A58_SHA256SUMS.txt`: بصمات جميع ملفات التوزيعة عدا ملف البصمات نفسه.
- `CHANGELOG.md`: سجل التغييرات وتاريخ `main.py` المنقول.
