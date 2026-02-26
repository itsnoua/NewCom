# عرض الخريطة وطبقتي GeoJSON

هذا المشروع يحتوي على خريطة بسيطة تعرض الطبقتين الجغرافيتين الموجودتين في المجلد:

- `Comapoints.geojson`
- `ComBulid.geojson`

كيف تشغّل الخريطة محليًا:

1. افتح Terminal في المجلد `c:/Users/itsno/Desktop/NewCom`.
2. شغّل خادم HTTP بسيط (Python 3):

```powershell
python -m http.server 8000
```

3. افتح المتصفح واذهب إلى:

```
http://localhost:8000/map.html
```

ملاحظات:
- يجب أن تكون ملفات `Comapoints.geojson` و `ComBulid.geojson` في نفس المجلد مع `map.html`.
- إذا ظهرت رسالة خطأ في جلب الملفات، تأكد من كتابة أسماء الملفات بشكل صحيح وتشغيل الخادم المحلي.
