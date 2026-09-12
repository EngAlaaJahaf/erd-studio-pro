# 🎨 TESTR ERD Studio Pro

<p align="center">
  <b>منصة تفاعلية متقدمة ومستقلة لتصميم وإدارة واستعراض مخططات قواعد البيانات (ERD) مع مساعد ذكاء اصطناعي مدمج</b><br>
  <i>An advanced, standalone, interactive Entity-Relationship Diagram (ERD) Studio with integrated AI Assistant and multi-workspace support.</i>
</p>

---

## 🌟 المميزات الرئيسية | Key Features

### 1. 🗂️ نظام مساحات العمل والتبويبات المتعددة (Multi-Page Workspaces)
- **تبويبات متزامنة (Browser-style Tabs):** فتح وتعديل عدة مخططات في نفس الجلسة والتنقل بينها فوراً.
- **مصادر بيانات متنوعة لكل صفحة:**
  - 🔄 **أوراكل مباشر (Live Oracle DB):** مزامنة حية واستخراج الجداول والعلاقات من `Oracle Database`.
  - 📄 **ملفات SQL / DDL:** تحليل ملفات SQL بلهجات متعددة (Oracle, PostgreSQL, MySQL, T-SQL / MSSQL, SQLite) عبر `sqlglot`.
  - 📊 **قاموس البيانات (Excel Dictionary):** استيراد وتوليد المخططات مباشرة من ملفات Excel `.xlsx`.
  - 🤖 **كود الوكيل (Agent Code):** توليد فوري لصفحات جديدة من كود المساعد الذكي بضغطة زر واحدة.
- **روابط عميقة (Deep-linking):** فتح أي صفحة في نافذة مستقلة عبر المعامل `?w=<id>`.
- **حفظ تلقائي دائم (Auto-Persistence):** حفظ إحداثيات الجداول والتبويبات والإعدادات في قاعدة بيانات `SQLite` المحلية (`data/app.db`) و `localStorage`.

### 2. 🤖 مساعد الذكاء الاصطناعي التفاعلي (Interactive AI Assistant)
- **شات تفاعلي غني (Markdown & Code Highlighting):** دعم كامل للغة العربية وتنسيق الجداول والأكواد البرمجية.
- **زر "استخدم هذا الكود" (Use this code):** تحويل أي كود DDL يكتبه الذكاء الاصطناعي مباشرة إلى صفحة ومخطط ERD تفاعلي جديد دون أي خطوات يدوية.
- **استمرارية المحادثة (Chat Persistence):** استرجاع سجل المحادثات تلقائياً عند إعادة فتح التطبيق.

### 3. 🎯 لوحة رسم تفاعلية بمستوى تطبيقات سطح المكتب (Desktop-Grade Canvas)
- **تحديد وسحب جماعي:** اضغط `Ctrl` واسحب لتحديد مجموعة جداول بمربع تحديد أزرق منقط، وتحريكها معاً مع تحديث لحظي لخطوط العلاقات.
- **خوارزميات ترتيب تلقائي ذكية:** تخطيط هرمي (Hierarchical)، دائري (Circular)، وشبكي متوازن.
- **أوضاع عرض مرنة للأعمدة:**
  - `Clean / No Audit`: استثناء أعمدة التدقيق وتاريخ التعديل لتبسيط المخطط.
  - `Keys Only`: عرض المفاتيح الأساسية والأجنبية فقط (`PK` / `FK`).
  - `Full View`: إظهار كافة الحقول مع إمكانية إخفاء وتخصيص أعمدة كل جدول بشكل منفصل.

### 4. 📊 استيراد وتصدير متكامل (Import & Export)
- تصدير المخطط إلى ملفات Excel منسقة ومنظمة (`.xlsx`).
- تصدير كود SQL DDL لكافة الجداول والعلاقات.
- تصدير واستيراد لقطات المخطط الكاملة بتنسيق JSON.
- توليد مخططات UML وتصديرها بتنسيقات Mermaid و `.drawio` XML.

### 5. 🌐 واجهة ثنائية اللغة وتخصيص المظهر (i18n & Themes)
- دعم كامل للغتين العربية والإنجليزية مع التبديل الفوري لاتجاه الواجهة (`RTL` / `LTR`).
- 4 ثيمات لونية احترافية:
  - 🌙 `Dark Pro`
  - 🟣 `Mermaid Purple`
  - 🟢 `Academic Emerald`
  - ☀️ `Light Clean`

---

## 🚀 التثبيت والتشغيل | Installation & Quick Start

### المتطلبات | Prerequisites
- Python 3.10+
- متصفح ويب حديث (Chrome, Edge, Firefox, Safari)

### خطوات التشغيل | Setup Steps

1. **استنساخ المستودع (Clone Repository):**
   ```bash
   git clone https://github.com/YOUR_USERNAME/erd-studio-pro.git
   cd erd-studio-pro/erd_studio_app
   ```

2. **إنشاء البيئة الافتراضية وتثبيت المكتبات (Install Dependencies):**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux / macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **تشغيل الخادم (Run Server):**
   - **على نظام Windows:** انقر نقراً مزدوجاً على `start.bat` أو شغل:
     ```powershell
     .\start.ps1
     ```
   - **عبر سطر الأوامر (Cross-platform):**
     ```bash
     python server.py
     ```

4. **فتح التطبيق (Open App):**
   افتح المتصفح على العنوان:
   ```
   http://localhost:8500
   ```

---

## 📁 هيكلية المشروع | Project Structure

```text
erd_studio_app/
├── server.py              # خادم FastAPI ومسارات الـ REST API والخدمات
├── database.py            # محرك قاعدة بيانات SQLite وعمليات الحفظ التلقائي
├── oracle_sync.py         # مستكشف ومزامن مخططات Oracle DB
├── sql_import.py          # محلل كود SQL و DDL متعدد اللهجات (sqlglot)
├── sql_export.py          # مولد كود SQL DDL
├── datadict_import.py     # مستورد قواميس البيانات من Excel
├── datadict_export.py     # مصدّر قواميس البيانات إلى Excel منسق
├── db_connectors.py       # موصلات قواعد البيانات المتعددة
├── subsystems.py          # محرك تصنيف وتقسيم الأنظمة الفرعية
├── ai_assistant.py        # محرك المساعد الذكي وخدمات الـ Streaming
├── ai_classify.py         # التصنيف الذكي للجداول عبر الـ LLM
├── diagram_specs.py       # مواصفات ومولدات مخططات UML و Draw.io
├── static/
│   ├── index.html         # الواجهة التفاعلية الكاملة للتطبيق
│   └── vendor/
│       └── mermaid.min.js # مكتبة رسم المخططات
├── data/
│   └── .gitkeep           # مجلد قاعدة البيانات المحلية (app.db)
├── requirements.txt       # قائمة مكتبات واحتياجات بايثون
├── .env.example           # نموذج المتغيرات البيئية
├── .gitignore             # قواعد استثناء الملفات غير المرغوبة
├── start.bat              # مشغل بنقرة واحدة (Windows Batch)
└── start.ps1              # مشغل الباورشيل (PowerShell Script)
```

---

## ⚙️ الإعدادات والمتغيرات البيئية | Configuration

يمكن ضبط الإعدادات إما من خلال واجهة المستخدم مباشرة (زر الإعدادات ⚙️) أو عبر ملف `.env`:

| المتغير | القيمة الافتراضية | الوصف |
|---|---|---|
| `SERVER_HOST` | `0.0.0.0` | عنوان استضافة الخادم |
| `SERVER_PORT` | `8500` | منفذ تشغيل التطبيق |
| `ORACLE_USER` | `TESTR` | اسم مستخدم Oracle |
| `ORACLE_PASSWORD` | `TESTR` | كلمة مرور Oracle |
| `ORACLE_HOST` | `localhost` | خادم Oracle |
| `ORACLE_PORT` | `1521` | منفذ Oracle |
| `ORACLE_SERVICE` | `orclpdb` | اسم الخدمة / PDB |
| `AI_PROVIDER` | `local` | مزود الذكاء الاصطناعي (`local` / `openai` / `custom`) |
| `AI_MODEL` | `gpt-4o-mini` | النموذج المستخدم في التحليل والتصنيف |

---

## 📜 الترخيص | License

هذا المشروع متاح تحت رخصة [MIT License](LICENSE).
