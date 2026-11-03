# Back4App XHTTP Relay (Python)

نسخة Python من [back4app-xhttp-relay](https://github.com/alrufaaey-yahoo/back4app-xhttp-relay)، مصممة للنشر على **Back4App Containers** عبر Docker وGitHub.

يقوم التطبيق بتمرير طلبات HTTP إلى الوجهة المحددة في `TARGET_DOMAIN` مع الحفاظ على طريقة الطلب، المسار، query string، الجسم، والرؤوس المناسبة. كما يوفر مساري فحص الصحة `/health` و`/healthz`.

## الخصائص

- Python 3.12 ومكتبات قياسية فقط؛ لا توجد حزم خارجية مطلوبة.
- يستمع إلى `0.0.0.0` ويقرأ المنفذ من `PORT`، والقيمة الافتراضية `3000`.
- الوجهة قابلة للضبط عبر `TARGET_DOMAIN`، والقيمة الافتراضية متوافقة مع المشروع الأصلي: `https://vps.thumbayan.com:443`.
- إزالة رؤوس Hop-by-Hop والرؤوس الخاصة بالوكلاء قبل الإرسال للوجهة.
- تمرير `X-Real-IP` أو `X-Forwarded-For` كـ `X-Forwarded-For` للوجهة.
- التعامل مع أخطاء الاتصال بإرجاع `502 Bad Gateway`.
- سجل وصول بسيط مناسب لفحص سجلات Back4App.

## التشغيل محليًا

```bash
export TARGET_DOMAIN="https://example.com"
export PORT=3000
python3 app.py
```

ثم اختبر:

```bash
curl http://localhost:3000/health
curl -i http://localhost:3000/path?value=1
```

## التشغيل باستخدام Docker

```bash
docker build -t back4app-xhttp-relay-python .
docker run --rm -p 3000:3000 \
  -e PORT=3000 \
  -e TARGET_DOMAIN=https://example.com \
  back4app-xhttp-relay-python
```

## النشر على Back4App Containers

يحتاج Back4App Containers إلى وجود `Dockerfile` في المستودع، ويجب أن يستمع التطبيق إلى قيمة `PORT` وأن يعرّف Dockerfile منفذ TCP. هذه المتطلبات مضمّنة في المشروع.

1. ادخل إلى Back4App Containers واربط حساب GitHub.
2. اختر المستودع `back4app-xhttp-relay-python` والفرع `main`.
3. تأكد من أن مسار Dockerfile هو الجذر `/Dockerfile`.
4. أضف متغيرات البيئة:
   - `TARGET_DOMAIN`: عنوان الخدمة الأصلية، مثل `https://example.com`.
   - `PORT`: عادةً يضبطه Back4App تلقائيًا؛ القيمة المحلية الافتراضية `3000`.
5. أنشئ التطبيق وراقب سجل البناء والتشغيل. استخدم `/health` للتحقق من جاهزية التطبيق.

> تنبيه أمني: لا تضع أسرارًا أو مفاتيح API في المستودع. كما أن هذا Relay يمرر الطلبات إلى الوجهة المحددة؛ احمِ الوجهة وطبّق المصادقة المناسبة في الطبقة الأمامية إذا كانت الخدمة غير عامة.

## الاختبارات

```bash
python3 -m unittest discover -s tests -v
```

## الترخيص

هذا المستودع الجديد مستقل عن المستودع المصدر. راجع سياسة الترخيص الخاصة بالمشروع الأصلي قبل إعادة استخدام أي أجزاء إضافية منه.
