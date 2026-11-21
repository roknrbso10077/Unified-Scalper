# A87 — مراجعة إضافة القرار التنفيذي والتنبيه الآلي (2026-11-20)

> هذا الملحق هو الإضافة الأحدث فوق محرك A86. أرقام الاختبار في هذا الملحق تخص الاختبارات التي أُعيد تشغيلها فعليًا لهذا التعديل، ولا تعني إثبات ربحية أو اختبار تكامل حي مع Telegram/MEXC.

## ما أُضيف

- قرار سوق BTC صريح ومفسر للـSpot Long اعتمادًا على بيانات شموع مغلقة 1H و4H ودرجات السيناريو؛ القرار `LONG_BIAS` يتطلب توافق النظام الصاعد مع اتجاهي 1H و4H، وإلا يعرض أحد أوضاع الانتظار/نقص البيانات.
- مستويان هابطان ومستويان صاعدان لـBTC، مع توضيح مصدر كل مستوى: دعم/مقاومة بنيوي من شموع مغلقة، أو امتداد ATR بديل معلّم صراحة. يعرض التقرير السعر المرجعي وEMA50/EMA200 وATR ومستوى إبطال السيناريو. الأهداف مستويات تخطيط وليست توقعات مضمونة.
- تصنيف كل عملة إلى دخول مشروط أو انتظار تأكيد BTC أو انتظار محفز الدخول أو مراقبة أو تجنب. الدخول المشروط لا يظهر إلا لمرشح `READY_NOW` اجتاز الاقتصاد/التكلفة، وبوجود توافق BTC صاعد 1H+4H؛ ولا يملك المحرك سلطة إرسال أمر.
- أمر `/decision SYMBOL`، وتوسيع `/brain` و`/forecast`، وإضافة تقرير تلقائي محدود التكرار بعد دورة المسح عبر Telegram Outbox الحالي.
- إعدادات: `A86_AUTO_BRAIN_REPORT_ENABLE=1`, `A86_AUTO_BRAIN_REPORT_INTERVAL_SEC=900`, `A86_BRAIN_REPORT_MAX_CANDIDATES=3`.

## سياسة الرسالة

توضح الرسالة اتجاه BTC وهدفه الهابط/الصاعد وفق السيناريو، وتعرض حتى ثلاثة مرشحين مع السعر المرجعي ومنطقة الدخول ووقف الخسارة والأهداف وصافي TP1 التقديري وNet RR والتكلفة والقوة النسبية والتوافق الزمني وسبب القرار. الدرجات ليست احتمالات، والـPaper ليس PnL حقيقيًا. القبول في Outbox لا يثبت التسليم؛ يلزم اختبار Telegram حي ببيانات اعتماد المستخدم لإثبات الوصول الفعلي.

## نتائج التحقق النهائي في بيئة الاختبار

- `python -m compileall -q .`: اجتاز **73/73 ملف Python**.
- `pytest -q test_release_contracts.py`: **85 passed, 1 skipped, 0 failed** من أصل 86 اختبارًا؛ سبب التخطي سجل A51 التاريخي غير المرفق.
- اختبارات A87 المركزة: **7/7 PASS** (قرار BTC، أهداف بنيوية/ATR، تقرير Telegram، Outbox rate-limit، وأمر `/decision SYMBOL`). هذه السبعة داخلة ضمن إجمالي 85 ولا تُضاف إليه.
- `python main.py --validate-only`: **Exit 0** مع `bot_started=false`, `live_threads=[]`, `active_env_aliases=[]`؛ لم تتوفر مفاتيح MEXC أو Telegram ولم يُفتح اتصال خاص.
- Telegram: اختبار محاكاة للـreply والـOutbox فقط؛ **التسليم الحقيقي غير مختبر** لعدم استخدام Token/Chat ID حقيقيين.
- ZIP بعد الإقفال: **99/99 مسارًا** وفق Manifest، واختبار CRC واستخراج نظيف والتحقق من 98 بصمة غير ذاتية.

## السلامة

تبقى `MONITOR_ONLY_NO_NEW_BUYS` قائمة. لم تتغير صلاحيات Selector/Order/Execution، ولم تُخفف بوابات السبريد أو السيولة أو HTF أو الرسوم أو المخاطر. لا توجد أوامر تداول حقيقية ضمن هذا التعديل.

## الملفات المتوقع تعديلها في هذا الإغلاق

`main.py`, `test_release_contracts.py`, `.env.example`, `README.md`, `CHANGELOG.md`, `FINAL_AUDIT_REPORT.md`, `FINAL_MANIFEST.json`, `A66_RELEASE_MANIFEST.json`, `A66_SHA256SUMS.txt`.

# A86 — التقرير التنفيذي النهائي (2026-11-20)

> هذا الملحق هو سجل الإصدار الحالي ويسبق تقارير A85 التاريخية أدناه. الحزمة: `FINAL_PRODUCTION_RELEASE.zip`. جميع عمليات التحقق هنا محلية/محاكاة؛ لم يُرسل أمر تداول حقيقي.

## النتيجة التنفيذية

- الحزمة الأصلية والنهائية: **99 ملفًا**؛ لا ملفات أُضيفت أو حُذفت. تم تعديل وحدتي Python (`main.py` و`test_release_contracts.py`) وسبعة ملفات إعداد/توثيق/بيانات إصدار.
- ملفات Python: **73/73** اجتازت `compileall`. ملفات الاختبار: **58 وحدة**، **657 اختبارًا جُمعت؛ 656 ناجحًا، 1 متخطّى، 0 إخفاقات**. نفذت الوحدات في عمليات pytest معزولة بقاعدة SQLite مستقلة لتجنب تداخل حالة الاختبار؛ لم يُسجل `pytest -q` أحادي العملية بوصفه نجاحًا.
- `test_release_contracts.py`: **80 ناجحًا، 1 متخطّى، 0 إخفاقات**. التخطي التاريخي يحتاج سجل A51 غير موجود في الحزمة. اختبارات A85/A86 المركزة مضمنة ضمن عدد المجموعة الكامل.
- اختبارات Paper الحرجة: TP1 يُحل من شمعة لاحقة مغلقة؛ ولمس SL وTP في الشمعة نفسها يُسجل `AMBIGUOUS` ويُستبعد من الإحصاءات؛ السجلات المفتوحة بلا بيانات بعد 24 ساعة تُغلق `DATA_GAP`، والانتظار بعد انتهاء صلاحيته يُغلق `EXPIRED` دون اختلاق PnL. أوامر `/brain` و`/forecast` و`/paper` اختُبرت بمجيب Telegram محاكى وهي للقراءة فقط.
- `main.py --validate-only`: Exit 0 بعد تنفيذ الاختبار على المصدر النهائي؛ `bot_started=false` و`live_threads=[]`، دون مفاتيح خاصة أو رصيد حقيقي أو أوامر تداول.

## ما تم دمجه فعليًا

1. **Market Radar محدود:** حتى 500 سجل ticker متاح من اللقطة المشتركة، مع ترتيب مجموعة وسيطة حتى 100–150 مرشحًا، وممر تحديث أولوية افتراضي 15، وتحليل شموع عميق حتى 60 رمزًا ضمن ميزانية A79 المشتركة. حد 500 ليس ادعاءً بفحص 500 OHLCV عميقًا في كل دورة.
2. **BTC Forecast:** أربع آفاق 15M/1H/4H/24H؛ درجات سيناريو BULLISH/BEARISH/RANGE من شموع Spot مغلقة. لا تتحول الدرجات إلى نسب تكرار تاريخية إلا بعد 30 نتيجة محلولة على الأقل لكل أفق/فئة.
3. **تصحيح عائد الساعة والقوة النسبية:** `return_1h_pct` يقارن شمعتين 1H مغلقتين متجاورتين، وأضيفت قياسات منفصلة لـ6H و4H و24H، مع مقارنة BTC على نفس المدة.
4. **Consensus/Adaptive Ranking:** خصم محدود لتعارض اتجاه عائلات الاستراتيجية، وتعديل تكيفي لا يتاح إلا بعد 60 نتيجة Paper محلولة على الأقل مع تقسيم زمني Train/Holdout واتفاق إشارة الـexpectancy. جميعها تعدّل الترتيب فقط ولا تغير فلاتر أو قرارات تنفيذ.
5. **Paper Ledger مستقل:** تسجيل الخطط المرجعية المؤهلة، ومتابعة دخول/خروج محاكى من شموع مغلقة مستقبلية، مع رسوم/تكلفة نموذجية وNet R. لا تُعامل أسعار Ask المرجعية كـfills فعلية. شمعة SL+TP المزدوجة `AMBIGUOUS` ولا تدخل ضمن Win Rate أو Expectancy؛ السجل المفتوح الذي يفقد بيانات السوق 24 ساعة يتحول إلى `DATA_GAP`، والفرصة المنتظرة بعد انتهاء نافذتها تتحول إلى `EXPIRED`، وكلتاهما خارج احتساب الأداء.
6. **Portfolio Brain:** قائمة قصيرة Paper لا تتجاوز خانتين افتراضيًا، تتجنب القطاع المعروف المكرر والارتباط المرتفع عند وجود 30 عينة متزامنة على الأقل. لا يجلب رصيد الحساب ولا يحجز رأسمالًا.
7. **Telegram:** أوامر `/brain` و`/forecast` و`/paper` تمت إضافتها إلى Dispatch القراءة فقط؛ تأكدت اختباريًا دون إرسال شبكي فعلي.

## تعديلات المصدر والملفات

- `main.py`: منطق A86 المدمج، ولا يوجد سكربت تشغيل بديل.
- `test_release_contracts.py`: عقود واختبارات A86 إضافية تشمل 500 ticker bounds، فترات returns، معايرة التوقع، Paper Ledger، الحالات الملتبسة، تنويع المحفظة، التكيف الزمني وأوامر Telegram.
- `.env.example`: إعدادات Radar وPaper وForecast وAdaptive.
- `README.md` و`CHANGELOG.md` و`FINAL_AUDIT_REPORT.md`: توثيق التنفيذ والقيود.
- `FINAL_MANIFEST.json` و`A66_RELEASE_MANIFEST.json` و`A66_SHA256SUMS.txt`: SHA-256 وجرد الإصدار.
- لم تُحذف ملفات؛ ولم تُضف ملفات جديدة. العدد النهائي 99.

## حدود لا يجوز تجاوزها في الادعاءات

- لا توجد وصلة موثقة حاليًا لبيانات Market Cap أو BTC Dominance أو OI أو Funding أو Liquidations أو CVD؛ تظهر `UNAVAILABLE` ولا يتم اختلاقها. تصنيف القطاعات جزئي وثابت.
- لا يضمن Radar أن 500 زوج ظهرت جميعها في لقطة التيكر، ولا أن 500 زوج حصلت على شموع عميقة في كل دورة.
- توقع BTC الحالي قائم على درجات مؤشرات/بنية من Spot OHLCV مغلق؛ لا يملك نموذجًا إحصائيًا معايرًا قبل عينة النتائج المحددة.
- Paper Ledger يُنتج نتائج محاكاة من OHLCV وتكاليف مقدرة، لا صفقات منفذة ولا PnL حقيقيًا. لا يوجد إثبات ربحية أو دخل يومي.
- لم تُستخدم بيانات اعتماد MEXC خاصة، ولم تُرسل أوامر. لم يُختبر اتصال Telegram حي، أو رسوم الحساب الخاصة، أو Docker target/Python 3.12، أو حمل Railway/Render أو التشغيل الطويل.
- تظل سياسة التداول `MONITOR_ONLY_NO_NEW_BUYS`، وتظل سلطات A85/A86 في Selector/Order/Execution = `false`. قرار النشر: `NO_GO_UNATTENDED_LIVE`.

# الإغلاق المستقل النهائي — مراجعة A85 وإثباتات الإصدار (2026-11-20)

> **هذا القسم هو المرجع الأحدث والملزم لهذا الإصدار، ويَسود على أي أعداد أو أحكام تاريخية مختلفة في الأقسام الأقدم أدناه.** ملف التسليم المطلوب: `FINAL_PRODUCTION_RELEASE.zip`.

## 1) النتيجة التنفيذية الصريحة

- الحزمة الأصلية: **99 ملفًا فريدًا**؛ الحزمة النهائية: **99 ملفًا**؛ الملفات المضافة: **0**؛ الملفات المحذوفة: **0**. جميع المسارات الـ99 مطابقة للمصدر الأصلي.
- ملفات Python: **73**؛ وحدات الاختبار: **58**؛ الاختبارات المجموعة: **647**.
- Compile Check: **73/73 PASS**.
- Regression Tests: **646 PASS، اختبار واحد SKIPPED، صفر FAIL**. نُفذت في 12 مجموعة غير متداخلة، ولكل مجموعة قاعدة SQLite مستقلة.
- `main.py --validate-only`: **Exit 0**، مع `bot_started=false` و`live_threads=[]`، ودون مفاتيح MEXC أو Telegram.
- أخطاء برمجية قابلة لإعادة الإنتاج وإثباتها في هذا الإغلاق: **0**؛ أخطاء كود أُصلحت في هذه المراجعة: **0**. لم أُجرِ تعديلًا تخمينيًا على منطق التداول أو أُرخِ بوابة مخاطر بغرض زيادة عدد الإشارات.
- تغييرات هذا الإغلاق اقتصرت على توثيق نتائج التحقق وتحديث Manifest وسجل SHA-256: **6 ملفات توثيق/بيانات إصدار معدّلة**، لا ملفات Python.

**حدّ المراجعة:** أُجري فحص بنيوي وAST، وCompile لجميع ملفات Python، وفحص الاستيراد/التهيئة والاختبارات، ومراجعة مركزة للمسارات الحساسة وA85. لم أُنجز قراءة بشرية حرفية لكل سطر من نحو 110 ألف سطر في `main.py`؛ لذلك لا أصف العمل بأنه تدقيق يدوي سطرًا بسطر لكل الملف، ولا أدّعي خلو كل مسارات التشغيل من أخطاء غير مكتشفة.

## 2) نتائج الاختبارات المنفذة

### Compile / Startup

- `python -m compileall -q .`: نجاح لجميع ملفات Python الـ73.
- `python main.py --validate-only`: Exit 0؛ `bot_started=false`؛ `live_threads=[]`؛ `active_env_aliases=[]`.
- لا يثبت `--validate-only` نجاح اتصال MEXC أو Telegram، ولا يبدأ دورة تداول؛ وظيفته هنا التحقق من الإعدادات والتهيئة الآمنة فقط.

### Regression

| المجموعة | عدد الاختبارات الناجحة |
|---|---:|
| G1 | 32 |
| G2 | 31 |
| G3 | 26 |
| G4 | 33 |
| G5 | 44 |
| G6 | 34 |
| G7 | 50 |
| G8 | 112 |
| G9 | 35 |
| G10 | 32 |
| G11 | 40 |
| G12 | 177 |
| **الإجمالي** | **646** |

- إجمالي المجموعة الكاملة: **647 collected = 646 passed + 1 skipped + 0 failed** عبر 58 وحدة.
- Release Contracts: **70 passed، 1 skipped**. سبب التخطي: `test_release_contracts.py:375` يحتاج سجل A51 تاريخيًا غير موجود في الحزمة.
- `test_v702_intraday_shadow.py`: **31 passed**.
- اختبار A85 المحدد بالمرشح `-k 'a85_'`: **4 passed**؛ واختبارات تقرير Micro اليومية المركزة: **2 passed**. هذه نتائج جزئية متداخلة مع المجموعة الكاملة ولا تُضاف إلى 646.
- تشغيل `pytest -q` في عملية واحدة تجاوز مهلة 300 ثانية ولم يكتمل. لذلك لم أقدمه كنتيجة نجاح؛ أُعيد تنفيذ وحدات الاختبار الـ58 في 12 مجموعة بعمليات مستقلة وقواعد بيانات اختبار منفصلة، واكتملت كلها بالنتائج أعلاه.

## 3) تشخيص سجل التشغيل الذي أرسله المستخدم

النتائج التالية مستخرجة من نصوص DIGEST المرفقة، وليست قراءة مباشرة من اتصال حي في هذه المراجعة:

- حالة BTC: `BEARISH`. آخر قيم السجل: إغلاق 1H عند **59,482.03** مقابل EMA50 **62,575.49** (أقل بنحو **4.94%**)؛ وإغلاق 4H عند **59,482.03** مقابل EMA50 **65,644.95** (أقل بنحو **9.39%**) وEMA200 **73,231.22** (أقل بنحو **18.78%**). هذا يؤيد الحذر في سوق Spot طويل فقط، ولا يثبت أن كل عملة بديلة هابطة بالمقدار نفسه.
- نافذة 30 دقيقة: `DISC=237`، `RANK=177`، `PRE=170`، `PASS=0`، `PRE_REJ=170`، ثم `SEL=0` و`BUILD=1/B_NONE=1`، مع صفر Queue/Telegram/Execution.
- سبب الرفض الأعلى: `htf.family_htf_strength_below_floor` بعدد **136** من 170؛ ثم رفض سيولة/تأكيد دفتر الأوامر `liquidity.v45_micro` بعدد **10**. هذا يشير إلى اختناق قبل Select، لا إلى خلل مثبت في Queue أو Telegram أو Execution؛ فهذه المراحل لم تستقبل مرشحًا مختارًا في النافذة المذكورة.
- موضع سياسة HTF في المصدر: `main.py` قرابة الأسطر **19235–19269**، حيث يُطبّق حد قوة HTF الخاص ببيانات الاستراتيجية. موضع تأكيد دفتر أوامر MICRO: قرابة **20180–20190**. أسماء الأسباب في السجل متوافقة مع هذين المسارين. لا يتضمن الملخص قيمة `strength` و`floor` لكل رمز، لذلك لا يمكن تحديد سبب كل مرشح على حدة من هذا الملخص.
- `A79` سجّل **29 نجاح جلب من 32 محاولة و3 إخفاقات**؛ ومن أسباب الإخفاق المعروضة `df_15m_fetch_failed` و`df_4h_fetch_failed`. هذه مشكلة تغطية بيانات/جلب يجب تتبعها بحسب الرمز والـ timeframe والـ API response، وليست دليلًا وحده على خطأ حساب مؤشر.
- `A51_POLICY_PREFILTER blocks=0` لا يتعارض مع ذلك؛ الرفض الظاهر يحدث في PreQual/HTF وسيولة MICRO وليس في عداد A51 المذكور.
- سياسة الدخول المرفقة هي `MONITOR_ONLY_NO_NEW_BUYS`؛ `live_ready=0` و`exec_try=0`. لا يوجد في هذه السجلات أمر تداول جديد ولا دليل على أن صفقة وصلت إلى التنفيذ.
- يوجد اختلاف نطاق يستحق المتابعة: تقرير Micro اليومي ليوم 2026-11-19 يعرض `Evaluated=0`، بينما DIGEST 3 يعرض عدادات A9 مثل `MOM1m=153/0/153` و`SWEEP1m=153/3/150`. قد تكون هذه عدادات بنطاق/فترة مختلفة؛ لا يجوز جمعها أو اعتبارها تناقضًا مؤكدًا دون مقارنة نافذة التقرير اليومية مع عدادات الدورة وسجلات SQLite الخام.
- لا يعرض الملخص المرسل قائمة رموز A85 الأعلى ترتيبًا ولا إثباتًا واضحًا لنتيجة `[A85]` لكل دورة؛ لذلك لا أختلق اسم «أفضل عملة» ولا صفقة Entry/SL/TP غير موجودة في البيانات.

**القرار بناءً على هذا السجل:** لا شراء جديد. لا تخفيف لحد HTF أو عمق/سبريد MICRO لمجرد تحويل `PASS=0` إلى إشارات. يجب أولًا فحص تفاصيل المرشحين المرفوضين حسب الاستراتيجية والرمز، ثم مراقبة Shadow لعينة كافية ونتائج صافية بعد الرسوم قبل أي تعديل انتقائي.

## 4) ما يقدمه A85 فعليًا وما لا يقدمه

محرّك `A85MarketIntelligence` موجود داخل `main.py` (يبدأ قرب السطر **108597**) ويعمل كمحلل **Read-only**؛ خصائص `execution_authority=false` و`selector_authority=false` و`order_authority=false`. يقرأ بيانات السوق/الشموع المشتركة، ويعرض `/market` و`/top` و`/ready` و`/waiting` و`/analyze` و`/chart` وغيرها. يتضمن سياق BTC/ETH، وتحليلًا متعدد الأطر المغلقة، ومؤشرات/بنية سعرية، وتصنيفًا وترتيبًا وخطة Entry/SL/TP تقديرية تراعي الرسوم والسبريد، ورسوم PNG.

حدود التغطية التي يجب عدم تجاوزها في وصفه:

- وجود سقف بحثي 500 رمز لا يعني تحليل 500 رمز OHLCV كاملًا في كل دورة. بيانات السجل المرسل أظهرت Universe بحجم **47** فقط في تلك اللحظة.
- مجموعة A85 المتوسطة تستهدف حتى 100–150 مرشحًا بحثيًا عند توافرها؛ ويُدوّر تحليل OHLCV العميق بعدد مضبوط (الافتراضي 16، النطاق 4–24) داخل ميزانية A79 المشتركة التي تصل إلى 32 رمزًا/دورة. سقف `A85_MAX_ANALYSIS_SYMBOLS` البالغ 60 ليس وعدًا بجلب 60 رمزًا في كل دورة.
- الأطر المدعومة في المحلل: 1D و4H و1H و15M و5M و1M بحسب توافر الشموع المغلقة؛ اتساع العينة لا يساوي تغطية كاملة للسوق.
- لا يوجد مزود موثوق موصول هنا لقياس إجمالي Market Cap أو BTC Dominance أو Futures OI/Funding/Liquidations أو CVD؛ هذه الحقول غير متاحة. تصنيف القطاعات ثابت/جزئي، وبيانات Breadth عينة من البيانات المشتركة.
- درجات A85 ترتيب/تقييم قواعدي وليست احتمال نجاح أو تنبؤًا معايرًا باتجاه السعر. لا يوجد إثبات Walk-forward/Out-of-sample أو ربحية مستقبلية في هذه الحزمة.
- `/ready` و`READY_NOW` وصف تحليلي للجاهزية فقط ولا يمنحان صلاحية تداول. A85 لا يحقن المرشح في Selector ولا يرسل أمرًا.

للوصول إلى «عقل مدبر» أكثر شمولًا، النقص الحقيقي ليس إضافة مؤشرات أكثر؛ بل تغطية سوق موثقة لكل الرموز، مصدر مشتقات/سيولة موثوق، سجل تاريخي متزامن، واختبار Walk-forward يفصل بين الإشارة والنتيجة والتكاليف. لا توجد في هذه المراجعة بيانات كافية لاختلاق هذه المكونات أو الادعاء بأنها موجودة.

## 5) الهيكل، الاعتماديات، والتكرار

- `main.py` حجمه نحو **6.25 MB** ويحتوي قرابة **110,105 سطرًا**؛ وهو نقطة صيانة/تحميل عالية المخاطر.
- فحص AST أظهر تعريفات عليا متكررة لعدد **11 اسم دالة** (بعضها 3 تعريفات). هذا لا يثبت وحده عطلًا؛ فترتيب التعريفات قد يكون جزءًا من طبقات التوافق/الإغلاق المتراكمة. لم أحذفها أو أدمجها دون إثبات أن التعريف النهائي لا يعتمد على السلوك السابق.
- لم يُحذف أي محرك استراتيجية أو ملف اختبار أو مسار حماية. لم تُغيّر واجهات الدوال أو أسماء الإعدادات.
- فحص الأرشيف لم يجد ملف `.env` فعليًا أو قاعدة بيانات تشغيل/كاش ضمن ملفات المصدر؛ الموجود `.env.example`. لم يُعثر في الفحص على قيمة تشغيلية حقيقية لمفتاح MEXC أو Token Telegram. اختبار فحص التسريب في `test_v702_production_audit_fixes.py` يتضمن Assertion على تنقيح سجل `MEXC_API_KEY`، وليس مفتاحًا حقيقيًا.

## 6) قيود بيئة التحقق ومخاطر النشر

- بيئة المراجعة: Python **3.13.5**؛ ملف Docker يستهدف Python **3.12**، لكن Python 3.12 غير مثبت في بيئة المراجعة. لذلك لم يُثبت التوافق على إصدار الإنتاج المقصود.
- لم تتوفر وحدتا `ccxt` و`aiosqlite` في بيئة المراجعة، رغم وجودهما ضمن الاعتماديات المثبتة في ملفات المتطلبات. اجتاز `--validate-only` بفضل مسار الاستيراد الاختياري، والاختبارات استخدمت المحاكاة حيث يلزم؛ هذا لا يثبت تكامل CCXT/SQLite async الحقيقي في بيئة نظيفة.
- `pip check` في بيئة المراجعة العالمية أظهر تعارضًا خارجيًا بين `moviepy 2.2.1` و`pillow 12.3.0` (MoviePy يطلب Pillow أقل من 12). لم يثبت أن MoviePy اعتماد مباشر للمشروع؛ لا تُنسب هذه المشكلة إلى الحزمة دون بناء بيئة معزولة من متطلباتها.
- Docker غير متاح، لذلك لم يُبنَ Image. ولم يُنفذ اتصال MEXC خاص موثّق، ولا إرسال Telegram حقيقي، ولا استعلام رسوم حساب، ولا أمر/Fill، ولا اختبار حمل Railway/Render، ولا Soak طويل، ولا دراسة ربحية.
- ذروة الذاكرة المقاسة في `--validate-only` وحده كانت **586,568 KiB ≈ 572.8 MiB**. هذا القياس لا يساوي استهلاك دورة تشغيل كاملة، لكنه يجعل تشغيل هذه النسخة على حد **512 MB** غير مثبت وغير آمن افتراضًا. استخدم بيئة **768 MB أو أكثر كتجربة أولية مع مراقبة**، ثم قِس دورة المسح الفعلية؛ لا أصف هذا كحد أدنى مضمون.
- التشغيل الأحادي الكامل لـpytest تجاوز 300 ثانية؛ نجحت المجموعات المعزولة. توجد حالة تاريخية واحدة متخطاة لعدم وجود ملف A51 log المطلوب.

## 7) ملفات هذا الإغلاق

تم تعديل الملفات الستة التالية فقط لأغراض توثيق نتيجة المراجعة وتثبيت معلومات الإصدار:

`README.md`، `CHANGELOG.md`، `FINAL_AUDIT_REPORT.md`، `FINAL_MANIFEST.json`، `A66_RELEASE_MANIFEST.json`، `A66_SHA256SUMS.txt`.

- ملفات Python المعدلة في هذا الإغلاق: **0**.
- الملفات المحذوفة: **0**.
- الملفات المضافة: **0**.
- عدد ملفات ZIP النهائي: **99**.

## 8) Google Colab — تشغيل تحقق آمن

ارفع الملف `FINAL_PRODUCTION_RELEASE.zip` إلى جلسة Colab، ثم نفّذ:

```python
!unzip -t /content/FINAL_PRODUCTION_RELEASE.zip
!unzip -q /content/FINAL_PRODUCTION_RELEASE.zip -d /content/unified_scalper
%cd /content/unified_scalper
!python --version
!pip install -r requirements.txt
!python -m compileall -q .
!python main.py --validate-only
```

ابدأ بوضع التحقق فقط. بعد ذلك، للمراقبة والإشعارات فقط، انسخ `.env.example` إلى `.env` واضبط قيم Telegram الاختيارية، وأبقِ `UNIFIED_LIVE_PILOT_ENABLE=0` و`UNIFIED_A55_LIVE_ARM=0` والسياسة `MONITOR_ONLY_NO_NEW_BUYS`. لا تضف مفاتيح تداول خاصة ولا تُفعّل أوامر حقيقية أثناء التحقق. انتبه إلى أن تخزين Colab مؤقت ما لم تستخدم تخزينًا دائمًا مدروسًا لقاعدة SQLite.

---

# FINAL AUDIT REPORT — VERIFIED RECOVERY RELEASE (2026-11-20)

## Release identity

- Base source: the supplied 99-file Unified Scalper V702 A84 archive.
- Recovery revision: `A84-RECOVERY-A85-PARTIAL-2026-11-20`.
- Final artifact: `FINAL_PRODUCTION_RELEASE_A85_RECOVERY.zip`.
- Inventory: 99 files retained; no files added or removed.
- Trading authority: `MONITOR_ONLY_NO_NEW_BUYS`; `UNIFIED_LIVE_PILOT_ENABLE=0`; `UNIFIED_A55_LIVE_ARM=0`.

## Root cause of repeated incomplete A85 delivery

A binary comparison of the previously named A84 and A85-provisional ZIPs showed that their `main.py` files were byte-for-byte identical (SHA-256 `4068a8aca7c83e16c2c592dc2161ae7f2e9bc80dda4ab667d78ba0a732bf0525`). Their `.env.example` files were also identical. The provisional archive had changed documentation/manifest metadata that described features not present in the executable. The full A85 market-intelligence engine and PNG chart renderer were absent. This is why repeated packaging did not produce the requested A85 behavior: staged documentation was updated without the corresponding runtime implementation being persisted into the release archive.

## Actual changes in this recovery closeout

1. Changed the stablecoin feature's canonical default from enabled to disabled (`STABLECOIN_MM_ENABLE=False`) and `.env.example` from `1` to `0`, matching the latest explicit A85 safe-default requirement.
2. Kept the A83 `USDC/USDT` research engine and its fee/market-data validation. When manually enabled, it remains `SHADOW` only and has no live order authority.
3. Kept BTC directional macro observational by default (`V410_FAMILY_MACRO_DIRECTION_GATE_ENABLE=0`) while retaining unknown/crash/extreme/hard-reject protections and all local symbol/market-risk gates.
4. Kept the existing nine-detector Router confluence behavior, six deduplicated groups, and maximum +1.5 ranking-point contribution. It is not a full cross-strategy statistical consensus engine.
5. Rewrote README/CHANGELOG and this report to distinguish implemented features from requested but missing A85 scope.
6. Updated existing regression assertion, release manifests and SHA-256 ledger. No new file paths were added.

## A85 items not implemented in this package

The following must not be considered delivered: dedicated 500-pair staged A85 market radar/fair rotation; full BTC/ETH regime, breadth and sector-rotation intelligence service; complete multi-timeframe OHLCV feature fusion beyond the existing runtime; new full SMC/price-action/structure engine beyond the existing SMC capabilities; cross-engine statistical Strategy Consensus beyond the Router confluence; full top-3-to-5 opportunity ranking authority; complete A85 trade-plan/expiry/invalidation authority; automated 1H/15M/4H PNG chart rendering; Telegram `sendPhoto` workflow and complete new `/market`, `/top`, `/ready`, `/waiting`, `/analyze`, `/chart` command dashboard; full walk-forward/out-of-sample adaptive performance engine. These capabilities are not present as an integrated and tested A85 path in the delivered code.

## Verification performed on the exact final ZIP extraction

- `python -m compileall -q .`: PASS for the 73 Python files.
- `SCALPER_DB=/tmp/a85_recovery_final_extract_validate.db python main.py --validate-only`: exit 0; `bot_started=false`; `live_threads=[]`; `active_env_aliases=[]`; no exchange credentials or Telegram credentials were present.
- Full regression suite: **619 passed, 1 skipped, 0 failed** across 58 modules (32.76 seconds) on a clean extraction whose 73 Python files, `.env.example`, README, CHANGELOG and release manifests were byte-for-byte identical to this final build. The skipped test requires a historical A51 runtime log not packaged in the clean source ZIP.
- Final-build extraction re-ran the release-contract and live-switch documentation tests: **45 passed, 1 historical-fixture skip, 0 failed**. The only later changes between the full-suite extraction and this final archive were the audit-report wording and checksum ledger.
- `sha256sum -c A66_SHA256SUMS.txt`: 98/98 entries matched after final extraction. ZIP CRC and clean extraction passed; archive inventory is 99 paths (73 Python files).
- A83 configuration contract updated to assert `STABLECOIN_MM_ENABLE is False`; fee economics remains tested using the fallback 0.1% maker fee per side (20 bps round trip) and 12 bps maximum spread, so the default quote remains economically blocked.
- No authenticated MEXC session, wallet query, live order, real fill, real Telegram send/ACK, Docker image build, long soak, or profitability test was performed.

## Operational notes

- To keep A83 off: retain `STABLECOIN_MM_ENABLE=0`.
- To intentionally run A83 Shadow: set `STABLECOIN_MM_ENABLE=1`, keep `STABLECOIN_MM_MODE=SHADOW` and `STABLECOIN_MM_LIVE_ARM=0`; check for overriding `.env`/Railway/Render values.
- Do not force zero fees. The fallback is 0.1% per side and is not an account-specific fee guarantee.
- Start with `python main.py --validate-only`; this checks configuration only and deliberately does not run background workers.

---

# FINAL PRODUCTION RELEASE — A84 Executive Audit Summary (2026-11-19)

**Artifact:** `FINAL_PRODUCTION_RELEASE.zip`  
**Project identity:** Unified Scalper 4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL  
**Audit closure:** A84 — A79 supplemental-scan NameError and A83 Shadow market-data integrity  
**Operating authority:** `MONITOR_ONLY_NO_NEW_BUYS`; no live orders are authorized by this release.

## Release result

- **Original files:** 99. **Final files:** 99. **Added:** 0. **Removed:** 0. **Existing files modified:** 8.
- **Defects identified and repaired in this closure:** 6. **Regression tests added:** 6. **Focused A79/A83 regression tests:** 21 passed.
- **Full automated test suite:** 58 modules; **615 passed, 1 skipped, 0 failed**, run in six non-overlapping groups (63, 59, 78, 136 plus one skip, 67, 212). The only skip requires a historical A51 runtime log that is not included in the source archive.
- **Python compilation:** `compileall` passed for all 73 Python files; explicit `py_compile` also passed for 73/73.
- **Release contract tests on the final clean extraction:** 44 passed, 1 historical-fixture skip, 0 failed.
- **Clean-extract `python main.py --validate-only`:** exit 0; `bot_started=false`; `live_threads=[]`; no exchange or Telegram credentials were present.
- **Archive integrity:** 99 unique paths; exact match to the original archive inventory; CRC check and clean extraction passed; all 98 entries in `A66_SHA256SUMS.txt` match. No `.env`, DB, bytecode, or cache files are packaged.

## A84 repairs

1. Fixed the undefined A79 monitor-only helper reference that prevented all supplemental research snapshots from being fetched (`attempted=32 / ok=0 / failed=32` in the supplied logs). The corrected path uses the canonical scan authorization helper and remains research-only.
2. Added fail-closed finite-number validation to A83 order-book metrics and public trade-flow values.
3. Rejects missing, invalid, stale, or future-dated order-book timestamps instead of treating untimed data as fresh.
4. Rejects non-finite and future-dated public prints during simulated fill processing.
5. Clamps virtual capital and reserve to non-negative values before deriving the minimum net-profit threshold.
6. Added six deterministic regression tests for the A79/A83 failure cases.

## Trading-opportunity and risk decision

The supplied 2026-11-18 Micro Shadow digest recorded 26 signals, 23 resolved, 3 TP, 14 SL and 6 timeouts; the reported modeled net expectancy for the listed Micro strategies was negative. These are simulated observations, not exchange fills, but they are sufficient reason **not** to promote those engines to live execution. The repeated bearish-BTC family-policy rejections are consistent with the configured strategy policy; that policy, HTF checks, spread/cost gates, liquidity floors, score thresholds, PreSend, execution, and protection controls were not weakened.

The A83 `USDC/USDT` market-making lane remains disabled by default and Shadow-only. Its fallback maker-fee assumption is 0.1% per side (20 bps round trip), greater than the default 12 bps spread ceiling before slippage; therefore it should not generate a quote under the default assumptions. A zero-fee override is only an operator-supplied assumption after independently confirming the exact account/pair fee tier. No `create_order` route, real fill, daily-income guarantee, or profitability claim is included.

## Files changed in A84

`main.py`; `test_v702_production_audit_fixes.py`; `README.md`; `CHANGELOG.md`; `FINAL_AUDIT_REPORT.md`; `FINAL_MANIFEST.json`; `A66_RELEASE_MANIFEST.json`; `A66_SHA256SUMS.txt`. No file was added or removed.

## Verification limits

The environment lacked `ccxt` and `aiosqlite` during the import probe. No authenticated MEXC session, wallet query, live order, real fill, Telegram network delivery acknowledgement, deployment soak, or out-of-sample profitability study was performed. The 100k+ line canonical runtime remains a large historical module; this closure is a targeted source repair, not a claim that every historical line was manually reviewed or that the whole runtime was modularized.

## Google Colab

```python
!unzip -q /content/FINAL_PRODUCTION_RELEASE.zip -d /content/unified_scalper
%cd /content/unified_scalper
!pip install -r requirements.txt
!python main.py --validate-only
```

For the initial monitor-only validation, keep live switches off and do not provide private MEXC trading credentials. Optional Telegram credentials are only for notifications.

---

# Historical audit record — A77 Micro Outcome Telegram Closure (2026-11-17)

## Executive result

A77 extends the A76 monitor-only Micro lane so an opportunity alert is followed by a durable Telegram result notification and a per-strategy daily report. The release also fixes a digest-compaction defect that could hide the `SELECTED → BUILDER BLOCK` evidence line while its aggregate counter remained visible.

**Distribution:** 99 files exactly, no new files, no deleted files.  
**Runtime authority:** `MONITOR_ONLY_NO_NEW_BUYS`; `V702_INTRADAY_SHADOW_LIVE_ENABLE=False`; `NO_GO_UNATTENDED_LIVE`.  
**Research DB schema:** v4, additive tables only.

## A77 changes

1. **Outcome notifications:** when an alerted 1m Micro sample resolves, the same SQLite transaction that updates its sample inserts one uniquely keyed outcome record. The result outbox supports `TP1`, `SL`, `TIMEOUT` and `AMBIGUOUS_DATA_GAP`; `sample_id` is unique, pending items are retryable, and ambiguous data gaps are excluded from scored returns.
2. **Telegram result message:** includes symbol, strategy, signal ID, entry/stop/target, reference exit, observation bars, modeled cost, gross R and net modeled R/percent. The message explicitly says Shadow/monitor-only and does not claim an exchange fill or realized PnL. Same-candle TP/SL behavior remains conservative stop-first.
3. **Opportunity links:** initial Micro alerts and their outcome notices reuse the existing opportunity link formatter. It can include the MEXC Spot TradingView chart and a Telegram public-channel/bot link when the corresponding public URL or username is configured. A private numeric chat ID is not converted into a fabricated `t.me` permalink. A Telegram link is omitted if no public link identity has been configured; the opportunity is still delivered to the configured bot chat when Telegram credentials are present.
4. **Daily report:** a unique durable report is generated for the previous calendar day in the configured timezone (default `Africa/Cairo`) after 00:05 local time. It reports each of the five intraday Shadow strategies separately, including samples, resolved outcomes, TP1/SL/timeout/ambiguous counts and average modeled net R/percent. It is a research report, not a profit guarantee.
5. **Digest evidence preservation:** when the operator digest is compacted to fit Telegram limits, the three `SELECTED → SCORER/ROUTE/BUILDER BLOCK` headings and their evidence rows now receive explicit preservation priority. This repairs an existing discrepancy where `builder_blocks=1` could be shown while the Builder section itself was dropped.
6. **Configuration and diagnostics:** `.env.example` documents the outcome outbox, batch cap, daily report enable/timezone/time, while `/digest`/service reporting expose pending/queued states. `QUEUED` means accepted into the application's durable Telegram dispatcher outbox; it is not an external Telegram delivery acknowledgement.

## Root-cause / safety boundary

A77 does not change the A76 core/micro scan allocation, family regime policies, macro crash filters, spread or cost thresholds, risk limits, selector, order builder, exchange execution, or position management. The 1m Micro lane stays independent and read-only. Outcome TP/SL labels are simulated closed-candle observations, not live order outcomes. No MEXC order, Telegram network call, external delivery ACK, or profitability claim was tested.

A public Telegram link requires a configured `TELEGRAM_OPPORTUNITY_PUBLIC_URL`, `TELEGRAM_PUBLIC_URL`/`TELEGRAM_CHANNEL_URL`, `TELEGRAM_PUBLIC_CHAT_USERNAME`, an `@channel` alias, or a public bot/channel username. The private bot chat ID alone cannot yield a valid public permalink.

## Verification

- **All packaged test modules:** 58 modules from the exact clean-extracted final ZIP in twelve non-overlapping groups of five modules (last group three); 574 passed, 1 skipped, 0 failed. Group results: 32, 31, 26, 33, 44, 34, 50, 86 + 1 skipped, 35, 32, 40, and 131 passed respectively. The skip is `test_release_contracts.py:375`, which requires a historical A51 runtime log not present in this source package.
- **Focused Micro/digest tests:** 25 passed, 0 failed after the final digest-compaction repair.
- **Compilation:** compileall and explicit `py_compile` for all 73 packaged Python files.
- **ZIP verification:** exact 99/99 manifest inventory, 99 unique archive paths, CRC clean, 98/98 non-self SHA-256 entries match `A66_SHA256SUMS.txt` (the checksum file intentionally does not hash itself).
- **Clean-extract `--validate-only`:** pass, exit code 0; `bot_started=false`, `live_threads=[]`. No live exchange or Telegram integrations are started by this validation.

## Operational recommendation

Keep A77 in `MONITOR_ONLY_NO_NEW_BUYS`. Confirm the Telegram bot token/chat ID and, if a clickable Telegram public link is required inside every alert, configure a public channel/bot URL or username. A durable enqueue is not proof that Telegram delivered the message to the client; monitor delivery acknowledgements and pending outbox counts in runtime logs. Evaluate virtual Micro net outcomes over a meaningful sample before considering any change to live authority.

## A78 — supplied-log diagnosis and applied Micro corrections (2026-11-18)

### Supplied log findings

The supplied `Untitled (2).txt` was parsed by unique Signal ID to avoid counting repeated Telegram copies as independent observations. It contains 193 initial Micro alert blocks but **190 unique signal IDs**. Among those unique IDs, 134 were labelled economically viable under the old modeled-cost gate and 56 were explicitly labelled `TECHNICAL PATTERN ONLY — cost gate not met`; nevertheless, the latter were also sent as initial alerts.

There are **184 unique result IDs** in the supplied log: 49 TP, 104 SL and 31 TIMEOUT. Eight of the 190 initial IDs have no result notice in the captured text; two result IDs have no initial alert in this captured text (their initial message may predate the excerpt). Repeated result messages were deduplicated by ID. Among outcomes with an unambiguous TP/SL result, TP share was 49 / (49 + 104) = **32.0%**; this is a historical Shadow alert statistic, not an exchange win rate.

| Strategy | Unique initial alerts | Resolved IDs | TP | SL | Timeout | TP share among TP/SL | Average modeled net R | Average modeled net % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MICRO_MOMENTUM_1M | 79 | 74 | 21 | 30 | 23 | 41.2% | -1.132R | -0.423% |
| MICRO_SWEEP_RECLAIM_1M | 69 | 68 | 22 | 40 | 6 | 35.5% | -2.000R | -0.456% |
| MICRO_PULLBACK_RECLAIM_1M | 42 | 40 | 6 | 32 | 2 | 15.8% | -2.912R | -0.696% |
| **Total** | **190** | **184** | **49** | **104** | **31** | **32.0%** | **-1.870R** | **-0.507%** |

The averages above are across resolved virtual samples; the summed percentages/R are not a compounded portfolio backtest. Multiple patterns can overlap on the same symbol and market move. Timeout is kept separate from TP and SL. The file also includes at least one TP that remained net-negative after modeled costs, demonstrating why price touching target is not enough to call the idea economically successful.

The clearest weaknesses are (1) the Pullback detector's 6 TP versus 32 SL, (2) alerts sent despite explicit failure of the old cost gate, and (3) the 1m signal lane's insufficient higher-timeframe confirmation. Several failures occurred within 1–4 bars, consistent with early one-minute false breaks/reclaims. Successful examples generally needed more bars to reach target. The log does not provide an independent out-of-sample period or actual fill records, so it cannot prove that any one indicator/filter will raise real-world profitability.

The same log shows a separate canonical pipeline bottleneck: 30-minute windows with many DISC/RANK/PRE candidates but PASS=0, primarily `family_regime_disallowed.macro` for PULLBACK/BREAKOUT_CONTINUATION under BEARISH BTC (`allow=BULLISH+NEUTRAL`). This is not the Micro alert outbox. The bearish family restriction must not be weakened merely to increase candidate count; the canonical entry policy remains monitor-only.

### A78 source changes

- Micro sample persistence remains independent from notification. Every detected setup can continue contributing to Shadow results, even when it is ineligible for Telegram.
- A Telegram initial alert now requires observed positive BBO spread. Missing/non-positive spread receives the configured fallback cost and cannot qualify as observed spread.
- The default alert gate requires all-in modeled round-trip cost <=0.50%, modeled net target >=0.15%, modeled net reward >=0.75R, closed 5m/15m trend confirmation, positive configured BTC-relative 15m strength, adequate history, aligned latest candle times, and no recent MTF history gap.
- `MICRO_PULLBACK_RECLAIM_1M` is retained in research but its initial Telegram alert is paused by default pending a larger holdout sample.
- Strategy reports now expose Micro alert eligibility/suppression totals and reasons. Telegram initial alerts now include observed spread and MTF/BTC-relative evidence.
- `.env.example` and the runtime environment parser expose A78 quality controls. Existing alert/outcome persistence and Telegram public-link contract remain unchanged.

### Validation limits

All changes remain `MONITOR_ONLY_NO_NEW_BUYS`; the Micro module still has no order API and `V702_INTRADAY_SHADOW_LIVE_ENABLE` remains hard false. The thresholds are conservative screening assumptions, not a claim of a guaranteed increase in TP rate. Only a fresh Shadow holdout with sufficient independent samples can determine whether performance improved. Full test, compile, manifest and archive results are updated in `FINAL_MANIFEST.json` after release validation.

### A78 automated test checkpoint

- Focused Micro + shared cost-model tests: **36 passed, 0 failed**.
- Full repository test suite before release-hash synchronization: **575 passed, 1 skipped, 5 failed**; all five failures were the expected canonical-source digest mismatch caused by modifying `main.py` while the old release manifests still contained the A77 digest. No strategy/runtime test failed.
- **Full repository suite after canonical digest synchronization:** **580 passed, 1 skipped, 0 failed** across 12 non-overlapping batches. Batch pass counts: 32, 31, 26, 33, 44, 34, 50, 86 (+1 skip), 35, 32, 40, and 137. The single skip is `test_release_contracts.py:375`, which requires a historical A51 runtime log not shipped in the clean source release.
- **Compilation:** `python -m compileall -q .` passed.
- **Entrypoint validation:** `python main.py --validate-only` passed with exit code 0, `bot_started=false`, and `live_threads=[]`. No exchange or Telegram credentials were present in the validation environment and no live order was submitted.
- **Packaging:** the final archive is checked against the 99-path manifest, with unique paths and a clean ZIP CRC; it is then extracted separately and `--validate-only` is repeated from that clean extraction.

## A79 — All-strategy research recall, Swing coverage and final safety audit (2026-11-18)

### Supplied latest-log findings

- BTC descriptive macro remained `BEARISH` (1H close 64,680.31 below EMA50 64,719.39; 4H close 64,878.96 below EMA50 68,021.34 and EMA200 75,202.58). The ordinary candidate policy remained separately reported as `NEUTRAL` in the supplied digest; these are distinct state models and must not be merged.
- Universe was READY at 48 symbols, but the Hunter frequently scanned only 15 symbols and created zero new rows. MTF D1 fetch coverage of 15/15 proves that D1 requests completed for that limited cohort, not that the full 48-symbol universe received Swing setup evaluation.
- The canonical 30-minute funnel showed DISC/RANK/PRE activity but PASS=0, with policy rejects dominating (`family_regime_disallowed.macro`, particularly `PULLBACK@BEARISH[allow=BULLISH+NEUTRAL]`). This is expected family-policy behavior under the supplied bearish context, not evidence that the canonical policy should be bypassed.
- The supplied daily research report showed zero signals for each of the five A9 strategies in the reported window. This could reflect both market conditions and bounded symbol coverage; the log alone cannot prove that market-data coverage was the only cause.

### Implemented changes

1. **Fair-rotated supplement:** each scan cycle selects up to eight additional liquid USDT symbols not already in the canonical scan map, using quote-volume checks, stable/forbidden-asset exclusion, active-Swing follow-up priority and deterministic round-robin rotation. Reads are bounded by concurrency=8 and an 11-second cycle budget.
2. **Separate data authority:** the new `_a79_research_market_data_map` is a copy of the canonical map plus supplemental snapshots. It is used only by the read-only Hunter and A9 research. GlobalOpportunityBrain continues to receive the original `market_data_map` unchanged; no supplement can become a canonical candidate or execution route by being scanned.
3. **All five research engines:** supplemental 5m/15m/1H/4H contexts are shared across Micro Momentum, Sweep/Reclaim, Pullback/Reclaim, VWAP Reclaim RS and Adaptive RS Pullback. Existing 1m retrieval remains bounded to the A9 fair-rotating batch.
4. **Five Swing families:** added closed-1H/4H breakout continuation, breakout retest, pre-breakout compression WATCH, pullback/reclaim and relative-strength/recovery. Incomplete patterns persist as WATCH; Telegram's existing confirmed-only and A74 strong-quality gate is retained.
5. **Bearish BTC handling:** discovery of local recovery/relative-strength leaders remains enabled, but confirmed Swing longs under a descriptive bearish BTC regime require closed local 1H/4H uptrend plus minimum absolute return and BTC-relative outperformance. Otherwise the idea stays WATCH. No canonical family policy, crash severity, PreQual, score, risk, spread, cost or PreSend gate was bypassed.
6. **Correct outcome timeframe:** every Swing read-only setup is explicitly stamped `strategy_style=SWING`, `timeframe=1H+4H`, `outcome_interval_sec=3600`; outcome checks therefore use closed 1H candles instead of default intraday 5m.
7. **Risk references:** Swing structural invalidation uses a bounded 0.35%-4.0% reference risk geometry, and research target references are 1.8R/2.8R/4.0R. Existing A74 market-quality, spread, volume and net-cost checks remain responsible for strong-alert eligibility; these levels are not live orders.
8. **Digest truth:** the descriptive BTC macro field now reads the stored macro-context regime, while candidate policy remains a separate field. `/digest` also exposes supplemental scan coverage, Swing WATCH/CONFIRMED funnel and per-engine A9 evaluation/signal/rejection counts.

### Safety and limits

- Entry policy remains `MONITOR_ONLY_NO_NEW_BUYS`; `OpportunityHunter.execution_authority` remains false.
- Research snapshots are excluded from the canonical MSE map. A79 adds no order methods or route handoff.
- `WATCH` does not mean a buy opportunity or Telegram confirmed alert. Strong confirmed alerts still depend on A74 quality checks and existing alert state rules.
- The supplied logs do not prove live profitability. The new coverage can increase the number of evaluated symbols and visible WATCH setups; it cannot guarantee additional TP hits or a higher win rate. New outcomes must be assessed on a separate Shadow holdout with fees/spread/slippage modelled consistently.
- Network/API behavior, exchange-specific rate limits, real MEXC fills and external Telegram delivery are not validated by offline unit tests.


### A79 final verification (clean source tree)

- **Regression suite:** 58 packaged test modules, run in eight non-overlapping groups; **585 passed, 1 skipped, 0 failed** (586 collected). Group pass counts were 53, 40, 61, 55, 109 (+1 skip), 53, 45 and 169. The single skip is `test_release_contracts.py:375`, which requires the historical A51 runtime log not included in this release.
- **A79-specific regressions:** 5 passed, covering supplemental-pool exclusions, fair rotation and active Swing priority, structural-stop bounds, hourly outcome metadata, read-only invariants, and bearish-BTC Swing demotion to WATCH without measured local/relative-strength confirmation.
- **Digest/A51 compatibility regression group:** 8 passed; the A51 policy-prefilter telemetry line remains visible under compacted Telegram digest budgets alongside the A79 coverage lines.
- **Compilation:** `python -m compileall -q .` and explicit `py_compile` for `main.py` and `v702_intraday_shadow.py` passed; 73 Python source files are packaged.
- **Validate-only:** `python main.py --validate-only` exited 0; the final log states `bot_started=false` and `live_threads=[]`. The command used an isolated temporary database; it did not start the bot or live exchange/Telegram workers.
- **Release integrity:** rebuilt ZIP contains the exact 99 paths from the supplied A78 archive; no paths added or removed. The SHA-256 ledger contains 98 non-self entries (the ledger does not hash itself). ZIP CRC and manifest inventory are checked after creation.
- **Execution safety:** `MONITOR_ONLY_NO_NEW_BUYS`; Hunter execution authority false; no family-regime, PreQual, score, risk, spread, cost, PreSend, builder or order-routing bypass was introduced.

Offline tests and the supplied logs do not verify exchange fills, actual fee/slippage, external Telegram delivery, or profitable out-of-sample performance. A79 increases the research coverage and visibility of WATCH setups; a new holdout Shadow sample is required to determine whether the proportion and net value of TP outcomes improve.


# A80 — Telegram /status, verified polling and expanded Spot research coverage (2026-11-18)

## New findings from the user's Railway and Telegram logs

- The user-visible `/status` response came from the A75 command wrapper: in MONITOR_ONLY it only allowed `/help`, `/ping`, `/digest`, and `/opportunities`, while `/status` fell through to the private-account command gate. The credentials may be present; the response is a command allowlist behavior, not proof of missing Telegram variables.
- Earlier Railway lines showed `webhook clear failed`, `getMe failed: Telegram API unreachable`, and `synchronous bootstrap_ready=False`, followed by an unconditional `command control ACTIVE` log. That ACTIVE log was premature and did not prove `getUpdates` had succeeded.
- A79 digest showed `research_universe=46/47`, `base=13`, but `eligible=0`; the research universe builder had a broader quote-volume fallback than the supplement selector. The selector did not consume venue fields such as `volValue`, so its eligible pool could be empty despite populated turnover fields.
- In the same logs, `SWING funnel ... WATCH=3 CONFIRMED=0` and A9 engine telemetry showed engines were evaluated, but most candidates were rejected by explicit closed-candle/macro/relative-strength/EMA/volume conditions. Those are not evidence that the engines were disabled.

## Implemented A80 changes

1. `/status` is now explicitly whitelisted in monitor-only and handled as a read-only digest/status response. It shows inbound poll state, bootstrap state, last API method/status/error, last successful poll timestamp, last send ACK/error and the current entry policy.
2. Telegram inbound and outbound status are separated. Polling requires `getMe` plus successful `deleteWebhook`; startup `sendMessage` failure is recorded as outbound-degraded but does not block `getUpdates` or `/status`. `ACTIVE` is logged only after a successful `getUpdates` response. A 409 conflict suspends polling and leaves an explicit conflict state instead of retrying indefinitely.
3. `TelegramDispatcher._send_one` records ACK, failure, HTTP code and timestamp, and logs network errors as warnings instead of hiding them at debug level.
4. The supplement pool now uses `_v702_a80_ticker_quote_volume` consistently, including `volValue` and other venue turnover fields.
5. The read-only Spot/USDT research universe is capped at 500 markets with a 250k USDT turnover floor. Up to 32 new symbols are fetched per cycle with 16-way concurrency and a 30-second bounded budget, fairly rotated with priority for active Swing follow-up. The canonical core liquidity floor (3M USDT) and canonical market-data map are preserved. The A9 rotating research sample is capped at 32 and its research-only turnover floor is 500k USDT.
6. Opportunity alerts that have already passed existing canonical technical/quality/cost gates are no longer suppressed solely because the account entry policy is MONITOR_ONLY; alerts confer no order authority.

## A80 verification

- Focused A80 regressions: 14/14 passed; A80 in-process self-test: 10/10 passed.
- Full repository regression validation: 594 passed, 1 skipped, 0 failed across 58 packaged test modules (595 collected). All test modules were completed in non-overlapping groups; the time-heavy A58 AST regression was run separately and passed. The only skip is `test_release_contracts.py:375`, which requires a historical A51 runtime log not shipped in the clean source release.
- `python -m compileall -q .` and explicit `py_compile` for 73/73 Python sources passed.
- `python main.py --validate-only` exited 0 with `bot_started=false` and `live_threads=[]`, using an isolated temporary database.

## Scope and limits

- The supplemental universe is research coverage only; it does not enter the canonical MSE, candidate selector, PreQual, Builder, PreSend, queue or exchange order paths.
- The 500-market limit is a ceiling, not a per-cycle OHLCV fetch count. Up to 32 supplemental symbols are fetched per cycle with fair rotation to respect public API/rate limits. Coverage and failures are logged; not every listing is evaluated simultaneously.
- No live MEXC authenticated account, real exchange order or continuous Telegram delivery/soak test was performed from this audit environment. The user subsequently supplied the actual Telegram `/status` response received in the Railway chat; that is evidence of at least one successful command-response round trip, but it does not establish long-term delivery reliability or successful opportunity-alert delivery.
- The work expands scanning and improves command observability; it does not prove an increase in TP rate or positive out-of-sample PnL. All results remain Shadow/monitor-only.
- `MONITOR_ONLY_NO_NEW_BUYS` remains active; `OpportunityHunter.execution_authority=False`; hard-gate bypass and live-gate relaxation remain false.


## A80 final release verification

- Final artifact: `FINAL_PRODUCTION_RELEASE_A80.zip`; exactly 99 unique file paths, matching the supplied A79 archive inventory with zero files added or removed. ZIP CRC validation passed after clean extraction.
- SHA-256 ledger: 98/98 packaged non-self files verified; the ledger does not hash itself. `main.py` SHA-256: `dfa0f819f8dee801c56af0f65ddafc7e66f7b07223ad0c07d897e193c187d427`.
- Test collection: 595 tests across 58 modules; grouped execution plus the separately executed A58 AST regression: **594 passed, 1 skipped, 0 failed**. The single skipped historical A51 fixture is absent from the clean release package.
- A80-specific regression tests: 14/14 passed; A80 runtime self-test: 10/10 passed. Python compile checks: 73/73. Validate-only: exit 0, `bot_started=false`, `live_threads=[]`.
- A user-supplied Telegram `/status` reply confirms at least one successful command-response round trip; continuous Telegram alert delivery, Railway network stability, authenticated MEXC calls, live orders/fills, and out-of-sample profitability were not tested in this offline audit. `MONITOR_ONLY_NO_NEW_BUYS` remains enforced; no live order authority was added.
- Research scope is capped at 500 active Spot/USDT markets with at least 250,000 USDT quote turnover, up to 32 supplemental symbols per cycle, 16-way concurrency and a 30-second fetch budget. This is a rotating research ceiling, not a promise to fetch 500 markets each cycle. The canonical core 3M USDT liquidity requirement and canonical order-selection path remain unchanged.


## A81 — final audit and targeted production patch (2026-11-18)

### Scope and source evidence

- Audited the supplied `FINAL_PRODUCTION_RELEASE_A80.zip` archive: 99 unique files; ZIP CRC check passed; no packaged runtime logs were present, so operational-log interpretation below is based only on the three digest snapshots supplied in the user prompt.
- Python source inventory: 73 `.py` files. Compilation check passed before and after the A81 source change. The canonical source is a large `main.py` monolith (~107k lines) with historical/versioned wrappers and repeated assignment layers. A full structural decomposition was not attempted: doing so under an offline constrained audit would risk altering the canonical runtime and invalidating its extensive backward-compatibility contracts.
- The archive has 18 registered core strategy engines whose `enabled()` checks returned true. This proves registration/configuration only; it does not prove that each strategy generated a qualified signal or has positive expectancy.

### Findings and changes

1. **A81 defect fixed — A79 config was parsed but not honored by its execution lane.** The supplement hard-coded 250,000 USDT minimum quote volume, concurrency 16, and 30-second budget rather than using the declared A79 settings. The loop now honors configured minimum (not below the pre-existing 250,000 research floor), concurrency bounded to 1–16, and time budget bounded to 3–30 seconds.
2. **A81 defect fixed — A9 research settings were not loaded into `CONFIG`.** The declared intraday Shadow minimum quote volume and per-cycle symbol batch size now flow through the existing environment loader.
3. Added a regression test in the existing test module; no new file was added. The focused A80/A81 selection passed 10 tests.
4. The package identity and canonical safety policy are preserved. No strategy family regime allowlist, score threshold, spread/depth gate, stop-loss, position-sizing, pre-send, order-reconciliation, or execution gate was loosened. No live orders were sent.

### Liquidity finding — do not conflate research and tradable universes

- **Canonical core Spot/USDT scanner floor:** 3,000,000 USDT 24-hour quote turnover. Some strategy/tier policies require a higher tier (for example, the Large tier is 15,000,000 USDT).
- **A79 supplemental research floor:** 250,000 USDT; **A9 intraday Shadow floor:** 500,000 USDT. These are isolated research/shadow populations and cannot enter the canonical order route.
- Quote turnover is not order-book liquidity. The independent spread/depth controls still apply. The user-supplied digest includes a spread rejection of 0.5168% against a 0.300% ceiling. That is a valid rejection, not evidence that the spread gate should be lowered.

### Operational diagnosis from supplied digests

- `MONITOR_ONLY_NO_NEW_BUYS` is active, therefore the bot is intentionally not authorized to place new buys.
- The sampled bearish BTC regime, combined with `PULLBACK@BEARISH[allow=BULLISH+NEUTRAL]`, explains the repeated `family_regime_disallowed.macro` rejects. HTF strength rejects form a second major choke; spread rejection appears in another sample. These are upstream PreQual decisions. Since `PASS=0` and `SEL/Q/TG/EXEC=0`, the downstream queue, Telegram signal delivery, and execution stages are not being exercised by these cycles; this is not enough evidence to diagnose them as broken.
- Universe is reported READY and market data is reported ready; A51 prefilter errors and observed event-buffer/backpressure drops are zero in the supplied digest. No measured queue or event-retention bottleneck is shown in that sample.
- All 18 core strategy engines report enabled in code, but the log evidence is not enough to claim all 18 have successfully generated signals. The A9 log counts show evaluation and a small number of Micro shadow signals; these lanes are read-only. `VWAP_RECLAIM_RS_5M` and `ADAPTIVE_RS_PULLBACK_15M` had zero signals in the displayed sample, not zero evaluations. Swing hunter produced no confirmed candidate in the sample.

### Verification boundary

- A81 targeted regression: **10 passed** for tests selected by `-k 'a80 or a81'`.
- `python main.py --validate-only`: exit 0, `bot_started=false`, no live worker threads; internal A79/A80 self-tests passed. This is offline validation, not an authenticated MEXC/Telegram test.
- `compileall` and explicit `py_compile` passed 73/73. The complete collected test set was run in groups; see the final A81 verification block below.
- No authenticated exchange access, Telegram network delivery, real order placement, target-platform Python/Docker memory soak, or profitability/backtest validation was performed. No daily-income claim is made.

### Architectural limitations retained

- The 100k+ line canonical runtime remains monolithic and has layered historical wrappers. A wholesale refactor was deliberately not performed because this package depends on versioned contracts and the supplied logs show a live-monitor-only state. The scoped A81 fixes avoid changing those contracts.
- `ccxt` and `aiosqlite` are not installed in the audit execution environment; dependency declarations exist in the package. Exchange-facing integration paths therefore remain unverified here.
- No files were added or removed; total package inventory remains 99.


### A81 final release verification

- Full grouped pytest run: **595 passed, 1 skipped, 0 failed** across **58 test modules** (**596 collected**). The only skip is `test_release_contracts.py:375`, because the immutable historical A51 validation log is intentionally absent from the clean source archive. The A81 environment-wiring regression is included in the 105-test `test_v702_production_audit_fixes.py` module; that module passed 105/105.
- Python compile verification: `compileall` passed and explicit `py_compile` passed **73/73** Python files.
- `python main.py --validate-only`: exit **0**; `bot_started=false`; `live_threads=[]`; internal validation reported PASS. This mode did not start the persistent bot and made no live trading/API requests.
- ZIP content inventory: exactly **99 files**, no additions/deletions relative to A80; archive CRC and manifest inventory verified after rebuild. SHA-256 ledger covers **98/98** other packaged files (the ledger does not hash itself).
- Import-time environment caveat: the audit container does not have `ccxt` or `aiosqlite` installed, although package dependencies are declared. Therefore direct exchange/SQLite integration paths, Docker build, authenticated MEXC/Telegram access, runtime memory soak, live fills, and profitability remain unverified. Install the declared dependencies in the target deployment before starting the service.


# A82 — Final production audit supplement (2026-11-18)

## Package and scope

- Source archive: the user-provided `FINAL_PRODUCTION_RELEASE.zip`. Original inventory: **99 files** (73 Python files, 58 test modules); final packaged top-level Python source total: **124,787 lines**. The source archive passed CRC validation before extraction.
- Final inventory: **99 files**, with **0 files added** and **0 files removed**. Existing source paths are retained; temporary caches, bytecode, runtime databases and local `.env` secrets are excluded from the release.
- This was a broad automated/static audit plus focused source review of the scan, research supplement, Swing Hunter, digest, candidate policy and execution-safety boundaries. The main source remains a large historical compatibility module; a wholesale decomposition was not attempted because it would risk changing the many pinned legacy interfaces and exceed the scope of a safe targeted closure. It is not represented as a manual line-by-line human review of every historical line.

## Findings and applied repairs

1. **Supplement exception under-reporting:** in the A79 outer exception handler, `attempted` could be populated before an exception, while `failed` remained the default zero. This made a state such as `attempted=32 / ok=0 / failed=0` ambiguous and could conceal a failed fetch cycle. The handler now reconciles `failed=max(previous_failed, attempted-ok)`, adds a failure stage, redacts credentials/URLs, and logs the safe diagnostic token.
2. **Supplement digest observability gap:** the digest previously omitted the outer error, timeout count and top fetch rejection reasons. It now surfaces those bounded fields alongside universe/base/eligible/attempted/ok/failed counts.
3. **Swing structure recall gap:** the A79 five-family Swing detector had no dedicated Higher-Low reclaim family. Added `SWING_HIGHER_LOW_RECLAIM` using confirmed closed-1H pivots. Early rising-low structures are WATCH-only; CONFIRMED needs higher-high reclaim, closed 1H/4H trend, volume/RSI checks and the existing bearish-BTC relative-strength rule. Structural stop risk remains bounded by the existing helper; invalid geometry suppresses this setup.

The supplied operator digest showed 229 candidates entering PreQual in its 30-minute window and zero passing, with macro family-policy rejects dominating. The policy is strategy-specific (`PULLBACK` not allowed under that bearish candidate policy) and is intentionally **not** weakened. The A82 Swing research lane is independent and cannot route candidates into canonical execution. The supplied Swing sample had 12 data rows and zero WATCH/CONFIRMED; the new family addresses one missing technical structure type but requires subsequent live Shadow evidence to show actual recall improvement.

### Defect count and exact source locations

- **Three code defects found and repaired:** (1) outer supplemental-fetch exception accounting could leave `failed=0` despite non-zero attempts; (2) the compact digest hid the outer error/timeout/rejection cause; (3) the A82 numeric pivot-threshold setting was documented but not consumed by the environment parser. The related regression coverage is in `test_v702_production_audit_fixes.py:1896-1973`.
- **One Swing discovery gap addressed:** no distinct Higher-Low / Higher-High reclaim family existed in the five-family A79 Hunter. The new structure logic is not labelled an old runtime exception; it is a deliberate research-coverage addition.
- Source map: `main.py:1317-1328` (float setting parsing); `main.py:27590-27597` (exception path); `main.py:105254-105264` (digest diagnostics); `main.py:106785-106805` (failure reconciliation and redaction); `main.py:106927-107015` (confirmed-pivot Higher-Low detection and candidate construction); `main.py:107360-107374` (A82 runtime identity).

**Counts:** 3 code defects detected / 3 repaired; 1 Swing structure coverage gap addressed; **9 existing files modified**, 0 deleted, 0 added. The 9 modified files are `main.py`, `test_v702_production_audit_fixes.py`, `.env.example`, `README.md`, `CHANGELOG.md`, `FINAL_AUDIT_REPORT.md`, `FINAL_MANIFEST.json`, `A66_RELEASE_MANIFEST.json`, and `A66_SHA256SUMS.txt`.

## Files modified

- `main.py` — Higher-Low structure family, supplemental failure reconciliation, bounded digest diagnostics, A82 runtime revision.
- `test_v702_production_audit_fixes.py` — three A82 regressions.
- `.env.example` — Higher-Low research switch and pivot threshold.
- `README.md` — A82 behavior, risk interpretation, and Google Colab steps.
- `CHANGELOG.md` — A82 change record.
- `FINAL_AUDIT_REPORT.md` — this report supplement.
- `FINAL_MANIFEST.json`, `A66_RELEASE_MANIFEST.json`, `A66_SHA256SUMS.txt` — canonical digest and release inventory metadata synchronization.

No files were deleted. No essential project module was merged or discarded.

## Verification

- Archive integrity before changes: `zipfile.testzip()` returned `None`; 99 unique file entries.
- Python compilation before the final A82 edits: 73/73 packaged Python files passed. A fresh full compile is required after this supplement and is included in the release verification record.
- Focused A82/A79 Swing tests: **5 passed**.
- Full `test_v702_production_audit_fixes.py`: **108 passed**.
- Historical test modules are being executed in non-overlapping batches to avoid the full-session timeout observed in the initial single-process run. The one release-hash mismatch observed during that staged run was expected before synchronizing the source digest in the manifests; no functional test failed in that batch. Final per-batch totals and any skips/failures are recorded after checksum synchronization.
- `python main.py --validate-only` passed on the source package before the A82 changes (exit 0, `bot_started=false`, `live_threads=[]`). It is re-run after the final source change.
- No MEXC authenticated account, live order, exchange fill, Telegram delivery ACK or profitability result was tested. Execution remains `MONITOR_ONLY_NO_NEW_BUYS`; no live trading was enabled.

## Swing invalidation: 4H versus 15m

For a multi-day Swing setup, use a structural 4H/1H pivot-low invalidation plus an ATR buffer. A 15m close below the level is generally too sensitive and will often turn normal intraday noise into a premature exit. For intraday trades, 15m/5m structure can be appropriate. A close-based invalidation is only the thesis rule: it does not protect against a sudden gap or wick before the next candle closes. In a live deployment, that risk requires a verified hard protective order on the venue or an explicitly accepted exposure policy; this monitor-only package places no exchange-side stop order.

## Google Colab quick start

```python
!unzip -q /content/FINAL_PRODUCTION_RELEASE.zip -d /content/unified_scalper
%cd /content/unified_scalper
!pip install -r requirements.txt
!python main.py --validate-only
```

For monitoring only, copy `.env.example` to `.env`; keep `UNIFIED_LIVE_PILOT_ENABLE=0`, `UNIFIED_A55_LIVE_ARM=0`, and `UNIFIED_MONITOR_ONLY_SCAN_ENABLE=1`. Do not supply private MEXC trading credentials for this dry-run/research audit. Optional Telegram credentials are only for notifications. Colab storage may be ephemeral, so persistent SQLite storage needs an intentionally mounted path.

## Final release artifact verification

- Built `/mnt/data/FINAL_PRODUCTION_RELEASE.zip` using the exact 99-path inventory from the source archive and final manifest; no caches or runtime state were added.
- Archive contains **99 unique files**; `ZipFile.testzip()` returned `None` (CRC pass); all 99 names match `FINAL_MANIFEST.json`; the final archive size is recorded in the delivery summary after packaging.
- All **98** entries in `A66_SHA256SUMS.txt` match their packaged files (the checksum file does not hash itself). `main.py` SHA-256 matches both release manifest source-digest fields.
- The release ZIP was extracted into a clean directory; the extracted inventory remained 99 files, `compileall` passed, and a clean-extract `python main.py --validate-only` exited 0 with `bot_started=false`, `live_threads=[]`, and no active environment aliases.

## Limitations

- Current sandbox did not have `ccxt` or `aiosqlite` installed at import-probe time; no dependency installation was assumed. The local `--validate-only` command is designed to remain runnable in validation mode. Full exchange integration and authenticated endpoint behavior remain unverified.
- The complete pytest suite exceeded the single-run time budget around 60%; all modules then completed successfully in twelve isolated batches, providing the final test result above.
- No historical OHLCV holdout/backtest was run for the new Higher-Low family. A82 increases pattern coverage, not proven expectancy. Do not promote WATCH alerts into trades based only on this implementation.

# A83 — USDC/USDT Shadow spread-capture lifecycle (2026-11-19)

## Implemented
- A separate read-only MEXC Spot Shadow task for the sole whitelisted pair `USDC/USDT`. `STABLECOIN_MM_ENABLE=0` by default; the only supported mode is `SHADOW`. A `LIVE_ARM` environment value is telemetry-only and cannot enable execution.
- Public CCXT order-book and trade-print polling, order-book integrity/depeg/spread/two-sided-depth/imbalance/flow filters, MEXC raw `isBuyerMaker` aggressor-side fallback when normalized `side` is unavailable, and bounded API timeout/error backoff.
- Simulated `BUY_PENDING` → `BUY_PARTIALLY_FILLED` → `SELL_PENDING` → `SELL_PARTIALLY_FILLED` → `CLOSED` lifecycle, with `EXPIRED_NO_FILL` for quotes that do not fill. A quote is not deemed filled by a price touch; public trade-print volume must first consume the estimated queue ahead and then reach the virtual order.
- SQLite persistence of active cycles and event history, restart recovery, daily aggregate queries and a date-idempotent daily-report marker.
- Telegram Outbox messages for quote creation, simulated buy/sell fills, completed cycles, API circuit pause and daily Shadow summary.
- Precision/minimum amount/minimum notional checks using market helpers before creating a virtual quote. One active cycle, virtual capital cap, reserve, daily completed-cycle cap, quote age and kill switch are enforced.
- No A83 code path calls `create_order`, `create_limit_buy_order`, `create_limit_sell_order` or another order-submission endpoint. The bot-wide policy remains `MONITOR_ONLY_NO_NEW_BUYS`.

## Cost model and fill limitations
- The default maker-fee assumption is the conservative configured fallback `0.001` (0.1%) per side. Public CCXT `market.maker` metadata is deliberately not used as proof of the account fee because it may be a generic exchange default. An explicit override (including zero) is only an operator-supplied assumption and requires independent verification of the exact account, pair and fee tier.
- Shadow PnL is `net_pnl_estimate_usdt`, not realized exchange PnL. It subtracts estimated maker fees and configured slippage. It does not use private fills, wallet deltas or account-specific fee records.
- Public L2 depth cannot reveal the matching engine's exact queue position, hidden liquidity, cancellations or priority changes. The queue-ahead multiplier is deliberately a conservative estimate, not proof of real fillability. Public prints at the limit or beyond are evidence for this simulator only.
- With the default 0.1% maker-fee fallback, round-trip modeled fees are 20 bps before slippage, while the default spread ceiling is 12 bps. Therefore the fail-closed default will not open Shadow quotes until the operator supplies a verified lower maker-fee assumption (for example zero only when the exact account/pair is confirmed). This is intentional; it prevents a generic public fee field from manufacturing a false edge. The engine does not promise 100 cycles per day, positive expectancy or any minimum realized return.

## Verification performed
- A83 deterministic tests: **10 passed**. Coverage includes microprice/spread/imbalance, invalid books, net cost checks, public-print queue consumption, quote filters, SQLite persistence and daily report idempotence, a no-order API assertion, and a complete simulated buy→sell→close cycle with positive estimated net PnL after modeled costs.
- `test_v702_production_audit_fixes.py`: **119 passed**.
- All **58 test modules** completed in 12 non-overlapping pytest batches: **609 passed, 1 skipped, 0 failed**. The one skip is the historical `test_release_contracts.py:375` case because the immutable A51 validation log is not part of the clean release archive.
- Python compilation: `compileall` passed; explicit `py_compile` passed **73/73** Python files.
- `python main.py --validate-only`: exit **0**, internal validation PASS, `bot_started=false`, `live_threads=[]`, `active_env_aliases=[]`.
- Original/final inventory comparison: **99 files**, **0 added**, **0 removed**. Nine existing files changed: `main.py`, `test_v702_production_audit_fixes.py`, `.env.example`, `README.md`, `CHANGELOG.md`, `FINAL_AUDIT_REPORT.md`, `FINAL_MANIFEST.json`, `A66_RELEASE_MANIFEST.json` and `A66_SHA256SUMS.txt`.

## Not verified / release limitations
- No authenticated MEXC account was used. No live MEXC market-data session, order, exchange fill, private fee query or Telegram delivery acknowledgement was performed from this environment.
- No historical replay, forward Shadow soak, account-tier fee confirmation, profitability/expectancy validation, Docker build or target-host load/memory test was performed. The deterministic fake exchange verifies code behavior only; it does not establish current exchange availability or profitability.
- Do not set `STABLECOIN_MM_ENABLE=1` until the operator has intentionally chosen to run the read-only Shadow monitor and configured persistent storage/Telegram as needed. This release does not authorize live stablecoin trading; any future live proposal requires a separate audited implementation and explicit release decision.


# A84 — A79 research scan NameError and Shadow market-data integrity closure (2026-11-19)

## Scope and evidence

The accompanying runtime digest repeatedly reported `A79_RESEARCH ... attempted=32 / ok=0 / failed=32` with `NameError:name__v702_monitor_only_scan_enabled_is_not_defined`. In the source, `_v702_a79_fetch_supplemental_snapshots` called `_v702_monitor_only_scan_enabled()`, but the only defined authority was `_v702_monitor_only_scan_authorized()`. The exception occurred before the supplemental OHLCV requests, so the extra A79 research coverage did not run. This did not disable the canonical scanner and did not grant or remove order authority.

The same log showed canonical candidate rejections dominated by `family_regime_disallowed.macro` for PULLBACK under `BTC=BEARISH`. That is consistent with the registered family policy (`PULLBACK@BEARISH[allow=BULLISH+NEUTRAL]`), not evidence of a broken selector. The release does not weaken this policy, HTF confirmation, liquidity, spread, cost, score, PreSend, execution or protection gates.

The 2026-11-18 Micro daily report in the supplied log recorded 26 Shadow signals, 23 resolved observations, 3 TP, 14 SL and 6 timeouts. Reported average modeled net returns were negative for MICRO_MOMENTUM_1M (-1.92R), MICRO_SWEEP_RECLAIM_1M (-2.16R), MICRO_PULLBACK_RECLAIM_1M (-1.83R), and VWAP_RECLAIM_RS_5M (-0.83R on one resolved observation). These are small, simulated samples, not realized account results; they do not justify enabling those patterns for live trading or claiming daily income.

## Applied source repairs

1. Replaced the undefined A79 helper call with `_v702_monitor_only_scan_authorized()`. The scan-disabled condition remains fail-closed, and enabled supplemental snapshots remain tagged `v702_a79_canonical_mse_eligible=False`.
2. Hardened A83 `microprice`, depth imbalance, spread and top-of-book validation against `NaN` and infinity.
3. Public trade-flow aggregation now ignores non-finite price/amount prints rather than counting them in signed flow.
4. A83 now rejects an order book without a valid exchange timestamp instead of assuming that an untimestamped snapshot is fresh.
5. A83 lifecycle fill processing now rejects non-finite prints and prints more than two seconds in the future relative to the current tick.
6. The virtual budget calculation clamps both capital and reserve to non-negative values before deriving the minimum required net-bps threshold.

## Opportunity and profitability decision

A79 supplemental research can again collect its bounded, fair-rotated 5m/15m/1H/4H evidence for read-only Swing and A9 analysis. It remains isolated from the canonical `market_data_map`; it cannot inject a candidate into selector, builder, queue or execution.

No additional strategy was promoted to trading. The supplied Micro Shadow results are negative, while the canonical core funnel is correctly rejecting strategies whose regime policy does not allow a bearish macro context. Increasing the number of alerts or weakening those policies would increase risk, not establish positive expectancy. The A83 stablecoin lane remains a Shadow simulator only. Its default 0.1% maker-fee fallback means modeled two-sided fees alone are 20 bps, above the configured 12 bps spread ceiling; a zero-fee override is only an operator assumption after confirming the actual account/pair fee schedule. The code does not verify that fee schedule or submit exchange orders.

## Files changed

- `main.py` — A79 authority-name correction and A83 input/freshness/fill integrity checks.
- `test_v702_production_audit_fixes.py` — six focused regression tests for A79 and A83.
- `README.md`, `CHANGELOG.md`, `FINAL_AUDIT_REPORT.md` — release and operational documentation.
- `FINAL_MANIFEST.json`, `A66_RELEASE_MANIFEST.json` — synchronized canonical source SHA-256 fields and A84 metadata.

No files were added to or removed from the archive. The supplied inventory was already exactly 99 files.

## Verification and limitations

- Python compilation: 73/73 packaged Python files passed `compileall`; edited Python files also passed `py_compile`.
- Focused A79/A83 tests: 21 passed, 0 failed.
- `python main.py --validate-only`: exit 0; final output showed `bot_started=false` and `live_threads=[]`.
- The full 58-module regression suite was run in six non-overlapping groups: **615 passed, 1 skipped, 0 failed**. Group pass counts: 63, 59, 78, 136 (+1 historical skip), 67, and 212. Five intermediate failures were stale source-digest assertions after the source patch; the canonical digest fields were synchronized and all affected groups were rerun successfully.
- No authenticated MEXC call, live order, real wallet access, or external Telegram delivery was attempted. This environment did not have `ccxt` or `aiosqlite` installed during the import probe. Synthetic lifecycle tests do not verify fills, fees, slippage, profitability, or 24/7 uptime.
- `main.py` remains a large canonical runtime module (108,000+ lines). A wholesale split/refactor was not attempted because it would alter the established import/runtime contract and materially increase regression risk in a 99-file release. The patch is targeted rather than a claim that every historical code path has been exhaustively reviewed line-by-line.



# A85 — تقرير تنفيذ Market Intelligence & Visual Analyst (2026-11-20)

## نطاق الدمج داخل المصدر الأصلي

تم دمج طبقة `A85MarketIntelligence` داخل `main.py`، مع الحفاظ على مخزون الملفات الأصلي البالغ 99 ملفًا وعدم حذف أي مسار. تعمل الطبقة بعد مسح Opportunity Hunter وتستهلك خريطة A79/A80 المشتركة ولقطة Ticker الموجودة، دون بناء عميل OHLCV موازٍ أو إرسال أوامر أو حقن مرشحين في Global Selector.

### الوحدات المدمجة

1. **الرادار المتدرج:** إحصاءات سريعة من لقطة Ticker المشتركة، ثم قائمة وسيطة 100–150 زوجًا وفق بيانات الحجم المتاحة، ثم تحليل شموع عميق افتراضيًا لـ60 زوجًا كحد أقصى في الدورة. حد 500 هو سقف سوق البحث A80 وليس ادعاء تحليل 500 شمعة في كل دورة. يستخدم الرادار دورانًا محفوظًا في SQLite ويخصص نصف الميزانية على الأقل للتدوير العادل.
2. **السياق العام:** BTC على شموع مغلقة 1D/4H/1H/15M عند توفرها، ETH 1H والقوة النسبية، وتصنيف BULLISH/BEARISH/NEUTRAL/HIGH_VOLATILITY/RANGE_BOUND/RECOVERY/DISTRIBUTION أو UNKNOWN. Breadth هو عينة من خريطة البيانات الحالية، وليس إحصاءً مؤكدًا لكل السوق.
3. **التحليل الفني:** 1D/4H/1H/15M/5M/1M، EMA 9/20/50/100/200، RSI، MACD، ATR، Bollinger، VWAP، Relative Volume، نماذج شموع، Swing/Pivots، HH/HL/LH/LL، BOS/CHoCH، Liquidity Sweep، Equal High/Low، FVG/OB proxies، دعم/مقاومة مجمّع وFibonacci. Volume Profile هو تقريب من Typical Price وOHLCV volume وليس تدفق صفقات كاملًا.
4. **تدوير القطاعات:** خريطة رموز ثابتة ومحددة للقطاعات المعروفة فقط، تقيس عائد/اتساع العينات المؤهلة. الحالة دائمًا جزئية (`PARTIAL_STATIC_TAXONOMY`) ولا تُسند العملات غير المعروفة إلى قطاعات.
5. **Consensus والترتيب:** تجميع عائلات Opportunity Hunter المنشورة، إزالة التكرارات داخل العائلة، رفض الدليل القديم، وإظهار الاستراتيجية الأساسية والداعمة والتعارض. يحتفظ Router ذي الكواشف التسعة بسلطته الأصلية؛ طبقة A85 لا تعيد تشغيل كل محرك خام ولا تستبدل Global Selector. فصل درجات Signal Quality وExecution Quality وData Confidence وRanking؛ لا توجد Win Probability مخترعة.
6. **خطة الصفقة:** Ask كمرجع شراء، Entry Zone وPreferred Entry وChase Limit وExpiry، وقف هيكلي/ATR، أهداف مرتبة من المقاومة/امتداد Fibonacci أو مضاعفات R محافظة، شروط إبطال، تقدير مدة إرشادي، وحساب تكلفة جانبي الرسوم والسبريد والانزلاق وصافي العائد وRR وربح USDT على حجم افتراضي إعداداتي. `READY_NOW` يتطلب تأكيد شموع 15M/5M وتأكيد 1M إذا كانت بياناته متاحة، ودفترًا حديثًا وعمقًا كافيًا وسبريدًا وجدوى صافية. ذلك تصنيف تحليلي لا أمر تداول.
7. **الرسم:** Matplotlib Agg ينشئ PNG فعلية 1H و15M بعناصر الشموع والمتوسطات وVWAP/BB والدعم/المقاومة وFVG/OB proxy والـSwing وBOS/CHoCH والـSweeps وFib وPOC التقريبي والحجم ومناطق Entry/SL/TP والطوابع الزمنية. يستخدم Telegram `sendPhoto` عند توافر إعدادات الاتصال، ويسجل الفشل بدل الادعاء بالإرسال.
8. **Telegram:** أوامر قراءة فقط `/market` و`/top` و`/ready` و`/waiting` و`/analyze` و`/chart` و`/portfolio` و`/strategies` و`/performance` و`/regime` و`/help` مدمجة في المعالج الأصلي. لا يوجد Monkey Patch جديد، وتبقى أوامر الإدارة والحماية السابقة في المعالج نفسه.
9. **الأداء والبحث:** مؤشرات Shadow مأخوذة من سجل Opportunity Hunter فقط، بحد أدنى 30 عينة، وفصل زمني Holdout عند كفاية العينة، وبدون تعديل تلقائي للأوزان أو حواجز المخاطر. تم تصحيح حساب Max Drawdown ليحسب النتائج زمنيًا من الأقدم إلى الأحدث.
10. **الرصد والميزانية:** يعرض ملخص A79/A80 عدد المحاولات والنجاحات والإخفاقات والمهل وأسباب الرفض؛ يميز أعداد Fast/Intermediate/Deep؛ يتعامل مع حالة BTC المفقودة كـUNKNOWN؛ ويعرض أعلى فرصة أولًا داخل الحالة نفسها.

## ملفات التعديل

التعديل محصور في الملفات الموجودة مسبقًا: `main.py`، `test_release_contracts.py`، `.env.example`، `requirements.in`، `requirements-lock.txt`، `LOCKFILE_NOTES.md`، `README.md`، `CHANGELOG.md`، `FINAL_AUDIT_REPORT.md`، `FINAL_MANIFEST.json`، `A66_RELEASE_MANIFEST.json`، `A66_SHA256SUMS.txt`. لا ملف مضاف ولا ملف محذوف؛ العدد المستهدف 99 بالضبط.

## حدود صريحة لم تدّع هذه الحزمة تجاوزها

- لا يوجد مزود موثوق مهيأ لـTotal Market Cap أو BTC Dominance أو OI/Funding/Liquidations أو CVD؛ هذه الحقول تبقى `UNAVAILABLE`.
- القطاع مبني على تصنيف رموز ثابت جزئي، وليس Taxonomy موثقًا لكل العملات.
- Consensus يجمع سجل عائلات Opportunity Hunter ولا يستدعي كل محرك خام بصورة مستقلة؛ Router الأصلي يظل سلطة المرشح الأساسية.
- بيانات Public L2 لا تكشف ترتيب Queue الحقيقي أو السيولة المخفية. مدة الصفقة تقدير إرشادي وليست نموذجًا معايرًا.
- نتائج الأداء Shadow فقط وليست صفقات منفذة أو أرباح حساب. لا يوجد إثبات ربحية.
- لم يُستخدم حساب MEXC حقيقي، ولم يُرسل أمر تداول، ولم يُتحقق من رسوم الحساب الخاصة. اختبار Telegram الحقيقي وDocker وRailway/Render والحمل المستمر لم يُنفذ في هذه البيئة.

## وضع الأمان

`UNIFIED_LIVE_PILOT_ENABLE=0`، و`UNIFIED_A55_LIVE_ARM=0`، والسياسة `MONITOR_ONLY_NO_NEW_BUYS`. A85 سلطاته الثلاث (Selector/Order/Execution) false. A83 يبقى محفوظًا لكنه `STABLECOIN_MM_ENABLE=0` افتراضيًا و`MODE=SHADOW` و`LIVE_ARM=0`. لا يخفف A85 حد السيولة الأساسي 3M USDT أو بوابات السبريد والرسوم والمخاطرة والحماية.

## الاختبارات

تُدرج الأعداد النهائية بعد تشغيل الاختبارات على النسخة المستخرجة من ZIP النهائي. لم تُسجل نتيجة شبكة MEXC أو Telegram حقيقية باعتبارها PASS.



# A85 — الإغلاق النهائي للاختبارات والإصدار (2026-11-20)

هذه الفقرة هي سجل الإغلاق الحالي وتَسود على أعداد الاختبارات التاريخية المذكورة في أقسام A80–A84 السابقة.

## النتائج النهائية الفعلية

- مجموعة Regression الكاملة: **58 وحدة اختبار، 5 دفعات مستقلة، 642 اختبارًا جُمعت؛ 641 ناجحًا، اختبار واحد متخطّى، صفر إخفاقات**. أعداد النجاح بالدفعات: 70، 84، 97، 157، 233. استُخدم مسار SQLite مستقل (`SCALPER_DB`) لكل دفعة لمنع تداخل حالة الاختبار. لا يُدّعى اكتمال تشغيل واحد مشترك لكل الاختبارات؛ الإغلاق مبني على الدفعات المنفصلة الناجحة.
- اختبارات A85 المركزة: **22 ناجحًا، صفر إخفاقات**.
- `test_release_contracts.py`: **66 ناجحًا، اختبار تاريخي واحد متخطّى، صفر إخفاقات**. سبب التخطي أن الاختبار يحتاج سجل A51 تاريخيًا غير مضمن في حزمة الإصدار النظيفة.
- `compileall` و`py_compile`: **73/73 ملف Python**.
- `python main.py --validate-only`: exit 0، و`bot_started=false`، و`live_threads=[]`، ولا صلاحية تداول حقيقي.
- ملف الأرشيف النهائي: 99 ملفًا بالضبط، 0 ملفات مضافة، 0 ملفات محذوفة، 12 ملفًا أصليًا معدّلًا. سجل SHA-256 الداخلي يحتوي 98 بصمة للملفات عدا ملف سجل البصمات نفسه.

## قائمة الملفات المعدلة

`main.py`، `test_release_contracts.py`، `.env.example`، `requirements.in`، `requirements-lock.txt`، `LOCKFILE_NOTES.md`، `README.md`، `CHANGELOG.md`، `FINAL_AUDIT_REPORT.md`، `FINAL_MANIFEST.json`، `A66_RELEASE_MANIFEST.json`، `A66_SHA256SUMS.txt`.

## صلاحيات وأمور لم تُختبر خارجيًا

`UNIFIED_LIVE_PILOT_ENABLE=0`، `UNIFIED_A55_LIVE_ARM=0`، و`MONITOR_ONLY_NO_NEW_BUYS`. A85 لا يملك سلطة Selector أو Order أو Execution. A83 محفوظ لكنه معطل افتراضيًا ويظل Shadow فقط عند تفعيله يدويًا. لم يُستخدم حساب MEXC حقيقي، ولم يُرسل أمر أو يُتحقق من Fill أو الرسوم الخاصة بالحساب؛ لم يتم اختبار تسليم Telegram الفعلي أو بناء Docker على منصة الاستهداف أو حمل Railway/Render أو تشغيل طويل. لا توجد نتيجة تثبت ربحية أو دخلًا يوميًا. الاعتماد `matplotlib==3.10.8` مثبت مباشرةً، لكن `requirements-lock.txt` هو direct-pin seed وليس lock كاملًا transitive/hash؛ لم يُختلق Hash ولم يُدّعَ بناء strict lock.

# A85 final diagnostic closure — authoritative test results (2026-11-20)

This section supersedes earlier A85 test totals and pending-status notes above.

## Last-mile diagnostic fixes

- `/market` now shows `A85 intermediate deep fetch selected/ok/failed` plus the actual shared A79 4-timeframe budget scope. This closes the observability gap where the daily Micro report showed zero signals but the operator could not distinguish no evaluations from failed/missing deep-fetch coverage.
- `/market` includes BTC context reason, data confidence and separate closed 1H/4H candle-open timestamps where available. Numeric close equality is not used as a timeframe-collision test.
- Legacy timestamp-less DataFrames retain their historical descriptive EMA regime for compatibility, but are labelled `UNKNOWN_LEGACY_NO_TIMESTAMPS`; they are not represented as verified timeframe cadence. Shared frame references and invalid/stale timestamped frames remain rejected for integrity validation.
- Telegram regression coverage verifies the actual `/market` response text contains A85 deep-fetch counts, BTC context reason/confidence and separate 1H/4H timestamps.

## Final test closure

- All packaged test modules: **58 modules, 12 isolated runs, 647 collected, 646 passed, 1 skipped, 0 failed**. Per-run pass counts: **70, 31, 86, 102, 6, 6, 9, 12, 29, 34, 28, 233**. Each pytest process ran with an isolated `SCALPER_DB` to prevent SQLite state sharing between test groups.
- `test_release_contracts.py`: **70 passed, 1 skipped, 0 failed**. The skip requires a historical A51 runtime log that is not packaged.
- `test_v702_intraday_shadow.py`: **31 passed, 0 failed**.
- Focused A85 and BTC timeframe regressions: **26 passed, 0 failed**.
- Daily Micro diagnostic tests: **2 passed, 0 failed** (included in the full regression totals; do not add them again).
- `py_compile` / `compileall`: **73/73 Python files passed**.
- `--validate-only` from the clean extracted release: exit code 0, `bot_started=false`, `live_threads=[]`.
- Archive inventory: exactly **99 paths**, identical to the input release path list; no archive path was added or removed. ZIP integrity, clean extraction, 98/98 SHA-256 ledger entries and Manifest agreement passed.

## Not tested / limitations

No authenticated MEXC private API, real order, Telegram network delivery, private fee retrieval, Docker build, Railway/Render resource load, long-duration soak or profitability was tested. Telegram photo ACK behavior is unit-tested with a mocked HTTP response, not a live Telegram delivery. A single skipped historical test depends on the missing A51 runtime log. These limitations are not presented as PASS.

# A88 final production audit closure — 2026-11-21

## Final A88 changes and regression evidence

- Closed the effective A75 wrapper truncation path: the runtime `OpportunityHunter._closed_frame` wrapper now retains the configured 400 closed candles instead of silently clipping them to 240. BTC requests 401 raw 1H/4H OHLCV rows so a still-forming candle can be discarded while preserving 400 closed observations. The supplemental A79 read-only research fetch now defines the same `ema_fetch_limit` locally and requests the required history; its regression fixture verifies 401-row 1H/4H depth.
- BTC macro regime is `UNKNOWN` when either the 1H/4H closed series lacks the configured EMA200 history or the latest closed candle exceeds its freshness limit. BTC 4H planning uses only verified 4H history and will not substitute 1H data.
- A86's displayed shortlist excludes BTC and includes only qualified non-BTC candidates passing configured quality, ranking, cost-aware economics, Net RR, bullish 1H/4H/MTF and positive 1H/4H BTC-relative-strength conditions. Unqualified symbols remain in the internal radar; the report presents an explicit empty-qualified-result and funnel counts.
- Forecast horizons are displayed as technical scenario points out of 100, not probability percentages. A bullish 15m reading against bearish 1H/4H is labelled a possible counter-trend rebound, not a higher-timeframe reversal.
- Brain briefing admission is reserved transactionally with SQLite `BEGIN IMMEDIATE` before durable outbox admission. This protects concurrent publishers that share one database; it does not provide cross-database/host deduplication or prove Telegram delivery ACK.
- Intraday Shadow scheduler events now distinguish empty selection, selected/started/completed, busy-skip and failed work. Daily selected/fetched/processed/failed metrics count authoritative stages rather than summing duplicate pipeline stages.
- No live authority, trade mode, forbidden-asset rule, spot-only restriction, order protection, reconciliation, fee gate or risk threshold was weakened. Effective policy remains `MONITOR_ONLY_NO_NEW_BUYS`.

## A88 validation results

- All packaged regression modules: **58 modules across 6 isolated pytest runs; 668 passed, 1 skipped, 0 failed**. Per-run passed counts: **63, 59, 78, 183, 67, 218**. Each run used a distinct `SCALPER_DB` to isolate SQLite test state. The only skip requires a historical A51 runtime log that is not included in the clean release archive.
- The six groups collectively covered every packaged `test_*.py` module once. An earlier batch invocation hit the command time limit before the third group completed; the affected groups were then rerun independently, and all six final independent groups passed.
- Focused A87/A88/release-contract/shadow checks passed; those focused results overlap with, and are not added to, the 668 full-regression passes.
- `python -m py_compile` for modified Python files and `python -m compileall -q .` passed. The archive contains **73 Python files**.
- `python main.py --validate-only` completed with exit code 0, `bot_started=false`, and `live_threads=[]`. This is offline validation only, not a live exchange/Telegram test.
- Final ZIP inventory is required to retain the original **99 unique archive paths**, with **0 added** and **0 removed**. The SHA ledger covers 98 files (excluding itself); final ZIP CRC, all ledger hashes and manifest agreement are checked at packaging time.

## Deployment boundary

No authenticated MEXC private API, real order/fill, private account fee retrieval, live Telegram delivery acknowledgement, Docker image build, Railway/Render resource-load test, long-duration soak or profitable-performance test was performed. The package remains a monitored, read-only market analyst; `MONITOR_ONLY_NO_NEW_BUYS` is intentionally retained. Do not enable unattended live trading based solely on offline tests or forecast scores.


# A89 final production audit — 2026-11-21

## Scope implemented
- Unified the BTC 1H/4H source consumed by A86 macro, forecasts, planning levels and candidate relative-strength. The long-history BTC request is bounded and separate from regular per-symbol scan budgets. A stale last-good observation is diagnostic only; a missing/old required frame blocks a directional entry decision.
- Reconciled the A86 candidate funnel with one primary exit disposition per analyzed symbol and explicit `UNATTRIBUTED` remainder. Existing quality, ranking, TP1 Net RR, MTF, RS and safety thresholds are retained.
- Added independent counterfactual diagnostics for missing HTF evidence versus a numeric weak-HTF rejection, and for BTC-relative strength without positive absolute return. Neither comparison alters canonical admission policy.
- Reworked the Paper fill lifecycle so READY_NOW waits for a later bar; WAITING_FOR_ENTRY requires an exact limit touch, not a zone touch; candle-volume participation is capped; plan creation/fill/expiry timestamps bound eligible outcome bars; unfilled plans expire; same-candle stop/target cases use a flagged conservative stop-first baseline.
- Added a full-TP1 baseline and a separately reported fixed partial-TP1 counterfactual. Costs are represented under normal and stressed assumptions. Per-cohort reporting separates RESEARCH, QUALIFIED, DELIVERED and RS_ONLY_ABSOLUTE_WEAK, and exposes attempt/eligibility/insertion/duplicate/rejection counts, fill ratios, Net R/USDT, days, drawdown and strategy/regime/timeframe slices.
- A86 report delivery distinguishes queued from delivered; delivered cohorts require successful Telegram API callbacks for every message part. Material-change notifications are separated from routine periodic summaries.
- Micro Shadow reporting distinguishes scheduler absence, empty selection, selected/fetched/processed outcomes and persisted evaluation evidence. Radar coverage uses unique symbols over a rolling 24-hour window with age and timeframe failure diagnostics.

## Interpretation and limitations
- `MONITOR_ONLY_NO_NEW_BUYS` remains the active entry policy. No live entry path or execution authority was added. Existing forbidden-asset, Spot-only, HTF, liquidity, spread, fee, score, reconciliation, position-protection and circuit-breaker controls were not relaxed.
- The Paper fill model is an OHLCV proxy with a capped volume-participation assumption, not exchange queue simulation. A next-bar open cannot prove an achievable real-world fill. The partial-exit cohort is a fixed counterfactual, not an adopted execution policy.
- Telegram `DELIVERED` is based on the application's Telegram API success callback. It is not evidence of a user's device displaying/reading the message. External authenticated connectivity and multi-host behavior have not been tested by offline regression.
- Chronological 70/30 breakdowns are descriptive only and are not an untouched out-of-sample proof. Performance remains unproven until adequate independent trade/day samples and later holdout validation are collected.
- No live MEXC order, authenticated fee verification, actual wallet PnL, Render/Railway soak, or profitability claim is made.

## A89 final regression and release validation
- Packaged test inventory: **58 test modules / 674 collected tests**. The modules were executed in isolated, non-overlapping batches, with the affected legacy contract tests rerun after the manifest/schema updates: **673 passed, 1 skipped, 0 failed**. The single skip is the historical A51 log-fixture test; that historical log is not included in the clean 99-file release archive.
- The new A89 source-contract self-test passed all nine A89 checks: unified BTC frame use across macro/forecast/RS; exact future-candle forecast resolution; no signal-time Paper fill; separate RESEARCH/QUALIFIED/DELIVERED cohorts; Telegram ACK gating; explicit QUEUED vs DELIVERED; reconciled candidate funnel; and unchanged monitor-only/no-live-order authority.
- `python main.py --validate-only`: **exit 0**, with `bot_started=false` and `live_threads=[]`. This validates startup contracts only and does not start a persistent trading process.
- `py_compile`: **73/73 packaged Python files passed**; `compileall` also completed successfully.
- Final artifact inventory is preserved at **99 unique original paths**, with 12 existing files modified and no files added or removed. SHA-256 ledger contains 98 non-self entries; final ZIP CRC and clean-extraction verification passed with all 99 paths and 98 hashes matching.
- Test execution was offline and deterministic. No authenticated MEXC request, real Telegram network send, exchange order, matching-engine fill, wallet PnL, long-duration deployment soak or profitability was tested or established.
