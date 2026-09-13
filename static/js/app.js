// --- Live Schema State ---
let tablesData = {};
let fkList = [];
let allTables = [];
let comTables = [];
let rafTables = [];
window._liveSchema = null;

// --- Audit Fields Definition ---
const AUDIT_COLUMNS_SET = new Set([
  'CREATED_BY', 'CREATED_TIME', 'CREATED_DATE', 'CREATED_AT',
  'UPDATED_BY', 'UPDATED_TIME', 'UPDATED_DATE', 'UPDATED_AT',
  'DELETED_BY', 'DELETED_TIME', 'DELETED_DATE', 'DELETED_AT', 'IS_DELETED',
  'VERSION_NUMBER',
  'LAST_ACTIVITY', 'LAST_LOGIN', 'LAST_IP_ADDRESS', 'DEVICE_FINGERPRINT', 'LOGIN_COUNT',
  'EMAIL_VERIFICATION_TOKEN', 'EMAIL_VERIFICATION_EXPIRY',
  'PASSWORD_RESET_CODE', 'RESET_CODE_EXPIRY', 'RESET_CODE_USED_AT',
  'SCAN_IP_ADDRESS', 'SCAN_LATITUDE', 'SCAN_LONGITUDE',
  'EXCUSE_REVIEWED_BY', 'EXCUSE_REVIEW_NOTES', 'REVIEWED_BY', 'REVIEWED_AT', 'REVIEW_NOTES'
]);

function isAuditColumn(colName) {
  if (AUDIT_COLUMNS_SET.has(colName)) return true;
  if (/^(CREATED|UPDATED|DELETED)_(BY|TIME|DATE|AT)$/i.test(colName)) return true;
  if (/^IS_DELETED$/i.test(colName)) return true;
  if (/^VERSION_NUMBER$/i.test(colName)) return true;
  return false;
}

// --- Bilingual Dictionary ---
let currentLang = (function() {
  try {
    var sl = localStorage.getItem('erd_lang');
    if (sl) return sl;
    var b = localStorage.getItem('testr_erd_studio_bundle');
    if (b) { var p = JSON.parse(b); if (p.lang) return p.lang; }
  } catch(e) {}
  return 'ar';
})();
let activeSidebarFilter = 'all';

const i18n = {
  ar: {
    brandTitle: "ERD Studio Pro",
    brandSubtitle: "Oracle 21c • SQLite App",
    searchPlaceholder: "بحث في الجداول...",
    chipAll: "الكل",
    exportSvg: "تصدير SVG",
    exportPng: "تصدير PNG",
    saveLayout: "حفظ",
    loadSaved: "استرجاع",
    resetLayout: "ضبط",
    presetHierarchical: "⑂ هرمي",
    presetGrid: "▦ شبكي",
    presetCluster: "❖ مجموعات",
    presetCircular: "◎ دائري",
    presetForce: "☍ فيزيائي",
    presetStar: "★ نجمي",
    themeDark: "داكن احترافي",
    themeLight: "فاتح",
    themeMermaid: "كلاسيكي",
    themeAcademic: "زمردي",
    viewNoAudit: "◫ بدون تدقيق",
    viewKeysOnly: "⚿ مفاتيح فقط",
    viewAllCols: "☰ كل الحقول",
    btnManageCols: "الحقول",
    btnHideAudit: "إخفاء التدقيق",
    btnKeysOnly: "المفاتيح فقط",
    btnShowAll: "إظهار الكل",
    btnMultiNoAudit: "إخفاء التدقيق",
    btnMultiKeysOnly: "المفاتيح فقط",
    btnMultiShowAll: "إظهار الكل",
    btnMultiHide: "إخفاء المحدّد",
    modalSubtitle: "اختر الحقول المطلوب إظهارها على المخطط",
    modalSearch: "فلترة الحقول...",
    modalDone: "تم",
    modalColCount: "حقل ظاهر",
    modalBtnNoAudit: "بدون تدقيق",
    modalBtnKeysOnly: "مفاتيح فقط",
    modalBtnShowAll: "كل الحقول",
    hintCtrlDrag: "<kbd>Ctrl</kbd> + <b>سحب:</b> تحديد متعدد",
    hintDragTable: "<b>سحب:</b> تحريك الجدول",
    hintZoom: "<b>عجلة الماوس:</b> تكبير / تصغير",
    langToggle: "English",
    legendTitle: "الأنظمة الفرعية",
    relLegendTitle: "خطوط العلاقات",
    relLegIdent: "معرِّفة (متصل): المفتاح الخارجي جزء من مفتاح الجدول",
    relLegNonIdent: "غير معرِّفة (متقطع): المفتاح الخارجي مستقل",
    relLegCard: "أصل سميك = واحد  |  قدم غراب = متعدد",
    relLegOptional: "دائرة = اختياري (قابل للقيمة الفارغة)",
    relLegSelf: "حلقة بنفسجية = مرجع ذاتي",
    relLegColor: "لون الخط = لون النطاق الفرعي",
    subsysFilterAll: "كل الأنظمة",
    viewCanvas: "المخطط",
    viewImport: "استيراد",
    viewExport: "تصدير",
    sideTables: "الجداول",
    newPageTitle: "صفحة جديدة",
    newPageSub: "اختر مصدر البيانات الذي ستعرضه هذه الصفحة",
    srcOracle: "اتصال Oracle مباشر",
    srcOracleSub: "جلب المخطط مباشرة من قاعدة البيانات المتصلة (نسخة قابلة للتعديل).",
    srcSql: "ملف SQL / DDL",
    srcSqlSub: "ارفع ملف .sql أو .ddl — يُنشئ صفحة جديدة بالجداول والعلاقات.",
    srcXlsx: "قاموس بيانات Excel (xlsx)",
    srcXlsxSub: "ملف أو عدة ملفات Excel بتعريفات الجداول تُدمج في صفحة واحدة.",
    srcPaste: "لصق كود SQL مباشر",
    srcPasteSub: "الصق كود DDL في نافذة منبثقة ويُرسم المخطط فورًا.",
    pasteModalTitle: "لصق كود SQL مباشر",
    pasteModalSub: "الصق أوامر CREATE TABLE (DDL) لإنشاء صفحة ومخطط جديد فوراً",
    pasteInputLabel: "كود SQL (DDL):",
    pasteClipboardBtn: "لصق من الحافظة",
    pasteCancelBtn: "إلغاء",
    pasteSubmitBtn: "إنشاء المخطط",
    copyCode: "نسخ",
 codeCopied: " تم النسخ",
 useThisCode: " استخدام هذا الكود",
 importTitle: " استيراد البيانات",
    importSub: "ارفع ملفات .sql أو قواميس .xlsx (ملفًا أو أكثر) وسيحللها التطبيق تلقائيًا إلى جداول وعلاقات وأنظمة فرعية، أو استعد نسخة محفوظة سابقًا.",
    impSqlTitle: "استيراد مخطّط من ملف SQL",
    impDictTitle: "استيراد قاموس البيانات (Data Dictionary .xlsx)",
    impRestoreTitle: "استعادة نسخة محفوظة",
    exportTitle: "تصدير البيانات",
    exportSub: "صدّر المخطط الحالي كصورة أو كود أو قاموس بيانات، أو نزّل نسخة احتياطية من التطبيق.",
    expImgTitle: "تصدير المخطط كصورة (SVG / PNG)",
    expImgHint: "تنزيل الرسم الحالي كملف SVG متجهي أو PNG بجودة عالية بأبعاد المخطط الكاملة.",
    expHtmlReportTitle: "تقرير HTML تفاعلي مستقل (Single-File Offline Report)",
    expHtmlReportHint: "تصدير المخطط بالكامل مع قاموس البيانات التفاعلي ومحرك البحث الداخلي في ملف HTML مستقل يعمل 100% بدون إنترنت ولا خادم، لمشاركته مع العميل أو فريق العمل أو إرفاقه في وثائق المشاريع.",
    expHtmlDownloadBtn: "تنزيل تقرير HTML (.html)",
    expHtmlPreviewBtn: "معاينة تفاعلية",
    expPdfReportTitle: "تقرير PDF معماري أنيق (Executive Data Dictionary PDF)",
    expPdfReportHint: "توليد وثيقة PDF منسقة ومجدولة تحتوي على مؤشرات المعمارية، ملخص المخطط، وجداول الحقول والأنواع والقيود المرجعية لتوثيق المشروع رسميًا.",
    expPdfDownloadBtn: "تنزيل وثيقة PDF (.pdf)",
    expPdfPrintBtn: "طباعة / معاينة",
    expDdlTitle: "تصدير سكربت DDL",
    expDictTitle: "قاموس البيانات (Data Dictionary .xlsx)",
    expDictHint: "توليد قاموس بيانات Excel (.xlsx) منسق ومفصل يحتوي على كافة الجداول، الحقول، الأنواع، المفاتيح الأساسية والعلاقات للمخطط الحالي مباشرة، أو من ملفات كود خارجية.",
    expDictDirectBtn: "توليد وتنزيل القاموس من المخطط الحالي مباشرة (.xlsx)",
    expDictUploadHint: "أو توليد القاموس من ملفات SQL خارجية مرفوعة:",
    expDictChooseFiles: "اختيار ملفات الكود",
    expDictFromFilesBtn: "توليد من الملفات (.xlsx)",
    expBackupTitle: "نسخة احتياطية من التطبيق",
 dbMovedHint: " أدوات استيراد/تصدير الملفات (SQL و قاموس البيانات والنسخ الاحتياطي) أصبحت في صفحات منفصلة من شريط التنقل العلوي: استيراد / تصدير.",
    storageRestoreHint: "استعد نسخة SQLite كاملة أو لقطة ترتيب JSON سبق تصديرها.",
    viewAudit: "الهندسة والتدقيق",
    auditTitle: "أدوات هندسة وتدقيق المخططات (Engineering & Audit)",
    auditSub: "فحص الجودة المعمارية، كشف الأخطاء التخطيطية، مقارنة المخططات وتوليد سكربتات الترقية، وتوليد البيانات التجريبية الذكية.",
    tabLinter: "فاحص الجودة المعمارية (Linter)",
    tabDiff: "مقارنة المخططات والترقية (Diff)",
    tabMock: "البيانات التجريبية (Mock Data)",
    btnRunLint: "فحص المخطط الحالي",
    btnDownloadRem: "تنزيل سكربت المعالجة (.sql)",
    btnRunDiff: "مقارنة المخططين الآن",
    btnCopyMig: "نسخ السكربت",
    btnDownMig: "تنزيل (.sql)",
    btnGenMock: "توليد البيانات التجريبية الذكية",
    btnCopyMock: "نسخ الكود",
    btnDownMock: "تنزيل (.sql)",
    aiTitle: "المساعد الذكي",
    aiPlaceholder: "اكتب سؤالاً أو أمراً لتعديل المخطط...",
 aiSend: "",
 aiClear: "",
    aiModeLocal: "محلي",
    aiModeCloud: "سحابي",
    aiThinking: "جارٍ التفكير...",
    aiWelcome: "مرحباً بك في المساعد الذكي لـ ERD Studio Pro.\nيمكنك إعطائي أوامر مباشرة للتحكم بالمخطط: تغيير التصميم، الترتيب، إبراز الجداول، وتصفية الأنظمة، أو الاستفسار عن الجداول وقواعد البيانات.",
    tabAi: "الذكاء الاصطناعي",
    aiProviderSection: "مزود الذكاء الاصطناعي",
    aiProvider: "المزود",
    aiModel: "النموذج",
    aiBaseUrl: "الرابط الأساسي",
    aiApiKey: "مفتاح API",
    aiTemp: "الحرارة",
    aiHint: "اترك المزود محلياً ليعمل المساعد بدون مفتاح API. عند إضافة مفتاح يتفعّل الوضع السحابي الذكي مع تنفيذ الأدوات على المخطط.",
    aiTestBtn: "فحص",
    aiSaveBtn: "حفظ إعدادات الذكاء",
    relModalTitle: "تفاصيل العلاقة بين الجداول",
    relParentTag: "الجدول الأب (المصدر)",
    relChildTag: "الجدول الابن (التابع)",
    relPropFkName: "اسم القيد (Constraint)",
    relPropCard: "التعددية (Cardinality)",
    relPropNature: "نوع التبعية (Identifying)",
    relPropNull: "الإلزامية (Nullability)",
    relSqlTitle: "تعريف جملة SQL (DDL)",
    relCopySqlText: "نسخ SQL",
    relFocusBtn: "التركيز على الجدولين",
    relAiBtn: "اسأل الذكاء الاصطناعي",
    relCloseBtn: "إغلاق",
  },
  en: {
    brandTitle: "ERD Studio Pro",
    brandSubtitle: "Oracle 21c • SQLite App",
    searchPlaceholder: "Search tables...",
    chipAll: "All",
    exportSvg: "SVG",
    exportPng: "PNG",
 saveLayout: " Save",
 loadSaved: " Load",
 resetLayout: " Reset",
 presetHierarchical: " ⑂ Tree",
 presetGrid: " ▦ Grid",
 presetCluster: " ❖ Clusters",
 presetCircular: " ◎ Circular",
 presetForce: " ☍ Force",
 presetStar: " ★ Star",
 themeDark: " Dark Pro",
 themeLight: " Light Clean",
 themeMermaid: " Mermaid",
 themeAcademic: " Emerald",
 viewNoAudit: " ◫ No Audit Cols",
 viewKeysOnly: " ⚿ Keys Only",
 viewAllCols: " ☰ All Columns",
    btnManageCols: "Columns",
    btnHideAudit: "Hide Audit",
    btnKeysOnly: "Keys Only",
    btnShowAll: "Show All",
    btnMultiNoAudit: "Hide Audit",
    btnMultiKeysOnly: "Keys Only",
    btnMultiShowAll: "Show All",
 btnMultiHide: " Hide",
    modalSubtitle: "Select columns to display on canvas",
    modalSearch: "Filter columns...",
    modalDone: "Done",
    modalColCount: "columns visible",
 modalBtnNoAudit: " No Audit",
    modalBtnKeysOnly: "Keys Only",
 modalBtnShowAll: " Show All",
 hintCtrlDrag: " <kbd>Ctrl</kbd> + <b>Drag:</b> Box selection",
 hintDragTable: " <b>Drag:</b> Live connectors",
 hintZoom: " <b>Scroll:</b> Zoom",
    langToggle: "العربية",
    legendTitle: "Subsystems",
    relLegendTitle: "Relation Lines",
    relLegIdent: "Identifying (solid): FK is part of child PK",
    relLegNonIdent: "Non-identifying (dashed): independent FK",
    relLegCard: "Thick bar = one  |  crow's foot = many",
    relLegOptional: "Circle = optional (nullable FK)",
    relLegSelf: "Purple loop = self-reference",
    relLegColor: "Line color = subsystem color",
    subsysFilterAll: "All subsystems",
    viewCanvas: "Diagram",
    viewImport: "Import",
    viewExport: "Export",
    sideTables: "Tables",
    newPageTitle: "New Page",
    newPageSub: "Choose the data source this page will display",
 srcOracle: " Direct Oracle connection",
    srcOracleSub: "Fetch the schema straight from the connected database (editable copy).",
 srcSql: " SQL / DDL file",
    srcSqlSub: "Upload a .sql or .ddl file — creates a new page with tables and relations.",
 srcXlsx: " Data Dictionary xlsx",
    srcXlsxSub: "One or more Excel files with table definitions merged into one page.",
 srcPaste: " Paste SQL code",
    srcPasteSub: "Paste DDL code into a dialog to generate diagram instantly.",
    pasteModalTitle: "Paste SQL Code",
    pasteModalSub: "Paste CREATE TABLE (DDL) statements to generate a new page and diagram instantly",
    pasteInputLabel: "SQL Code (DDL):",
    pasteClipboardBtn: "Paste from Clipboard",
    pasteCancelBtn: "Cancel",
    pasteSubmitBtn: "Generate Diagram",
    copyCode: "Copy",
 codeCopied: " Copied",
 useThisCode: " Use this code",
 importTitle: " Import Data",
    importSub: "Upload .sql files or .xlsx dictionaries (one or many) — the app parses them into tables, relations and subsystems, or restore a saved copy.",
    impSqlTitle: "Import schema from SQL file",
    impDictTitle: "Import Data Dictionary (.xlsx)",
    impRestoreTitle: "Restore a saved copy",
 exportTitle: " Export Data",
    exportSub: "Export the current diagram as an image, code or data dictionary, or download an app backup.",
    expImgTitle: "Export diagram image (SVG / PNG)",
    expImgHint: "Download the current drawing as a vector SVG or high-quality PNG at full diagram size.",
    expHtmlReportTitle: "Single-File Offline Report (Interactive HTML)",
    expHtmlReportHint: "Export the full diagram with interactive data dictionary and built-in search in a single self-contained HTML file that runs 100% offline with zero server dependencies.",
    expHtmlDownloadBtn: "Download Standalone HTML (.html)",
    expHtmlPreviewBtn: "Preview Interactive Report",
    expPdfReportTitle: "Executive Data Dictionary PDF",
    expPdfReportHint: "Generate an executive, publication-ready PDF document containing architecture metrics, overview diagrams, and structured data dictionary tables for formal project documentation.",
    expPdfDownloadBtn: "Download Executive PDF (.pdf)",
    expPdfPrintBtn: "Print / PDF Preview",
    expDdlTitle: "Export DDL script",
    expDictTitle: "Data Dictionary (.xlsx)",
    expDictHint: "Generate a formatted Excel (.xlsx) Data Dictionary with all tables, columns, types, PKs, and relationships directly from the active diagram or external files.",
    expDictDirectBtn: "Generate & Download Dictionary from current diagram (.xlsx)",
    expDictUploadHint: "Or generate dictionary from uploaded external SQL files:",
    expDictChooseFiles: "Choose Code Files",
    expDictFromFilesBtn: "Generate from Files (.xlsx)",
    expBackupTitle: "Application backup",
 dbMovedHint: " File import/export tools (SQL, data dictionary and backup) moved to separate pages in the top navigation: Import / Export.",
    storageRestoreHint: "Restore a full SQLite backup or a previously exported JSON layout snapshot.",
    viewAudit: "Engineering & Audit",
    auditTitle: "Database Engineering & Architecture Audit",
    auditSub: "Automated schema linting, visual diff & migration generator, and smart mock data synthesis.",
    tabLinter: "Architecture Linter",
    tabDiff: "Schema Diff & Migration",
    tabMock: "Smart Mock Data",
    btnRunLint: "Run Schema Audit",
    btnDownloadRem: "Download Remediation (.sql)",
    btnRunDiff: "Run Schema Diff",
    btnCopyMig: "Copy Script",
    btnDownMig: "Download (.sql)",
    btnGenMock: "Generate Smart Mock Data",
    btnCopyMock: "Copy Script",
    btnDownMock: "Download (.sql)",
    aiTitle: "Smart Assistant",
    aiPlaceholder: "Type a command... e.g. switch theme to dark",
 aiSend: "",
 aiClear: "",
    aiModeLocal: "Local",
    aiModeCloud: "Cloud",
    aiThinking: "Thinking...",
    aiWelcome: "Welcome to ERD Studio Pro Assistant.\nYou can ask questions about your database schema or issue commands to change themes, layouts, highlight tables, or filter subsystems.",
    tabAi: "AI",
    aiProviderSection: "AI Provider",
    aiProvider: "Provider",
    aiModel: "Model",
    aiBaseUrl: "Base URL",
    aiApiKey: "API Key",
    aiTemp: "Temperature",
    aiHint: "Keep the provider local for an assistant that works with no API key. Adding a key enables the smart cloud mode with tool execution on the diagram.",
    aiTestBtn: "Test",
    aiSaveBtn: "Save AI Settings",
    relModalTitle: "Relationship Details",
    relParentTag: "Parent Table (Source)",
    relChildTag: "Child Table (Target)",
    relPropFkName: "Constraint Name",
    relPropCard: "Cardinality",
    relPropNature: "Identifying Nature",
    relPropNull: "Nullability",
    relSqlTitle: "SQL DDL Definition",
    relCopySqlText: "Copy SQL",
    relFocusBtn: "Focus Tables",
    relAiBtn: "Ask AI Assistant",
    relCloseBtn: "Close",
  }
};
window.i18n = i18n;

// --- Application State ---
let selectedTables = new Set(allTables);
let tablePositions = {};
let tableCustomHiddenCols = {};
let globalViewMode = 'no-audit';
let currentTheme = (function() {
  try {
    var st = localStorage.getItem('erd_theme');
    if (st) return st;
    var b = localStorage.getItem('testr_erd_studio_bundle');
    if (b) { var p = JSON.parse(b); if (p.theme) return p.theme; }
  } catch(e) {}
  return 'light';
})();
let isSidebarCollapsed = false;
let selectedTableNodes = new Set();

let layoutSpacing = (function() {
  const defaults = {
    circular: 550,
    force: 220,
    hierarchical: 320,
    grid: 310,
    cluster: 310,
    star: 380
  };
  try {
    const saved = localStorage.getItem('erd_layout_spacing');
    if (saved) return Object.assign(defaults, JSON.parse(saved));
  } catch(e) {}
  return defaults;
})();

// Transform State
let panX = 40, panY = 40, zoom = 0.82;
let isPanning = false, startPanX = 0, startPanY = 0;

// Marquee State
let isMarqueeActive = false;
let marqueeStartX = 0, marqueeStartY = 0;

// Dragging State
let draggedNode = null;
let dragStartX = 0, dragStartY = 0;
let groupInitialPositions = {};
let isDraggingNode = false;

// Table Dimension Constants
let TABLE_WIDTH = 270;
const HEADER_HEIGHT = 28;
const ROW_HEIGHT = 22;
const TYPE_COL_WIDTH = 105;

// Auto-save debounce timer
let autoSaveTimer = null;

// Settings Modal State
let dbCfg = { dialect: 'oracle', host: 'localhost', port: 1521, service: 'orclpdb', user: 'TESTR', password: 'TESTR', file: '' };
let autoSaveEnabled = true;
let dbSettingsLoaded = false;
let isDbConnected = false;
let isCheckingDbConnection = false;
let dbConnectionError = '';

async function checkDbConnection(silent = true) {
  if (isCheckingDbConnection) return;
  isCheckingDbConnection = true;
  if (typeof updateStatusBar === 'function') updateStatusBar();

  try {
    const dialect = (dbCfg && dbCfg.dialect) || 'oracle';
    const payload = { dialect, params: {} };
    if (dialect === 'sqlite_file') {
      payload.params = { path: (dbCfg && dbCfg.file) || '' };
    } else {
      payload.params = {
        host: (dbCfg && dbCfg.host) || 'localhost',
        port: parseInt((dbCfg && dbCfg.port), 10) || (dialect === 'mysql' ? 3306 : dialect === 'postgres' ? 5432 : dialect === 'mssql' ? 1433 : 1521),
        user: (dbCfg && dbCfg.user) || '',
        password: (dbCfg && dbCfg.password) || ''
      };
      if (dialect === 'oracle') {
        payload.params.service_name = (dbCfg && dbCfg.service) || 'orclpdb';
      } else {
        payload.params.database = (dbCfg && dbCfg.service) || '';
      }
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    const res = await fetch('/api/connectors/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      isDbConnected = !!data.success;
      dbConnectionError = data.success ? '' : (data.error || 'Connection failed');
    } else {
      isDbConnected = false;
      dbConnectionError = 'HTTP error ' + res.status;
    }
  } catch (err) {
    isDbConnected = false;
    dbConnectionError = err.name === 'AbortError' ? 'Connection timed out' : (err.message || 'Connection error');
  } finally {
    isCheckingDbConnection = false;
    if (typeof updateStatusBar === 'function') updateStatusBar();
  }
}

// ==================== ON LOAD: AUTO-PERSISTENCE FROM SQLITE ====================
window.addEventListener('DOMContentLoaded', async () => {
  // 1. Immediately apply cached language and theme synchronously!
  applyLanguage(currentLang);
  setTheme(currentTheme, false);

  setupCanvasEvents();
  setupKeyboardShortcuts();

  // 2. Fetch live schema and saved state from SQLite backend
  await loadStateFromSQLiteOrLocal();

  // 3. Fetch app-wide settings (DB connection etc.)
  await loadAppSettings();

  // 4. Fetch AI config + subsystem classification
  await loadAIConfig();
  await loadSubsystems();

  // 5. Initialize workspaces with live schema
  await initWorkspaces();

  // 6. Build UI and render cleanly with the live schema
  buildSidebarList();
  renderAll();
  applyLanguage(currentLang);
  refreshCurrentSchemaInfo();
  await loadChatHistory();
  bindAiCodeButtons();
  initAIChatInput();
});

// Load DB connection & app-wide settings from SQLite
async function loadAppSettings() {
  try {
    const res = await fetch('/api/settings');
    if (res.ok) {
      const s = await res.json();
      if (s.db_host) dbCfg.host = s.db_host;
      if (s.db_port) dbCfg.port = parseInt(s.db_port, 10) || 1521;
      if (s.db_service) dbCfg.service = s.db_service;
      if (s.db_user) dbCfg.user = s.db_user;
      if (s.db_password) dbCfg.password = s.db_password;
      if (s.db_dialect) dbCfg.dialect = s.db_dialect;
      if (s.db_file) dbCfg.file = s.db_file;
      if (s.auto_save !== undefined) autoSaveEnabled = (s.auto_save === '1' || s.auto_save === true || s.auto_save === 'true');
      dbSettingsLoaded = true;
      if (typeof updateStatusBar === 'function') updateStatusBar();
    }
  } catch (err) {
    console.warn('Could not load app settings:', err);
  }
}

// Load full state from SQLite API
// Ensure every position object has valid finite x/y/width/height
function normalizePositions() {
  allTables.forEach(t => {
    const p = tablePositions[t];
    if (!p) return;
    if (!isFinite(p.x)) p.x = 100;
    if (!isFinite(p.y)) p.y = 100;
    if (!isFinite(p.width) || p.width <= 0) p.width = TABLE_WIDTH;
    const h = getTableHeight(t);
    p.height = isFinite(h) && h > 0 ? h : HEADER_HEIGHT + ROW_HEIGHT;
  });
}

async function loadStateFromSQLiteOrLocal() {
  try {
    // 1. Fetch Schema
    const schemaRes = await fetch('/api/schema');
    if (schemaRes.ok) {
      const schema = await schemaRes.json();
      if (schema.tablesData && schema.fkList) {
        tablesData = schema.tablesData;
        fkList = schema.fkList;
        allTables = Object.keys(tablesData);
        comTables = allTables.filter(t => t.startsWith('COM_'));
        rafTables = allTables.filter(t => t.startsWith('RAF_'));
        selectedTables = new Set(allTables);
        window._liveSchema = {
          tablesData: schema.tablesData,
          fkList: schema.fkList,
          tableCount: schema.tableCount,
          fkCount: schema.fkCount,
          dialect: schema.dialect
        };
      }
    }

    // 2. Fetch State from SQLite
    const stateRes = await fetch('/api/state');
    if (stateRes.ok) {
      const state = await stateRes.json();
      
      // Restore Positions
      if (state.positions && Object.keys(state.positions).length > 0) {
        tablePositions = state.positions;
      } else {
        calculateInitialLayout('hierarchical');
      }
      normalizePositions();

      // Restore Custom Hidden Columns
      if (state.hidden_cols) {
        tableCustomHiddenCols = {};
        Object.keys(state.hidden_cols).forEach(k => {
          tableCustomHiddenCols[k] = new Set(state.hidden_cols[k]);
        });
      }

      // Restore Visible Tables (prune any tables that no longer exist)
      if (state.visible_tables && state.visible_tables.length > 0) {
        const validSet = new Set(allTables);
        const filtered = state.visible_tables.filter(t => validSet.has(t));
        selectedTables = new Set(filtered.length > 0 ? filtered : allTables);
      }

      // Restore Settings
      if (state.settings) {
        const s = state.settings;
        if (s.current_theme) {
          currentTheme = (s.current_theme === 'light') ? 'light' : 'dark';
          const sel = document.getElementById('themeSelect');
          if (sel) sel.value = currentTheme;
          setTheme(currentTheme, false);
        }
        if (s.current_lang) {
          currentLang = s.current_lang;
        }
        if (s.global_view_mode) {
          globalViewMode = s.global_view_mode;
          const gmSel = document.getElementById('globalViewModeSelect');
          if (gmSel) gmSel.value = globalViewMode;
        }
        if (s.zoom) zoom = parseFloat(s.zoom);
        if (s.pan_x) panX = parseFloat(s.pan_x);
        if (s.pan_y) panY = parseFloat(s.pan_y);
      }
      return;
    }
  } catch (err) {
    console.warn("Backend API unavailable, loading from localStorage fallback:", err);
  }

  // Fallback to localStorage
  const saved = localStorage.getItem('testr_erd_studio_bundle');
  if (saved) {
    try {
      const bundle = JSON.parse(saved);
      if (bundle.positions) tablePositions = bundle.positions;
      if (bundle.globalViewMode) globalViewMode = bundle.globalViewMode;
      if (bundle.theme) { currentTheme = bundle.theme; setTheme(currentTheme, false); }
      if (bundle.lang) currentLang = bundle.lang;
      if (bundle.customCols) {
        tableCustomHiddenCols = {};
        Object.keys(bundle.customCols).forEach(k => {
          tableCustomHiddenCols[k] = new Set(bundle.customCols[k]);
        });
      }
      normalizePositions();
    } catch(e){}
  } else {
    calculateInitialLayout('hierarchical');
  }
}

// Auto-save to SQLite on every modification
function scheduleAutoSave() {
  if (workspaces && workspaces.length > 0) {
    var curWs = workspaces.find(function(w){ return w.id === activeWorkspaceId; });
    if (curWs) _captureCurrentInto(curWs);
    _saveWorkspacesLocal();
  }
  if (!autoSaveEnabled) return;
  // Only sync the primary Oracle workspace to SQLite; temp pages (agent code,
  // SQL/xlsx imports, pastes) must never clobber the cached schema.
  var active = workspaces.find(function(w){ return w.id === activeWorkspaceId; });
  if (!active || active.source !== 'oracle') return;
  clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(() => {
    saveStateToSQLite(false);
  }, 400);
}

// Toggle Subsystem Legend Visibility
function toggleSubsysLegend() {
  const legend = document.getElementById('subsysLegend');
  const btn = document.getElementById('subsysToggleBtn');
  if (!legend) return;
  const hidden = legend.style.display === 'none';
  legend.style.display = hidden ? '' : 'none';
  if (btn) {
    btn.style.opacity = hidden ? '1' : '0.45';
    btn.style.filter = hidden ? 'none' : 'grayscale(1)';
  }
}
function toggleRelLegend() {
  const legend = document.getElementById('relLegend');
  const btn = document.getElementById('relToggleBtn');
  if (!legend) return;
  const hidden = legend.style.display === 'none';
  legend.style.display = hidden ? '' : 'none';
  if (btn) {
    btn.style.opacity = hidden ? '1' : '0.45';
    btn.style.filter = hidden ? 'none' : 'grayscale(1)';
  }
}

// Save Full State to SQLite Backend & LocalStorage
async function saveStateToSQLite(showToastMsg = true) {
  const customColsPlain = {};
  Object.keys(tableCustomHiddenCols).forEach(k => {
    customColsPlain[k] = Array.from(tableCustomHiddenCols[k]);
  });

  const statePayload = {
    positions: tablePositions,
    hidden_cols: customColsPlain,
    visible_tables: Array.from(selectedTables),
    settings: {
      current_theme: currentTheme,
      current_lang: currentLang,
      global_view_mode: globalViewMode,
      zoom: zoom.toString(),
      pan_x: panX.toString(),
      pan_y: panY.toString(),
      is_sidebar_collapsed: isSidebarCollapsed ? "1" : "0"
    }
  };

  // 1. Mirror to localStorage
  localStorage.setItem('testr_erd_studio_bundle', JSON.stringify({
    positions: tablePositions,
    customCols: customColsPlain,
    globalViewMode: globalViewMode,
    theme: currentTheme,
    lang: currentLang
  }));
  try {
    localStorage.setItem('erd_theme', currentTheme);
    localStorage.setItem('erd_lang', currentLang);
  } catch(e) {}

  // 2. Post to SQLite Backend
  try {
    const res = await fetch('/api/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(statePayload)
    });
    if (res.ok && showToastMsg) {
 const msg = currentLang === 'ar' ? ' تم حفظ الترتيب في قاعدة بيانات SQLite' : ' Saved to SQLite Database!';
      showToast(msg);
    }
  } catch (err) {
 if (showToastMsg) showToast(currentLang === 'ar' ? ' تم الحفظ محلياً' : ' Saved locally');
  }
}

// Live Sync from DB (Oracle via saved connection by default)
async function syncWithOracleDB() {
 showToast(currentLang === 'ar' ? ' جاري تحميل المخطط من قاعدة البيانات...' : ' Loading schema from DB...');
  try {
    const payload = { dialect: dbCfg.dialect, params: {
      user: dbCfg.user, password: dbCfg.password,
      host: dbCfg.host, port: dbCfg.port,
      service_name: dbCfg.service
    } };
    if (dbCfg.dialect === 'sqlite_file') { payload.params = { path: dbCfg.file }; }
    else if (dbCfg.dialect !== 'oracle') { payload.params.database = dbCfg.service; }
    const res = await fetch('/api/connectors/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        isDbConnected = true;
        dbConnectionError = '';
        applySchemaPayload(result);
        refreshCurrentSchemaInfo();
        if (typeof updateStatusBar === 'function') updateStatusBar();
      } else {
        isDbConnected = false;
        dbConnectionError = result.error || result.detail || 'Sync failed';
        if (typeof updateStatusBar === 'function') updateStatusBar();
        throw new Error(dbConnectionError);
      }
    } else {
      isDbConnected = false;
      dbConnectionError = 'Sync failed - check DB connection';
      if (typeof updateStatusBar === 'function') updateStatusBar();
      throw new Error(dbConnectionError);
    }
  } catch (err) {
 showToast(' ' + err.message);
  }
}

// Bilingual Switcher
function toggleLanguage() {
  currentLang = currentLang === 'ar' ? 'en' : 'ar';
  try { localStorage.setItem('erd_lang', currentLang); } catch(e) {}
  applyLanguage(currentLang);
  scheduleAutoSave();
  showToast(currentLang === 'ar' ? 'تم التبديل إلى العربية' : 'Switched to English');
}

// ==================== MARKDOWN RENDERER (safe, compact) ====================
function _escapeHtml(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
window.__codeBlocks = [];
function _inlineMd(s) {
  return s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>')
    .replace(/~~(.+?)~~/g, '<del>$1</del>')
    .replace(/`([^`]+?)`/g, '<code>$1</code>')
    .replace(/\[([^\]]*?)\]\(([^)]*?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function mdToHtml(text) {
  if (!text) return '';
  var codes = [];
  var result = String(text).replace(/```(\w*)\n?([\s\S]*?)```/g, function(m, lang, code) {
    var langLabel = lang || 'code';
    var isSQL = /sql|ddl|oracle|mysql|postgres|sqlite|mssql|ansi/i.test(langLabel);
    var idx = codes.length;
    codes.push({
      lang: langLabel,
      text: String(code).replace(/\n$/, ''),
      isSQL: isSQL
    });
    return '\u0000CB' + idx + '\u0000';
  });
  result = result.split('\n').map(function(line) {
    var e = _escapeHtml(line);
    if (/^#{1,4}\s/.test(e)) {
      var lvl = e.match(/^(#{1,4})/)[1].length;
      return '<h' + lvl + '>' + _inlineMd(e.replace(/^#{1,4}\s+/, '')) + '</h' + lvl + '>';
    }
    if (/^>\s+/.test(e)) return '<blockquote>' + _inlineMd(e.replace(/^>\s+/, '')) + '</blockquote>';
    if (/^(-{3,}|\*{3,})\s*$/.test(e)) return '<hr>';
    if (/^\|.+\|$/.test(e)) return '|ROW|' + e;
    return e;
  }).join('\n');
  // tables (group consecutive |ROW| lines)
  result = result.replace(/((?:\|ROW\|[^\n]*\n?)+)/g, function(block) {
    var rows = block.split('\n').filter(function(r) { return /^\|ROW\|/.test(r); });
    var html = '<table>';
    rows.forEach(function(r, i) {
      var cells = r.replace(/^\|ROW\|/, '').replace(/\s*\|\s*/g, '|').split('|').filter(function(c, j, a) { return !(j === 0 && a.length && c === '') && !(j === a.length - 1 && c === ''); }).map(function(c) { return c.trim(); });
      var tag = (i === 1 && cells.length >= 1 && cells.every(function(c){ return /^-{2,}$/.test(c); })) ? '_-' : (i === 0 ? 'th' : 'td');
      if (tag === '_-') return '';
      return '<tr>' + cells.map(function(c) { return '<' + tag + '>' + _inlineMd(c) + '</' + tag + '>'; }).join('') + '</tr>';
    });
    return html + '</table>';
  });
  // lists
  result = result.replace(/(?:^|\n)[ \t]*[-*+][ \t]+(.+)(?:\n[ \t]*[-*+][ \t]+.+)*/g, function(m) {
    var items = m.split('\n').map(function(x) { return x.replace(/^[ \t]*[-*+][ \t]+/, ''); });
    return '<ul>' + items.map(function(i) { return '<li>' + _inlineMd(i.trim()) + '</li>'; }).join('') + '</ul>';
  });
  result = result.replace(/(?:^|\n)[ \t]*\d+[.][ \t]+(.+)(?:\n[ \t]*\d+[.][ \t]+.+)*/g, function(m) {
    var items = m.split('\n').map(function(x) { return x.replace(/^[ \t]*\d+[.][ \t]+/, ''); });
    return '<ol>' + items.map(function(i) { return '<li>' + _inlineMd(i.trim()) + '</li>'; }).join('') + '</ol>';
  });
  // Format prose while fenced code is still protected by placeholders.
  // Formatting restored SQL would insert paragraph/BR tags inside <pre><code>,
  // losing newlines in textContent and extending -- comments over later DDL.
  result = result.split(/\n{2,}/).map(function(p) {
    p = p.trim();
    if (!p) return '';
    if (/^\u0000CB\d+\u0000$/.test(p)) return p;
    if (/^<(h[1-4]|ul|ol|li|table|blockquote|hr|div)/.test(p)) return p;
    return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
  }).filter(Boolean).join('\n');
  // Restore code only after all prose formatting is complete.
  result = result.replace(/\u0000CB(\d+)\u0000/g, function(m, idx) {
    var c = codes[parseInt(idx, 10)];
    if (!c) return '';
    var langLabel = (i18n[currentLang] && i18n[currentLang].codeLangLabel) ? ((i18n[currentLang].codeLangLabel).replace('{lang}', c.lang)) : c.lang;
    return '<div class="ai-codeblock" data-ws-code="' + window.__codeBlocks.length + '"><div class="ai-code-head">' +
      '<span class="ai-code-lang">' + _escapeHtml(c.lang) + '</span>' +
      '<span class="ai-code-actions">' +
      '<button class="ai-code-btn ai-copy-btn">' + _escapeHtml((i18n[currentLang] && i18n[currentLang].copyCode) || 'Copy') + '</button>' +
      (c.isSQL ? '<button class="ai-code-btn ai-use-code-btn">' + _escapeHtml((i18n[currentLang] && i18n[currentLang].useThisCode) || 'Use this code') + '</button>' +
 '<button class="ai-code-btn ai-dictionary-btn"> ' + (currentLang === 'ar' ? 'قاموس البيانات' : 'Data Dictionary') + '</button>' +
 '<button class="ai-code-btn ai-download-sql-btn"> SQL</button>' : '') +
      '</span></div><pre><code>' + _escapeHtml(c.text) + '</code></pre></div>';
  });
  window.__codeBlocks = codes;
  return result;
}
// Delegated handler for code-block buttons inside #aiMessages
function bindAiCodeButtons() {
  var box = document.getElementById('aiMessages');
  if (!box) return;
  box.removeEventListener('click', _aiCodeClickHandler);
  box.addEventListener('click', _aiCodeClickHandler);
}
function _aiCodeClickHandler(ev) {
  var btn = ev.target && ev.target.closest ? ev.target.closest('button') : null;
  if (!btn) return;
  var block = btn.closest('.ai-codeblock');
  if (!block) return;
  var codeEl = block.querySelector('pre code');
  var text = codeEl ? codeEl.textContent : '';
  if (btn.classList.contains('ai-copy-btn')) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function(){});
    } else {
      var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch(e) {}
      document.body.removeChild(ta);
    }
 var orig = btn.textContent; btn.textContent = (i18n[currentLang] && i18n[currentLang].codeCopied) || ' Copied'; setTimeout(function() { btn.textContent = orig; }, 1500);
  } else if (btn.classList.contains('ai-use-code-btn') || btn.classList.contains('ai-dictionary-btn') || btn.classList.contains('ai-download-sql-btn')) {
    // Collect ALL code blocks within the same assistant message so that when
    // the model replies with one SQL block per table, the whole script is used.
    var msgBox = block.closest('.ai-msg');
    var allText = '';
    (msgBox ? msgBox.querySelectorAll('.ai-codeblock pre code') : []).forEach(function(el) {
      var t = el.textContent || '';
      if (t.trim()) allText += t + '\n\n';
    });
    const sql = allText.trim() || text;
    if (btn.classList.contains('ai-dictionary-btn')) dictionaryFromCode(sql);
    else if (btn.classList.contains('ai-download-sql-btn')) downloadQuickBlob(new Blob([sql], {type: 'text/sql;charset=utf-8'}), 'assistant.sql');
    else applyAgentCode(sql);
  }
}

// ==================== WORKSPACE / MULTI-PAGE MANAGER ====================
let workspaces = [];
let activeWorkspaceId = null;
const WS_KEY = 'testr_erd_workspaces_v2';
const WS_ICONS = {
  oracle: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
  sql: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
  xlsx: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>',
  'agent-code': '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><rect x="4" y="8" width="16" height="12" rx="2"/></svg>',
  paste: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>',
  duplicate: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  saved: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg>'
};
const WS_NAMES_AR = { oracle: 'أوراكل', sql: 'ملف SQL', xlsx: 'قاموس بيانات', 'agent-code': 'كود الوكيل', paste: 'DDL ملصق', duplicate: 'نسخة', saved: 'نسخة محفوظة' };
const WS_NAMES_EN = { oracle: 'Oracle', sql: 'SQL', xlsx: 'Dictionary', 'agent-code': 'Agent DDL', paste: 'Pasted DDL', duplicate: 'Copy', saved: 'Restored' };
function _wsObj(id, cfg) {
  cfg = cfg || {};
  return {
    id: id,
    name: cfg.name || 'صفحة جديدة',
    source: cfg.source || 'oracle',
    tablesData: cfg.tablesData || null,
    fkList: cfg.fkList || [],
    allTables: cfg.allTables || [],
    comTables: cfg.comTables || [],
    rafTables: cfg.rafTables || [],
    selectedTables: cfg.selectedTables || new Set(),
    selectedTableNodes: cfg.selectedTableNodes || new Set(),
    tablePositions: cfg.tablePositions || {},
    tableCustomHiddenCols: cfg.tableCustomHiddenCols || {},
    subsystemData: cfg.subsystemData || null,
    subsystemMapping: cfg.subsystemMapping || {},
    viewMode: cfg.viewMode || 'no-audit',
    zoom: (cfg.zoom != null) ? cfg.zoom : 0.85,
    tableWidth: cfg.tableWidth || TABLE_WIDTH,
    dialect: cfg.dialect || 'oracle',
  };
}
function _captureCurrentInto(w) {
  w.tablesData = tablesData; w.fkList = fkList; w.allTables = allTables; w.comTables = comTables; w.rafTables = rafTables;
  w.selectedTables = (selectedTables instanceof Set) ? new Set(selectedTables) : new Set(Array.isArray(selectedTables) ? selectedTables : []);
  w.selectedTableNodes = (selectedTableNodes instanceof Set) ? new Set(selectedTableNodes) : new Set(Array.isArray(selectedTableNodes) ? selectedTableNodes : []);
  w.tablePositions = JSON.parse(JSON.stringify(tablePositions || {}));
  w.tableCustomHiddenCols = {};
  Object.keys(tableCustomHiddenCols || {}).forEach(function(k) {
    var v = tableCustomHiddenCols[k];
    w.tableCustomHiddenCols[k] = (v instanceof Set) ? new Set(v) : new Set(Array.isArray(v) ? v : []);
  });
  w.subsystemData = subsystemData; w.subsystemMapping = subsystemMapping;
  w.viewMode = globalViewMode; w.zoom = zoom; w.tableWidth = TABLE_WIDTH; w.dialect = window.currentDialect || 'oracle';
}
function _applyWorkspaceToGlobal(w) {
  const exportPreview = document.getElementById('exportPreview');
  if (exportPreview) { exportPreview.value = ''; exportPreview.style.display = 'none'; }

  // Oracle workspace always reflects the live database schema
  if (w.source === 'oracle' && window._liveSchema && window._liveSchema.tablesData && Object.keys(window._liveSchema.tablesData).length > 0) {
    w.tablesData = window._liveSchema.tablesData;
    w.fkList = window._liveSchema.fkList;
    w.allTables = Object.keys(w.tablesData);
    w.comTables = w.allTables.filter(function(t) { return t.indexOf('COM_') === 0; });
    w.rafTables = w.allTables.filter(function(t) { return t.indexOf('RAF_') === 0; });
  }

  tablesData = w.tablesData || {};
  fkList = w.fkList || [];
  allTables = (w.allTables || Object.keys(tablesData));
  comTables = w.comTables || allTables.filter(function(t) { return t.indexOf('COM_') === 0; });
  rafTables = w.rafTables || allTables.filter(function(t) { return t.indexOf('RAF_') === 0; });
  selectedTables = (w.selectedTables instanceof Set) ? new Set(w.selectedTables) : new Set(Array.isArray(w.selectedTables) ? w.selectedTables : []);
  if (selectedTables.size === 0 && allTables.length > 0) {
    selectedTables = new Set(allTables);
  }
  selectedTableNodes = (w.selectedTableNodes instanceof Set) ? new Set(w.selectedTableNodes) : new Set(Array.isArray(w.selectedTableNodes) ? w.selectedTableNodes : []);
  tablePositions = JSON.parse(JSON.stringify(w.tablePositions || {}));
  tableCustomHiddenCols = {};
  Object.keys(w.tableCustomHiddenCols || {}).forEach(function(k) {
    var v = w.tableCustomHiddenCols[k];
    tableCustomHiddenCols[k] = (v instanceof Set) ? new Set(v) : new Set(Array.isArray(v) ? v : []);
  });
  subsystemData = w.subsystemData; subsystemMapping = w.subsystemMapping || {};
  activeSubsystemFilter = '';
  if (w.viewMode) { globalViewMode = w.viewMode; var el = document.getElementById('globalViewModeSelect'); if (el) el.value = globalViewMode; }
  if (w.zoom) zoom = w.zoom;
  if (w.tableWidth) TABLE_WIDTH = w.tableWidth;
  window.currentDialect = w.dialect;
  document.documentElement.setAttribute('data-dialect', w.dialect || 'oracle');
  normalizePositions();
}
function _sanitizeWsForStorage(w) {
  var s = Object.assign({}, w);
  s.selectedTables = Array.from(w.selectedTables || []);
  s.selectedTableNodes = Array.from(w.selectedTableNodes || []);
  s.tableCustomHiddenCols = {};
  Object.keys(w.tableCustomHiddenCols || {}).forEach(function(k) { s.tableCustomHiddenCols[k] = Array.from(w.tableCustomHiddenCols[k] || []); });
  return s;
}
function _restoreWsFromStorage(s) {
  var w = Object.assign({}, s);
  w.selectedTables = (s.selectedTables instanceof Set) ? new Set(s.selectedTables) : new Set(Array.isArray(s.selectedTables) ? s.selectedTables : []);
  w.selectedTableNodes = (s.selectedTableNodes instanceof Set) ? new Set(s.selectedTableNodes) : new Set(Array.isArray(s.selectedTableNodes) ? s.selectedTableNodes : []);
  w.tableCustomHiddenCols = {};
  Object.keys(s.tableCustomHiddenCols || {}).forEach(function(k) {
    var v = s.tableCustomHiddenCols[k];
    w.tableCustomHiddenCols[k] = (v instanceof Set) ? new Set(v) : new Set(Array.isArray(v) ? v : []);
  });
  return w;
}
function _saveWorkspacesLocal() {
  if (!workspaces || workspaces.length === 0) return;
  try { localStorage.setItem(WS_KEY, JSON.stringify(workspaces.map(_sanitizeWsForStorage))); } catch(e) {}
}
function _loadWorkspacesLocal() {
  try { var d = localStorage.getItem(WS_KEY); return d ? JSON.parse(d) : null; } catch(e) { return null; }
}
function _nextWsId() { return workspaces.length > 0 ? Math.max.apply(null, workspaces.map(function(w) { return w.id; })) + 1 : 0; }
function renderWsBar() {
  var bar = document.getElementById('wsBar'); if (!bar) return;
  var isRTL = currentLang === 'ar';
  bar.dir = isRTL ? 'rtl' : 'ltr';
  bar.innerHTML = '';

  var tabsWrap = document.createElement('div');
  tabsWrap.className = 'ws-tabs-wrapper';

  workspaces.forEach(function(w) {
    var tab = document.createElement('div');
    tab.className = 'ws-tab' + (w.id === activeWorkspaceId ? ' active' : '');
    tab.onclick = function() { activateWorkspace(w.id); };
    var icon = document.createElement('span'); icon.className = 'ws-tab-icon'; icon.innerHTML = WS_ICONS[w.source] || '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>';
    var nm = document.createElement('span'); nm.className = 'ws-tab-name'; nm.textContent = w.name || '—';
    nm.title = w.name;
    var chip = document.createElement('span'); chip.className = 'ws-src-chip';
    chip.textContent = (isRTL ? WS_NAMES_AR[w.source] : WS_NAMES_EN[w.source]) || w.source;
    var acts = document.createElement('span'); acts.className = 'ws-tab-actions';
    var openBtn = document.createElement('button');
    openBtn.className = 'ws-tab-open';
    openBtn.title = isRTL ? 'فتح في نافذة جديدة' : 'Open in new tab';
    openBtn.setAttribute('aria-label', openBtn.title);
    openBtn.innerHTML = '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>';
    openBtn.onclick = function(e) {
      e.stopPropagation();
      var parts = (location.search || '').replace(/^\?/, '').split('&').filter(function(x) { return x && x.indexOf('w=') !== 0; });
      parts.push('w=' + w.id);
      window.open(location.pathname + '?' + parts.join('&'), '_blank');
    };
    acts.appendChild(openBtn);

    var closeBtn = document.createElement('button');
    closeBtn.className = 'ws-tab-x';
    closeBtn.title = isRTL ? 'إغلاق الصفحة' : 'Close page';
    closeBtn.setAttribute('aria-label', closeBtn.title);
    closeBtn.innerHTML = '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    closeBtn.onclick = function(e) {
      e.stopPropagation();
      closeWorkspace(w.id);
    };
    acts.appendChild(closeBtn);

    tab.appendChild(icon); tab.appendChild(nm); tab.appendChild(chip); tab.appendChild(acts);
    tabsWrap.appendChild(tab);
  });

  var addBtn = document.createElement('button');
  addBtn.className = 'ws-add';
  addBtn.textContent = '+ ' + (isRTL ? 'جديد' : 'New');
  addBtn.onclick = function() { toggleNewPageModal(true); };
  tabsWrap.appendChild(addBtn);

  bar.appendChild(tabsWrap);

  var quickActions = document.createElement('div');
  quickActions.className = 'ws-quick-actions';
  quickActions.innerHTML = 
    '<div class="select-with-icon">' +
      '<span class="select-prefix-icon"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg></span>' +
      '<select class="select-clean with-prefix-icon" id="quickActionSelect" aria-label="Quick Actions" onchange="runQuickAction(this.value); this.value=\'\';">' +
        '<option value="">' + (isRTL ? '⋯ المزيد...' : '⋯ More...') + '</option>' +
        '<option value="audit_linter">' + (isRTL ? '🔍 فاحص الجودة المعمارية (Linter)' : '🔍 Schema Architecture Linter') + '</option>' +
        '<option value="audit_diff">' + (isRTL ? '⚖️ مقارنة المخططات والترقية (Diff)' : '⚖️ Schema Diff & Migration') + '</option>' +
        '<option value="audit_mock">' + (isRTL ? '🎲 توليد بيانات تجريبية (Mock Data)' : '🎲 Smart Mock Data Generator') + '</option>' +
        '<option value="report_html">' + (isRTL ? '📊 تقرير HTML تفاعلي (.html)' : '📊 Interactive HTML Report (.html)') + '</option>' +
        '<option value="report_pdf">' + (isRTL ? '📑 تقرير PDF معماري (.pdf)' : '📑 Executive PDF Report (.pdf)') + '</option>' +
        '<option value="dictionary">' + (isRTL ? '📖 قاموس Excel (.xlsx)' : '📖 Excel Dictionary (.xlsx)') + '</option>' +
        '<option value="sql">' + (isRTL ? '💾 تنزيل سكربت SQL' : '💾 Download SQL') + '</option>' +
        '<option value="svg">' + (isRTL ? '🖼 تصدير صورة SVG' : '🖼 Export SVG') + '</option>' +
        '<option value="preview">' + (isRTL ? '👁 معاينة كود SQL' : '👁 Preview SQL') + '</option>' +
        '<option value="copy">' + (isRTL ? '📋 نسخ كود SQL' : '📋 Copy SQL') + '</option>' +
        '<option value="state">' + (isRTL ? '📦 تصدير لقطة JSON' : '📦 Export JSON') + '</option>' +
      '</select>' +
    '</div>';

  bar.appendChild(quickActions);
}
function activateWorkspace(id) {
  if (id === activeWorkspaceId || !workspaces.length) return;
  var target = workspaces.find(function(w) { return w.id === id; });
  if (!target) return;
  var current = workspaces.find(function(w) { return w.id === activeWorkspaceId; });
  if (current) _captureCurrentInto(current);
  activeWorkspaceId = id;
  _applyWorkspaceToGlobal(target);
  buildSidebarList(); updateSubsysFilterOptions(); renderLegend(); renderAll();
  setTimeout(fitView, 60);
  renderWsBar();
  scheduleAutoSave();
}
function closeWorkspace(id) {
  var isRTL = currentLang === 'ar';
  if (workspaces.length <= 1) {
    var resetWs = _wsObj(_nextWsId(), {
      name: isRTL ? 'المخطط الأساسي' : 'Main Schema',
      source: 'oracle'
    });
    workspaces = [resetWs];
    activeWorkspaceId = resetWs.id;
    _applyWorkspaceToGlobal(resetWs);
    buildSidebarList(); updateSubsysFilterOptions(); renderLegend(); renderAll();
    setTimeout(fitView, 60);
    _saveWorkspacesLocal();
    renderWsBar();
    showToast(isRTL ? 'تم إغلاق التبويب وبدء مخطط جديد' : 'Tab closed, started fresh schema');
    return;
  }
  var idx = workspaces.findIndex(function(w) { return w.id === id; });
  if (idx === -1) return;
  var closedName = workspaces[idx].name || '';
  workspaces.splice(idx, 1);
  if (activeWorkspaceId === id) {
    var next = workspaces[Math.min(idx, workspaces.length - 1)];
    _applyWorkspaceToGlobal(next);
    activeWorkspaceId = next.id;
    buildSidebarList(); updateSubsysFilterOptions(); renderLegend(); renderAll();
    setTimeout(fitView, 60);
  }
  _saveWorkspacesLocal();
  renderWsBar();
  showToast((isRTL ? 'تم إغلاق التبويب: ' : 'Closed tab: ') + closedName);
}
function createWorkspaceFromPayload(cfg) {
  var sd = cfg.schema || {};
  var allT = Object.keys(sd.tablesData || {});
  var w = _wsObj(_nextWsId(), {
    name: cfg.name || 'صفحة جديدة',
    source: cfg.source || 'agent-code',
    tablesData: sd.tablesData || {},
    fkList: sd.fkList || [],
    allTables: allT,
    comTables: allT.filter(function(t) { return t.indexOf('COM_') === 0; }),
    rafTables: allT.filter(function(t) { return t.indexOf('RAF_') === 0; }),
    selectedTables: new Set(allT),
    subsystemData: cfg.subsystems || null,
    subsystemMapping: (cfg.subsystems && cfg.subsystems.mapping) || {},
    viewMode: 'no-audit',
    zoom: 0.85,
    dialect: sd.dialect || 'oracle',
  });
  workspaces.push(w);
  activeWorkspaceId = w.id;
  _applyWorkspaceToGlobal(w);
  buildSidebarList(); updateSubsysFilterOptions(); renderLegend();
  calculateInitialLayout('hierarchical');
  renderAll();
  setTimeout(fitView, 60);
  _saveWorkspacesLocal();
  renderWsBar();
  if (currentView !== 'canvas') switchView('canvas');
 showToast((currentLang === 'ar' ? ' تم فتح الصفحة: ' : ' Opened page: ') + w.name);
}
async function applyAgentCode(sqlText) {
 if (!sqlText || !String(sqlText).trim()) { showToast(' لا يوجد كود'); return; }
 showToast((currentLang === 'ar') ? ' جاري تحليل كود الوكيل...' : ' Parsing agent DDL...');
  try {
    var res = await fetch('/api/schema/parse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql: String(sqlText) }) });
    var data = await res.json();
    if (!data.success) throw new Error(data.detail || 'Parse failed');
    var keys = Object.keys(data.schema.tablesData || {});
    var shortName = keys[0] ? (keys[0].substring(0, 24)) : 'Agent';
    createWorkspaceFromPayload({ name: 'AI ' + shortName, source: 'agent-code', schema: data.schema });
 } catch (err) { showToast(' ' + err.message); }
}
async function initWorkspaces() {
  var isRTL = currentLang === 'ar';
  var liveTd = (window._liveSchema && window._liveSchema.tablesData) || tablesData || {};
  var liveFk = (window._liveSchema && window._liveSchema.fkList) || fkList || [];
  var liveAll = Object.keys(liveTd);

  var saved = _loadWorkspacesLocal();
  if (saved && Array.isArray(saved) && saved.length > 0) {
    workspaces = saved.map(_restoreWsFromStorage);
  } else {
    workspaces = [];
  }

  // Ensure Oracle primary workspace always exists and is synced with the live schema
  var oracleWs = workspaces.find(function(w) { return w.source === 'oracle'; });
  if (!oracleWs) {
    oracleWs = _wsObj(0, {
      name: isRTL ? 'المخطط الأساسي' : 'Main Schema',
      source: 'oracle',
      tablesData: liveTd,
      fkList: liveFk,
      allTables: liveAll,
      selectedTables: new Set(liveAll)
    });
    workspaces.unshift(oracleWs);
  } else {
    // Keep oracle workspace synced to live schema, avoiding stale/obsolete cached tables
    if (liveAll.length > 0) {
      oracleWs.tablesData = liveTd;
      oracleWs.fkList = liveFk;
      oracleWs.allTables = liveAll;
      oracleWs.comTables = liveAll.filter(function(t) { return t.indexOf('COM_') === 0; });
      oracleWs.rafTables = liveAll.filter(function(t) { return t.indexOf('RAF_') === 0; });
      var validSet = new Set(liveAll);
      var prunedSel = new Set();
      (oracleWs.selectedTables || []).forEach(function(t) { if (validSet.has(t)) prunedSel.add(t); });
      oracleWs.selectedTables = prunedSel.size > 0 ? prunedSel : new Set(liveAll);
    }
  }

  // Sanitize all workspaces: purge any legacy demo workspaces with obsolete prefixes
  workspaces = workspaces.filter(function(w) {
    if (w.source !== 'oracle' && w.tablesData) {
      var keys = Object.keys(w.tablesData);
      var hasLegacy = keys.some(function(k) { return k.startsWith('COM_') || k.startsWith('RAF_'); });
      if (hasLegacy && !liveAll.some(function(k) { return k.startsWith('COM_') || k.startsWith('RAF_'); })) {
        return false;
      }
    }
    return true;
  });

  workspaces.forEach(function(w) {
    if (w.source === 'oracle') {
      w.tablesData = liveTd;
      w.fkList = liveFk;
      w.allTables = liveAll;
    }
  });

  if (activeWorkspaceId === null || !workspaces.some(function(w) { return w.id === activeWorkspaceId; })) {
    activeWorkspaceId = workspaces[0].id;
  }

  var params = new URLSearchParams(window.location.search);
  var wParam = params.get('w');
  if (wParam !== null) {
    var targetId = parseInt(wParam, 10);
    if (!isNaN(targetId) && workspaces.some(function(w) { return w.id === targetId; })) {
      activeWorkspaceId = targetId;
    }
  }

  var activeWs = workspaces.find(function(w) { return w.id === activeWorkspaceId; }) || workspaces[0];
  _applyWorkspaceToGlobal(activeWs);
  renderWsBar();
  _saveWorkspacesLocal();
  buildSidebarList(); updateSubsysFilterOptions(); renderLegend(); renderAll();
  setTimeout(fitView, 60);
}
// ---- New page / source modal ----
function toggleNewPageModal(show) {
  var modal = document.getElementById('newPageModal');
  if (!modal) return;
  modal.style.display = show ? 'flex' : 'none';
  if (!show) return;
  var t = (typeof i18n !== 'undefined' && i18n[currentLang]) || (window.i18n && window.i18n[currentLang]) || {};
  var list = document.getElementById('newPageSourceList');
  list.innerHTML = '';

  var grid = document.createElement('div');
  grid.className = 'newpage-grid';
  var cards = [
    {
      src: 'oracle',
      ico: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
      name: t.srcOracle || (currentLang === 'ar' ? 'اتصال أوراكل مباشر' : 'Live Oracle Connection'),
      sub: t.srcOracleSub || (currentLang === 'ar' ? 'جلب المخطط مباشرة من قاعدة البيانات المتصلة (نسخة قابلة للتعديل).' : 'Fetch live schema straight from connected database into an independent workspace.'),
      fn: function(){ toggleNewPageModal(false); createPageOracle(); }
    },
    {
      src: 'sql',
      ico: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
      name: t.srcSql || (currentLang === 'ar' ? 'ملف SQL / DDL' : 'SQL / DDL File'),
      sub: t.srcSqlSub || (currentLang === 'ar' ? 'ارفع ملف .sql أو .ddl — يُنشئ صفحة جديدة بالجداول والعلاقات.' : 'Upload a .sql or .ddl script to parse and visualize tables and relations.'),
      fn: function(){ toggleNewPageModal(false); createPageSql(); }
    },
    {
      src: 'xlsx',
      ico: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>',
      name: t.srcXlsx || (currentLang === 'ar' ? 'قاموس بيانات Excel (xlsx)' : 'Excel Data Dictionary'),
      sub: t.srcXlsxSub || (currentLang === 'ar' ? 'ملف أو عدة ملفات Excel بتعريفات الجداول تُدمج في صفحة واحدة.' : 'Import table definitions and foreign keys from .xlsx workbook sheets.'),
      fn: function(){ toggleNewPageModal(false); createPageXlsx(); }
    },
    {
      src: 'paste',
      ico: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/></svg>',
      name: t.srcPaste || (currentLang === 'ar' ? 'لصق كود SQL مباشر' : 'Paste SQL Code'),
      sub: t.srcPasteSub || (currentLang === 'ar' ? 'الصق كود DDL في مربع منبثق ويُرسم المخطط فورًا.' : 'Paste raw CREATE TABLE scripts directly into a prompt to generate diagram.'),
      fn: function(){ toggleNewPageModal(false); createPagePaste(); }
    }
  ];
  cards.forEach(function(c) {
    var card = document.createElement('div');
    card.className = 'newpage-card';
    card.onclick = c.fn;
    card.innerHTML = '<div class="np-ico">' + c.ico + '</div><div class="np-name">' + _escapeHtml(c.name) + '</div><div class="np-sub">' + _escapeHtml(c.sub) + '</div>';
    grid.appendChild(card);
  });
  list.appendChild(grid);
}
function createPageOracle() {
  var w = _wsObj(_nextWsId(), { name: (currentLang === 'ar') ? 'أوراكل' : 'Oracle', source: 'oracle' });
  w.tablesData = JSON.parse(JSON.stringify(tablesData || {}));
  w.fkList = JSON.parse(JSON.stringify(fkList || []));
  w.allTables = allTables.slice(); w.comTables = comTables.slice(); w.rafTables = rafTables.slice();
  w.selectedTables = new Set(selectedTables); w.selectedTableNodes = new Set(selectedTableNodes);
  w.tablePositions = JSON.parse(JSON.stringify(tablePositions || {}));
  w.tableCustomHiddenCols = {};
  Object.keys(tableCustomHiddenCols || {}).forEach(function(k) { w.tableCustomHiddenCols[k] = new Set(tableCustomHiddenCols[k]); });
  w.subsystemData = subsystemData; w.subsystemMapping = subsystemMapping;
  w.viewMode = globalViewMode; w.zoom = zoom; w.tableWidth = TABLE_WIDTH; w.dialect = window.currentDialect || 'oracle';
  workspaces.push(w);
  activeWorkspaceId = w.id;
  _applyWorkspaceToGlobal(w);
  buildSidebarList(); updateSubsysFilterOptions(); renderLegend();
  calculateInitialLayout('hierarchical'); renderAll(); setTimeout(fitView, 60);
  _saveWorkspacesLocal(); renderWsBar();
  if (currentView !== 'canvas') switchView('canvas');
}
function createPageSql() {
  var input = document.createElement('input');
  input.type = 'file'; input.accept = '.sql,.ddl,.txt';
  input.onchange = async function() {
    var file = input.files && input.files[0]; if (!file) return;
 showToast((currentLang === 'ar') ? ' جاري تحليل ملف SQL...' : ' Parsing SQL...');
    try {
      var res = await fetch('/api/schema/parse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql: await file.text() }) });
      var data = await res.json();
      if (!data.success) throw new Error(data.detail || 'Parse failed');
      createWorkspaceFromPayload({ name: (file.name.replace(/\.(sql|ddl|txt)$/i, '') || 'SQL'), source: 'sql', schema: data.schema });
 } catch (err) { showToast(' ' + err.message); }
  };
  input.click();
}
function createPageXlsx() {
  var input = document.createElement('input');
  input.type = 'file'; input.multiple = true; input.accept = '.xlsx,.xlsm';
  input.onchange = async function() {
    if (!input.files || input.files.length === 0) return;
 showToast((currentLang === 'ar') ? ' جاري تحليل قاموس البيانات...' : ' Parsing data dictionary...');
    var fd = new FormData();
    for (var i = 0; i < input.files.length; i++) fd.append('files', input.files[i]);
    fd.append('dialect', window.currentDialect || 'oracle');
    fd.append('include_drop', 'true');
    fd.append('store', 'false');
    fd.append('audit', 'keep');
    try {
      var res = await fetch('/api/dictionary/import', { method: 'POST', body: fd });
      var data = await res.json();
      if (!data.success) throw new Error(data.detail || 'Import failed');
      createWorkspaceFromPayload({ name: (input.files[0].name.replace(/\.xlsx?$/i, '') || 'Dictionary'), source: 'xlsx', schema: data.schema });
 } catch (err) { showToast(' ' + err.message); }
  };
  input.click();
}
function togglePasteSqlModal(show) {
  var modal = document.getElementById('pasteSqlModal');
  if (!modal) return;
  modal.style.display = show ? 'flex' : 'none';
  if (show) {
    var ta = document.getElementById('pasteSqlInput');
    if (ta) {
      ta.value = '';
      setTimeout(function() { ta.focus(); }, 60);
    }
  }
}

async function pasteFromClipboard() {
  try {
    var text = await navigator.clipboard.readText();
    var ta = document.getElementById('pasteSqlInput');
    if (ta && text) {
      ta.value = text;
      ta.focus();
    }
  } catch (err) {
    showToast(currentLang === 'ar' ? 'تعذر القراءة من الحافظة' : 'Could not read from clipboard');
  }
}

function submitPasteSql() {
  var ta = document.getElementById('pasteSqlInput');
  var text = ta ? ta.value.trim() : '';
  if (!text) {
    showToast(currentLang === 'ar' ? 'يرجى لصق كود SQL' : 'Please paste SQL code');
    return;
  }
  togglePasteSqlModal(false);
  applyAgentCode(text);
}

function createPagePaste() {
  toggleNewPageModal(false);
  togglePasteSqlModal(true);
}

window.togglePasteSqlModal = togglePasteSqlModal;
window.pasteFromClipboard = pasteFromClipboard;
window.submitPasteSql = submitPasteSql;
// expose for inline handlers
window.applyAgentCode = applyAgentCode;
window.toggleNewPageModal = toggleNewPageModal;
window.activateWorkspace = activateWorkspace;
window.openNewPageFromModal = function(src) { toggleNewPageModal(true); };

function applyLanguage(lang) {
  try { localStorage.setItem('erd_lang', lang); } catch(e) {}
  const t = i18n[lang];
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.body.dir = lang === 'ar' ? 'rtl' : 'ltr';

  const updateBtnText = (btnId, text) => {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    const labelSpan = btn.querySelector('.btn-label-text');
    if (labelSpan) {
      labelSpan.textContent = text;
    } else {
      let found = false;
      for (const node of btn.childNodes) {
        if (node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()) {
          node.nodeValue = ' ' + text;
          found = true;
          break;
        }
      }
      if (!found) {
        btn.title = text;
      }
    }
  };

  // langToggleBtn keeps SVG icon
  if (document.getElementById('searchInput')) document.getElementById('searchInput').placeholder = t.searchPlaceholder;
  if (document.getElementById('i18n-pasteModalTitle') && t.pasteModalTitle) document.getElementById('i18n-pasteModalTitle').textContent = t.pasteModalTitle;
  if (document.getElementById('i18n-pasteModalSub') && t.pasteModalSub) document.getElementById('i18n-pasteModalSub').textContent = t.pasteModalSub;
  if (document.getElementById('i18n-pasteInputLabel') && t.pasteInputLabel) document.getElementById('i18n-pasteInputLabel').textContent = t.pasteInputLabel;
  updateBtnText('i18n-pasteClipboardBtn', t.pasteClipboardBtn);
  updateBtnText('i18n-pasteCancelBtn', t.pasteCancelBtn);
  updateBtnText('i18n-pasteSubmitBtn', t.pasteSubmitBtn);
  if (document.getElementById('i18n-relModalTitle') && t.relModalTitle) {
    const titleSpan = document.querySelector('#i18n-relModalTitle span');
    if (titleSpan) titleSpan.textContent = t.relModalTitle;
  }
  if (document.getElementById('i18n-relParentTag') && t.relParentTag) document.getElementById('i18n-relParentTag').textContent = t.relParentTag;
  if (document.getElementById('i18n-relChildTag') && t.relChildTag) document.getElementById('i18n-relChildTag').textContent = t.relChildTag;
  if (document.getElementById('i18n-propFkName') && t.relPropFkName) document.getElementById('i18n-propFkName').textContent = t.relPropFkName;
  if (document.getElementById('i18n-propCard') && t.relPropCard) document.getElementById('i18n-propCard').textContent = t.relPropCard;
  if (document.getElementById('i18n-propNature') && t.relPropNature) document.getElementById('i18n-propNature').textContent = t.relPropNature;
  if (document.getElementById('i18n-propNull') && t.relPropNull) document.getElementById('i18n-propNull').textContent = t.relPropNull;
  if (document.getElementById('i18n-relSqlTitle') && t.relSqlTitle) document.getElementById('i18n-relSqlTitle').textContent = t.relSqlTitle;
  updateBtnText('relCopySqlBtn', t.relCopySqlText);
  updateBtnText('i18n-relFocusBtn', t.relFocusBtn);
  updateBtnText('i18n-relAiBtn', t.relAiBtn);
  updateBtnText('i18n-relCloseBtn', t.relCloseBtn);
  renderFilterChips();
  updateSubsysFilterOptions();
  updateThemeSwitchUI();
  updateControlIcons();
  updateSidebarToggleIcon();

  updateBtnText('i18n-exportSvg', t.exportSvg);
  updateBtnText('i18n-exportPng', t.exportPng);
  updateBtnText('i18n-saveLayout', t.saveLayout);
  updateBtnText('i18n-resetLayout', t.resetLayout);

  document.getElementById('opt-hierarchical').textContent = t.presetHierarchical;
  document.getElementById('opt-grid').textContent = t.presetGrid;
  document.getElementById('opt-cluster').textContent = t.presetCluster;
  document.getElementById('opt-circular').textContent = t.presetCircular;
  document.getElementById('opt-force').textContent = t.presetForce;
  if (document.getElementById('opt-star')) document.getElementById('opt-star').textContent = t.presetStar;

  if (document.getElementById('opt-dark')) document.getElementById('opt-dark').textContent = t.themeDark;
  if (document.getElementById('opt-mermaid')) document.getElementById('opt-mermaid').textContent = t.themeMermaid;
  if (document.getElementById('opt-academic')) document.getElementById('opt-academic').textContent = t.themeAcademic;
  if (document.getElementById('opt-light')) document.getElementById('opt-light').textContent = t.themeLight;
  updateThemeSwitchUI();
  updateControlIcons();

  document.getElementById('opt-no-audit').textContent = t.viewNoAudit;
  document.getElementById('opt-keys-only').textContent = t.viewKeysOnly;
  document.getElementById('opt-all-columns').textContent = t.viewAllCols;

  updateBtnText('i18n-btnManageCols', t.btnManageCols);
  updateBtnText('i18n-btnHideAudit', t.btnHideAudit);
  updateBtnText('i18n-btnKeysOnly', t.btnKeysOnly);
  updateBtnText('i18n-btnShowAll', t.btnShowAll);
  updateBtnText('i18n-btnMultiNoAudit', t.btnMultiNoAudit);
  updateBtnText('i18n-btnMultiKeysOnly', t.btnMultiKeysOnly);
  updateBtnText('i18n-btnMultiShowAll', t.btnMultiShowAll);
  updateBtnText('i18n-btnMultiHide', t.btnMultiHide);

  document.getElementById('modalTableSubtitle').textContent = t.modalSubtitle;
  document.getElementById('modalSearchInput').placeholder = t.modalSearch;
  updateBtnText('i18n-modalDone', t.modalDone);
  document.getElementById('i18n-modalBtnNoAudit').textContent = t.modalBtnNoAudit;
  document.getElementById('i18n-modalBtnKeysOnly').textContent = t.modalBtnKeysOnly;
  document.getElementById('i18n-modalBtnShowAll').textContent = t.modalBtnShowAll;

  document.getElementById('i18n-hintCtrlDrag').innerHTML = t.hintCtrlDrag;
  document.getElementById('i18n-hintDragTable').innerHTML = t.hintDragTable;
  document.getElementById('i18n-hintZoom').innerHTML = t.hintZoom;

  const legendTitle = document.getElementById('i18n-legendTitle');
  if (legendTitle) legendTitle.textContent = t.legendTitle;
  const relTag = (id, key) => {
    const node = document.getElementById(id);
    if (node && t[key]) node.textContent = t[key];
  };
  relTag('i18n-relLegendTitle', 'relLegendTitle');
  relTag('i18n-relLegIdent', 'relLegIdent');
  relTag('i18n-relLegNonIdent', 'relLegNonIdent');
  relTag('i18n-relLegCard', 'relLegCard');
  relTag('i18n-relLegOptional', 'relLegOptional');
  relTag('i18n-relLegSelf', 'relLegSelf');
  relTag('i18n-relLegColor', 'relLegColor');
  relTag('i18n-viewCanvas', 'viewCanvas');
  relTag('i18n-newPageTitle', 'newPageTitle');
  relTag('i18n-newPageSub', 'newPageSub');
  relTag('i18n-viewImport', 'viewImport');
  relTag('i18n-viewExport', 'viewExport');
  relTag('i18n-sideTables', 'sideTables');
  relTag('i18n-importTitle', 'importTitle');
  relTag('i18n-importSub', 'importSub');
  relTag('i18n-impSqlTitle', 'impSqlTitle');
  relTag('i18n-impDictTitle', 'impDictTitle');
  relTag('i18n-impRestoreTitle', 'impRestoreTitle');
  relTag('i18n-exportTitle', 'exportTitle');
  relTag('i18n-exportSub', 'exportSub');
  relTag('i18n-expImgTitle', 'expImgTitle');
  relTag('i18n-expImgHint', 'expImgHint');
  relTag('i18n-expHtmlReportTitle', 'expHtmlReportTitle');
  relTag('i18n-expHtmlReportHint', 'expHtmlReportHint');
  relTag('i18n-expHtmlDownloadBtn', 'expHtmlDownloadBtn');
  relTag('i18n-expHtmlPreviewBtn', 'expHtmlPreviewBtn');
  relTag('i18n-expPdfReportTitle', 'expPdfReportTitle');
  relTag('i18n-expPdfReportHint', 'expPdfReportHint');
  relTag('i18n-expPdfDownloadBtn', 'expPdfDownloadBtn');
  relTag('i18n-expPdfPrintBtn', 'expPdfPrintBtn');
  relTag('i18n-expDdlTitle', 'expDdlTitle');
  relTag('i18n-expDictTitle', 'expDictTitle');
  relTag('i18n-expDictHint', 'expDictHint');
  relTag('i18n-expDictDirectBtn', 'expDictDirectBtn');
  relTag('i18n-expDictUploadHint', 'expDictUploadHint');
  relTag('i18n-expDictChooseFiles', 'expDictChooseFiles');
  relTag('i18n-expDictFromFilesBtn', 'expDictFromFilesBtn');
  relTag('i18n-expBackupTitle', 'expBackupTitle');
  relTag('i18n-dbMovedHint', 'dbMovedHint');
  relTag('i18n-storageRestoreHint', 'storageRestoreHint');
  relTag('i18n-viewAudit', 'viewAudit');
  relTag('i18n-auditTitle', 'auditTitle');
  relTag('i18n-auditSub', 'auditSub');
  relTag('i18n-tabLinter', 'tabLinter');
  relTag('i18n-tabDiff', 'tabDiff');
  relTag('i18n-tabMock', 'tabMock');
  relTag('i18n-btnRunLint', 'btnRunLint');
  relTag('i18n-btnDownloadRem', 'btnDownloadRem');
  relTag('i18n-btnRunDiff', 'btnRunDiff');
  relTag('i18n-btnCopyMig', 'btnCopyMig');
  relTag('i18n-btnDownMig', 'btnDownMig');
  relTag('i18n-btnGenMock', 'btnGenMock');
  relTag('i18n-btnCopyMock', 'btnCopyMock');
  relTag('i18n-btnDownMock', 'btnDownMock');
  const aiTitle = document.getElementById('aiTitleText');
  if (aiTitle) aiTitle.textContent = t.aiTitle || 'Smart Assistant';
  const aiInput = document.getElementById('aiInput');
  if (aiInput) aiInput.placeholder = t.aiPlaceholder || 'Ask AI about your schema...';
  const aiHint = document.getElementById('aiInputHint');
  if (aiHint) {
    aiHint.innerHTML = currentLang === 'ar'
      ? '<span><kbd>Shift</kbd> + <kbd>Enter</kbd> سطر جديد</span><span class="ai-hint-dot">·</span><span><kbd>Enter</kbd> إرسال</span>'
      : '<span><kbd>Shift</kbd> + <kbd>Enter</kbd> newline</span><span class="ai-hint-dot">·</span><span><kbd>Enter</kbd> send</span>';
  }
  const aiSend = document.getElementById('aiSendBtn');
  if (aiSend) aiSend.title = (currentLang === 'ar' ? 'إرسال (Enter)' : 'Send (Enter)');
  const aiClear = document.getElementById('aiClearBtn');
  if (aiClear) aiClear.title = (currentLang === 'ar' ? 'مسح المحادثة' : 'Clear chat');
  const langBtn = document.getElementById('langToggleBtn');
  if (langBtn) langBtn.title = (currentLang === 'ar' ? 'English' : 'العربية');
  updateSubsysFilterOptions();
  renderLegend();
  buildSuggestions();
  updateAIBadge();

  updateSidebarToggleIcon();
  buildSidebarList();
  if (typeof renderWsBar === 'function') renderWsBar();
  if (typeof toggleNewPageModal === 'function') {
    var m = document.getElementById('newPageModal');
    if (m && m.style.display === 'flex') toggleNewPageModal(true);
  }
  if (typeof updateStatusBar === 'function') updateStatusBar();
}

// Collapsible Sidebar
function toggleSidebar() {
  isSidebarCollapsed = !isSidebarCollapsed;
  const sidebar = document.getElementById('appSidebar');
  sidebar.classList.toggle('collapsed', isSidebarCollapsed);
  updateSidebarToggleIcon();
  scheduleAutoSave();
  setTimeout(fitView, 240);
}

// ---- APP VIEW NAVIGATION (Diagram / Import / Export) ----
let currentView = 'canvas';
function switchView(name) {
  currentView = name;
  ['canvas', 'import', 'export', 'audit'].forEach(v => {
    const sec = document.getElementById('view-' + v);
    if (sec) sec.classList.toggle('hidden', v !== name);
    const tab = document.getElementById('viewTab' + v.charAt(0).toUpperCase() + v.slice(1));
    if (tab) {
      tab.classList.toggle('active', v === name);
      tab.setAttribute('aria-selected', v === name ? 'true' : 'false');
    }
    const railBtn = document.getElementById('railBtn' + v.charAt(0).toUpperCase() + v.slice(1));
    if (railBtn) railBtn.classList.toggle('active', v === name);
  });
  if (name === 'canvas') {
    setTimeout(fitView, 80);
  } else if (name === 'audit') {
    if (typeof populateDiffSelectors === 'function') populateDiffSelectors();
  }
  if (typeof updateStatusBar === 'function') updateStatusBar();
}

// collapsible accordion cards on the pages
function toggleAccordion(head) {
  const card = head ? head.closest('.accordion-card') : null;
  if (card) card.classList.toggle('closed');
}

// collapsible sidebar sections
function toggleSideSection(id) {
  const el = document.getElementById(id);
  const section = el ? el.closest('.side-section') : null;
  if (section) section.classList.toggle('closed');
}

function updateSidebarToggleIcon() {
  const logo = document.getElementById('railLogoToggle') || document.querySelector('.rail-logo');
  if (logo) {
    logo.classList.toggle('sidebar-closed', isSidebarCollapsed);
    const titleText = currentLang === 'ar' 
      ? (isSidebarCollapsed ? 'فتح القائمة الجانبية (B)' : 'طي القائمة الجانبية (B)') 
      : (isSidebarCollapsed ? 'Open Table Panel (B)' : 'Collapse Table Panel (B)');
    logo.setAttribute('title', titleText);
    logo.setAttribute('aria-expanded', !isSidebarCollapsed);
  }
  const btn = document.getElementById('sidebarToggleBtn');
  if (btn) {
    btn.classList.toggle('active', !isSidebarCollapsed);
  }
}

// Render filter chips (removed from UI)
function renderFilterChips() {}

function setSidebarFilter(filter) {
  activeSidebarFilter = filter;
  renderFilterChips();
  buildSidebarList();
}

// Build Sidebar Tree — Fully Dynamic & Guarantees ALL Tables Appear
function buildSidebarList() {
  const container = document.getElementById('tableListContainer');
  if (!container) return;
  container.innerHTML = '';

  const searchInput = document.getElementById('searchInput');
  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
  const tList = (allTables && allTables.length) ? allTables : Object.keys(tablesData || {});
  const isAr = currentLang === 'ar';

  if (tList.length === 0) {
    container.innerHTML = `<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:12px;">${isAr ? 'لا توجد جداول محملة' : 'No tables loaded'}</div>`;
    updateVisibleStats();
    return;
  }

  // 1. Filter by search query
  let filtered = tList.filter(t => !query || t.toLowerCase().includes(query));

  // 2. Filter by dropdown selector (activeSubsystemFilter)
  if (activeSubsystemFilter === '__selected__') {
    filtered = filtered.filter(t => selectedTables.has(t));
  } else if (activeSubsystemFilter === '__unselected__') {
    filtered = filtered.filter(t => !selectedTables.has(t));
  } else if (activeSubsystemFilter) {
    if (subsystemData && subsystemMapping && subsystemMapping[activeSubsystemFilter]) {
      filtered = filtered.filter(t => tableSubsystem(t) === activeSubsystemFilter);
    } else {
      filtered = filtered.filter(t => t.toUpperCase().startsWith(activeSubsystemFilter.toUpperCase()));
    }
  }

  // 3. Filter by filter chip (activeSidebarFilter)
  if (activeSidebarFilter === 'selected') {
    filtered = filtered.filter(t => selectedTables.has(t));
  } else if (activeSidebarFilter === 'unselected') {
    filtered = filtered.filter(t => !selectedTables.has(t));
  } else if (activeSidebarFilter && activeSidebarFilter !== 'all') {
    filtered = filtered.filter(t => t.toUpperCase().startsWith(activeSidebarFilter.toUpperCase()));
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:12px;">${isAr ? 'لا توجد جداول مطابقة' : 'No matching tables'}</div>`;
    updateVisibleStats();
    return;
  }

  // 4. Dynamic Grouping: Subsystem or Prefix or Unified General
  const prefixCounts = {};
  filtered.forEach(t => {
    const parts = t.split('_');
    if (parts.length > 1 && parts[0].length >= 2) {
      const p = parts[0].toUpperCase() + '_';
      prefixCounts[p] = (prefixCounts[p] || 0) + 1;
    }
  });
  const multiPrefixes = Object.keys(prefixCounts).filter(p => prefixCounts[p] >= 2);

  const groupsMap = new Map();

  filtered.forEach(t => {
    let groupKey = 'general';
    let groupTitle = isAr ? 'الجداول العامة' : 'General Tables';
    let groupColor = '#3b82f6';

    if (subsystemData && subsystemMapping && tableSubsystem(t) && tableSubsystem(t) !== 'general') {
      const subKey = tableSubsystem(t);
      const subObj = (subsystemData.subsystems || []).find(s => s.key === subKey);
      groupKey = subKey;
      groupTitle = subObj ? subsystemLocaleName(subObj) : subKey;
      groupColor = SUBSYS_COLORS[subKey] || (subObj && subObj.color) || '#3b82f6';
    } else {
      const parts = t.split('_');
      if (parts.length > 1) {
        const p = parts[0].toUpperCase() + '_';
        if (multiPrefixes.includes(p)) {
          groupKey = p;
          groupTitle = `${p}`;
          groupColor = p.startsWith('COM') ? '#2563eb' : (p.startsWith('RAF') ? '#059669' : '#8b5cf6');
        }
      }
    }

    if (!groupsMap.has(groupKey)) {
      groupsMap.set(groupKey, { key: groupKey, title: groupTitle, color: groupColor, tables: [] });
    }
    groupsMap.get(groupKey).tables.push(t);
  });

  if (groupsMap.size === 1 && groupsMap.has('general')) {
    groupsMap.get('general').title = isAr ? `قائمة الجداول` : `Tables`;
  }

  // 5. Render groups and table rows
  groupsMap.forEach(g => {
    const totalInGroup = g.tables.length;
    const checkedInGroup = g.tables.filter(t => selectedTables.has(t)).length;

    const groupHeader = document.createElement('div');
    groupHeader.className = 'section-header';
    groupHeader.innerHTML = `
      <span>${g.title} (${totalInGroup})</span>
      <div class="section-actions">
        <input type="checkbox" class="group-select-checkbox" title="${isAr ? 'تحديد / إلغاء تحديد الكل' : 'Select / Deselect All'}" aria-label="${isAr ? 'تحديد الكل' : 'Select All'}" />
      </div>
    `;

    const groupCheckbox = groupHeader.querySelector('.group-select-checkbox');
    if (groupCheckbox) {
      if (checkedInGroup === totalInGroup && totalInGroup > 0) {
        groupCheckbox.checked = true;
        groupCheckbox.indeterminate = false;
      } else if (checkedInGroup > 0) {
        groupCheckbox.checked = false;
        groupCheckbox.indeterminate = true;
      } else {
        groupCheckbox.checked = false;
        groupCheckbox.indeterminate = false;
      }

      groupCheckbox.onclick = (e) => {
        e.stopPropagation();
        const shouldSelect = (checkedInGroup < totalInGroup);
        if (shouldSelect) {
          g.tables.forEach(t => selectedTables.add(t));
        } else {
          g.tables.forEach(t => {
            selectedTables.delete(t);
            selectedTableNodes.delete(t);
          });
        }
        buildSidebarList();
        renderAll();
        scheduleAutoSave();
        renderFilterChips();
        updateSubsysFilterOptions();
      };
    }
    container.appendChild(groupHeader);

    g.tables.forEach(t => {
      const data = tablesData[t] || { columns: [] };
      const isChecked = selectedTables.has(t);
      const isSelected = selectedTableNodes.has(t);

      const itemDiv = document.createElement('div');
      itemDiv.className = `tree-row ${isSelected ? 'is-selected' : ''}`;
      itemDiv.id = `sidebar-item-${t}`;
      itemDiv.style.borderInlineStart = `3px solid ${subsystemColorOf(t)}`;
      itemDiv.innerHTML = `
        <input type="checkbox" value="${t}" ${isChecked ? 'checked' : ''} />
        <span class="tree-name">${t}</span>
        <span class="tree-badge">${data.columns ? data.columns.length : 0}</span>
        <span class="tree-gear" title="Manage Columns"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></span>
      `;

      itemDiv.querySelector('.tree-name').onclick = (e) => handleSidebarItemClick(t, e);
      itemDiv.querySelector('.tree-gear').onclick = (e) => {
        e.stopPropagation();
        openColumnModalFor(t);
      };

      itemDiv.querySelector('input').addEventListener('change', (e) => {
        if (e.target.checked) selectedTables.add(t);
        else {
          selectedTables.delete(t);
          selectedTableNodes.delete(t);
        }
        updateVisibleStats();
        renderAll();
        scheduleAutoSave();
        renderFilterChips();
        updateSubsysFilterOptions();
      });

      container.appendChild(itemDiv);
    });
  });

  updateVisibleStats();
}

function handleSidebarItemClick(tableName, event) {
  if (event.ctrlKey || event.metaKey || event.shiftKey) {
    toggleTableInMultiSelection(tableName);
  } else {
    selectedTableNodes.clear();
    selectedTableNodes.add(tableName);
    updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
  }
}

function updateVisibleStats() {
  const visibleFks = fkList.filter(f => selectedTables.has(f.child) && selectedTables.has(f.parent)).length;
  document.getElementById('statSummary').textContent = `${selectedTables.size} Tables · ${visibleFks} FKs`;
  if (typeof updateStatusBar === 'function') updateStatusBar();
}

// ==================== SUBSYSTEM CLASSIFICATION UI ====================
let subsystemData = null;
let subsystemMapping = {};
let subsystemColorEnabled = true;
let activeSubsystemFilter = '';
let highlightedTables = new Set();

const SUBSYS_COLORS = {
  auth: '#2563eb', reference: '#7c3aed', notifications: '#f59e0b',
  academic: '#059669', facilities: '#0891b2', curriculum: '#ea580c',
  students: '#0d9488', assignments: '#db2777', exams: '#dc2626', general: '#64748b'
};

async function loadSubsystems() {
  try {
    const res = await fetch('/api/subsystems');
    if (!res.ok) return;
    subsystemData = await res.json();
    subsystemMapping = subsystemData.mapping || {};
    updateSubsysFilterOptions();
    renderLegend();
    renderAll();
  } catch (err) {
    console.warn('loadSubsystems failed:', err);
  }
}

function tableSubsystem(t) {
  return subsystemMapping[t] || 'general';
}

function subsystemColorOf(t) {
  return SUBSYS_COLORS[tableSubsystem(t)] || SUBSYS_COLORS.general;
}

function subsystemLocaleName(s) {
  return currentLang === 'ar' ? s.name_ar : s.name_en;
}

function updateSubsysFilterOptions() {
  const sel = document.getElementById('subsysSelect');
  if (!sel) return;
  sel.innerHTML = '';

  const tList = (allTables && allTables.length) ? allTables : Object.keys(tablesData || {});
  const totalCount = tList.length;
  const selectedCount = tList.filter(t => selectedTables.has(t)).length;
  const unselectedCount = totalCount - selectedCount;
  const isAr = currentLang === 'ar';

  // Option 1: All tables
  const allOpt = document.createElement('option');
  allOpt.value = '';
  allOpt.textContent = `${isAr ? 'جميع الجداول' : 'All Tables'} (${totalCount})`;
  sel.appendChild(allOpt);

  // Option 2: Selected only
  const selOpt = document.createElement('option');
  selOpt.value = '__selected__';
  selOpt.textContent = `${isAr ? 'الجداول المحددة على المخطط' : 'Selected on Diagram'} (${selectedCount})`;
  sel.appendChild(selOpt);

  // Option 3: Hidden / Unselected
  if (unselectedCount > 0) {
    const unselOpt = document.createElement('option');
    unselOpt.value = '__unselected__';
    unselOpt.textContent = `${isAr ? 'الجداول غير المحددة (مخفية)' : 'Hidden / Unselected'} (${unselectedCount})`;
    sel.appendChild(unselOpt);
  }

  // Option 4: Subsystems if defined
  if (subsystemData && subsystemData.subsystems && subsystemData.subsystems.length > 0) {
    subsystemData.subsystems.slice().sort((a, b) => (b.tableCount || 0) - (a.tableCount || 0)).forEach(s => {
      if (!s.tableCount) return;
      const o = document.createElement('option');
      o.value = s.key;
      o.textContent = `${subsystemLocaleName(s)} (${s.tableCount})`;
      sel.appendChild(o);
    });
  } else {
    // Dynamic prefixes if no subsystems
    const prefixCounts = {};
    tList.forEach(t => {
      const parts = t.split('_');
      if (parts.length > 1 && parts[0].length >= 2) {
        const p = parts[0].toUpperCase() + '_';
        prefixCounts[p] = (prefixCounts[p] || 0) + 1;
      }
    });
    Object.keys(prefixCounts).filter(p => prefixCounts[p] >= 2).forEach(p => {
      const o = document.createElement('option');
      o.value = p;
      o.textContent = `${p} (${prefixCounts[p]})`;
      sel.appendChild(o);
    });
  }

  sel.value = activeSubsystemFilter;
}

function setSubsystemFilter(key) {
  activeSubsystemFilter = key || '';
  buildSidebarList();
  renderFilterChips();
}

function renderLegend() {
  const list = document.getElementById('legendList');
  if (!list) return;
  list.innerHTML = '';
  if (!subsystemData) return;
  subsystemData.subsystems.forEach(s => {
    if (!s.tableCount) return;
    const item = document.createElement('div');
    item.className = 'legend-item';
    const color = SUBSYS_COLORS[s.key] || s.color || '#64748b';
    item.innerHTML = `<span class="legend-color" style="background:${color}"></span><span class="legend-label">${subsystemLocaleName(s)}</span><span class="legend-count">${s.tableCount}</span>`;
    item.title = `${subsystemLocaleName(s)} — ${s.tableCount}`;
    item.addEventListener('click', () => {
      const key = activeSubsystemFilter === s.key ? '' : s.key;
      setSubsystemFilter(key);
      updateSubsysFilterOptions();
      if (key) showOnlySubsystem(key);
      else showAllTables();
    });
    list.appendChild(item);
  });
}

function showOnlySubsystem(key) {
  selectedTables = new Set(allTables.filter(t => tableSubsystem(t) === key));
  highlightedTables.clear();
  updateVisibleStats();
  renderAll();
  scheduleAutoSave();
}

function showAllTables() {
  selectedTables = new Set(allTables);
  highlightedTables.clear();
  updateVisibleStats();
  renderAll();
  scheduleAutoSave();
}

// ==================== AI ASSISTANT PANEL ====================
let aiOpen = false;
let aiBusy = false;
let aiConfig = { provider: 'local', base_url: '', api_key: '', model: 'gpt-4o-mini', temperature: 0.4 };
let aiHistory = [];
let _mdThrottle = null;

async function loadAIConfig() {
  try {
    const res = await fetch('/api/ai/config');
    if (res.ok) aiConfig = await res.json();
    updateAIBadge();
  } catch (e) {}
}

function updateAIBadge() {
  const badge = document.getElementById('aiModeBadge');
  if (!badge) return;
  const t = (typeof i18n !== 'undefined' && i18n[currentLang]) || {};
  const prov = aiConfig && aiConfig.provider;

  if (prov === 'opencode') {
    badge.textContent = 'OpenCode Zen';
    badge.className = 'ai-mode-badge opencode';
    badge.title = currentLang === 'ar' ? 'بوابة OpenCode Zen المجانية (بدون مفتاح API)' : 'OpenCode Zen Free Gateway (No API key)';
  } else if (prov && prov !== 'local' && aiConfig.api_key) {
    badge.textContent = t.aiModeCloud || 'Cloud';
    badge.className = 'ai-mode-badge cloud';
    badge.title = 'OpenAI-compatible Cloud API';
  } else {
    badge.textContent = t.aiModeLocal || 'Local';
    badge.className = 'ai-mode-badge';
    badge.title = currentLang === 'ar' ? 'المساعد الذكي المحلي' : 'Local Smart Assistant';
  }
}


function toggleAIPanel() {
  aiOpen = !aiOpen;
  const panel = document.getElementById('aiPanel');
  if (panel) {
    panel.classList.toggle('open', aiOpen);
  }
  const topBtn = document.getElementById('aiToggleBtn');
  if (topBtn) topBtn.classList.toggle('active', aiOpen);
  const railBtn = document.getElementById('railBtnAI');
  if (railBtn) railBtn.classList.toggle('active', aiOpen);

  if (aiOpen) {
    const inp = document.getElementById('aiInput');
    if (inp) setTimeout(() => inp.focus(), 60);
    const box = document.getElementById('aiMessages');
    if (box && box.children.length === 0) {
      appendAIMessage('assistant', (i18n[currentLang] && i18n[currentLang].aiWelcome) || 'Hello!');
    }
    buildSuggestions();
  }
}

// Resizable AI panel: drag the thin handle on the canvas-facing edge.
(function initAIPanelResize() {
  const panel = document.getElementById('aiPanel');
  const handle = document.getElementById('aiResizeHandle');
  if (!panel || !handle) return;
  const MIN = 320, MAX = 1200;
  let dragging = false, startX = 0, startW = 0;

  try {
    const savedW = localStorage.getItem('erd_ai_panel_w');
    if (savedW) panel.style.setProperty('--ai-panel-w', savedW);
  } catch(e){}

  function currentWidth() {
    const w = getComputedStyle(panel).width;
    const n = parseFloat(w);
    return isFinite(n) ? n : 480;
  }

  handle.addEventListener('mousedown', (e) => {
    dragging = true;
    startX = e.clientX;
    startW = currentWidth();
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const isLtr = document.body.dir === 'ltr';
    // RTL: panel on the left, dragging right grows it. LTR: panel on the right, dragging left grows it.
    const next = Math.min(MAX, Math.max(MIN, startW + (isLtr ? -dx : dx)));
    panel.style.setProperty('--ai-panel-w', next + 'px');
  });

  window.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    try {
      const cur = getComputedStyle(panel).width;
      localStorage.setItem('erd_ai_panel_w', cur);
    } catch(e){}
  });
})();

function toggleAIWidth() {
  const panel = document.getElementById('aiPanel');
  if (!panel) return;
  const curW = parseFloat(getComputedStyle(panel).width) || 480;
  if (curW > 600) {
    panel.style.setProperty('--ai-panel-w', '480px');
    try { localStorage.setItem('erd_ai_panel_w', '480px'); } catch(e){}
  } else {
    const wideW = Math.min(880, Math.round(window.innerWidth * 0.65)) + 'px';
    panel.style.setProperty('--ai-panel-w', wideW);
    try { localStorage.setItem('erd_ai_panel_w', wideW); } catch(e){}
  }
}

function buildSuggestions() {
  const box = document.getElementById('aiSuggestions');
  if (!box) return;
  const sampleTbl = (allTables && allTables.length > 0) ? allTables[0] : 'USERS';
  const items = currentLang === 'ar'
    ? ['أبرز الجداول الرئيسية', 'طبّق ترتيب شبكي', 'غيّر الثيم إلى داكن', `ما علاقات جدول ${sampleTbl}؟`, 'ما الأنظمة الفرعية في المخطط؟', 'رتب المخطط هرمياً']
    : ['Highlight primary tables', 'Apply grid layout', 'Switch theme to dark', `Relations of ${sampleTbl}?`, 'List schema subsystems', 'Arrange hierarchically'];
  box.innerHTML = '';
  items.forEach(s => {
    const b = document.createElement('button');
    b.className = 'ai-suggestion';
    b.textContent = s;
    b.addEventListener('click', () => { const inp = document.getElementById('aiInput'); if (inp) { inp.value = s; resizeAiInput(inp); const btn = document.getElementById('aiSendBtn'); if (btn) btn.classList.add('has-text'); } sendChatMessage(); });
    box.appendChild(b);
  });
}

function _formatTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
function appendAIMessage(role, content, isRawHtml = false) {
  const box = document.getElementById('aiMessages');
  if (!box) return { el: null, bodyEl: null };
  const div = document.createElement('div');
  div.className = 'ai-msg ' + role;
  const av = document.createElement('div');
  av.className = 'msg-avatar';
  const svgs = {
    user: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    assistant: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><rect x="4" y="8" width="16" height="12" rx="2"/><circle cx="9" cy="13" r="1.5" fill="currentColor"/><circle cx="15" cy="13" r="1.5" fill="currentColor"/><line x1="9" y1="17" x2="15" y2="17"/></svg>',
    tool: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    error: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
  };
  av.innerHTML = svgs[role] || svgs.assistant;
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  const body = document.createElement('div');
  body.className = 'md-body';
  if (role === 'tool' || role === 'error') body.textContent = content;
  else if (isRawHtml) body.innerHTML = content;
  else body.innerHTML = mdToHtml(content || '');
  bubble.appendChild(body);

  const footer = document.createElement('div');
  footer.style.display = 'flex';
  footer.style.alignItems = 'center';
  footer.style.justifyContent = 'space-between';
  footer.style.gap = '8px';
  footer.style.marginTop = '4px';

  const ts = document.createElement('span');
  ts.className = 'msg-time';
  ts.textContent = _formatTime();
  footer.appendChild(ts);

  if (role === 'assistant') {
    const copyBtn = document.createElement('button');
    copyBtn.className = 'msg-action-btn copy-msg-btn';
    copyBtn.title = (currentLang === 'ar' ? 'نسخ الرسالة' : 'Copy message');
    copyBtn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg><span>' + (currentLang === 'ar' ? 'نسخ' : 'Copy') + '</span>';
    copyBtn.addEventListener('click', () => {
      const textToCopy = body.innerText || body.textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textToCopy).catch(()=>{});
      } else {
        const ta = document.createElement('textarea'); ta.value = textToCopy; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch(e){}
        document.body.removeChild(ta);
      }
      copyBtn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><span style="color:var(--success)">' + (currentLang === 'ar' ? 'تم النسخ' : 'Copied') + '</span>';
      setTimeout(() => {
        copyBtn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg><span>' + (currentLang === 'ar' ? 'نسخ' : 'Copy') + '</span>';
      }, 1800);
    });
    footer.appendChild(copyBtn);
  }

  bubble.appendChild(footer);
  div.appendChild(av);
  div.appendChild(bubble);
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return { el: div, bodyEl: body };
}
function updateAIMessageBody(bodyEl, content) {
  if (!bodyEl) return;
  bodyEl.innerHTML = mdToHtml(content || '');
}

function setAIStatus(txt) {
  document.getElementById('aiStatus').textContent = txt || '';
}

function resizeAiInput(el) {
  if (!el) el = document.getElementById('aiInput');
  if (!el) return;
  el.style.height = 'auto';
  const newH = Math.min(Math.max(el.scrollHeight, 28), 140);
  el.style.height = newH + 'px';
}

function initAIChatInput() {
  const aiInp = document.getElementById('aiInput');
  if (!aiInp) return;
  aiInp.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Shift + Enter: allow newline and expand height
        setTimeout(() => resizeAiInput(this), 0);
      } else {
        // Enter: submit message
        e.preventDefault();
        sendChatMessage();
      }
    }
  });
  aiInp.addEventListener('input', function() {
    resizeAiInput(this);
    const sendBtn = document.getElementById('aiSendBtn');
    if (sendBtn) {
      if (this.value.trim().length > 0) {
        sendBtn.classList.add('has-text');
      } else {
        sendBtn.classList.remove('has-text');
      }
    }
  });
}

async function sendChatMessage() {
  const input = document.getElementById('aiInput');
  const content = input ? input.value.trim() : '';
  if (!content || aiBusy) return;
  input.value = '';
  resizeAiInput(input);
  const sendBtn = document.getElementById('aiSendBtn');
  if (sendBtn) sendBtn.classList.remove('has-text');

  appendAIMessage('user', content);
  aiHistory.push({ role: 'user', content });
  aiBusy = true;

  const box = document.getElementById('aiMessages');
  const thinkingDiv = appendAIMessage('assistant', '<div class="ai-typing-indicator"><span class="ai-typing-dot"></span><span class="ai-typing-dot"></span><span class="ai-typing-dot"></span></div>', true);
  const msgEl = thinkingDiv.el;
  const msgBodyEl = thinkingDiv.bodyEl;
  _mdThrottle = null;
  setAIStatus('...');

  let assistantText = '';
  try {
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: aiHistory.slice(-30), context: {} })
    });
    if (!res.ok || !res.body) throw new Error('chat request failed');
    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        let ev;
        try { ev = JSON.parse(trimmed); } catch (e) { continue; }
        if (ev.type === 'token') {
          assistantText += ev.content || '';
          if (_mdThrottle === null || Date.now() - _mdThrottle > 70) {
            updateAIMessageBody(msgBodyEl, assistantText);
            box.scrollTop = box.scrollHeight;
            _mdThrottle = Date.now();
          }
        } else if (ev.type === 'action') {
          executeClientAction(ev);
          appendAIMessage('tool', `${ev.name}${ev.arguments && Object.keys(ev.arguments).length ? ' ' + JSON.stringify(ev.arguments) : ''}`);
        } else if (ev.type === 'tool') {
          setAIStatus(`${ev.name} ...`);
        } else if (ev.type === 'error') {
          msgEl.classList.add('error');
          if (msgBodyEl) msgBodyEl.textContent = ev.message;
        } else if (ev.type === 'done') {
          setAIStatus('');
        }
      }
    }
    if (assistantText) aiHistory.push({ role: 'assistant', content: assistantText });
    _mdThrottle = null;
    updateAIMessageBody(msgBodyEl, assistantText);
  } catch (err) {
    msgEl.classList.add('error');
    if (msgBodyEl) msgBodyEl.textContent = err.message;
  } finally {
    if (!msgEl.classList.contains('error') && !assistantText && msgBodyEl) msgBodyEl.textContent = '...';
    if (msgBodyEl) msgBodyEl.classList.remove('ai-thinking-pulse');
    setAIStatus('');
    aiBusy = false;
    box.scrollTop = box.scrollHeight;
  }
}

function clearAIChat() {
  aiHistory = [];
  document.getElementById('aiMessages').innerHTML = '';
  appendAIMessage('assistant', (i18n[currentLang] && i18n[currentLang].aiWelcome) || 'Hello!');
  fetch('/api/ai/history', { method: 'DELETE' }).catch(()=>{});
 showToast(currentLang === 'ar' ? ' تم مسح المحادثة' : ' Chat cleared');
}

// Restores the AI conversation from the server so history survives page refreshes
async function loadChatHistory() {
  const box = document.getElementById('aiMessages');
  if (!box) return;
  try {
    const res = await fetch('/api/ai/history');
    const data = await res.json();
    const msgs = data.messages || [];
    if (msgs.length > 0) {
      box.innerHTML = '';
      aiHistory = msgs.filter(m => (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string');
      msgs.forEach(m => {
        if ((m.role === 'user' || m.role === 'assistant') && m.content) appendAIMessage(m.role, m.content);
      });
    } else if (box.children.length === 0) appendAIMessage('assistant', (i18n[currentLang] && i18n[currentLang].aiWelcome) || 'Hello!');
  } catch (err) {
    if (box.children.length === 0) appendAIMessage('assistant', (i18n[currentLang] && i18n[currentLang].aiWelcome) || 'Hello!');
  }
}

const KNOWN_THEMES = ['mermaid', 'dark', 'academic', 'light'];
const KNOWN_PRESETS = ['hierarchical', 'grid', 'cluster', 'circular', 'force', 'star'];
const KNOWN_MODES = ['no-audit', 'keys-only', 'all-columns'];

function executeClientAction(action) {
  if (!action || !action.name) return;
  const args = action.arguments || {};
  switch (action.name) {
    case 'set_theme':
      if (KNOWN_THEMES.includes(args.theme)) setTheme(args.theme, false);
      break;
    case 'set_view_mode':
      if (KNOWN_MODES.includes(args.mode)) setGlobalViewMode(args.mode);
      break;
    case 'apply_preset':
      if (KNOWN_PRESETS.includes(args.preset)) applyPresetLayout(args.preset);
      break;
    case 'fit_view':
      fitView();
      break;
    case 'focus_tables':
      if (Array.isArray(args.tables)) {
        selectedTableNodes.clear();
        args.tables.forEach(t => { if (allTables.includes(t)) { selectedTableNodes.add(t); } });
        updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
        fitView();
      }
      break;
    case 'highlight_tables':
      if (Array.isArray(args.tables)) {
        highlightedTables = new Set(args.tables.filter(t => allTables.includes(t)));
        renderAll();
      }
      break;
    case 'clear_highlights':
      highlightedTables.clear();
      renderAll();
      break;
    case 'hide_tables':
      if (Array.isArray(args.tables)) {
        args.tables.forEach(t => { selectedTables.delete(t); selectedTableNodes.delete(t); });
        updateVisibleStats(); renderAll(); scheduleAutoSave();
      }
      break;
    case 'show_tables':
      if (Array.isArray(args.tables)) {
        args.tables.forEach(t => { if (allTables.includes(t)) selectedTables.add(t); });
        updateVisibleStats(); renderAll(); scheduleAutoSave();
      }
      break;
    case 'show_only_subsystem':
      if (args.key) {
        showOnlySubsystem(args.key);
        activeSubsystemFilter = args.key;
        updateSubsysFilterOptions();
        buildSidebarList();
      }
      break;
    case 'show_all_tables':
      activeSubsystemFilter = '';
      updateSubsysFilterOptions();
      showAllTables();
      break;
    case 'color_by_subsystem':
      subsystemColorEnabled = !!args.enabled;
      renderAll();
      break;
    case 'hide_audit_columns':
      setGlobalViewMode('no-audit');
      break;
    case 'show_all_columns':
      setGlobalViewMode('all-columns');
      break;
    case 'add_table': {
      const rawName = (args.table_name || args.name || '').toUpperCase().trim();
      if (!rawName) break;
      const tname = rawName;
      const cols = Array.isArray(args.columns) && args.columns.length > 0 ? args.columns.map(c => ({
        name: (c.name || '').toLowerCase().trim(),
        type: c.type || 'VARCHAR2(100)',
        nullable: c.nullable !== false,
        unique: !!c.is_unique,
        comment: c.comment || '',
        description: c.comment || '',
        caption: c.comment || '-'
      })) : [{ name: 'id', type: 'NUMBER', nullable: false, unique: true, comment: 'Primary Key', description: 'Primary Key', caption: '-' }];

      const pks = Array.isArray(args.pks) && args.pks.length > 0 
        ? args.pks.map(p => p.toLowerCase().trim())
        : cols.filter(c => c.is_pk).map(c => c.name);
      if (pks.length === 0 && cols.length > 0) pks.push(cols[0].name);

      tablesData[tname] = {
        columns: cols,
        pks: pks,
        comment: args.comment || '',
        description: args.comment || ''
      };

      if (!allTables.includes(tname)) allTables.push(tname);
      if (tname.startsWith('COM_') && !comTables.includes(tname)) comTables.push(tname);
      if (tname.startsWith('RAF_') && !rafTables.includes(tname)) rafTables.push(tname);
      selectedTables.add(tname);

      let primaryParent = null;
      if (Array.isArray(args.foreign_keys)) {
        args.foreign_keys.forEach(f => {
          const pTable = (f.parent_table || '').toUpperCase().trim();
          const cCol = (f.child_col || '').toLowerCase().trim();
          if (pTable && cCol) {
            if (!primaryParent && allTables.includes(pTable)) primaryParent = pTable;
            fkList.push({
              child: tname,
              parent: pTable,
              cols: cCol,
              pcols: (f.parent_col || cCol).toLowerCase().trim(),
              fk: f.fk_name || `FK_${tname}_${pTable}_${cCol}`
            });
          }
        });
      }

      // Smart positioning: place near primary parent or in open area without overlap
      const tableH = getTableHeight(tname);
      let posX = 120, posY = 120;
      if (primaryParent && tablePositions[primaryParent]) {
        const pp = tablePositions[primaryParent];
        posX = pp.x + TABLE_WIDTH + 60;
        posY = pp.y;
      } else {
        let found = false;
        for (let y = 80; y < 1500; y += 140) {
          for (let x = 80; x < 2000; x += TABLE_WIDTH + 50) {
            const collision = Object.keys(tablePositions).some(t => {
              if (!selectedTables.has(t)) return false;
              const p = tablePositions[t];
              return Math.abs(p.x - x) < TABLE_WIDTH + 30 && Math.abs(p.y - y) < 180;
            });
            if (!collision) {
              posX = x; posY = y; found = true; break;
            }
          }
          if (found) break;
        }
      }
      tablePositions[tname] = { x: posX, y: posY, width: TABLE_WIDTH, height: tableH };

      selectedTableNodes.clear();
      selectedTableNodes.add(tname);
      highlightedTables = new Set([tname]);

      renderFilterChips();
      updateSubsysFilterOptions();
      buildSidebarList();
      renderAll();
      updateSelectionUI();
      if (typeof updateStatusBar === 'function') updateStatusBar();
      scheduleAutoSave();

      fetch('/api/schema/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add_table', params: args })
      }).catch(()=>{});

      try {
        const svgW = window.innerWidth || 1200;
        const svgH = window.innerHeight || 800;
        panX = svgW / 2 - (posX + TABLE_WIDTH / 2) * zoom;
        panY = svgH / 2 - (posY + tableH / 2) * zoom;
        updateTransform();
      } catch(e) {}

      showToast(currentLang === 'ar' ? `✨ تمت إضافة جدول ${tname} إلى المخطط` : `✨ Added table ${tname} to diagram`);
      break;
    }
    case 'add_column': {
      const t = (args.table || '').toUpperCase().trim();
      const colName = (args.column_name || '').toLowerCase().trim();
      if (!t || !colName || !tablesData[t]) break;
      const data = tablesData[t];
      if (!data.columns) data.columns = [];

      const existingIdx = data.columns.findIndex(c => c.name.toLowerCase() === colName);
      const colObj = {
        name: colName,
        type: args.data_type || 'VARCHAR2(100)',
        nullable: args.nullable !== false,
        unique: !!args.is_unique,
        comment: args.comment || '',
        description: args.comment || '',
        caption: args.comment || '-'
      };
      if (existingIdx >= 0) {
        data.columns[existingIdx] = Object.assign(data.columns[existingIdx], colObj);
      } else {
        data.columns.push(colObj);
      }

      if (args.is_pk) {
        if (!data.pks) data.pks = [];
        if (!data.pks.includes(colName)) data.pks.push(colName);
      }

      if (args.fk_parent_table) {
        const pTable = args.fk_parent_table.toUpperCase().trim();
        const pCol = (args.fk_parent_col || colName).toLowerCase().trim();
        fkList.push({
          child: t,
          parent: pTable,
          cols: colName,
          pcols: pCol,
          fk: args.fk_name || `FK_${t}_${pTable}_${colName}`
        });
      }

      if (tablePositions[t]) {
        tablePositions[t].height = getTableHeight(t);
      }
      highlightedTables = new Set([t]);
      renderAll();
      scheduleAutoSave();

      fetch('/api/schema/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add_column', params: args })
      }).catch(()=>{});

      showToast(currentLang === 'ar' ? `✨ أضيف الحقل ${colName} إلى ${t}` : `✨ Added column ${colName} to ${t}`);
      break;
    }
    case 'drop_column': {
      const t = (args.table || '').toUpperCase().trim();
      const colName = (args.column_name || '').toLowerCase().trim();
      if (!t || !colName || !tablesData[t]) break;
      const data = tablesData[t];
      if (data.columns) {
        data.columns = data.columns.filter(c => c.name.toLowerCase() !== colName);
      }
      if (data.pks) {
        data.pks = data.pks.filter(p => p.toLowerCase() !== colName);
      }
      fkList = fkList.filter(f => !(f.child === t && f.cols.toLowerCase() === colName));
      if (tablePositions[t]) {
        tablePositions[t].height = getTableHeight(t);
      }
      renderAll();
      scheduleAutoSave();

      fetch('/api/schema/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'drop_column', params: args })
      }).catch(()=>{});

      showToast(currentLang === 'ar' ? `تم حذف الحقل ${colName} من ${t}` : `Dropped column ${colName} from ${t}`);
      break;
    }
    case 'add_relationship': {
      const cTable = (args.child_table || '').toUpperCase().trim();
      const pTable = (args.parent_table || '').toUpperCase().trim();
      const cCol = (args.child_column || '').toLowerCase().trim();
      const pCol = (args.parent_column || cCol).toLowerCase().trim();
      if (!cTable || !pTable || !cCol) break;
      const fkName = args.fk_name || `FK_${cTable}_${pTable}_${cCol}`;
      fkList.push({
        child: cTable,
        parent: pTable,
        cols: cCol,
        pcols: pCol,
        fk: fkName
      });
      highlightedTables = new Set([cTable, pTable]);
      renderAll();
      scheduleAutoSave();

      fetch('/api/schema/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add_relationship', params: args })
      }).catch(()=>{});

      showToast(currentLang === 'ar' ? `🔗 تم ربط ${cTable} بـ ${pTable}` : `🔗 Connected ${cTable} to ${pTable}`);
      break;
    }
    case 'drop_table': {
      const t = (args.table || '').toUpperCase().trim();
      if (!t || !tablesData[t]) break;
      delete tablesData[t];
      allTables = allTables.filter(x => x !== t);
      comTables = comTables.filter(x => x !== t);
      rafTables = rafTables.filter(x => x !== t);
      selectedTables.delete(t);
      selectedTableNodes.delete(t);
      delete tablePositions[t];
      delete tableCustomHiddenCols[t];
      fkList = fkList.filter(f => f.child !== t && f.parent !== t);
      renderFilterChips();
      updateSubsysFilterOptions();
      buildSidebarList();
      renderAll();
      if (typeof updateStatusBar === 'function') updateStatusBar();
      scheduleAutoSave();

      fetch('/api/schema/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'drop_table', params: args })
      }).catch(()=>{});

      showToast(currentLang === 'ar' ? `تم حذف جدول ${t}` : `Deleted table ${t}`);
      break;
    }
    case 'set_table_comment': {
      const t = (args.table || '').toUpperCase().trim();
      if (t && tablesData[t]) {
        tablesData[t].comment = args.comment || '';
        tablesData[t].description = args.comment || '';
        renderAll();
        scheduleAutoSave();
        fetch('/api/schema/mutate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'set_table_comment', params: args })
        }).catch(()=>{});
        showToast(currentLang === 'ar' ? `تم تحديث وصف جدول ${t}` : `Updated comment for ${t}`);
      }
      break;
    }
    case 'set_column_comment': {
      const t = (args.table || '').toUpperCase().trim();
      const colName = (args.column || '').toLowerCase().trim();
      if (t && colName && tablesData[t] && tablesData[t].columns) {
        const col = tablesData[t].columns.find(c => c.name.toLowerCase() === colName);
        if (col) {
          col.comment = args.comment || '';
          col.description = args.comment || '';
          col.caption = args.comment || '-';
          renderAll();
          scheduleAutoSave();
          fetch('/api/schema/mutate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'set_column_comment', params: args })
          }).catch(()=>{});
          showToast(currentLang === 'ar' ? `تم توثيق الحقل ${colName}` : `Documented column ${colName}`);
        }
      }
      break;
    }
    case 'document_schema': {
      let count = 0;
      if (Array.isArray(args.comments)) {
        args.comments.forEach(item => {
          const t = (item.table || '').toUpperCase().trim();
          if (t && tablesData[t]) {
            if (item.table_comment) {
              tablesData[t].comment = item.table_comment;
              tablesData[t].description = item.table_comment;
            }
            if (Array.isArray(item.columns)) {
              item.columns.forEach(colC => {
                const cn = (colC.name || '').toLowerCase().trim();
                const col = tablesData[t].columns && tablesData[t].columns.find(c => c.name.toLowerCase() === cn);
                if (col) {
                  col.comment = colC.comment || '';
                  col.description = colC.comment || '';
                  col.caption = colC.comment || '-';
                  count++;
                }
              });
            }
          }
        });
      }
      renderAll();
      scheduleAutoSave();
      fetch('/api/schema/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'document_schema', params: args })
      }).catch(()=>{});
      showToast(currentLang === 'ar' ? `📖 تم توثيق ${count} حقل بالذكاء الاصطناعي بنجاح` : `📖 Documented ${count} columns successfully`);
      break;
    }
    default:
      break;
  }
}

// Get Visible Columns for a Table
function getVisibleColumns(tableName) {
  const data = tablesData[tableName];
  if (!data) return [];
  
  if (tableCustomHiddenCols[tableName]) {
    const hiddenSet = tableCustomHiddenCols[tableName];
    const filtered = data.columns.filter(c => !hiddenSet.has(c.name));
    return filtered.length > 0 ? filtered : [data.columns[0]];
  }
  
  if (globalViewMode === 'keys-only') {
    const pks = data.pks;
    const childFkCols = fkList.filter(f => f.child === tableName).map(f => f.cols.split(',').map(s=>s.trim())).flat();
    const parentFkCols = fkList.filter(f => f.parent === tableName).map(f => f.cols.split(',').map(s=>s.trim())).flat();
    const keySet = new Set([...pks, ...childFkCols, ...parentFkCols]);
    const filtered = data.columns.filter(c => keySet.has(c.name));
    return filtered.length > 0 ? filtered : [data.columns[0]];
  }

  if (globalViewMode === 'no-audit') {
    const pks = new Set(data.pks);
    const filtered = data.columns.filter(c => {
      if (pks.has(c.name)) return true;
      return !isAuditColumn(c.name);
    });
    return filtered.length > 0 ? filtered : [data.columns[0]];
  }

  return data.columns;
}

// Calculate Table Height
function getTableHeight(tableName) {
  const cols = getVisibleColumns(tableName);
  return HEADER_HEIGHT + Math.max(1, cols.length) * ROW_HEIGHT;
}

// Preset Layout Engines
function calculateInitialLayout(preset = 'hierarchical') {
  const tables = Array.from(selectedTables);
  if (tables.length === 0) return;

  if (preset === 'grid') {
    const cols = 5;
    const gapX = (layoutSpacing.grid || 310) + 30;
    const gapY = Math.round((layoutSpacing.grid || 310) * 0.95);
    tables.forEach((t, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      tablePositions[t] = {
        x: col * gapX + 80,
        y: row * gapY + 60,
        width: TABLE_WIDTH,
        height: getTableHeight(t)
      };
    });
  } else if (preset === 'cluster') {
    const gap = layoutSpacing.cluster || 310;
    comTables.forEach((t, i) => {
      if (!selectedTables.has(t)) return;
      const col = i % 2;
      const row = Math.floor(i / 2);
      tablePositions[t] = { x: col * gap + 60, y: row * Math.round(gap * 0.84) + 60, width: TABLE_WIDTH, height: getTableHeight(t) };
    });
    rafTables.forEach((t, i) => {
      if (!selectedTables.has(t)) return;
      const col = i % 4;
      const row = Math.floor(i / 4);
      tablePositions[t] = { x: col * gap + Math.round(gap * 2.38), y: row * Math.round(gap * 0.9) + 60, width: TABLE_WIDTH, height: getTableHeight(t) };
    });
  } else if (preset === 'circular') {
    const radius = layoutSpacing.circular || 550;
    const centerX = radius + 100, centerY = radius + 80;
    tables.forEach((t, i) => {
      const angle = (2 * Math.PI * i) / tables.length;
      tablePositions[t] = {
        x: Math.round(centerX + radius * Math.cos(angle) - TABLE_WIDTH / 2),
        y: Math.round(centerY + radius * Math.sin(angle) - getTableHeight(t) / 2),
        width: TABLE_WIDTH,
        height: getTableHeight(t)
      };
    });
  } else if (preset === 'hierarchical') {
    const inDegree = {}, outDegree = {};
    tables.forEach(t => { inDegree[t] = 0; outDegree[t] = 0; });
    fkList.forEach(f => {
      if (selectedTables.has(f.child) && selectedTables.has(f.parent)) {
        inDegree[f.child] = (inDegree[f.child] || 0) + 1;
        outDegree[f.parent] = (outDegree[f.parent] || 0) + 1;
      }
    });

    const levels = {};
    tables.forEach(t => {
      if (inDegree[t] === 0) levels[t] = 0;
      else if (outDegree[t] === 0) levels[t] = 3;
      else levels[t] = 1 + (inDegree[t] % 2);
    });

    const levelGroups = { 0: [], 1: [], 2: [], 3: [] };
    tables.forEach(t => {
      const lvl = levels[t] !== undefined ? levels[t] : 1;
      levelGroups[lvl].push(t);
    });

    let currentY = 60;
    [0, 1, 2, 3].forEach(lvl => {
      const list = levelGroups[lvl];
      const spacingX = layoutSpacing.hierarchical || 320;
      let maxHeightInLevel = 180;
      list.forEach((t, colIndex) => {
        const h = getTableHeight(t);
        if (h > maxHeightInLevel) maxHeightInLevel = h;
        tablePositions[t] = {
          x: colIndex * spacingX + 60,
          y: currentY,
          width: TABLE_WIDTH,
          height: h
        };
      });
      if (list.length > 0) currentY += maxHeightInLevel + 90;
    });
  } else if (preset === 'force') {
    const N = tables.length;
    // 1. Calculate connectivity degree for intelligent initial cluster placement
    const degree = {};
    tables.forEach(t => { degree[t] = 0; });
    fkList.forEach(f => {
      if (selectedTables.has(f.child) && selectedTables.has(f.parent)) {
        degree[f.child] = (degree[f.child] || 0) + 1;
        degree[f.parent] = (degree[f.parent] || 0) + 1;
      }
    });

    const sortedTables = tables.slice().sort((a, b) => (degree[b] || 0) - (degree[a] || 0));
    const cols = Math.max(4, Math.ceil(Math.sqrt(N) * 1.05));
    const GAP_X = 330, GAP_Y = 240;
    const centerX = (cols * GAP_X) / 2 + 80;
    const centerY = (Math.ceil(N / cols) * GAP_Y) / 2 + 60;

    // Reset initial positions deterministically around center
    sortedTables.forEach((t, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      tablePositions[t] = {
        x: col * GAP_X + 80,
        y: row * GAP_Y + 60,
        width: TABLE_WIDTH,
        height: getTableHeight(t)
      };
    });

    const k = (layoutSpacing.force || 220);
    const k2 = k * k;
    let temp = 42.0;
    const cooling = 0.92;

    const edges = [];
    fkList.forEach(f => {
      if (selectedTables.has(f.child) && selectedTables.has(f.parent) && f.child !== f.parent) {
        edges.push([f.parent, f.child]);
      }
    });

    // 2. Main Force Simulation Loop with Annealing
    for (let it = 0; it < 32; it++) {
      const disp = {};
      tables.forEach(t => { disp[t] = [0.0, 0.0]; });

      // Pairwise repulsion (Coulomb inverse-square model)
      for (let i = 0; i < N; i++) {
        const t1 = tables[i];
        const p1 = tablePositions[t1];
        const h1 = getTableHeight(t1);
        const c1x = p1.x + TABLE_WIDTH / 2;
        const c1y = p1.y + h1 / 2;

        for (let j = i + 1; j < N; j++) {
          const t2 = tables[j];
          const p2 = tablePositions[t2];
          const h2 = getTableHeight(t2);
          const c2x = p2.x + TABLE_WIDTH / 2;
          const c2y = p2.y + h2 / 2;

          const dx = c1x - c2x;
          const dy = c1y - c2y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
          const force = k2 / dist;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          disp[t1][0] += fx;
          disp[t1][1] += fy;
          disp[t2][0] -= fx;
          disp[t2][1] -= fy;
        }
      }

      // Edge attraction along Foreign Keys (Spring Hooke's model)
      for (let e = 0; e < edges.length; e++) {
        const pName = edges[e][0], cName = edges[e][1];
        const p1 = tablePositions[pName], p2 = tablePositions[cName];
        if (!p1 || !p2) continue;
        const h1 = getTableHeight(pName), h2 = getTableHeight(cName);
        const c1x = p1.x + TABLE_WIDTH / 2, c1y = p1.y + h1 / 2;
        const c2x = p2.x + TABLE_WIDTH / 2, c2y = p2.y + h2 / 2;

        const dx = c1x - c2x;
        const dy = c1y - c2y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
        const force = (dist * dist) / k;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        disp[pName][0] -= fx;
        disp[pName][1] -= fy;
        disp[cName][0] += fx;
        disp[cName][1] += fy;
      }

      // Central gravity (keeps tables unified and prevents runaway dispersion)
      for (let i = 0; i < N; i++) {
        const t = tables[i];
        const p = tablePositions[t];
        const h = getTableHeight(t);
        const cx = p.x + TABLE_WIDTH / 2;
        const cy = p.y + h / 2;
        disp[t][0] += (centerX - cx) * 0.25;
        disp[t][1] += (centerY - cy) * 0.25;
      }

      // Apply displacements with temperature damping
      for (let i = 0; i < N; i++) {
        const t = tables[i];
        const dx = disp[t][0];
        const dy = disp[t][1];
        const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
        const clamped = Math.min(dist, temp);
        tablePositions[t].x += (dx / dist) * clamped;
        tablePositions[t].y += (dy / dist) * clamped;
      }
      temp *= cooling;
    }

    // 3. Card Anti-Collision & Relaxation Pass (guarantees zero overlap between cards)
    for (let pass = 0; pass < 35; pass++) {
      for (let i = 0; i < N; i++) {
        const t1 = tables[i];
        const p1 = tablePositions[t1];
        const h1 = getTableHeight(t1);
        const c1x = p1.x + TABLE_WIDTH / 2;
        const c1y = p1.y + h1 / 2;

        for (let j = i + 1; j < N; j++) {
          const t2 = tables[j];
          const p2 = tablePositions[t2];
          const h2 = getTableHeight(t2);
          const c2x = p2.x + TABLE_WIDTH / 2;
          const c2y = p2.y + h2 / 2;

          const dx = c2x - c1x;
          const dy = c2y - c1y;
          const adx = Math.abs(dx);
          const ady = Math.abs(dy);

          const minW = TABLE_WIDTH + 40;
          const minH = (h1 + h2) / 2 + 35;

          if (adx < minW && ady < minH) {
            const overlapX = minW - adx;
            const overlapY = minH - ady;
            if (overlapX < overlapY) {
              const push = overlapX / 2 + 3;
              const sign = dx >= 0 ? 1 : -1;
              p1.x -= push * sign;
              p2.x += push * sign;
            } else {
              const push = overlapY / 2 + 3;
              const sign = dy >= 0 ? 1 : -1;
              p1.y -= push * sign;
              p2.y += push * sign;
            }
          }
        }
      }
    }

    // 4. Normalize to top-left padding (80, 60)
    let minX = Infinity, minY = Infinity;
    tables.forEach(t => {
      const p = tablePositions[t];
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
    });
    if (isFinite(minX) && isFinite(minY)) {
      tables.forEach(t => {
        tablePositions[t].x = Math.round(tablePositions[t].x - minX + 80);
        tablePositions[t].y = Math.round(tablePositions[t].y - minY + 60);
      });
    }
  } else if (preset === 'star') {
    const N = tables.length;
    // 1. Calculate connectivity degrees and adjacency
    const degree = {};
    const adj = {};
    tables.forEach(t => { degree[t] = 0; adj[t] = new Set(); });
    fkList.forEach(f => {
      if (selectedTables.has(f.child) && selectedTables.has(f.parent) && f.child !== f.parent) {
        degree[f.child] = (degree[f.child] || 0) + 1;
        degree[f.parent] = (degree[f.parent] || 0) + 1;
        adj[f.child].add(f.parent);
        adj[f.parent].add(f.child);
      }
    });

    // 2. Partition into connected components (supports multi-star constellations)
    const visited = new Set();
    const components = [];
    tables.forEach(t => {
      if (!visited.has(t)) {
        const comp = [];
        const queue = [t];
        visited.add(t);
        while (queue.length > 0) {
          const curr = queue.shift();
          comp.push(curr);
          (adj[curr] || []).forEach(neighbor => {
            if (!visited.has(neighbor)) {
              visited.add(neighbor);
              queue.push(neighbor);
            }
          });
        }
        components.push(comp);
      }
    });

    // Sort components descending by size
    components.sort((a, b) => b.length - a.length);

    // 3. Layout each component around its central fact / hub table
    let compOffsetX = 80;
    const baseRadius = layoutSpacing.star || 380;

    components.forEach((comp) => {
      const sortedComp = comp.slice().sort((a, b) => (degree[b] || 0) - (degree[a] || 0));
      const hub = sortedComp[0];
      const satellites = sortedComp.slice(1);

      if (satellites.length === 0) {
        tablePositions[hub] = {
          x: compOffsetX,
          y: 60,
          width: TABLE_WIDTH,
          height: getTableHeight(hub)
        };
        compOffsetX += TABLE_WIDTH + 90;
        return;
      }

      // Directly use the user-configured Star radius from settings
      const radius = baseRadius;
      const centerX = compOffsetX + radius + TABLE_WIDTH / 2;
      const centerY = radius + 80;

      // Position central hub (fact table)
      tablePositions[hub] = {
        x: Math.round(centerX - TABLE_WIDTH / 2),
        y: Math.round(centerY - getTableHeight(hub) / 2),
        width: TABLE_WIDTH,
        height: getTableHeight(hub)
      };

      // Order satellites: direct neighbors first, then by degree
      satellites.sort((a, b) => {
        const aDirect = adj[hub] && adj[hub].has(a) ? 1 : 0;
        const bDirect = adj[hub] && adj[hub].has(b) ? 1 : 0;
        if (aDirect !== bDirect) return bDirect - aDirect;
        return (degree[b] || 0) - (degree[a] || 0);
      });

      // Position dimension satellites radially at exact user radius
      satellites.forEach((t, i) => {
        const angle = (2 * Math.PI * i) / satellites.length - Math.PI / 2;
        tablePositions[t] = {
          x: Math.round(centerX + radius * Math.cos(angle) - TABLE_WIDTH / 2),
          y: Math.round(centerY + radius * Math.sin(angle) - getTableHeight(t) / 2),
          width: TABLE_WIDTH,
          height: getTableHeight(t)
        };
      });

      compOffsetX = centerX + radius + TABLE_WIDTH / 2 + 110;
    });

    // 4. Anti-Collision & Relaxation Pass (guarantees zero overlap)
    for (let pass = 0; pass < 25; pass++) {
      for (let i = 0; i < N; i++) {
        const t1 = tables[i];
        const p1 = tablePositions[t1];
        const h1 = getTableHeight(t1);
        const c1x = p1.x + TABLE_WIDTH / 2;
        const c1y = p1.y + h1 / 2;

        for (let j = i + 1; j < N; j++) {
          const t2 = tables[j];
          const p2 = tablePositions[t2];
          const h2 = getTableHeight(t2);
          const c2x = p2.x + TABLE_WIDTH / 2;
          const c2y = p2.y + h2 / 2;

          const dx = c2x - c1x;
          const dy = c2y - c1y;
          const adx = Math.abs(dx);
          const ady = Math.abs(dy);

          const minW = TABLE_WIDTH + 35;
          const minH = (h1 + h2) / 2 + 30;

          if (adx < minW && ady < minH) {
            const overlapX = minW - adx;
            const overlapY = minH - ady;
            if (overlapX < overlapY) {
              const push = overlapX / 2 + 2;
              const sign = dx >= 0 ? 1 : -1;
              p1.x -= push * sign;
              p2.x += push * sign;
            } else {
              const push = overlapY / 2 + 2;
              const sign = dy >= 0 ? 1 : -1;
              p1.y -= push * sign;
              p2.y += push * sign;
            }
          }
        }
      }
    }

    // 5. Normalize coordinates to top-left padding (80, 60)
    let minX = Infinity, minY = Infinity;
    tables.forEach(t => {
      const p = tablePositions[t];
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
    });
    if (isFinite(minX) && isFinite(minY)) {
      tables.forEach(t => {
        tablePositions[t].x = Math.round(tablePositions[t].x - minX + 80);
        tablePositions[t].y = Math.round(tablePositions[t].y - minY + 60);
      });
    }
  }

  tables.forEach(t => {
    if (tablePositions[t]) tablePositions[t].height = getTableHeight(t);
  });
}

// Render Both Tables and Dynamic Connecting Arrows
function renderAll() {
  renderTables();
  renderRelationships();
  updateCanvasTransform();
  updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
}

// Render Tables SVG matching exact Mermaid markup with strict LTR
function renderTables() {
  const layer = document.getElementById('tablesLayer');
  layer.innerHTML = '';

  const sel = Array.from(selectedTables);
  sel.forEach(t => {
    const data = tablesData[t];
    if (!data) return;

    if (!tablePositions[t]) {
      tablePositions[t] = { x: 100, y: 100, width: TABLE_WIDTH, height: getTableHeight(t) };
    }
    const pos = tablePositions[t];
    if (!isFinite(pos.x)) pos.x = 100;
    if (!isFinite(pos.y)) pos.y = 100;
    if (!isFinite(pos.width) || pos.width <= 0) pos.width = TABLE_WIDTH;
    pos.height = getTableHeight(t);

    const isSelected = selectedTableNodes.has(t);

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', `table-node er ${isSelected ? 'selected-node' : ''}${highlightedTables.has(t) ? ' is-highlighted' : ''}`);
    g.setAttribute('id', `node-${t}`);
    g.setAttribute('data-id', t);
    g.setAttribute('dir', 'ltr');
    g.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);

    const cols = getVisibleColumns(t);
    const totalHeight = HEADER_HEIGHT + cols.length * ROW_HEIGHT;

    // Header Entity Box
    const headerRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    headerRect.setAttribute('class', 'er entityBox');
    headerRect.setAttribute('x', '0');
    headerRect.setAttribute('y', '0');
    headerRect.setAttribute('width', TABLE_WIDTH);
    headerRect.setAttribute('height', HEADER_HEIGHT);
    if (subsystemColorEnabled) {
      const subColor = subsystemColorOf(t);
      headerRect.setAttribute('style', `stroke:${subColor};stroke-width:${highlightedTables.has(t) ? 2.6 : 1.6}px;`);
    }
    if (data.comment || data.description) {
      const tTitle = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      tTitle.textContent = `${t}: ${data.comment || data.description}`;
      headerRect.appendChild(tTitle);
    }
    g.appendChild(headerRect);

    // Header Text
    const headerText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    headerText.setAttribute('class', 'er entityTitleText');
    headerText.setAttribute('x', TABLE_WIDTH / 2);
    headerText.setAttribute('y', HEADER_HEIGHT / 2);
    headerText.setAttribute('text-anchor', 'middle');
    headerText.setAttribute('direction', 'ltr');
    headerText.textContent = t;
    g.appendChild(headerText);

    // Attribute Rows
    cols.forEach((col, idx) => {
      const rowY = HEADER_HEIGHT + idx * ROW_HEIGHT;
      const isOdd = idx % 2 === 0;
      const isPK = data.pks.includes(col.name);
      const isFK = fkList.some(f => f.child === t && f.cols.includes(col.name));
      const keyLabel = (isPK && isFK) ? 'PK,FK' : isPK ? 'PK' : isFK ? 'FK' : '';

      // Name Box (Left)
      const nameRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      nameRect.setAttribute('class', isOdd ? 'er attributeBoxOdd' : 'er attributeBoxEven');
      nameRect.setAttribute('x', '0');
      nameRect.setAttribute('y', rowY);
      nameRect.setAttribute('width', TYPE_COL_WIDTH);
      nameRect.setAttribute('height', ROW_HEIGHT);
      if (col.comment || col.description) {
        const cTitle = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        cTitle.textContent = `${col.name} (${col.type}): ${col.comment || col.description}`;
        nameRect.appendChild(cTitle);
      }
      g.appendChild(nameRect);

      // Name Text
      const nameText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      nameText.setAttribute('class', 'er attrTextName');
      nameText.setAttribute('x', '6');
      nameText.setAttribute('y', rowY + ROW_HEIGHT / 2);
      nameText.setAttribute('text-anchor', 'start');
      nameText.setAttribute('direction', 'ltr');
      nameText.setAttribute('unicode-bidi', 'bidi-override');
      nameText.textContent = col.name;
      g.appendChild(nameText);

      // Type Box (Right)
      const typeRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      typeRect.setAttribute('class', isOdd ? 'er attributeBoxOdd' : 'er attributeBoxEven');
      typeRect.setAttribute('x', TYPE_COL_WIDTH);
      typeRect.setAttribute('y', rowY);
      typeRect.setAttribute('width', TABLE_WIDTH - TYPE_COL_WIDTH);
      typeRect.setAttribute('height', ROW_HEIGHT);
      g.appendChild(typeRect);

      // Type Text
      const typeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      typeText.setAttribute('class', 'er attrTextType');
      typeText.setAttribute('x', TYPE_COL_WIDTH + 6);
      typeText.setAttribute('y', rowY + ROW_HEIGHT / 2);
      typeText.setAttribute('text-anchor', 'start');
      typeText.setAttribute('direction', 'ltr');
      typeText.setAttribute('unicode-bidi', 'bidi-override');
      typeText.textContent = col.type;
      g.appendChild(typeText);

      // Key Badge Text (right end of type cell, clear of long column names)
      if (keyLabel) {
        const keyText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        keyText.setAttribute('class', 'er attrTextKey');
        keyText.setAttribute('x', TABLE_WIDTH - 6);
        keyText.setAttribute('y', rowY + ROW_HEIGHT / 2);
        keyText.setAttribute('text-anchor', 'end');
        keyText.setAttribute('direction', 'ltr');
        keyText.textContent = keyLabel;
        g.appendChild(keyText);
      }
    });

    // Listeners
    g.addEventListener('mousedown', (e) => startNodeDrag(e, t));
    g.addEventListener('dblclick', (e) => {
      e.stopPropagation();
      openColumnModalFor(t);
    });

    layer.appendChild(g);
  });
}

// Render Dynamic Relationship Connectors
function relMarkerId(kind, color) {
  return `md-${kind}-${String(color).replace('#', '')}`;
}
function pathMarker(kind, color) {
  const id = relMarkerId(kind, color);
  if (document.getElementById(id)) return `url(#${id})`;
  const defs = document.querySelector('#mainSvg defs');
  if (!defs) return `url(#md-${kind}-hi)`;
  const m = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
  m.setAttribute('id', id);
  m.setAttribute('orient', 'auto-start-reverse');
  const mk = (w, h, refX, refY, mw, mh) => {
    m.setAttribute('viewBox', `0 0 ${w} ${h}`);
    m.setAttribute('refX', refX); m.setAttribute('refY', refY);
    m.setAttribute('markerWidth', mw); m.setAttribute('markerHeight', mh);
  };
  const el = (tag) => document.createElementNS('http://www.w3.org/2000/svg', tag);
  const path = el('path');
  const solid = (sw, lc) => { path.setAttribute('stroke', color); path.setAttribute('stroke-width', sw); path.setAttribute('fill', 'none'); if (lc) path.setAttribute('stroke-linecap', lc); };
  const circleMarker = (cx, cy, r, sw) => {
    const c = el('circle');
    c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('r', r);
    c.setAttribute('stroke', color); c.setAttribute('stroke-width', sw); c.setAttribute('fill', 'none');
    m.appendChild(c);
    return c;
  };
  if (kind === 'one') {
    mk(12, 12, 10, 6, 7, 7);
    path.setAttribute('d', 'M 2,0 L 2,12'); solid(2.4, 'round');
  } else if (kind === 'opt') {
    mk(12, 12, 9, 6, 8, 8);
    circleMarker(6, 6, 3.4, 2);
  } else if (kind === 'oneOpt') {
    mk(22, 12, 20, 6, 14, 9);
    path.setAttribute('d', 'M 2,1 L 2,11'); solid(2.2, 'round');
    circleMarker(18, 6, 3.2, 1.8);
  } else if (kind === 'crowfootOpt') {
    mk(22, 24, 20, 12, 14, 16);
    path.setAttribute('d', 'M 5,12 L 16,1 M 5,12 L 20,12 M 5,12 L 16,23'); solid(2, 'round');
    circleMarker(1.5, 12, 3.2, 1.8);
  } else if (kind === 'crowfoot') {
    mk(20, 24, 16, 12, 12, 15);
    path.setAttribute('d', 'M 1,12 L 16,1 M 1,12 L 18,12 M 1,12 L 16,23'); solid(2, 'round');
  } else { // ident diamond
    mk(16, 12, 13, 6, 11, 10);
    path.setAttribute('d', 'M 2,6 L 8,0 L 14,6 L 8,12 Z'); path.setAttribute('fill', color);
  }
  m.appendChild(path);
  defs.appendChild(m);
  return `url(#${id})`;
}
function renderRelationships() {
  const layer = document.getElementById('relationsLayer');
  layer.innerHTML = '';

  const activeFks = fkList.filter(f => selectedTables.has(f.child) && selectedTables.has(f.parent));

  const pairCount = {};
  activeFks.forEach(fk => {
    const k = fk.parent + '||' + fk.child;
    pairCount[k] = (pairCount[k] || 0) + 1;
  });
  const pairSeq = {};

  activeFks.forEach((fk, idx) => {
    const parentPos = tablePositions[fk.parent];
    const childPos = tablePositions[fk.child];
    if (!parentPos || !childPos) return;
    if (!isFinite(parentPos.width) || !isFinite(parentPos.height) || !isFinite(childPos.width) || !isFinite(childPos.height)) return;

    const isSelfRef = fk.parent === fk.child;

    // Relationship typing
    const childData = tablesData[fk.child] || {};
    const childPks = childData.pks || [];
    const fkCols = (fk.cols || '').split(',').map(c => c.trim()).filter(Boolean);
    const isIdentifying = fkCols.length > 0 && fkCols.some(c => childPks.includes(c));
    const isOneToOne = fkCols.length > 0 && fkCols.length === childPks.length &&
      childPks.length > 0 && fkCols.every(c => childPks.includes(c));
    const manyKind = isSelfRef ? 'ident' : isIdentifying ? 'ident' : isOneToOne ? 'one' : 'crowfoot';
    let childColNullable = false;
    (childData.columns || []).forEach(col => {
      if (fkCols.includes(col.name) && col.nullable !== false) childColNullable = true;
    });

    // Nullable FK → optional circle at the "one" end (0..1), and 0..n at the many end
    const oneMarker = childColNullable ? 'opt' : 'one';
    let endKind;
    if (isSelfRef || isIdentifying) endKind = 'ident';
    else if (isOneToOne) endKind = childColNullable ? 'oneOpt' : 'one';
    else endKind = childColNullable ? 'crowfootOpt' : 'crowfoot';

    const color = isSelfRef ? '#8b5cf6' : subsystemColorOf(fk.child);

    const relG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    relG.setAttribute('class', 'rel-group');
    relG.setAttribute('id', `rel-${idx}`);
    relG.setAttribute('data-parent', fk.parent);
    relG.setAttribute('data-child', fk.child);
    relG.setAttribute('data-ident', isIdentifying ? '1' : '0');
    relG.setAttribute('data-many', manyKind === 'crowfoot' ? '1' : '0');

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('class', 'relationshipLine');
    path.style.stroke = color;

    let me, ms, midX, midY;
    if (isSelfRef) {
      const px = parentPos.x + parentPos.width;
      const py = parentPos.y + Math.min(parentPos.height * 0.4, HEADER_HEIGHT + 10);
      const loopEnd = parentPos.y + parentPos.height * 0.72;
      path.setAttribute('d', `M ${px} ${py} C ${px + 64} ${py - 34}, ${px + 64} ${loopEnd + 34}, ${px} ${loopEnd}`);
      path.setAttribute('stroke-dasharray', '7 4');
      me = 'url(#md-ident-hi)';
      ms = 'url(#md-one-hi)';
      midX = px + 42; midY = (py + loopEnd) / 2 + 6;
    } else {
      // Spread overlapping connectors between the same table pair
      const pairKey = fk.parent + '||' + fk.child;
      if (!(pairKey in pairSeq)) pairSeq[pairKey] = 0;
      const localIdx = pairSeq[pairKey]++;
      const totalForPair = pairCount[pairKey] || 1;
      const perp = totalForPair > 1 ? (localIdx - (totalForPair - 1) / 2) * 13 : 0;
      relG.setAttribute('data-perp', String(perp));

      const pA = Object.assign({}, parentPos);
      const cB = Object.assign({}, childPos);
      const dx = (cB.x + cB.width / 2) - (pA.x + pA.width / 2);
      const dy = (cB.y + cB.height / 2) - (pA.y + pA.height / 2);
      if (Math.abs(dx) >= Math.abs(dy)) { pA.y += perp; cB.y += perp; } else { pA.x += perp; cB.x += perp; }

      const points = calculateConnectorPoints(pA, cB);
      if (!points) return;
      path.setAttribute('d', `M ${points.x1} ${points.y1} C ${points.cx1} ${points.cy1}, ${points.cx2} ${points.cy2}, ${points.x2} ${points.y2}`);
      path.setAttribute('stroke-width', isIdentifying ? '2.1' : '1.7');
      if (!isIdentifying) path.setAttribute('stroke-dasharray', '7 4');

      me = pathMarker(endKind, color);
      ms = pathMarker(oneMarker, color);
      midX = (points.x1 + points.x2) / 2;
      midY = (points.y1 + points.y2) / 2;
    }

    path.setAttribute('marker-end', me);
    path.setAttribute('marker-start', ms);
    path.setAttribute('data-me', me);
    path.setAttribute('data-ms', ms);
    path.setAttribute('data-me-hi', `url(#md-${manyKind}-hi)`);
    path.setAttribute('data-ms-hi', 'url(#md-one-hi)');
    relG.appendChild(path);

    // Midpoint Label
    const labelText = fk.fk;
    const textWidth = Math.min(150, labelText.length * 6.5 + 14);
    const labelBox = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    labelBox.setAttribute('class', 'rel-label-box');
    labelBox.setAttribute('x', midX - textWidth / 2);
    labelBox.setAttribute('y', midY - 9);
    labelBox.setAttribute('width', textWidth);
    labelBox.setAttribute('height', 18);
    relG.appendChild(labelBox);
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('class', 'rel-label-text');
    label.setAttribute('x', midX);
    label.setAttribute('y', midY);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('direction', 'ltr');
    label.textContent = labelText;
    relG.appendChild(label);

    // Native SVG tooltip
    const tipText = (typeof currentLang !== 'undefined' && currentLang === 'ar')
      ? `انقر لعرض تفاصيل العلاقة: ${fk.fk || ''} (${fk.parent} ➔ ${fk.child})`
      : `Click to view relationship details: ${fk.fk || ''} (${fk.parent} ➔ ${fk.child})`;
    const titleEl = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    titleEl.textContent = tipText;
    relG.appendChild(titleEl);

    // Interactive Relationship Inspection Click & Hover Events
    const relMeta = {
      relG, path, labelBox, label,
      isIdentifying, isOneToOne, childColNullable,
      manyKind, oneMarker, color
    };

    const onRelClick = (ev) => {
      ev.stopPropagation();
      ev.preventDefault();
      openRelationshipModal(fk, relMeta);
    };

    const onRelMouseDown = (ev) => {
      ev.stopPropagation();
    };

    labelBox.style.cursor = 'pointer';
    label.style.cursor = 'pointer';
    path.style.cursor = 'pointer';

    labelBox.addEventListener('click', onRelClick);
    labelBox.addEventListener('mousedown', onRelMouseDown);
    label.addEventListener('click', onRelClick);
    label.addEventListener('mousedown', onRelMouseDown);
    path.addEventListener('click', onRelClick);
    path.addEventListener('mousedown', onRelMouseDown);

    relG.addEventListener('mouseenter', () => {
      const pNode = document.getElementById(`node-${fk.parent}`);
      const cNode = document.getElementById(`node-${fk.child}`);
      if (pNode) pNode.classList.add('connected-node');
      if (cNode) cNode.classList.add('connected-node');
    });
    relG.addEventListener('mouseleave', () => {
      if (!relG.classList.contains('active-rel') && (!selectedTableNodes || selectedTableNodes.size === 0)) {
        const pNode = document.getElementById(`node-${fk.parent}`);
        const cNode = document.getElementById(`node-${fk.child}`);
        if (pNode && selectedTableNodes && !selectedTableNodes.has(fk.parent)) pNode.classList.remove('connected-node');
        if (cNode && selectedTableNodes && !selectedTableNodes.has(fk.child)) cNode.classList.remove('connected-node');
      }
    });

    layer.appendChild(relG);
  });
}

// Calculate Connection Anchor Points
function calculateConnectorPoints(boxA, boxB) {
  if (!boxA || !boxB) return null;
  const vals = [boxA.x, boxA.y, boxA.width, boxA.height, boxB.x, boxB.y, boxB.width, boxB.height];
  if (vals.some(v => !isFinite(v)) || boxA.width <= 0 || boxB.width <= 0) return null;

  const centerA = { x: boxA.x + boxA.width / 2, y: boxA.y + boxA.height / 2 };
  const centerB = { x: boxB.x + boxB.width / 2, y: boxB.y + boxB.height / 2 };

  const dx = centerB.x - centerA.x;
  const dy = centerB.y - centerA.y;

  let x1, y1, x2, y2;

  if (Math.abs(dx) >= Math.abs(dy)) {
    if (dx > 0) {
      x1 = boxA.x + boxA.width;
      y1 = Math.max(boxA.y + 15, Math.min(boxA.y + boxA.height - 15, centerA.y));
      x2 = boxB.x;
      y2 = Math.max(boxB.y + 15, Math.min(boxB.y + boxB.height - 15, centerB.y));
    } else {
      x1 = boxA.x;
      y1 = Math.max(boxA.y + 15, Math.min(boxA.y + boxA.height - 15, centerA.y));
      x2 = boxB.x + boxB.width;
      y2 = Math.max(boxB.y + 15, Math.min(boxB.y + boxB.height - 15, centerB.y));
    }
  } else {
    if (dy > 0) {
      x1 = Math.max(boxA.x + 15, Math.min(boxA.x + boxA.width - 15, centerA.x));
      y1 = boxA.y + boxA.height;
      x2 = Math.max(boxB.x + 15, Math.min(boxB.x + boxB.width - 15, centerB.x));
      y2 = boxB.y;
    } else {
      x1 = Math.max(boxA.x + 15, Math.min(boxA.x + boxA.width - 15, centerA.x));
      y1 = boxA.y;
      x2 = Math.max(boxB.x + 15, Math.min(boxB.x + boxB.width - 15, centerB.x));
      y2 = boxB.y + boxB.height;
    }
  }

  const offset = Math.min(100, Math.max(40, Math.hypot(x2 - x1, y2 - y1) * 0.35));
  let cx1 = x1, cy1 = y1, cx2 = x2, cy2 = y2;

  if (Math.abs(dx) >= Math.abs(dy)) {
    cx1 = x1 + (dx > 0 ? offset : -offset);
    cx2 = x2 + (dx > 0 ? -offset : offset);
  } else {
    cy1 = y1 + (dy > 0 ? offset : -offset);
    cy2 = y2 + (dy > 0 ? -offset : offset);
  }

  return { x1, y1, x2, y2, cx1, cy1, cx2, cy2 };
}

// MULTI-SELECTION & GROUP DRAG
function startNodeDrag(e, tableName) {
  if (e.button !== 0) return;
  e.stopPropagation();

  const isCtrl = e.ctrlKey || e.metaKey || e.shiftKey;

  if (isCtrl) {
    toggleTableInMultiSelection(tableName);
    return;
  }

  if (!selectedTableNodes.has(tableName)) {
    selectedTableNodes.clear();
    selectedTableNodes.add(tableName);
    updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
  }

  draggedNode = tableName;
  isDraggingNode = false;
  dragStartX = e.clientX;
  dragStartY = e.clientY;

  groupInitialPositions = {};
  selectedTableNodes.forEach(t => {
    if (tablePositions[t]) {
      groupInitialPositions[t] = { x: tablePositions[t].x, y: tablePositions[t].y };
    }
  });
}

function onMouseMove(e) {
  if (isMarqueeActive) {
    const wrap = document.getElementById('canvasWrap');
    const wrapRect = wrap.getBoundingClientRect();
    const curX = e.clientX - wrapRect.left;
    const curY = e.clientY - wrapRect.top;

    const left = Math.min(marqueeStartX, curX);
    const top = Math.min(marqueeStartY, curY);
    const width = Math.abs(curX - marqueeStartX);
    const height = Math.abs(curY - marqueeStartY);

    const mBox = document.getElementById('marqueeBox');
    mBox.style.left = `${left}px`;
    mBox.style.top = `${top}px`;
    mBox.style.width = `${width}px`;
    mBox.style.height = `${height}px`;

    const canvasMinX = (left - panX) / zoom;
    const canvasMinY = (top - panY) / zoom;
    const canvasMaxX = (left + width - panX) / zoom;
    const canvasMaxY = (top + height - panY) / zoom;

    selectedTableNodes.clear();
    Array.from(selectedTables).forEach(t => {
      const p = tablePositions[t];
      if (p) {
        const tableRight = p.x + p.width;
        const tableBottom = p.y + p.height;
        const intersects = !(p.x > canvasMaxX || tableRight < canvasMinX || p.y > canvasMaxY || tableBottom < canvasMinY);
        if (intersects) {
          selectedTableNodes.add(t);
        }
      }
    });

    updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();

  } else if (draggedNode) {
    const dist = Math.hypot(e.clientX - dragStartX, e.clientY - dragStartY);
    if (dist > 4) {
      if (!isDraggingNode) {
        isDraggingNode = true;
        selectedTableNodes.forEach(t => {
          const nodeEl = document.getElementById(`node-${t}`);
          if (nodeEl) nodeEl.classList.add('dragging');
        });
      }

      const dx = (e.clientX - dragStartX) / zoom;
      const dy = (e.clientY - dragStartY) / zoom;

      selectedTableNodes.forEach(t => {
        const initPos = groupInitialPositions[t];
        if (initPos && tablePositions[t]) {
          tablePositions[t].x = initPos.x + dx;
          tablePositions[t].y = initPos.y + dy;

          const nodeEl = document.getElementById(`node-${t}`);
          if (nodeEl) {
            nodeEl.setAttribute('transform', `translate(${tablePositions[t].x}, ${tablePositions[t].y})`);
          }

          updateConnectedRelationships(t);
        }
      });
    }
  } else if (isPanning) {
    panX = e.clientX - startPanX;
    panY = e.clientY - startPanY;
    updateCanvasTransform();
  }
}

function onMouseUp(e) {
  if (isMarqueeActive) {
    isMarqueeActive = false;
    document.getElementById('marqueeBox').style.display = 'none';
    document.getElementById('canvasWrap').classList.remove('crosshair');
    if (selectedTableNodes.size > 0) {
 const msg = currentLang === 'ar' ? ` تم تحديد ${selectedTableNodes.size} جداول - اسحب لتحريك المجموعة!` : ` Selected ${selectedTableNodes.size} tables - Drag to move group!`;
      showToast(msg);
    }
  }

  if (draggedNode) {
    selectedTableNodes.forEach(t => {
      const nodeEl = document.getElementById(`node-${t}`);
      if (nodeEl) nodeEl.classList.remove('dragging');
    });

    if (!isDraggingNode) {
      selectedTableNodes.clear();
      selectedTableNodes.add(draggedNode);
      updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
    } else {
      // Auto-save dragged positions to SQLite
      scheduleAutoSave();
    }

    draggedNode = null;
    isDraggingNode = false;
  }

  if (isPanning) {
    isPanning = false;
    document.getElementById('canvasWrap').classList.remove('grabbing');
    scheduleAutoSave();
  }
}

function updateConnectedRelationships(tableName) {
  const relGroups = document.querySelectorAll(`.rel-group[data-parent="${tableName}"], .rel-group[data-child="${tableName}"]`);
  relGroups.forEach(layoutRel);
}

function layoutRel(relG) {
  if (!relG) return;
  const parent = relG.getAttribute('data-parent');
  const child = relG.getAttribute('data-child');
  const parentPos = tablePositions[parent];
  const childPos = tablePositions[child];
  if (!parentPos || !childPos) return;
  const path = relG.querySelector('path');
  if (!path) return;

  let midX, midY;
  if (parent === child) {
    const px = parentPos.x + parentPos.width;
    const py = parentPos.y + Math.min(parentPos.height * 0.4, HEADER_HEIGHT + 10);
    const loopEnd = parentPos.y + parentPos.height * 0.72;
    path.setAttribute('d', `M ${px} ${py} C ${px + 64} ${py - 34}, ${px + 64} ${loopEnd + 34}, ${px} ${loopEnd}`);
    path.setAttribute('stroke-dasharray', '7 4');
    midX = px + 42; midY = (py + loopEnd) / 2 + 6;
  } else {
    const perp = parseFloat(relG.getAttribute('data-perp')) || 0;
    const pA = Object.assign({}, parentPos);
    const cB = Object.assign({}, childPos);
    const dx = (cB.x + cB.width / 2) - (pA.x + pA.width / 2);
    const dy = (cB.y + cB.height / 2) - (pA.y + pA.height / 2);
    if (Math.abs(dx) >= Math.abs(dy)) { pA.y += perp; cB.y += perp; } else { pA.x += perp; cB.x += perp; }

    const pts = calculateConnectorPoints(pA, cB);
    if (!pts) return;
    path.setAttribute('d', `M ${pts.x1} ${pts.y1} C ${pts.cx1} ${pts.cy1}, ${pts.cx2} ${pts.cy2}, ${pts.x2} ${pts.y2}`);
    midX = (pts.x1 + pts.x2) / 2;
    midY = (pts.y1 + pts.y2) / 2;
  }

  const box = relG.querySelector('.rel-label-box');
  const txt = relG.querySelector('.rel-label-text');
  if (box && txt) {
    const w = parseFloat(box.getAttribute('width')) || 40;
    box.setAttribute('x', midX - w / 2);
    box.setAttribute('y', midY - 9);
    txt.setAttribute('x', midX);
    txt.setAttribute('y', midY);
  }
}

function toggleTableInMultiSelection(tableName) {
  if (selectedTableNodes.has(tableName)) {
    selectedTableNodes.delete(tableName);
  } else {
    selectedTableNodes.add(tableName);
  }
  updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
}

function updateSelectionUI() {
  const allNodes = document.querySelectorAll('.table-node');
  const allLines = document.querySelectorAll('.relationshipLine');
  const allSidebarItems = document.querySelectorAll('.tree-row');

  allNodes.forEach(n => { n.classList.remove('selected-node', 'connected-node'); });
  allLines.forEach(l => {
    l.classList.remove('highlighted', 'dimmed');
    if (l.dataset.me) l.setAttribute('marker-end', l.dataset.me);
    if (l.dataset.ms) l.setAttribute('marker-start', l.dataset.ms);
  });
  allSidebarItems.forEach(el => el.classList.remove('is-selected'));

  const count = selectedTableNodes.size;
  const bar = document.getElementById('floatingActionBar');
  const barTitle = document.getElementById('barTableName');
  const singleActions = document.getElementById('barSingleActions');
  const multiActions = document.getElementById('barMultiActions');
  const t = i18n[currentLang];

  if (count === 0) {
    bar.classList.remove('show');
    return;
  }

  bar.classList.add('show');

  if (count === 1) {
    const singleTable = Array.from(selectedTableNodes)[0];
    barTitle.textContent = singleTable;
    singleActions.style.display = 'flex';
    multiActions.style.display = 'none';

    const current = document.getElementById(`node-${singleTable}`);
    if (current) current.classList.add('selected-node');

    const connectedTables = new Set();
    fkList.forEach((fk, idx) => {
      if (selectedTables.has(fk.child) && selectedTables.has(fk.parent)) {
        const isRelated = fk.child === singleTable || fk.parent === singleTable;
        const lineEl = document.querySelector(`#rel-${idx} path`);
        if (isRelated) {
          if (lineEl) {
            lineEl.classList.add('highlighted');
            if (lineEl.dataset.meHi) lineEl.setAttribute('marker-end', lineEl.dataset.meHi);
            if (lineEl.dataset.msHi) lineEl.setAttribute('marker-start', lineEl.dataset.msHi);
          }
          connectedTables.add(fk.child);
          connectedTables.add(fk.parent);
        } else {
          if (lineEl) lineEl.classList.add('dimmed');
        }
      }
    });

    connectedTables.forEach(t => {
      if (t !== singleTable) {
        const el = document.getElementById(`node-${t}`);
        if (el) el.classList.add('connected-node');
      }
    });

    const sidebarEl = document.getElementById(`sidebar-item-${singleTable}`);
    if (sidebarEl) sidebarEl.classList.add('is-selected');

  } else {
    barTitle.textContent = `${count} ${t.chipAll}`;
    singleActions.style.display = 'none';
    multiActions.style.display = 'flex';

    selectedTableNodes.forEach(t => {
      const nodeEl = document.getElementById(`node-${t}`);
      if (nodeEl) nodeEl.classList.add('selected-node');
      const sidebarEl = document.getElementById(`sidebar-item-${t}`);
      if (sidebarEl) sidebarEl.classList.add('is-selected');
    });

    fkList.forEach((fk, idx) => {
      if (selectedTables.has(fk.child) && selectedTables.has(fk.parent)) {
        const bothSelected = selectedTableNodes.has(fk.child) && selectedTableNodes.has(fk.parent);
        const lineEl = document.querySelector(`#rel-${idx} path`);
        if (bothSelected && lineEl) {
          lineEl.classList.add('highlighted');
          if (lineEl.dataset.meHi) lineEl.setAttribute('marker-end', lineEl.dataset.meHi);
          if (lineEl.dataset.msHi) lineEl.setAttribute('marker-start', lineEl.dataset.msHi);
        }
      }
    });
  }
}

function deselectAll() {
  selectedTableNodes.clear();
  updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
}

// Multi-Selection Quick Actions
function applyNoAuditToMultiSelection() {
  selectedTableNodes.forEach(t => {
    const data = tablesData[t];
    if (!data) return;
    const pks = new Set(data.pks);
    const hidden = new Set();
    data.columns.forEach(c => {
      if (!pks.has(c.name) && isAuditColumn(c.name)) hidden.add(c.name);
    });
    tableCustomHiddenCols[t] = hidden;
    tablePositions[t].height = getTableHeight(t);
  });
  renderAll();
  scheduleAutoSave();
 const msg = currentLang === 'ar' ? ` تم إخفاء أعمدة التدقيق عن ${selectedTableNodes.size} جداول` : ` Hidden audit columns on ${selectedTableNodes.size} tables`;
  showToast(msg);
}

function applyKeysOnlyToMultiSelection() {
  selectedTableNodes.forEach(t => {
    const data = tablesData[t];
    if (!data) return;
    const pks = data.pks;
    const childFkCols = fkList.filter(f => f.child === t).map(f => f.cols.split(',').map(s=>s.trim())).flat();
    const parentFkCols = fkList.filter(f => f.parent === t).map(f => f.cols.split(',').map(s=>s.trim())).flat();
    const keySet = new Set([...pks, ...childFkCols, ...parentFkCols]);
    tableCustomHiddenCols[t] = new Set(data.columns.map(c => c.name).filter(name => !keySet.has(name)));
    tablePositions[t].height = getTableHeight(t);
  });
  renderAll();
  scheduleAutoSave();
 const msg = currentLang === 'ar' ? ` إبقاء المفاتيح فقط لـ ${selectedTableNodes.size} جداول` : ` Keys Only applied to ${selectedTableNodes.size} tables`;
  showToast(msg);
}

function applyShowAllToMultiSelection() {
  selectedTableNodes.forEach(t => {
    tableCustomHiddenCols[t] = new Set();
    tablePositions[t].height = getTableHeight(t);
  });
  renderAll();
  scheduleAutoSave();
 const msg = currentLang === 'ar' ? ` إظهار كل الحقول لـ ${selectedTableNodes.size} جداول` : ` Showing all columns on ${selectedTableNodes.size} tables`;
  showToast(msg);
}

function hideAllSelectedTables() {
  const count = selectedTableNodes.size;
  selectedTableNodes.forEach(t => {
    selectedTables.delete(t);
  });
  selectedTableNodes.clear();
  buildSidebarList();
  renderAll();
  scheduleAutoSave();
  const msg = currentLang === 'ar' ? `تم إخفاء ${count} جداول` : `Hidden ${count} tables`;
  showToast(msg);
}

// COLUMN MANAGER MODAL DIALOG
function openColumnModalFor(tableName) {
  selectedTableNodes.clear();
  selectedTableNodes.add(tableName);
  updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();

  const modal = document.getElementById('columnModal');
  const title = document.getElementById('modalTableTitle');
  const subtitle = document.getElementById('modalTableSubtitle');
  document.getElementById('modalSearchInput').value = '';

  const data = tablesData[tableName];
  if (!data) return;

  title.textContent = tableName;
  const visibleCols = getVisibleColumns(tableName);
  const t = i18n[currentLang];
  subtitle.textContent = currentLang === 'ar' ? `${visibleCols.length} من أصل ${data.columns.length} حقول` : `${visibleCols.length} of ${data.columns.length} columns`;

  renderModalColumnsList(tableName);
  modal.classList.add('open');
}

function openModalForSelected() {
  if (selectedTableNodes.size === 1) {
    openColumnModalFor(Array.from(selectedTableNodes)[0]);
  }
}

function closeColumnModal() {
  document.getElementById('columnModal').classList.remove('open');
}

function closeModalOnBackdrop(e) {
  if (e.target.id === 'columnModal') closeColumnModal();
  if (e.target.id === 'settingsModal') closeSettingsModal();
  if (e.target.id === 'relationshipModal') closeRelationshipModal();
}

// ==================== RELATIONSHIP INSPECTION MODAL ====================
let currentInspectedFk = null;
let currentInspectedFkMeta = null;

function openRelationshipModal(fk, meta) {
  if (!fk) return;
  currentInspectedFk = fk;
  currentInspectedFkMeta = meta || {};

  // Highlight relationship on canvas
  document.querySelectorAll('.rel-group').forEach(g => g.classList.remove('active-rel'));
  if (meta && meta.relG) {
    meta.relG.classList.add('active-rel');
  } else {
    const foundG = document.querySelector(`.rel-group[data-parent="${fk.parent}"][data-child="${fk.child}"]`);
    if (foundG) foundG.classList.add('active-rel');
  }

  // Get table metadata
  const parentData = tablesData[fk.parent] || {};
  const childData = tablesData[fk.child] || {};
  const parentPks = parentData.pks || [];
  const childPks = childData.pks || [];

  const fkCols = (fk.cols || '').split(',').map(c => c.trim()).filter(Boolean);
  const parentCols = (fk.parent_cols || (parentPks.length > 0 ? parentPks.join(', ') : 'ID'))
    .split(',').map(c => c.trim()).filter(Boolean);

  // Column types & nullability
  const parentColName = parentCols[0] || 'ID';
  const childColName = fkCols[0] || 'FK_ID';

  let parentColType = 'NUMBER';
  let childColType = 'NUMBER';
  let childColNullable = false;

  (parentData.columns || []).forEach(c => {
    if (c.name && c.name.toLowerCase() === parentColName.toLowerCase()) {
      parentColType = c.type || 'NUMBER';
    }
  });

  (childData.columns || []).forEach(c => {
    if (c.name && c.name.toLowerCase() === childColName.toLowerCase()) {
      childColType = c.type || 'NUMBER';
      if (c.nullable !== false) childColNullable = true;
    }
  });

  const isSelfRef = fk.parent === fk.child;
  const isIdentifying = fkCols.length > 0 && fkCols.some(c => childPks.includes(c));
  const isOneToOne = fkCols.length > 0 && fkCols.length === childPks.length &&
    childPks.length > 0 && fkCols.every(c => childPks.includes(c));

  const cardinalityStr = isSelfRef
    ? (currentLang === 'ar' ? 'علاقة ذاتية (Self)' : 'Self-Referencing')
    : isOneToOne
      ? '1 : 1'
      : '1 : N';

  const cardinalityDesc = isSelfRef
    ? (currentLang === 'ar' ? 'علاقة ذاتية في نفس الجدول' : 'Self-referencing relationship')
    : isOneToOne
      ? (currentLang === 'ar' ? 'واحد إلى واحد (One-to-One)' : 'One-to-One')
      : (currentLang === 'ar' ? 'واحد إلى متعدد (One-to-Many)' : 'One-to-Many');

  const natureStr = isIdentifying
    ? (currentLang === 'ar' ? 'تعريفية (Identifying - جزء من المفتاح الأساسي)' : 'Identifying (Part of Primary Key)')
    : (currentLang === 'ar' ? 'غير تعريفية (Non-Identifying)' : 'Non-Identifying');

  const nullStr = childColNullable
    ? (currentLang === 'ar' ? 'اختيارية (NULL مسموح)' : 'Optional (Nullable)')
    : (currentLang === 'ar' ? 'إلزامية (NOT NULL)' : 'Required (NOT NULL)');

  // Fill Header
  const fkNameEl = document.getElementById('relModalFkName');
  if (fkNameEl) fkNameEl.textContent = fk.fk || `FK_${fk.child}_${fk.parent}`;
  const headerBadge = document.getElementById('relHeaderTypeBadge');
  if (headerBadge) headerBadge.textContent = cardinalityStr;

  // Fill Flow Card
  const elPTable = document.getElementById('relFlowParentTable');
  if (elPTable) elPTable.textContent = fk.parent;
  const elPCol = document.getElementById('relFlowParentCol');
  if (elPCol) elPCol.textContent = parentCols.join(', ');
  const elPType = document.getElementById('relFlowParentType');
  if (elPType) elPType.textContent = parentColType;

  const elCTable = document.getElementById('relFlowChildTable');
  if (elCTable) elCTable.textContent = fk.child;
  const elCCol = document.getElementById('relFlowChildCol');
  if (elCCol) elCCol.textContent = fkCols.join(', ');
  const elCType = document.getElementById('relFlowChildType');
  if (elCType) elCType.textContent = childColType;

  const elCardBadge = document.getElementById('relFlowCardBadge');
  if (elCardBadge) elCardBadge.textContent = cardinalityStr;
  const elNatureTag = document.getElementById('relFlowNatureTag');
  if (elNatureTag) elNatureTag.textContent = isIdentifying
    ? (currentLang === 'ar' ? 'علاقة تعريفية' : 'Identifying')
    : (currentLang === 'ar' ? 'علاقة غير تعريفية' : 'Non-Identifying');

  const flowConn = document.getElementById('relFlowConnector');
  if (flowConn) {
    if (isIdentifying) flowConn.classList.remove('is-non-identifying');
    else flowConn.classList.add('is-non-identifying');
  }

  // Fill Properties Grid
  const elPropFk = document.getElementById('relPropFkName');
  if (elPropFk) elPropFk.textContent = fk.fk;
  const elPropCard = document.getElementById('relPropCardinality');
  if (elPropCard) elPropCard.textContent = cardinalityDesc;
  const elPropIdent = document.getElementById('relPropIdentifying');
  if (elPropIdent) elPropIdent.textContent = natureStr;
  const elPropNull = document.getElementById('relPropNull');
  if (elPropNull) elPropNull.textContent = nullStr;

  // Generate SQL DDL
  const childColsFormatted = fkCols.map(c => `"${c}"`).join(', ');
  const parentColsFormatted = parentCols.map(c => `"${c}"`).join(', ');
  const sqlDdl = `ALTER TABLE "${fk.child}"
  ADD CONSTRAINT "${fk.fk}"
  FOREIGN KEY (${childColsFormatted})
  REFERENCES "${fk.parent}" (${parentColsFormatted});`;

  const elSql = document.getElementById('relSqlCodeBox');
  if (elSql) {
    elSql.textContent = sqlDdl;
  }

  // Open modal
  const modal = document.getElementById('relationshipModal');
  if (modal) modal.classList.add('open');
}

function closeRelationshipModal() {
  const modal = document.getElementById('relationshipModal');
  if (modal) modal.classList.remove('open');
  document.querySelectorAll('.rel-group').forEach(g => g.classList.remove('active-rel'));
}

function copyRelationshipFkName() {
  if (!currentInspectedFk) return;
  const name = currentInspectedFk.fk;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(name).then(() => {
      showToast(currentLang === 'ar' ? `تم نسخ اسم العلاقة: ${name}` : `Copied FK Name: ${name}`);
    }).catch(() => {});
  } else {
    showToast(name);
  }
}

function copyRelationshipSql() {
  const elSql = document.getElementById('relSqlCodeBox');
  if (!elSql) return;
  const sql = elSql.textContent;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(sql).then(() => {
      const btn = document.getElementById('relCopySqlBtn');
      const origText = btn ? btn.innerHTML : '';
      if (btn) {
        btn.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> <span>${currentLang === 'ar' ? 'تم النسخ!' : 'Copied!'}</span>`;
        setTimeout(() => { btn.innerHTML = origText; }, 1600);
      }
      showToast(currentLang === 'ar' ? 'تم نسخ جملة SQL بنجاح' : 'SQL DDL copied to clipboard');
    }).catch(() => {});
  } else {
    showToast(currentLang === 'ar' ? 'تم نسخ جملة SQL' : 'Copied SQL');
  }
}

function focusRelationshipTables() {
  if (!currentInspectedFk) return;
  const fk = currentInspectedFk;
  closeRelationshipModal();

  selectedTableNodes.clear();
  selectedTableNodes.add(fk.parent);
  selectedTableNodes.add(fk.child);
  updateSelectionUI();
  if (typeof updateStatusBar === 'function') updateStatusBar();

  // Focus and zoom to both tables
  focusTables([fk.parent, fk.child]);
}

function askAiAboutRelationship() {
  if (!currentInspectedFk) return;
  const fk = currentInspectedFk;
  closeRelationshipModal();
  if (!aiOpen) toggleAIPanel();
  const inp = document.getElementById('aiInput');
  if (inp) {
    const prompt = currentLang === 'ar'
      ? `اشرح لي دور العلاقة "${fk.fk}" بين جدول "${fk.child}" وجدول "${fk.parent}" (الحقول: ${fk.cols})، وما هي قواعد تكامل البيانات المفروضة؟`
      : `Explain the relationship "${fk.fk}" between table "${fk.child}" and "${fk.parent}" (columns: ${fk.cols}), and what data integrity rules apply.`;
    inp.value = prompt;
    inp.dispatchEvent(new Event('input'));
    setTimeout(sendChatMessage, 120);
  }
}

window.openRelationshipModal = openRelationshipModal;
window.closeRelationshipModal = closeRelationshipModal;
window.copyRelationshipFkName = copyRelationshipFkName;
window.copyRelationshipSql = copyRelationshipSql;
window.focusRelationshipTables = focusRelationshipTables;
window.askAiAboutRelationship = askAiAboutRelationship;

function renderModalColumnsList(tableParam) {
  const tableName = tableParam || Array.from(selectedTableNodes)[0];
  if (!tableName) return;
  const data = tablesData[tableName];
  const list = document.getElementById('modalColumnsList');
  list.innerHTML = '';

  const query = document.getElementById('modalSearchInput').value.toLowerCase().trim();

  if (!tableCustomHiddenCols[tableName]) {
    const defaultVisible = getVisibleColumns(tableName).map(c => c.name);
    const initialHidden = new Set(data.columns.map(c => c.name).filter(name => !defaultVisible.includes(name)));
    tableCustomHiddenCols[tableName] = initialHidden;
  }

  const currentHidden = tableCustomHiddenCols[tableName];

  data.columns.forEach(col => {
    if (query && !col.name.toLowerCase().includes(query) && !col.type.toLowerCase().includes(query)) return;

    const isPK = data.pks.includes(col.name);
    const isFK = fkList.some(f => f.child === tableName && f.cols.includes(col.name));
    const isAudit = isAuditColumn(col.name);
    const isVisible = !currentHidden.has(col.name);

    const row = document.createElement('div');
    row.className = `col-row ${isVisible ? '' : 'is-hidden'} ${isAudit ? 'is-audit' : ''}`;

    let badgeHtml = '';
    if (isPK && isFK) badgeHtml += '<span class="col-badge badge-pkfk">PK, FK</span>';
    else if (isPK) badgeHtml += '<span class="col-badge badge-pk">PK</span>';
    else if (isFK) badgeHtml += '<span class="col-badge badge-fk">FK</span>';

    if (isAudit) badgeHtml += '<span class="col-badge badge-audit" title="Audit Column">AUDIT</span>';

    row.innerHTML = `
      <input type="checkbox" ${isVisible ? 'checked' : ''} />
      <span class="col-name">${col.name}</span>
      <span class="col-type">${col.type}</span>
      ${badgeHtml}
    `;

    row.addEventListener('click', (e) => {
      if (e.target.tagName !== 'INPUT') {
        const cb = row.querySelector('input');
        cb.checked = !cb.checked;
      }
      const isChecked = row.querySelector('input').checked;
      if (isChecked) currentHidden.delete(col.name);
      else currentHidden.add(col.name);

      row.classList.toggle('is-hidden', !isChecked);

      tablePositions[tableName].height = getTableHeight(tableName);
      renderAll();
      scheduleAutoSave();

      const visCount = getVisibleColumns(tableName).length;
      const t = i18n[currentLang];
      document.getElementById('modalTableSubtitle').textContent = `${visCount} / ${data.columns.length} ${t.modalColCount}`;
      document.getElementById('modalColCount').textContent = `${visCount} ${t.modalColCount}`;
    });

    list.appendChild(row);
  });

  const visCount = getVisibleColumns(tableName).length;
  const t = i18n[currentLang];
  document.getElementById('modalColCount').textContent = `${visCount} ${t.modalColCount}`;
}

function filterModalColumns() {
  renderModalColumnsList();
}

function setModalColumnsVisibility(showAll) {
  const t = Array.from(selectedTableNodes)[0];
  if (!t) return;
  const data = tablesData[t];

  if (showAll) {
    tableCustomHiddenCols[t] = new Set();
  } else {
    const pks = new Set(data.pks);
    tableCustomHiddenCols[t] = new Set(data.columns.map(c => c.name).filter(name => !pks.has(name)));
  }

  tablePositions[t].height = getTableHeight(t);
  renderAll();
  scheduleAutoSave();
  renderModalColumnsList(t);
}

function setModalColumnsNoAudit() {
  const t = Array.from(selectedTableNodes)[0];
  if (!t) return;
  const data = tablesData[t];
  const pks = new Set(data.pks);

  const hidden = new Set();
  data.columns.forEach(c => {
    if (!pks.has(c.name) && isAuditColumn(c.name)) {
      hidden.add(c.name);
    }
  });

  tableCustomHiddenCols[t] = hidden;
  tablePositions[t].height = getTableHeight(t);
  renderAll();
  scheduleAutoSave();
  renderModalColumnsList(t);
}

function setModalColumnsKeysOnly() {
  const t = Array.from(selectedTableNodes)[0];
  if (!t) return;
  const data = tablesData[t];

  const pks = data.pks;
  const childFkCols = fkList.filter(f => f.child === t).map(f => f.cols.split(',').map(s=>s.trim())).flat();
  const parentFkCols = fkList.filter(f => f.parent === t).map(f => f.cols.split(',').map(s=>s.trim())).flat();
  const keySet = new Set([...pks, ...childFkCols, ...parentFkCols]);

  tableCustomHiddenCols[t] = new Set(data.columns.map(c => c.name).filter(name => !keySet.has(name)));

  tablePositions[t].height = getTableHeight(t);
  renderAll();
  scheduleAutoSave();
  renderModalColumnsList(t);
}

function showAllForSelected() {
  if (selectedTableNodes.size === 1) setModalColumnsVisibility(true);
}
function showNoAuditForSelected() {
  if (selectedTableNodes.size === 1) setModalColumnsNoAudit();
}
function showKeysOnlyForSelected() {
  if (selectedTableNodes.size === 1) setModalColumnsKeysOnly();
}
function hideSelectedTable() {
  if (selectedTableNodes.size === 1) {
    const t = Array.from(selectedTableNodes)[0];
    selectedTables.delete(t);
    selectedTableNodes.clear();
    buildSidebarList();
    renderAll();
    scheduleAutoSave();
  }
}

// Global View Mode
function setGlobalViewMode(mode) {
  setTimeout(updateControlIcons, 10);
  globalViewMode = mode;
  tableCustomHiddenCols = {};
  allTables.forEach(t => {
    if (tablePositions[t]) tablePositions[t].height = getTableHeight(t);
  });
  renderAll();
  scheduleAutoSave();
  const t = i18n[currentLang];
  const labels = { 'no-audit': t.viewNoAudit, 'keys-only': t.viewKeysOnly, 'all-columns': t.viewAllCols };
  showToast(labels[mode] || mode);
}

// Canvas Events
function setupCanvasEvents() {
  const wrap = document.getElementById('canvasWrap');

  wrap.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;

    const isCtrl = e.ctrlKey || e.metaKey || e.shiftKey;
    const isBackground = (e.target === wrap || e.target.id === 'mainSvg' || e.target.tagName === 'svg');

    if (isBackground) {
      if (isCtrl) {
        isMarqueeActive = true;
        const wrapRect = wrap.getBoundingClientRect();
        marqueeStartX = e.clientX - wrapRect.left;
        marqueeStartY = e.clientY - wrapRect.top;

        const mBox = document.getElementById('marqueeBox');
        mBox.style.left = `${marqueeStartX}px`;
        mBox.style.top = `${marqueeStartY}px`;
        mBox.style.width = '0px';
        mBox.style.height = '0px';
        mBox.style.display = 'block';

        wrap.classList.add('crosshair');
      } else {
        isPanning = true;
        startPanX = e.clientX - panX;
        startPanY = e.clientY - panY;
        wrap.classList.add('grabbing');
        deselectAll();
      }
    }
  });

  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);

  wrap.addEventListener('wheel', (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    const mouseX = e.clientX - wrap.getBoundingClientRect().left;
    const mouseY = e.clientY - wrap.getBoundingClientRect().top;

    panX = mouseX - (mouseX - panX) * zoomFactor;
    panY = mouseY - (mouseY - panY) * zoomFactor;
    zoom = Math.max(0.2, Math.min(2.5, zoom * zoomFactor));

    updateCanvasTransform();
    scheduleAutoSave();
  }, { passive: false });

  document.getElementById('searchInput').addEventListener('input', buildSidebarList);
}

// Shortcuts
function setupKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      toggleAIPanel();
      return;
    }
    if (e.key === 'Escape') {
      if (aiOpen) {
        toggleAIPanel();
        return;
      }
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
      const activeInput = document.activeElement;
      if (activeInput && (activeInput.tagName === 'INPUT' || activeInput.tagName === 'TEXTAREA')) return;
      e.preventDefault();
      selectedTableNodes = new Set(selectedTables);
      updateSelectionUI(); if (typeof updateStatusBar === 'function') updateStatusBar();
    }
    if (e.key === 'Escape') {
      deselectAll();
      closeColumnModal();
      closeSettingsModal();
      toggleNewPageModal(false);
      togglePasteSqlModal(false);
      closeRelationshipModal();
    }
    if ((e.key === 'b' || e.key === 'B') && !e.ctrlKey && !e.metaKey) {
      const activeInput = document.activeElement;
      if (!activeInput || (activeInput.tagName !== 'INPUT' && activeInput.tagName !== 'TEXTAREA')) {
        toggleSidebar();
      }
    }
  });
}

function updateCanvasTransform() {
  const layer = document.getElementById('canvasLayer');
  if (layer) {
    layer.setAttribute('transform', `translate(${panX}, ${panY}) scale(${zoom})`);
  if (typeof updateStatusBar === 'function') updateStatusBar();
  }
}

function zoomCanvas(factor) {
  zoom = Math.max(0.2, Math.min(2.5, zoom * factor));
  updateCanvasTransform();
  scheduleAutoSave();
}

function resetCanvasTransform() {
  panX = 60; panY = 60; zoom = 0.85;
  updateCanvasTransform();
  scheduleAutoSave();
}

function fitView() {
  const tables = Array.from(selectedTables);
  if (tables.length === 0) return;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  tables.forEach(t => {
    const p = tablePositions[t];
    if (p) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x + p.width);
      maxY = Math.max(maxY, p.y + p.height);
    }
  });
  const wrap = document.getElementById('canvasWrap');
  const w = wrap.clientWidth, h = wrap.clientHeight;
  const contentW = maxX - minX + 140;
  const contentH = maxY - minY + 140;
  zoom = Math.max(0.25, Math.min(1.2, Math.min(w / contentW, h / contentH)));
  panX = (w - contentW * zoom) / 2 - minX * zoom + 60 * zoom;
  panY = (h - contentH * zoom) / 2 - minY * zoom + 60 * zoom;
  updateCanvasTransform();
  scheduleAutoSave();
}

function focusTables(tableNames) {
  const targets = (tableNames || []).filter(t => tablePositions[t]);
  if (targets.length === 0) return;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  targets.forEach(t => {
    const p = tablePositions[t];
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x + p.width);
    maxY = Math.max(maxY, p.y + p.height);
  });
  const wrap = document.getElementById('canvasWrap');
  if (!wrap) return;
  const w = wrap.clientWidth, h = wrap.clientHeight;
  const pad = 120;
  const contentW = (maxX - minX) + pad * 2;
  const contentH = (maxY - minY) + pad * 2;
  zoom = Math.max(0.35, Math.min(1.3, Math.min(w / contentW, h / contentH)));
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  panX = (w / 2) - (cx * zoom);
  panY = (h / 2) - (cy * zoom);
  updateCanvasTransform();
  scheduleAutoSave();
}
window.focusTables = focusTables;

function applyPresetLayout(preset) {
  setTimeout(updateControlIcons, 10);
  calculateInitialLayout(preset);
  renderAll();
  scheduleAutoSave();
  setTimeout(fitView, 50);
}

function syncSpacingInput(type, val) {
  var num = document.getElementById('spacing' + type);
  if (num) num.value = val;
  var key = type.toLowerCase();
  layoutSpacing[key] = parseInt(val, 10) || layoutSpacing[key];
  try { localStorage.setItem('erd_layout_spacing', JSON.stringify(layoutSpacing)); } catch(e) {}
  
  // Live update: switch presetSelect to this preset so user sees live feedback immediately!
  var sel = document.getElementById('presetSelect');
  if (sel) {
    if (sel.value !== key) {
      sel.value = key;
      updateControlIcons();
      if (typeof updateStatusBar === 'function') updateStatusBar();
    }
    calculateInitialLayout(key);
    renderAll();
    scheduleAutoSave();
  }
}

function syncSpacingRange(type, val) {
  var rng = document.getElementById('spacing' + type + 'Range');
  if (rng) rng.value = val;
  syncSpacingInput(type, val);
}

window.syncSpacingInput = syncSpacingInput;
window.syncSpacingRange = syncSpacingRange;

function toggleThemeSwitch() {
  const newTheme = (currentTheme === 'light') ? 'dark' : 'light';
  setTheme(newTheme);
}

function updateThemeSwitchUI() {
  const btn = document.getElementById('themeToggleBtn');
  const label = document.getElementById('themeSwitchLabel');
  if (!btn) return;
  const isLight = (currentTheme === 'light');
  if (label) {
    label.textContent = currentLang === 'ar' ? (isLight ? 'فاتح' : 'داكن') : (isLight ? 'Light' : 'Dark');
  }
  btn.setAttribute('title', currentLang === 'ar'
    ? (isLight ? 'التبديل إلى الوضع الداكن' : 'التبديل إلى الوضع الفاتح')
    : (isLight ? 'Switch to Dark Mode' : 'Switch to Light Mode'));
}

function setTheme(theme, save = true) {
  currentTheme = (theme === 'light') ? 'light' : 'dark';
  document.documentElement.classList.remove('theme-dark', 'theme-academic', 'theme-light', 'theme-mermaid');
  document.documentElement.classList.add('theme-' + currentTheme);
  document.body.classList.remove('theme-dark', 'theme-academic', 'theme-light', 'theme-mermaid');
  document.body.classList.add('theme-' + currentTheme);
  try { localStorage.setItem('erd_theme', currentTheme); } catch(e) {}
  
  const sel = document.getElementById('themeSelect');
  if (sel && sel.value !== currentTheme) sel.value = currentTheme;
  const settingsSel = document.getElementById('settingsTheme');
  if (settingsSel && settingsSel.value !== currentTheme) settingsSel.value = currentTheme;

  updateThemeSwitchUI();
  updateControlIcons();
  if (save) scheduleAutoSave();
}

function selectGroup(groupKey, val) {
  const tList = (allTables && allTables.length) ? allTables : Object.keys(tablesData || {});
  tList.forEach(t => {
    let matches = false;
    if (!groupKey || groupKey === 'all') {
      matches = true;
    } else if (subsystemData && subsystemMapping && tableSubsystem(t) === groupKey) {
      matches = true;
    } else if (t.toUpperCase().startsWith(groupKey.toUpperCase())) {
      matches = true;
    }
    if (matches) {
      if (val) selectedTables.add(t);
      else {
        selectedTables.delete(t);
        selectedTableNodes.delete(t);
      }
    }
  });
  buildSidebarList();
  renderAll();
  scheduleAutoSave();
  renderFilterChips();
  updateSubsysFilterOptions();
}

function resetToInitial() {
  localStorage.removeItem('testr_erd_studio_bundle');
  tableCustomHiddenCols = {};
  globalViewMode = 'no-audit';
  document.getElementById('globalViewModeSelect').value = 'no-audit';
  calculateInitialLayout('hierarchical');
  renderAll();
  fitView();
  scheduleAutoSave();
 showToast(currentLang === 'ar' ? ' تم الضبط الافتراضي' : ' Reset Default');
}

// ==================== SETTINGS MODAL ====================
function openSettingsModal() {
  document.getElementById('settingsModal').classList.add('open');
  populateSettingsForm();
  refreshSettingsI18n();
}

function closeSettingsModal() {
  document.getElementById('settingsModal').classList.remove('open');
}

function openSettingsTab(tabId) {
  document.querySelectorAll('.settings-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.settings-pane').forEach(p => p.style.display = 'none');
  document.querySelector(`.settings-tab[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).style.display = 'flex';
}

function populateSettingsForm() {
  document.getElementById('dbDialect').value = dbCfg.dialect;
  document.getElementById('dbHost').value = dbCfg.host;
  document.getElementById('dbPort').value = dbCfg.port;
  document.getElementById('dbService').value = dbCfg.service;
  document.getElementById('dbUser').value = dbCfg.user;
  document.getElementById('dbPassword').value = dbCfg.password;
  document.getElementById('dbFilePath').value = dbCfg.file;
  toggleDbFields();
  document.getElementById('settingsViewMode').value = globalViewMode;
  document.getElementById('settingsTheme').value = currentTheme;
  document.getElementById('settingsLang').value = currentLang;
  document.getElementById('settingsAutoSave').checked = autoSaveEnabled;
  document.getElementById('settingsTableWidth').value = TABLE_WIDTH;
  document.getElementById('settingsZoomPct').value = Math.round(zoom * 100);

  const setVal = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.value = v;
    const rng = document.getElementById(id + 'Range');
    if (rng) rng.value = v;
  };
  setVal('spacingCircular', layoutSpacing.circular || 550);
  setVal('spacingForce', layoutSpacing.force || 220);
  setVal('spacingHierarchical', layoutSpacing.hierarchical || 320);
  setVal('spacingGrid', layoutSpacing.grid || 310);
  setVal('spacingCluster', layoutSpacing.cluster || 310);
  setVal('spacingStar', layoutSpacing.star || 380);
  const curProv = (aiConfig && aiConfig.provider) || 'local';
  document.getElementById('aiProvider').value = (curProv === 'opencode' || curProv === 'openai') ? curProv : 'local';
  document.getElementById('aiBaseUrl').value = (aiConfig && aiConfig.base_url) || (curProv === 'opencode' ? 'https://opencode.ai/zen/v1' : 'https://api.openai.com/v1');
  document.getElementById('aiApiKey').value = (aiConfig && aiConfig.api_key) || '';
  document.getElementById('aiModel').value = (aiConfig && aiConfig.model) || (curProv === 'opencode' ? 'big-pickle' : 'gpt-4o-mini');
  document.getElementById('aiTemperature').value = (aiConfig && aiConfig.temperature) || '0.4';
  toggleAiKeyFields();
  const resultEl = document.getElementById('dbTestResult');
  resultEl.className = 'db-test-result';
  resultEl.textContent = '';
  const aiRes = document.getElementById('aiTestResult');
  if (aiRes) { aiRes.className = 'db-test-result'; aiRes.textContent = ''; }
}

function toggleAiKeyFields() {
  const provider = document.getElementById('aiProvider').value;
  const baseUrlEl = document.getElementById('aiBaseUrl');
  const apiKeyEl = document.getElementById('aiApiKey');
  const modelEl = document.getElementById('aiModel');
  const tempEl = document.getElementById('aiTemperature');
  const hintEl = document.getElementById('i18n-aiHint');

  if (provider === 'local') {
    if (baseUrlEl) baseUrlEl.disabled = true;
    if (apiKeyEl) {
      apiKeyEl.disabled = true;
      apiKeyEl.placeholder = 'sk-...';
    }
    if (modelEl) modelEl.disabled = true;
    if (tempEl) tempEl.disabled = true;
    if (hintEl) {
      hintEl.textContent = currentLang === 'ar'
        ? 'المساعد الذكي المحلي يعمل دون اتصال بالإنترنت ودون الحاجة لأي مفاتيح أو استهلاك حصص.'
        : 'Local smart assistant works completely offline without API keys or quota consumption.';
    }
  } else if (provider === 'opencode') {
    if (baseUrlEl) {
      baseUrlEl.disabled = false;
      if (!baseUrlEl.value || baseUrlEl.value.includes('api.openai.com')) baseUrlEl.value = 'https://opencode.ai/zen/v1';
    }
    if (apiKeyEl) {
      apiKeyEl.disabled = true;
      apiKeyEl.placeholder = currentLang === 'ar' ? 'غير مطلوب لبوابة OpenCode Zen المجانية' : 'Not required for OpenCode Zen (Free)';
    }
    if (modelEl) {
      modelEl.disabled = false;
      if (!modelEl.value || modelEl.value === 'gpt-4o-mini') modelEl.value = 'big-pickle';
    }
    if (tempEl) tempEl.disabled = false;
    if (hintEl) {
      hintEl.textContent = currentLang === 'ar'
        ? 'بوابة OpenCode Zen توفر نماذج ذكاء سحابية مجانية (big-pickle وغيرها) بدون مفتاح API عبر حصة IP يومية.'
        : 'OpenCode Zen provides free cloud models (big-pickle, etc.) without an API key using daily IP quota.';
    }
  } else {
    // openai-compatible
    if (baseUrlEl) {
      baseUrlEl.disabled = false;
      if (!baseUrlEl.value || baseUrlEl.value.includes('opencode.ai')) baseUrlEl.value = 'https://api.openai.com/v1';
    }
    if (apiKeyEl) {
      apiKeyEl.disabled = false;
      apiKeyEl.placeholder = 'sk-...';
    }
    if (modelEl) {
      modelEl.disabled = false;
      if (!modelEl.value || modelEl.value === 'big-pickle') modelEl.value = 'gpt-4o-mini';
    }
    if (tempEl) tempEl.disabled = false;
    if (hintEl) {
      hintEl.textContent = currentLang === 'ar'
        ? 'أدخل مفتاح API الخاص بك للتواصل مع OpenAI أو أي خادم متوافق (مثل Ollama أو LM Studio أو vLLM).'
        : 'Enter your API key to connect to OpenAI or any compatible endpoint (Ollama, LM Studio, vLLM).';
    }
  }
}

async function testAIConnection() {
  const el = document.getElementById('aiTestResult');
  el.classList.add('loading');
  el.classList.remove('ok', 'fail');
 el.textContent = currentLang === 'ar' ? ' جاري فحص المزود...' : ' Testing provider...';
  const payload = {
    ai_provider: document.getElementById('aiProvider').value,
    ai_base_url: document.getElementById('aiBaseUrl').value.trim(),
    ai_api_key: document.getElementById('aiApiKey').value.trim(),
    ai_model: document.getElementById('aiModel').value.trim()
  };
  try {
    const res = await fetch('/api/ai/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    el.classList.remove('loading');
    if (data.success) {
      el.classList.add('ok');
      const mode = data.mode === 'remote' ? (currentLang === 'ar' ? 'سحابي' : 'Remote') : (currentLang === 'ar' ? 'محلي' : 'Local');
 el.textContent = ` ${mode}: ${data.message || 'OK'}`;
    } else {
      el.classList.add('fail');
 el.textContent = (currentLang === 'ar' ? ' فشل الفحص:\n' : ' Test failed:\n') + (data.error || data.message || 'Unknown error');
    }
  } catch (err) {
    el.classList.remove('loading');
    el.classList.add('fail');
 el.textContent = (currentLang === 'ar' ? ' خطأ:\n' : ' Error:\n') + err.message;
  }
}

async function saveAiSettings() {
  const prov = document.getElementById('aiProvider').value;
  const payload = {
    ai_provider: prov,
    ai_base_url: document.getElementById('aiBaseUrl').value.trim(),
    ai_api_key: document.getElementById('aiApiKey').value.trim(),
    ai_model: document.getElementById('aiModel').value.trim(),
    ai_temperature: document.getElementById('aiTemperature').value
  };
  try {
    const res = await fetch('/api/ai/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.config) aiConfig = data.config;
    updateAIBadge();
 showToast(currentLang === 'ar' ? ' تم حفظ إعدادات الذكاء الاصطناعي' : ' AI settings saved');
  } catch (err) {
 showToast(' ' + err.message);
  }
}

function toggleDbFields() {
  const d = (document.getElementById('dbDialect') || {}).value || dbCfg.dialect;
  const server = d === 'sqlite_file' ? 'none' : 'block';
  document.getElementById('dbFieldsServer').style.display = server;
  document.getElementById('dbFieldsFile').style.display = d === 'sqlite_file' ? 'flex' : 'none';
  if (d === 'mysql' && document.getElementById('dbPort').value === '1521') document.getElementById('dbPort').value = '3306';
  if (d === 'postgres' && (document.getElementById('dbPort').value === '1521' || document.getElementById('dbPort').value === '1433' || document.getElementById('dbPort').value === '3306')) document.getElementById('dbPort').value = '5432';
  if (d === 'mssql' && (document.getElementById('dbPort').value === '1521' || document.getElementById('dbPort').value === '3306' || document.getElementById('dbPort').value === '5432')) document.getElementById('dbPort').value = '1433';
  if (d === 'oracle' && (document.getElementById('dbPort').value === '3306' || document.getElementById('dbPort').value === '5432' || document.getElementById('dbPort').value === '1433')) document.getElementById('dbPort').value = '1521';
}

async function refreshCurrentSchemaInfo() {
  const el = document.getElementById('dbCurrentInfo');
  if (!el) return;
  try {
    const res = await fetch('/api/connectors');
    const data = await res.json();
    const cur = data.current || {};
    const label = { oracle: 'Oracle', mysql: 'MySQL', postgres: 'PostgreSQL', mssql: 'SQL Server', sqlite_file: 'SQLite' }[cur.dialect] || cur.dialect;
    const src = cur.source === 'sql' ? 'SQL Import' : label;
    const s = await (await fetch('/api/schema')).json();
 const name = s.schemaName ? `\n ${s.schemaName}` : '';
 el.textContent = `${src}${name}\n ${s.tableCount} tables • ${s.fkCount} FKs • ${(s.lastSync || '').slice(0, 19)}`;
  } catch (e) {
    el.textContent = currentLang === 'ar' ? '—' : '—';
  }
}

function dbParamsFromForm() {
  const d = (document.getElementById('dbDialect') || {}).value || dbCfg.dialect;
  const params = { user: document.getElementById('dbUser').value.trim() };
  const pw = document.getElementById('dbPassword').value;
  if (pw) params.password = pw;
  if (d === 'sqlite_file') {
    params.path = document.getElementById('dbFilePath').value.trim();
  } else {
    params.host = document.getElementById('dbHost').value.trim();
    params.port = parseInt(document.getElementById('dbPort').value, 10);
    if (d === 'oracle') {
      params.service_name = document.getElementById('dbService').value.trim();
    } else {
      params.database = document.getElementById('dbService').value.trim();
    }
  }
  return params;
}

async function testDbConnection() {
  const resultEl = document.getElementById('dbTestResult');
  resultEl.classList.add('loading');
  resultEl.classList.remove('ok', 'fail');
 resultEl.textContent = currentLang === 'ar' ? ' جاري اختبار الاتصال...' : ' Testing connection...';

  const d = (document.getElementById('dbDialect') || {}).value || dbCfg.dialect;
  const payload = { dialect: d, params: dbParamsFromForm() };

  try {
    const res = await fetch('/api/connectors/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    resultEl.classList.remove('loading');
    if (data.success) {
      isDbConnected = true;
      dbConnectionError = '';
      if (typeof updateStatusBar === 'function') updateStatusBar();
      resultEl.classList.add('ok');
 let msg = currentLang === 'ar' ? ' الاتصال ناجح!' : ' Connection successful!';
      if (data.detail) msg += `\n${data.detail}`;
      if (data.tablesFound) msg += `\n${currentLang === 'ar' ? 'الجدول المكتشفة' : 'Tables found'}: ${data.tablesFound}`;
      if (data.latencyMs) msg += `\n${currentLang === 'ar' ? 'الاستجابة' : 'Latency'}: ${data.latencyMs} ms`;
      resultEl.textContent = msg;
    } else {
      isDbConnected = false;
      dbConnectionError = data.error || 'Unknown error';
      if (typeof updateStatusBar === 'function') updateStatusBar();
      resultEl.classList.add('fail');
 resultEl.textContent = (currentLang === 'ar' ? ' فشل الاتصال:\n' : ' Connection failed:\n') + (data.error || 'Unknown error');
    }
  } catch (err) {
    isDbConnected = false;
    dbConnectionError = err.message || 'Error';
    if (typeof updateStatusBar === 'function') updateStatusBar();
    resultEl.classList.remove('loading');
    resultEl.classList.add('fail');
 resultEl.textContent = (currentLang === 'ar' ? ' خطأ:\n' : ' Error:\n') + err.message;
  }
}

async function connectDatabase() {
  const d = (document.getElementById('dbDialect') || {}).value || dbCfg.dialect;
 showToast(currentLang === 'ar' ? ' جاري تحميل المخطط...' : ' Loading schema...');
  try {
    const payload = { dialect: d, params: dbParamsFromForm() };
    const res = await fetch('/api/connectors/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!data.success) {
      isDbConnected = false;
      dbConnectionError = data.error || data.detail || 'Connect failed';
      if (typeof updateStatusBar === 'function') updateStatusBar();
      throw new Error(dbConnectionError);
    }
    isDbConnected = true;
    dbConnectionError = '';
    applySchemaPayload(data);
    dbCfg.dialect = d;
    if (d === 'sqlite_file') {
      dbCfg.file = document.getElementById('dbFilePath').value.trim();
    } else {
      dbCfg.host = document.getElementById('dbHost').value.trim();
      dbCfg.port = parseInt(document.getElementById('dbPort').value, 10);
      dbCfg.service = document.getElementById('dbService').value.trim();
      dbCfg.user = document.getElementById('dbUser').value.trim();
    }
    if (typeof updateStatusBar === 'function') updateStatusBar();
    const info = document.getElementById('dbCurrentInfo');
    if (info) info.textContent = '';
 showToast(currentLang === 'ar' ? ` تم تحميل ${data.schema.tableCount} جدول` : ` Loaded ${data.schema.tableCount} tables`);
    refreshCurrentSchemaInfo();
  } catch (err) {
 showToast(' ' + err.message);
  }
}

async function importSqlFile(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
 showToast(currentLang === 'ar' ? ' جاري تحليل ملف SQL...' : ' Parsing SQL file...');
  try {
    const res = await fetch('/api/schema/import/sql', { method: 'POST', body: fd });
    const data = await res.json();
    if (!data.success) throw new Error(data.detail || data.error || 'Import failed');
    applySchemaPayload(data);
 showToast(currentLang === 'ar' ? ` تم استيراد ${data.schema.tableCount} جدول (${data.schema.dialect})` : ` Imported ${data.schema.tableCount} tables (${data.schema.dialect})`);
    refreshCurrentSchemaInfo();
  } catch (err) {
 showToast(' ' + err.message);
  } finally {
    input.value = '';
  }
}

function applySchemaPayload(data) {
  const s = data.schema || {};
  if (s.tablesData) {
    tablesData = s.tablesData;
    fkList = s.fkList || [];
    allTables = Object.keys(tablesData);
    comTables = allTables.filter(t => t.startsWith('COM_'));
    rafTables = allTables.filter(t => t.startsWith('RAF_'));
    selectedTables = new Set(allTables);
    selectedTableNodes.clear();
    tablePositions = {};
    tableCustomHiddenCols = {};
    calculateInitialLayout('hierarchical');
    dbUpdateSubsystems(data.subsystems);
    buildSidebarList();
    renderAll();
    const filter = document.getElementById('subsysSelect');
    if (filter) { updateSubsysFilterOptions(); }
  }
}

function dbUpdateSubsystems(subsData) {
  subsystemData = subsData || null;
  subsystemMapping = (subsData && subsData.mapping) || {};
  renderLegend();
}

function currentDiagramSchema() {
  const tables = {};
  selectedTables.forEach(name => {
    if (tablesData[name]) tables[name] = tablesData[name];
  });
  const relations = fkList.filter(fk => tables[fk.child] && tables[fk.parent]);
  return { tablesData: tables, fkList: relations };
}

function requestCurrentSchemaExport(dialect, drop) {
  const schema = currentDiagramSchema();
  return fetch('/api/schema/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...schema, dialect: dialect, include_drop: drop })
  });
}

function downloadQuickBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(() => { a.remove(); URL.revokeObjectURL(url); }, 1500);
}

async function downloadDictionary(schema) {
  if (!Object.keys(schema.tablesData || {}).length) throw new Error('لا توجد جداول / No tables');
  const res = await fetch('/api/dictionary/from-schema', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(schema)
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Dictionary export failed');
  }
  downloadQuickBlob(await res.blob(), 'data_dictionary.xlsx');
 showToast(' Data Dictionary • ' + res.headers.get('X-Tables') + ' tables');
}

async function dictionaryFromCode(sql) {
  try {
 showToast(' Data Dictionary...');
    const res = await fetch('/api/schema/parse', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({sql})
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'SQL parse failed');
    await downloadDictionary(data.schema);
 } catch (err) { showToast(' ' + err.message); }
}

async function runQuickAction(action) {
  try {
    switch (action) {
      case 'audit_linter': switchView('audit'); switchAuditTab('linter'); await runSchemaLint(); break;
      case 'audit_diff': switchView('audit'); switchAuditTab('diff'); break;
      case 'audit_mock': switchView('audit'); switchAuditTab('mock'); break;
      case 'report_html': await exportInteractiveHtmlReport(); break;
      case 'report_pdf': await exportExecutivePdfReport(); break;
      case 'dictionary': await downloadDictionary(currentDiagramSchema()); break;
      case 'preview': switchView('export'); await previewExport(); break;
      case 'sql': await exportSchema(); break;
      case 'copy': {
        const res = await requestCurrentSchemaExport(document.getElementById('dbExportDialect').value, document.getElementById('dbExportDrop').checked);
        const data = await res.json();
        if (!res.ok || !data.success) throw new Error(data.detail || 'Export failed');
        await navigator.clipboard.writeText(data.script);
 showToast(' SQL copied'); break;
      }
      case 'svg': exportSVG(); break;
      case 'png': exportPNG(); break;
      case 'state': exportStateJson(); break;
      case 'save': await saveStateToSQLite(); break;
      case 'fit': switchView('canvas'); fitView(); break;
    }
 } catch (err) { showToast(' ' + err.message); }
}

async function exportInteractiveHtmlReport() {
  const isRTL = currentLang === 'ar';
  try {
    showToast(isRTL ? '⏳ جاري إنشاء تقرير HTML التفاعلي...' : '⏳ Generating interactive HTML report...');
    const schema = currentDiagramSchema();
    const payload = {
      tablesData: Object.keys(schema.tablesData).length ? schema.tablesData : tablesData,
      fkList: schema.fkList.length ? schema.fkList : fkList,
      positions: tablePositions,
      subsystems: subsystemData,
      theme: currentTheme || 'dark',
      lang: currentLang || 'ar'
    };
    const res = await fetch('/api/export/report/html', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'HTML export failed');
    }
    const blob = await res.blob();
    const wsName = (workspaces && workspaces.length ? (workspaces.find(w => w.id === activeWorkspaceId)?.name || 'schema') : 'schema');
    const safeName = wsName.replace(/[^\w\u0600-\u06FF\-]/g, '_');
    downloadQuickBlob(blob, `${safeName}_Interactive_Report.html`);
    showToast(isRTL ? '✅ تم تنزيل تقرير HTML التفاعلي المستقل بنجاح' : '✅ Offline HTML report downloaded successfully');
  } catch (err) {
    showToast('❌ ' + err.message);
  }
}

async function previewInteractiveHtmlReport() {
  const isRTL = currentLang === 'ar';
  try {
    showToast(isRTL ? '⏳ جاري تجهيز المعاينة التفاعلية...' : '⏳ Preparing interactive preview...');
    const schema = currentDiagramSchema();
    const payload = {
      tablesData: Object.keys(schema.tablesData).length ? schema.tablesData : tablesData,
      fkList: schema.fkList.length ? schema.fkList : fkList,
      positions: tablePositions,
      subsystems: subsystemData,
      theme: currentTheme || 'dark',
      lang: currentLang || 'ar'
    };
    const res = await fetch('/api/export/report/html', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'HTML preview failed');
    }
    const html = await res.text();
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  } catch (err) {
    showToast('❌ ' + err.message);
  }
}

async function exportExecutivePdfReport() {
  const isRTL = currentLang === 'ar';
  try {
    showToast(isRTL ? '⏳ جاري توليد وثيقة PDF المعمارية...' : '⏳ Generating executive PDF report...');
    const schema = currentDiagramSchema();
    const dialect = document.getElementById('dbExportDialect')?.value || 'oracle';
    const payload = {
      tablesData: Object.keys(schema.tablesData).length ? schema.tablesData : tablesData,
      fkList: schema.fkList.length ? schema.fkList : fkList,
      subsystems: subsystemData,
      dialect: dialect,
      lang: currentLang || 'ar'
    };
    const res = await fetch('/api/export/report/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'PDF export failed');
    }
    const blob = await res.blob();
    const wsName = (workspaces && workspaces.length ? (workspaces.find(w => w.id === activeWorkspaceId)?.name || 'schema') : 'schema');
    const safeName = wsName.replace(/[^\w\u0600-\u06FF\-]/g, '_');
    downloadQuickBlob(blob, `${safeName}_Executive_Dictionary.pdf`);
    showToast(isRTL ? '✅ تم تنزيل وثيقة PDF المعمارية بنجاح' : '✅ Executive PDF report downloaded successfully');
  } catch (err) {
    showToast('❌ ' + err.message);
  }
}

async function printExecutiveReport() {
  const isRTL = currentLang === 'ar';
  try {
    showToast(isRTL ? '⏳ جاري تجهيز وثيقة PDF للطباعة...' : '⏳ Preparing PDF for printing...');
    const schema = currentDiagramSchema();
    const dialect = document.getElementById('dbExportDialect')?.value || 'oracle';
    const payload = {
      tablesData: Object.keys(schema.tablesData).length ? schema.tablesData : tablesData,
      fkList: schema.fkList.length ? schema.fkList : fkList,
      subsystems: subsystemData,
      dialect: dialect,
      lang: currentLang || 'ar'
    };
    const res = await fetch('/api/export/report/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'PDF report failed');
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const printWin = window.open(url, '_blank');
    if (printWin) {
      printWin.focus();
    }
  } catch (err) {
    showToast('❌ ' + err.message);
  }
}

async function exportSchema() {
  const dialect = document.getElementById('dbExportDialect').value;
  const drop = document.getElementById('dbExportDrop').checked;
  try {
    const res = await requestCurrentSchemaExport(dialect, drop);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Export failed');
    const blob = new Blob([data.script], { type: 'text/sql;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `schema.${dialect}.sql`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
 showToast(` ${data.tableCount} tables • ${data.fkCount} FKs`);
  } catch (err) {
 showToast(' ' + err.message);
  }
}

async function previewExport() {
  const workspaceId = activeWorkspaceId;
  const dialect = document.getElementById('dbExportDialect').value;
  const drop = document.getElementById('dbExportDrop').checked;
  const pre = document.getElementById('exportPreview');
  try {
    const res = await requestCurrentSchemaExport(dialect, drop);
    const data = await res.json();
    if (workspaceId !== activeWorkspaceId) return;
    if (!data.success) throw new Error(data.error || 'Export failed');
    pre.value = data.script;
    pre.style.display = 'block';
 showToast(` Generated for ${dialect}`);
  } catch (err) {
 showToast(' ' + err.message);
  }
}

window.__ddFile = window.__ddFile || 'data_dictionary';
function setDdFile(input) {
  const files = (input.files && Array.from(input.files)) || [];
  const el = document.getElementById('ddFileList');
  if (!files.length) { el.textContent = ''; return; }
  try {
    const first = files[0].name.replace(/\.(xlsx|xlsm)$/i, '') || 'data_dictionary';
    window.__ddFile = files.length > 1 ? `merged_${first}` : first;
  } catch (_) { window.__ddFile = 'data_dictionary'; }
 el.textContent = ` ${files.length} ملف: ` + files.map(f => f.name).join(' ، ');
 showToast(` تم اختيار ${files.length} ملف`);
}
function setDdSqlFile(input) {
  const files = (input.files && Array.from(input.files)) || [];
  const el = document.getElementById('ddSqlFileList');
 el.textContent = files.length ? ` ${files.length} ملف: ` + files.map(f => f.name).join(' ، ') : '';
}
function ddEsc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
async function importDataDictionary(input, store) {
  const files = (input.files && Array.from(input.files)) || [];
  if (!files.length) {
 showToast(' اختر ملفات .xlsx أولاً (Select .xlsx file(s) first)');
    return;
  }
  for (const f of files) {
    if (!/\.(xlsx|xlsm)$/i.test(f.name)) {
 showToast(' يجب أن تكون جميع الملفات بصيغة Excel (.xlsx)');
      input.value = '';
      return;
    }
  }
  const audit = (document.getElementById('ddAudit') || {}).value || 'keep';
  const fd = new FormData();
  files.forEach(f => fd.append('files', f));
  fd.append('dialect', document.getElementById('ddDialect').value);
  fd.append('include_drop', document.getElementById('ddDrop').checked ? 'true' : 'false');
  fd.append('audit', audit);
  fd.append('store', store ? 'true' : 'false');
 showToast(store ? ' جاري استيراد قاموس البيانات ورسم المخطط...' : ' جاري تحليل قاموس البيانات...');
  try {
    const res = await fetch('/api/dictionary/import', { method: 'POST', body: fd });
    let data;
    try { data = await res.json(); } catch (_) { data = {}; }
    if (!data.success) throw new Error(data.detail || data.error || ('Import failed (' + res.status + ')'));
    try {
      const first = files[0].name.replace(/\.(xlsx|xlsm)$/i, '') || 'data_dictionary';
      window.__ddFile = files.length > 1 ? `merged_${first}` : first;
    } catch (_) {}
    const pre = document.getElementById('ddPreview');
    pre.value = data.ddl;
    pre.style.display = 'block';
    const warn = (data.summary && data.summary.warnings) || [];
 let html = `<b> ${data.schema.tableCount} جدول • ${data.schema.fkCount} علاقة</b> — اللهجة: <b>${ddEsc(data.targetDialect)}</b>`;
    if (files.length > 1) html += ` • الملفات: <b>${files.length}</b>`;
    if (data.classifier) html += ` • التصنيف: ${ddEsc(data.classifier)}`;
 if (warn.length) html += '<div style="margin-top:6px;color:#d97706"> ' + warn.map(w => ddEsc(w)).join('<br> ') + '</div>';
    document.getElementById('ddSummary').innerHTML = html;
    if (store) {
      applySchemaPayload(data);
      refreshCurrentSchemaInfo();
      setTimeout(fitView, 150);
    }
    showToast(store
 ? ` تم الاستيراد: ${data.schema.tableCount} جدول ورُسم المخطط`
 : ` تمت المعاينة: ${data.schema.tableCount} جدول`);
  } catch (err) {
 showToast(' ' + err.message);
  } finally {
    input.value = '';
    const el = document.getElementById('ddFileList');
    if (el) el.textContent = '';
  }
}
async function exportDataDictionaryFromSql() {
  const input = document.getElementById('ddSqlFileInput');
  const files = (input.files && Array.from(input.files)) || [];
  const info = document.getElementById('ddSqlExportInfo');
 if (!files.length) { info.textContent = ' اختر ملفات SQL أولاً'; showToast(' اختر ملفات SQL أولاً'); return; }
  const fd = new FormData();
  files.forEach(f => fd.append('files', f));
 info.textContent = ' جارٍ توليد القاموس من الكود...';
 showToast(' جارٍ توليد قاموس البيانات من الكود...');
  try {
    const res = await fetch('/api/dictionary/export', { method: 'POST', body: fd });
    if (!res.ok) {
      let msg = 'تعذر التوليد';
      try { const t = await res.json(); if (t.detail) msg = t.detail; } catch (_) {}
      throw new Error(msg);
    }
    const blob = await res.blob();
    const cd = res.headers.get('Content-Disposition') || '';
    const m = /filename="([^"]+)"/.exec(cd);
    const fname = m ? m[1] : 'data_dictionary_merged.xlsx';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = fname;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1500);
 info.innerHTML = ` تم توليد <b>${ddEsc(fname)}</b> — <b>${res.headers.get('X-Tables') || '?'}</b> جدول • <b>${res.headers.get('X-Fks') || '?'}</b> علاقة.`;
 showToast(' تم توليد قاموس البيانات وتنزيله');
  } catch (err) {
 info.textContent = ' ' + err.message;
 showToast(' ' + err.message);
  }
}
function downloadDdSql() {
  const pre = document.getElementById('ddPreview');
 if (!pre.value) { showToast(' لا يوجد كود جاهز للتنزيل'); return; }
  const dialect = document.getElementById('ddDialect').value;
  const blob = new Blob([pre.value], { type: 'text/sql;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${window.__ddFile || 'data_dictionary'}_${dialect}.sql`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
async function copyDdSql() {
  const pre = document.getElementById('ddPreview');
 if (!pre.value) { showToast(' لا يوجد كود جاهز للنسخ'); return; }
  try {
    await navigator.clipboard.writeText(pre.value);
 showToast(' تم نسخ الكود');
  } catch (e) {
    pre.select();
    document.execCommand('copy');
 showToast(' تم نسخ الكود');
  }
}

async function saveDbSettings() {
  const dialect = (document.getElementById('dbDialect') || {}).value || dbCfg.dialect;
  const d = dbParamsFromForm();
  dbCfg = { ...dbCfg, dialect, host: d.host || dbCfg.host, port: d.port || dbCfg.port,
            service: d.service_name || d.database || dbCfg.service, user: d.user || dbCfg.user,
            password: d.password || dbCfg.password, file: document.getElementById('dbFilePath').value.trim() };

  const payload = {
    settings: {
      db_dialect: dialect,
      db_host: dbCfg.host,
      db_port: String(dbCfg.port),
      db_service: dbCfg.service,
      db_user: dbCfg.user,
      db_password: dbCfg.password,
      db_file: dbCfg.file
    }
  };

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    await res.json();
    if (typeof updateStatusBar === 'function') updateStatusBar();
    checkDbConnection();
 showToast(currentLang === 'ar' ? ' تم حفظ إعدادات قاعدة البيانات في SQLite' : ' Database settings saved to SQLite');
  } catch (err) {
 showToast(' ' + err.message);
  }
}

function applySettingsChanges() {
  const vmode = document.getElementById('settingsViewMode').value;
  const theme = document.getElementById('settingsTheme').value;
  const lang = document.getElementById('settingsLang').value;
  autoSaveEnabled = document.getElementById('settingsAutoSave').checked;
  const widthPx = parseInt(document.getElementById('settingsTableWidth').value, 10) || 270;
  const zoomPct = parseInt(document.getElementById('settingsZoomPct').value, 10) || 85;

  const readVal = (id, def) => {
    const el = document.getElementById(id);
    return el ? (parseInt(el.value, 10) || def) : def;
  };
  layoutSpacing.circular = readVal('spacingCircular', 550);
  layoutSpacing.force = readVal('spacingForce', 220);
  layoutSpacing.hierarchical = readVal('spacingHierarchical', 320);
  layoutSpacing.grid = readVal('spacingGrid', 310);
  layoutSpacing.cluster = readVal('spacingCluster', 310);
  layoutSpacing.star = readVal('spacingStar', 380);
  try { localStorage.setItem('erd_layout_spacing', JSON.stringify(layoutSpacing)); } catch(e) {}

  if (vmode !== globalViewMode) setGlobalViewMode(vmode);
  if (theme !== currentTheme) setTheme(theme, false);
  if (lang !== currentLang) { currentLang = lang; applyLanguage(lang); }
  refreshSettingsI18n();

  const selPreset = document.getElementById('presetSelect');
  if (selPreset && selPreset.value) {
    calculateInitialLayout(selPreset.value);
    renderAll();
    scheduleAutoSave();
  }

  const payload = {
    settings: {
      auto_save: autoSaveEnabled ? '1' : '0',
      table_width: String(widthPx),
      zoom: zoomPct.toString()
    }
  };
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(() => {
 showToast(currentLang === 'ar' ? ' تم تحديث الإعدادات' : ' Settings updated');
  }).catch(() => {});
}

function applyTableWidth(widthPx) {
  document.querySelectorAll('.table-node').forEach(() => {
    allTables.forEach(t => {
      const p = tablePositions[t];
      if (p) p.width = widthPx;
    });
  });
  renderAll();
  scheduleAutoSave();
}

async function backupDatabase() {
  try {
    const res = await fetch('/api/db/backup');
    if (!res.ok) throw new Error('backup failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TESTR_ERD_Studio_Backup_${new Date().toISOString().slice(0,10)}.db`;
    a.click();
    URL.revokeObjectURL(url);
 showToast(currentLang === 'ar' ? ' تم تنزيل نسخة احتياطية من قاعدة البيانات' : ' Database backup downloaded');
  } catch (err) {
 showToast(' Backup error: ' + err.message);
  }
}

async function restoreDatabase(input) {
  const file = input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  try {
 showToast(currentLang === 'ar' ? ' جاري استعادة قاعدة البيانات...' : ' Restoring database...');
    const res = await fetch('/api/db/restore', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success) {
 showToast(currentLang === 'ar' ? ' تمت الاستعادة - سيتم تحديث الصفحة' : ' Restored - reloading page');
      setTimeout(() => location.reload(), 900);
    } else {
 showToast(' ' + (data.detail || 'restore failed'));
    }
  } catch (err) {
 showToast(' ' + err.message);
  } finally {
    input.value = '';
  }
}

function exportStateJson() {
  const customColsPlain = {};
  Object.keys(tableCustomHiddenCols).forEach(k => {
    customColsPlain[k] = Array.from(tableCustomHiddenCols[k]);
  });
  const snapshot = {
    app: 'TESTR ERD Studio Pro',
    version: 1,
    exported_at: new Date().toISOString(),
    positions: tablePositions,
    hidden_cols: customColsPlain,
    visible_tables: Array.from(selectedTables),
    settings: {
      current_theme: currentTheme,
      current_lang: currentLang,
      global_view_mode: globalViewMode,
      zoom: zoom.toString(),
      pan_x: panX.toString(),
      pan_y: panY.toString()
    }
  };
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `TESTR_ERD_State_${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
 showToast(currentLang === 'ar' ? ' تم تصدير لقطة الحالة' : ' State snapshot exported');
}

function importStateJson(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const snap = JSON.parse(e.target.result);
      if (snap.positions) {
        tablePositions = snap.positions;
        allTables.forEach(t => { if (!tablePositions[t]) tablePositions[t] = { x: 100, y: 100, width: TABLE_WIDTH, height: getTableHeight(t) }; });
      }
      if (snap.hidden_cols) {
        tableCustomHiddenCols = {};
        Object.keys(snap.hidden_cols).forEach(k => { tableCustomHiddenCols[k] = new Set(snap.hidden_cols[k]); });
      }
      if (snap.visible_tables && snap.visible_tables.length > 0) selectedTables = new Set(snap.visible_tables);
      if (snap.settings) {
        if (snap.settings.current_theme) setTheme(snap.settings.current_theme, false);
        if (snap.settings.current_lang) { currentLang = snap.settings.current_lang; applyLanguage(currentLang); }
        if (snap.settings.global_view_mode) { globalViewMode = snap.settings.global_view_mode; document.getElementById('globalViewModeSelect').value = globalViewMode; }
        if (snap.settings.zoom) zoom = parseFloat(snap.settings.zoom);
        if (snap.settings.pan_x) panX = parseFloat(snap.settings.pan_x);
        if (snap.settings.pan_y) panY = parseFloat(snap.settings.pan_y);
      }
      buildSidebarList();
      renderAll();
      fitView();
      scheduleAutoSave();
 showToast(currentLang === 'ar' ? ' تم استيراد لقطة الحالة بنجاح' : ' State imported successfully');
    } catch (err) {
 showToast(' ' + ('Invalid JSON file: ' + err.message));
    }
  };
  reader.readAsText(file);
  input.value = '';
}

async function factoryReset() {
 if (!confirm(currentLang === 'ar' ? ' سيتم مسح كل البيانات المحفوظة (الإعدادات، المواضيع، الأنماط). متابعة؟' : ' This will erase all saved data (settings, positions, layouts). Continue?')) return;
  try {
    const res = await fetch('/api/db/factory-reset', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      localStorage.removeItem('testr_erd_studio_bundle');
 showToast(currentLang === 'ar' ? ' تمت إعادة التعيين - تحديث الصفحة' : ' Reset done - reloading');
      setTimeout(() => location.reload(), 1000);
    } else {
 showToast(' ' + (data.detail || 'reset failed'));
    }
  } catch (err) {
 showToast(' ' + err.message);
  }
}

function refreshSettingsI18n() {
  const safeQ = s => { const n = document.querySelector(s); return n || { set textContent(v) {} }; };
  safeQ('#i18n-settingsTitle').textContent = currentLang === 'ar' ? 'الإعدادات' : 'Settings';
  safeQ('#i18n-settingsSubtitle').textContent = currentLang === 'ar' ? 'إعدادات التطبيق الشاملة' : 'Application-wide configuration';
  safeQ('#i18n-tabDb').textContent = currentLang === 'ar' ? 'قاعدة البيانات' : 'Database';
  safeQ('#i18n-tabDisplay').textContent = currentLang === 'ar' ? 'العرض' : 'Display';
  safeQ('#i18n-tabStorage').textContent = currentLang === 'ar' ? 'البيانات' : 'Data';
  safeQ('#i18n-dbHost').textContent = currentLang === 'ar' ? 'المضيف' : 'Host';
  safeQ('#i18n-dbPort').textContent = currentLang === 'ar' ? 'المنفذ' : 'Port';
  safeQ('#i18n-dbService').textContent = currentLang === 'ar' ? 'اسم الخدمة' : 'Service Name';
  safeQ('#i18n-dbUser').textContent = currentLang === 'ar' ? 'اسم المستخدم' : 'Username';
  safeQ('#i18n-dbPass').textContent = currentLang === 'ar' ? 'كلمة المرور' : 'Password';
  safeQ('#i18n-dbHint').textContent = currentLang === 'ar' ? 'يستخدم للاتصال بقاعدة بيانات Oracle عند المزامنة واختبار الربط.' : 'Used to connect to the Oracle database when syncing and testing connectivity.';
  safeQ('#i18n-dbTestBtn').textContent = currentLang === 'ar' ? 'اختبار الاتصال' : 'Test Connection';
  safeQ('#i18n-dbSaveBtn').textContent = currentLang === 'ar' ? 'حفظ الاتصال' : 'Save Connection';
  safeQ('#i18n-dispSection1').textContent = currentLang === 'ar' ? 'التخطيط والمظهر' : 'Layout & Appearance';
  safeQ('#i18n-dispViewMode').textContent = currentLang === 'ar' ? 'وضع العرض الافتراضي' : 'Default View Mode';
  safeQ('#i18n-dispTheme').textContent = currentLang === 'ar' ? 'المظهر' : 'Theme';
  safeQ('#i18n-dispLang').textContent = currentLang === 'ar' ? 'اللغة' : 'Language';
  safeQ('#i18n-dispAutoSave').textContent = currentLang === 'ar' ? 'الحفظ التلقائي في SQLite' : 'Auto-Save to SQLite';
  safeQ('#i18n-dispTableWidth').textContent = currentLang === 'ar' ? 'عرض الجدول (بكسل)' : 'Table Width (px)';
  safeQ('#i18n-dispZoom').textContent = currentLang === 'ar' ? 'التكبير الابتدائي (٪)' : 'Initial Zoom (%)';
  safeQ('#i18n-dispSectionSpacing').textContent = currentLang === 'ar' ? 'مستوى التباعد والتنافر لكل نمط تخطيط' : 'Layout Spacing & Repulsion Per Preset';
  safeQ('#i18n-lblSpacingCircular').textContent = currentLang === 'ar' ? 'تنافر النمط الدائري (نصف القطر px)' : 'Circular Layout Radius (px)';
  safeQ('#i18n-lblSpacingForce').textContent = currentLang === 'ar' ? 'قوة التنافر الفيزيائي (Repulsion Force)' : 'Physical Repulsion Force';
  safeQ('#i18n-lblSpacingHierarchical').textContent = currentLang === 'ar' ? 'تباعد النمط الهرمي (Column Gap px)' : 'Hierarchical Column Gap (px)';
  safeQ('#i18n-lblSpacingGrid').textContent = currentLang === 'ar' ? 'تباعد النمط الشبكي (Grid Gap px)' : 'Grid Layout Gap (px)';
  safeQ('#i18n-lblSpacingCluster').textContent = currentLang === 'ar' ? 'تباعد نمط المجموعات (Cluster Gap px)' : 'Clusters Gap (px)';
  const lblStar = document.getElementById('i18n-lblSpacingStar');
  if (lblStar) lblStar.textContent = currentLang === 'ar' ? 'نصف قطر النمط النجمي (Star Radius px)' : 'Star Layout Radius (px)';
  safeQ('#i18n-storageSection1').textContent = currentLang === 'ar' ? 'النسخ والاستعادة' : 'Backup & Restore';
  safeQ('#i18n-storageBackupHint').textContent = currentLang === 'ar' ? 'نزّل نسخة كاملة من قاعدة بيانات SQLite تشمل كل المواضع والإعدادات والأنماط المحفوظة.' : 'Download a full copy of the SQLite database including all positions, settings and saved layouts.';
  safeQ('#i18n-storageBackupBtn').textContent = currentLang === 'ar' ? 'تنزيل نسخة احتياطية' : 'Download SQLite Backup';
  safeQ('#i18n-storageRestoreBtn').textContent = currentLang === 'ar' ? 'استعادة من نسخة' : 'Restore from Backup';
  safeQ('#i18n-storageSection2').textContent = currentLang === 'ar' ? 'لقطة الحالة' : 'State Snapshot';
  safeQ('#i18n-storageSnapHint').textContent = currentLang === 'ar' ? 'تصدير/استيراد لقطة JSON للترتيب الحالي (مواضع الجداول، الحقول المخفية، العرض).' : 'Export/import a JSON snapshot of the current layout (table positions, hidden columns, view).';
  safeQ('#i18n-storageExportStateBtn').textContent = currentLang === 'ar' ? 'تصدير لقطة (JSON)' : 'Export State (.json)';
  safeQ('#i18n-storageImportStateBtn').textContent = currentLang === 'ar' ? 'استيراد لقطة' : 'Import State';
  safeQ('#i18n-storageSection3').textContent = currentLang === 'ar' ? 'منطقة الخطر' : 'Danger Zone';
  safeQ('#i18n-storageDangerHint').textContent = currentLang === 'ar' ? 'إعادة تعيين قاعدة البيانات كلها إلى الحالة الافتراضية ومسح كل التعديلات. لا يمكن التراجع.' : 'Reset the entire database to its default state and wipe all changes. This cannot be undone.';
  safeQ('#i18n-storageFactoryBtn').textContent = currentLang === 'ar' ? 'إعادة تعيين المصنع' : 'Factory Reset';
  const q = s => document.querySelector(s);
  safeQ('#i18n-tabAi').textContent = currentLang === 'ar' ? 'الذكاء الاصطناعي' : 'AI';
  safeQ('#i18n-aiProviderSection').textContent = currentLang === 'ar' ? 'مزود الذكاء الاصطناعي' : 'AI Provider';
  safeQ('#i18n-aiProvider').textContent = currentLang === 'ar' ? 'المزود' : 'Provider';
  if (document.getElementById('opt-provider-local')) {
    document.getElementById('opt-provider-local').textContent = currentLang === 'ar' ? 'المساعد المحلي الذكي (بدون مفتاح API)' : 'Local Smart Assistant (No API key)';
  }
  if (document.getElementById('opt-provider-opencode')) {
    document.getElementById('opt-provider-opencode').textContent = currentLang === 'ar' ? 'OpenCode Zen (مجاني سحابي - بدون مفتاح API)' : 'OpenCode Zen (Free Cloud - No API key)';
  }
  if (document.getElementById('opt-provider-openai')) {
    document.getElementById('opt-provider-openai').textContent = currentLang === 'ar' ? 'OpenAI / متوافق (بمفتاح API)' : 'OpenAI / Compatible (With API key)';
  }
  safeQ('#i18n-aiModel').textContent = currentLang === 'ar' ? 'النموذج' : 'Model';
  safeQ('#i18n-aiBaseUrl').textContent = currentLang === 'ar' ? 'الرابط الأساسي' : 'Base URL';
  safeQ('#i18n-aiApiKey').textContent = currentLang === 'ar' ? 'مفتاح API' : 'API Key';
  safeQ('#i18n-aiTemp').textContent = currentLang === 'ar' ? 'الحرارة' : 'Temperature';
  safeQ('#i18n-aiHint').textContent = currentLang === 'ar' ? 'اترك المزود محلياً ليعمل المساعد بدون مفتاح API. عند إضافة مفتاح يتفعّل الوضع السحابي الذكي مع تنفيذ الأدوات على المخطط.' : 'Keep the provider local for an assistant that works with no API key. Adding a key enables the smart cloud mode with tool execution on the diagram.';
  safeQ('#i18n-aiTestBtn').textContent = currentLang === 'ar' ? 'فحص' : 'Test';
  safeQ('#i18n-aiSaveBtn').textContent = currentLang === 'ar' ? 'حفظ إعدادات الذكاء' : 'Save AI Settings';
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  if (!t) return;
  if (!type) {
    if (/error|fail|فشل|خطأ|لا يمكن|تعذر/i.test(msg)) type = 'error';
    else if (/warn|تحذير|انتبه/i.test(msg)) type = 'warning';
    else if (/saved|loaded|تم|success|ناجح|restored|مكتمل/i.test(msg)) type = 'success';
    else type = 'info';
  }
  // Strip any legacy emojis
 const cleanMsg = msg.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}]/gu, '').trim();
  
  const icons = {
    success: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    error: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    warning: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    info: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
  };

  t.className = `toast toast-${type} show`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span class="toast-msg">${cleanMsg}</span>`;
  
  clearTimeout(t._timer);
  t._timer = setTimeout(() => {
    t.classList.remove('show');
  }, 2000);
}

// ==================== EXPORT (SVG / PNG) FIXED ====================
// Build a self-contained SVG with resolved colors, explicit viewBox and background.
function buildExportSvg() {
  const root = document.getElementById('mainSvg');
  const clone = root.cloneNode(true);
  clone.removeAttribute('id');
  clone.removeAttribute('style');
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

  // Remove the live pan/zoom transform so export is clean 1:1 in content coords
  const layer = clone.querySelector('#canvasLayer');
  if (layer) layer.removeAttribute('transform');

  // Compute bounding box from table positions / node elements
  const nodes = root.querySelectorAll('.table-node');
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  nodes.forEach((n) => {
    const t = n.getAttribute('data-id');
    const p = tablePositions[t];
    if (p) {
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x + p.width > maxX) maxX = p.x + p.width;
      if (p.y + p.height > maxY) maxY = p.y + p.height;
    }
  });
  if (!isFinite(minX)) { minX = 0; minY = 0; maxX = 900; maxY = 700; }

  const pad = 60;
  minX -= pad; minY -= pad; maxX += pad; maxY += pad;
  const width = Math.max(200, maxX - minX);
  const height = Math.max(200, maxY - minY);

  clone.setAttribute('viewBox', `${minX} ${minY} ${width} ${height}`);
  clone.setAttribute('width', width);
  clone.setAttribute('height', height);

  // Background color per theme
  const bgColor = currentTheme === 'dark' ? '#090d16'
    : currentTheme === 'academic' ? '#ffffff'
    : currentTheme === 'light' ? '#f8fafc'
    : '#ffffff';

  // Resolve CSS custom properties to concrete colors
  const cs = getComputedStyle(document.body);
  const V = (name, fallback) => (cs.getPropertyValue(name) || '').trim() || fallback;

  const styleText = `
    .er.entityBox { fill: ${V('--tbl-header-bg', '#ECECFF')}; stroke: ${V('--tbl-header-stroke', '#9370DB')}; stroke-width: 1.2px; rx: 4px; ry: 4px; }
    .er.attributeBoxOdd { fill: ${V('--tbl-odd-bg', '#ffffff')}; stroke: ${V('--tbl-border', '#9370DB')}; stroke-width: 1px; }
    .er.attributeBoxEven { fill: ${V('--tbl-even-bg', '#f8f9fe')}; stroke: ${V('--tbl-border', '#9370DB')}; stroke-width: 1px; }
    .er.entityTitleText { font-family: "trebuchet ms", verdana, arial, sans-serif; font-size: 12px; font-weight: 700; fill: ${V('--tbl-header-text', '#1e1b4b')}; text-anchor: middle; dominant-baseline: middle; }
    .er.attrTextType { font-family: monospace; font-size: 9.8px; fill: ${V('--tbl-type-color', '#64748b')}; text-anchor: start; dominant-baseline: middle; }
    .er.attrTextName { font-family: monospace; font-size: 10.5px; font-weight: 600; fill: ${V('--tbl-name-color', '#0f172a')}; text-anchor: start; dominant-baseline: middle; }
    .er.attrTextKey { font-family: monospace; font-size: 9px; font-weight: 700; fill: ${V('--tbl-key-color', '#7c3aed')}; text-anchor: end; dominant-baseline: middle; }
    .relationshipLine { stroke: ${V('--line-color', '#64748b')}; stroke-width: 1.5px; fill: none; }
    .rel-label-box { fill: ${V('--card', '#ffffff')}; stroke: ${V('--border', '#e2e8f0')}; stroke-width: 1px; }
    .rel-label-text { font-family: monospace; font-size: 9.5px; fill: ${V('--text-muted', '#64748b')}; text-anchor: middle; dominant-baseline: middle; }
  `;

  const styleEl = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  styleEl.textContent = styleText;
  clone.insertBefore(styleEl, clone.firstChild);

  // Background rect covering the whole viewBox
  const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  bgRect.setAttribute('x', minX);
  bgRect.setAttribute('y', minY);
  bgRect.setAttribute('width', width);
  bgRect.setAttribute('height', height);
  bgRect.setAttribute('fill', bgColor);
  clone.insertBefore(bgRect, styleEl.nextSibling);

  // Fix marker arrow fill colors to match theme lines
  const arrowPath = clone.querySelector('#marker-arrow path');
  if (arrowPath) arrowPath.setAttribute('fill', V('--line-color', '#64748b'));
  const arrowHlPath = clone.querySelector('#marker-arrow-highlight path');
  if (arrowHlPath) arrowHlPath.setAttribute('fill', V('--line-highlight', '#38bdf8'));

  return { svg: clone, width, height, bgColor };
}

function exportSVG() {
  const { svg } = buildExportSvg();
  const blob = new Blob([new XMLSerializer().serializeToString(svg)], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'TESTR_ERD_Studio.svg';
  a.click();
  URL.revokeObjectURL(url);
 showToast(currentLang === 'ar' ? ' تم تصدير SVG' : ' SVG Exported');
}

function exportPNG() {
  const { svg, width, height, bgColor } = buildExportSvg();
  const svgStr = new XMLSerializer().serializeToString(svg);
  const img = new Image();
  img.onload = () => {
    const scale = 2;
    const canvas = document.createElement('canvas');
    canvas.width = Math.ceil(width * scale);
    canvas.height = Math.ceil(height * scale);
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = 'TESTR_ERD_Studio.png';
    a.click();
 showToast(currentLang === 'ar' ? ' تم تصدير PNG' : ' PNG Exported');
  };
  img.onerror = () => {
 showToast(currentLang === 'ar' ? ' فشل توليد PNG' : ' Failed to generate PNG');
  };
  img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgStr)));
}


function setRailActive(btn) {
  document.querySelectorAll('.rail-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

function setViewTab(btn) {
  document.querySelectorAll('.view-tab').forEach(b => {
    b.classList.remove('active');
    b.setAttribute('aria-selected', 'false');
  });
  btn.classList.add('active');
  btn.setAttribute('aria-selected', 'true');
  // Sync rail
  const map = { viewTabCanvas: 'railBtnCanvas', viewTabImport: 'railBtnImport', viewTabExport: 'railBtnExport' };
  const railId = map[btn.id];
  if (railId) {
    document.querySelectorAll('.rail-btn').forEach(b => b.classList.remove('active'));
    const rb = document.getElementById(railId);
    if (rb) rb.classList.add('active');
  }
}



function getDatabaseDisplayInfo() {
  const activeWs = (typeof workspaces !== 'undefined' && Array.isArray(workspaces))
    ? workspaces.find(w => w.id === activeWorkspaceId)
    : null;

  // If active workspace is non-DB custom source (e.g. SQL file, DDL paste, Excel, Agent)
  if (activeWs && activeWs.source && activeWs.source !== 'oracle') {
    if (activeWs.source === 'sql') {
      return {
        dialectName: 'SQL DDL',
        targetName: activeWs.name || (currentLang === 'ar' ? 'ملف محلي' : 'Local File'),
        isLiveDb: false
      };
    }
    if (activeWs.source === 'paste') {
      return {
        dialectName: 'SQL Script',
        targetName: activeWs.name || (currentLang === 'ar' ? 'كود مباشر' : 'Pasted Code'),
        isLiveDb: false
      };
    }
    if (activeWs.source === 'xlsx') {
      return {
        dialectName: 'Excel',
        targetName: activeWs.name || (currentLang === 'ar' ? 'قاموس بيانات' : 'Data Dictionary'),
        isLiveDb: false
      };
    }
    if (activeWs.source === 'agent-code') {
      return {
        dialectName: 'AI Schema',
        targetName: activeWs.name || 'AI Architect',
        isLiveDb: false
      };
    }
  }

  // Live database connection from dbCfg or active workspace dialect
  const rawDialect = (dbCfg && dbCfg.dialect) || (activeWs && activeWs.dialect) || 'oracle';
  const dialectMap = {
    oracle: 'Oracle',
    mysql: 'MySQL',
    postgres: 'PostgreSQL',
    postgresql: 'PostgreSQL',
    mssql: 'SQL Server',
    sqlserver: 'SQL Server',
    sqlite: 'SQLite',
    sqlite_file: 'SQLite'
  };
  const dialectName = dialectMap[rawDialect] || (rawDialect ? rawDialect.toUpperCase() : 'Database');

  let targetName = '';
  if (rawDialect === 'sqlite_file' || rawDialect === 'sqlite') {
    if (dbCfg && dbCfg.file) {
      targetName = dbCfg.file.replace(/\\/g, '/').split('/').pop() || dbCfg.file;
    } else {
      targetName = (currentLang === 'ar') ? 'ملف محلي' : 'Local File';
    }
  } else {
    const srv = (dbCfg && dbCfg.service) ? dbCfg.service : (rawDialect === 'oracle' ? 'ORCLPDB' : 'DATABASE');
    const host = (dbCfg && dbCfg.host) ? dbCfg.host : 'localhost';
    const defPort = (rawDialect === 'mysql' ? 3306 : rawDialect === 'postgres' ? 5432 : rawDialect === 'mssql' ? 1433 : 1521);
    const port = (dbCfg && dbCfg.port) ? dbCfg.port : defPort;
    targetName = `${srv} (${host}:${port})`;
  }

  return {
    dialectName,
    targetName,
    isLiveDb: true
  };
}

function updateStatusBar() {
  const dbText = document.getElementById('statusDbText');
  const dbDot = document.getElementById('statusDbDot') || document.querySelector('#statusDbIndicator .status-dot');
  const dbIndicator = document.getElementById('statusDbIndicator');

  const dbInfo = getDatabaseDisplayInfo();

  if (dbInfo.isLiveDb) {
    if (dbDot) {
      dbDot.classList.remove('connected', 'disconnected', 'checking');
    }

    let stateLabel = '';
    let titleStr = '';

    if (isCheckingDbConnection) {
      if (dbDot) dbDot.classList.add('checking');
      stateLabel = (currentLang === 'ar') ? ' (جاري الفحص...)' : ' (checking...)';
      titleStr = (currentLang === 'ar')
        ? `جاري التحقق من الاتصال بقاعدة بيانات ${dbInfo.dialectName}...\nانقر لضبط الإعدادات`
        : `Checking connection to ${dbInfo.dialectName} database...\nClick to configure settings`;
    } else if (isDbConnected) {
      if (dbDot) dbDot.classList.add('connected');
      stateLabel = '';
      titleStr = (currentLang === 'ar')
        ? `متصل بقاعدة البيانات (${dbInfo.dialectName})\n${dbInfo.targetName}\nانقر لإدارة الاتصال`
        : `Connected to database (${dbInfo.dialectName})\n${dbInfo.targetName}\nClick to manage connection`;
    } else {
      if (dbDot) dbDot.classList.add('disconnected');
      stateLabel = (currentLang === 'ar') ? ' (غير متصل)' : ' (Disconnected)';
      titleStr = (currentLang === 'ar')
        ? `غير متصل بقاعدة بيانات ${dbInfo.dialectName}${dbConnectionError ? ': ' + dbConnectionError : ''}\nانقر لضبط واختبار الاتصال`
        : `Disconnected from ${dbInfo.dialectName}${dbConnectionError ? ': ' + dbConnectionError : ''}\nClick to configure and test connection`;
    }

    if (dbText) {
      dbText.textContent = `${dbInfo.dialectName} · ${dbInfo.targetName}${stateLabel}`;
    }
    if (dbIndicator) {
      dbIndicator.title = titleStr;
    }
  } else {
    // Non-DB workspace (local file / script / excel)
    if (dbDot) {
      dbDot.classList.remove('connected', 'disconnected', 'checking');
      dbDot.classList.add('connected');
    }
    if (dbText) {
      dbText.textContent = `${dbInfo.dialectName} · ${dbInfo.targetName}`;
    }
    if (dbIndicator) {
      dbIndicator.title = (currentLang === 'ar')
        ? `مساحة عمل محلية: ${dbInfo.dialectName}\nانقر لفتح الإعدادات`
        : `Local workspace: ${dbInfo.dialectName}\nClick to open settings`;
    }
  }

  const tblCount = selectedTables ? selectedTables.size : 0;
  const visibleFks = (fkList || []).filter(f => selectedTables && selectedTables.has(f.child) && selectedTables.has(f.parent)).length;
  const statsStr = (currentLang === 'ar') 
    ? `${tblCount} جدول · ${visibleFks} علاقة`
    : `${tblCount} Tables · ${visibleFks} FKs`;

  const schemaStats = document.getElementById('statusSchemaStats');
  if (schemaStats) schemaStats.textContent = statsStr;

  const statSummary = document.getElementById('statSummary');
  if (statSummary) statSummary.textContent = statsStr;

  const selInfo = document.getElementById('statusSelectionInfo');
  if (selInfo) {
    if (selectedTableNodes && selectedTableNodes.size > 0) {
      selInfo.textContent = (currentLang === 'ar')
        ? `${selectedTableNodes.size} محدد`
        : `${selectedTableNodes.size} selected`;
    } else {
      selInfo.textContent = (currentLang === 'ar') ? 'جاهز' : 'Ready';
    }
  }
  const zoomEl = document.getElementById('statusZoomLevel');
  if (zoomEl) {
    zoomEl.textContent = Math.round(zoom * 100) + '%';
  }
  const layoutEl = document.getElementById('statusActiveLayout');
  if (layoutEl) {
    const presetNames = {
      hierarchical: (currentLang === 'ar' ? 'هرمي' : 'Tree'),
      grid: (currentLang === 'ar' ? 'شبكي' : 'Grid'),
      cluster: (currentLang === 'ar' ? 'مجموعات' : 'Clusters'),
      circular: (currentLang === 'ar' ? 'دائري' : 'Circular'),
      force: (currentLang === 'ar' ? 'فيزيائي' : 'Force'),
      star: (currentLang === 'ar' ? 'نجمي' : 'Star')
    };
    const sel = document.getElementById('presetSelect');
    const val = sel ? sel.value : 'hierarchical';
    layoutEl.textContent = presetNames[val] || val;
  }
  const langEl = document.getElementById('statusLangIndicator');
  if (langEl) {
    langEl.textContent = (currentLang === 'ar') ? 'العربية (RTL)' : 'English (LTR)';
  }
}

function updateControlIcons() {
  const presetSel = document.getElementById('presetSelect');
  const presetIcon = document.getElementById('icon-presetSelect');
  if (presetSel && presetIcon) {
    const val = presetSel.value || 'hierarchical';
    const icons = {
      hierarchical: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v6M12 9l-6 6M12 9l6 6"/><circle cx="12" cy="4" r="1.8"/><circle cx="6" cy="18" r="1.8"/><circle cx="18" cy="18" r="1.8"/></svg>',
      grid: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
      cluster: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="17" r="4"/></svg>',
      circular: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="4" r="1.5"/><circle cx="20" cy="12" r="1.5"/><circle cx="12" cy="20" r="1.5"/><circle cx="4" cy="12" r="1.5"/></svg>',
      force: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="8" r="2"/><circle cx="8" cy="20" r="2"/><circle cx="18" cy="18" r="2"/><line x1="6" y1="7" x2="10" y2="10"/><line x1="18" y1="9" x2="14" y2="11"/><line x1="9" y1="18" x2="11" y2="14"/><line x1="17" y1="17" x2="14" y2="13"/></svg>',
      star: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' 
    };
    presetIcon.innerHTML = icons[val] || icons.hierarchical;
  }

  const modeSel = document.getElementById('globalViewModeSelect');
  const modeIcon = document.getElementById('icon-globalViewModeSelect');
  if (modeSel && modeIcon) {
    const val = modeSel.value || 'no-audit';
    const icons = {
      'no-audit': '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>',
      'keys-only': '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3L19 4"/><path d="M15 4l4 4"/><path d="M17 6l2 2"/></svg>',
      'all-columns': '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>'
    };
    modeIcon.innerHTML = icons[val] || icons['no-audit'];
  }
}


// ============================================================================
// 🛠️ DATABASE ENGINEERING & AUDIT SUITE (Linter, Diff, Mock Data)
// ============================================================================

let currentAuditTab = 'linter';
let currentLintResults = null;
let currentDiffResult = null;
let currentMockResult = null;
let diffMigrationMode = 'forward'; // 'forward' or 'rollback'

function switchAuditTab(tabId) {
  currentAuditTab = tabId;
  ['linter', 'diff', 'mock'].forEach(function(t) {
    const btn = document.getElementById('auditTab' + t.charAt(0).toUpperCase() + t.slice(1));
    const panel = document.getElementById('panel-audit-' + t);
    if (btn) btn.classList.toggle('active', t === tabId);
    if (panel) panel.style.display = (t === tabId) ? 'block' : 'none';
  });
  if (tabId === 'diff') {
    populateDiffSelectors();
  }
}

// ------------------------- 1. SCHEMA LINTER -------------------------

async function runSchemaLint() {
  const isRTL = currentLang === 'ar';
  try {
    showToast(isRTL ? '⏳ جاري فحص الجودة المعمارية للمخطط...' : '⏳ Running schema architecture audit...');
    
    let schema = currentDiagramSchema();
    if (!schema.tablesData || Object.keys(schema.tablesData).length === 0) {
      schema = { tablesData: tablesData, fkList: fkList };
    }
    if (!schema.tablesData || Object.keys(schema.tablesData).length === 0) {
      showToast(isRTL ? '⚠️ لا توجد جداول لفحصها في المخطط' : '⚠️ No tables found to audit');
      return;
    }

    const payload = {
      tablesData: schema.tablesData,
      fkList: schema.fkList || [],
      dialect: (document.getElementById('dbExportDialect') ? document.getElementById('dbExportDialect').value : 'oracle') || 'oracle'
    };

    const res = await fetch('/api/audit/lint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(function() { return {}; });
      throw new Error(err.detail || 'Lint audit failed');
    }

    const data = await res.json();
    currentLintResults = data;

    // Update Hero stats
    const circle = document.getElementById('linterScoreCircle');
    const badge = document.getElementById('linterGradeBadge');
    const title = document.getElementById('linterRatingTitle');
    const remBtn = document.getElementById('btnDownloadRemediation');

    if (circle) {
      circle.textContent = data.score;
      circle.className = 'score-circle ' + (data.score >= 90 ? 'score-excellent' : data.score >= 75 ? 'score-good' : data.score >= 50 ? 'score-warning' : 'score-critical');
    }
    if (badge) {
      badge.textContent = data.grade;
      badge.className = 'score-grade-badge ' + (data.score >= 90 ? 'grade-excellent' : data.score >= 75 ? 'grade-good' : data.score >= 50 ? 'grade-warning' : 'grade-critical');
    }
    if (title) {
      title.textContent = (isRTL ? data.rating_ar : data.rating_en) || (isRTL ? ('التقييم المعماري: ' + data.grade + ' (' + data.score + '/100)') : ('Architecture Rating: ' + data.grade + ' (' + data.score + '/100)'));
    }

    // Counters
    const counts = data.counts || {};
    const countAll = document.getElementById('countAll');
    const countCrit = document.getElementById('countCritical');
    const countWarn = document.getElementById('countWarning');
    const countInfo = document.getElementById('countInfo');
    if (countAll) countAll.textContent = counts.total || 0;
    if (countCrit) countCrit.textContent = counts.critical || 0;
    if (countWarn) countWarn.textContent = counts.warning || 0;
    if (countInfo) countInfo.textContent = counts.info || 0;

    // Show/hide download remediation button
    if (remBtn) {
      remBtn.style.display = (data.findings && data.findings.length > 0) ? 'inline-flex' : 'none';
    }

    // Render findings
    renderLinterFindings(data.findings, 'all');

    showToast(isRTL ? ('✅ اكتمل الفحص: التقييم ' + data.grade + ' (' + data.score + '/100)') : ('✅ Audit complete: Grade ' + data.grade + ' (' + data.score + '/100)'));
  } catch (err) {
    console.error('runSchemaLint error:', err);
    showToast('❌ ' + err.message);
  }
}

function filterLinterFindings(filter, chipEl) {
  if (chipEl) {
    const parent = chipEl.closest('.filter-chips');
    if (parent) {
      parent.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
      chipEl.classList.add('active');
    }
  }
  if (!currentLintResults || !currentLintResults.findings) return;
  const filtered = filter === 'all' 
    ? currentLintResults.findings 
    : currentLintResults.findings.filter(function(f) { return f.severity === filter; });
  renderLinterFindings(filtered, filter);
}

function renderLinterFindings(findings, filter) {
  const container = document.getElementById('linterFindingsList');
  if (!container) return;
  const isRTL = currentLang === 'ar';

  if (!findings || findings.length === 0) {
    const isClean = currentLintResults && currentLintResults.findings && currentLintResults.findings.length === 0;
    if (isClean) {
      container.innerHTML = 
        '<div class="audit-empty-state clean-state">' +
          '<div style="font-size:36px; margin-bottom:8px;">🎉</div>' +
          '<div style="font-weight:700; font-size:15px; color:#10b981;">' + (isRTL ? 'المخطط مثالي ومتوافق مع كافة أفضل الممارسات المعمارية!' : 'Flawless Architecture! No schema anti-patterns detected.') + '</div>' +
          '<div style="color:var(--text-muted); font-size:12px; margin-top:4px;">' + (isRTL ? 'لا توجد جداول بلا مفاتيح أساسية أو أخطاء في تطابق المفاتيح الخارجية أو جداول معزولة.' : 'All primary keys, foreign key data types, and index constraints are valid.') + '</div>' +
        '</div>';
    } else {
      container.innerHTML = 
        '<div class="audit-empty-state">' +
          '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>' +
          '<div>' + (isRTL ? 'لا توجد ملاحظات ضمن هذا التصنيف' : 'No findings in this category') + '</div>' +
        '</div>';
    }
    return;
  }

  const ruleNames = {
    MISSING_PK: isRTL ? 'غياب المفتاح الأساسي' : 'Missing Primary Key',
    FK_DATATYPE_MISMATCH: isRTL ? 'عدم تطابق نوع المفتاح الخارجي' : 'FK Data Type Mismatch',
    ORPHAN_TABLE: isRTL ? 'جدول معزول بلا علاقات' : 'Orphan / Isolated Table',
    MISSING_FK_INDEX: isRTL ? 'غياب الفهرس على حقل FK' : 'Missing Index on FK Column',
    RESERVED_WORD_NAME: isRTL ? 'استخدام كلمة محجوزة' : 'Reserved Word Identifier',
    NON_STANDARD_NAMING: isRTL ? 'تسمية غير قياسية' : 'Non-Standard Naming'
  };

  let html = '';
  findings.forEach(function(f, idx) {
    const sevClass = f.severity ? f.severity.toLowerCase() : 'info';
    const ruleLabel = ruleNames[f.ruleId] || f.ruleId;
    const titleText = isRTL ? (f.title_ar || ruleLabel) : (f.title_en || ruleLabel);
    const descText = isRTL ? (f.description_ar || '') : (f.description_en || '');
    const tableBadge = f.table ? ('<span class="finding-table-tag">📋 ' + f.table + '</span>') : '';
    const colBadge = f.column ? ('<span class="finding-col-tag">🔹 ' + f.column + '</span>') : '';

    html += 
      '<div class="finding-card sev-' + sevClass + '">' +
        '<div class="finding-header">' +
          '<div class="finding-header-left">' +
            '<span class="finding-badge badge-' + sevClass + '">' + f.severity + '</span>' +
            '<span class="finding-rule-name">' + titleText + '</span>' +
            tableBadge +
            colBadge +
          '</div>' +
          '<div class="finding-actions">' +
            (f.table ? ('<button class="btn-tool btn-sm" onclick="focusLintTable(\\\'' + f.table + '\\\')" title="' + (isRTL ? 'التركيز على الجدول في المخطط' : 'Focus on canvas') + '">' +
              '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
              '<span>' + (isRTL ? 'عرض على الكانفاس' : 'Canvas Focus') + '</span>' +
            '</button>') : '') +
            (f.fixSql ? ('<button class="btn-tool btn-sm primary" onclick="copyLintFix(' + idx + ')" title="' + (isRTL ? 'نسخ كود المعالجة التلقائي' : 'Copy SQL fix') + '">' +
              '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>' +
              '<span>' + (isRTL ? 'نسخ حل SQL' : 'Copy SQL Fix') + '</span>' +
            '</button>') : '') +
          '</div>' +
        '</div>' +
        (descText ? ('<div class="finding-message">' + descText + '</div>') : '') +
        (f.impact ? ('<div class="finding-recommendation">⚠️ <b>' + (isRTL ? 'التأثير المعماري:' : 'Impact:') + '</b> ' + f.impact + '</div>') : '') +
        (f.fixSql ? ('<div class="finding-sql-box"><pre><code>' + f.fixSql + '</code></pre></div>') : '') +
      '</div>';
  });

  container.innerHTML = html;
}

function focusLintTable(tableName) {
  if (!tableName) return;
  const isRTL = currentLang === 'ar';
  switchView('canvas');

  if (tablesData[tableName] && !selectedTables.has(tableName)) {
    selectedTables.add(tableName);
    renderAll();
  }

  setTimeout(function() {
    const pos = tablePositions[tableName];
    if (pos) {
      panX = window.innerWidth / 2 - (pos.x + 140) * zoom;
      panY = window.innerHeight / 2 - (pos.y + 100) * zoom;
      applyTransform();
    }
    const el = document.getElementById('table-' + tableName);
    if (el) {
      el.classList.add('audit-pulse', 'is-highlighted');
      setTimeout(function() {
        el.classList.remove('audit-pulse', 'is-highlighted');
      }, 3500);
    }
    showToast(isRTL ? ('🎯 تم التركيز على جدول ' + tableName) : ('🎯 Focused on ' + tableName));
  }, 100);
}

function copyLintFix(findingIndex) {
  if (!currentLintResults || !currentLintResults.findings) return;
  const finding = currentLintResults.findings[findingIndex];
  if (!finding || !finding.fixSql) return;
  navigator.clipboard.writeText(finding.fixSql).then(function() {
    showToast(currentLang === 'ar' ? '📋 تم نسخ كود المعالجة SQL' : '📋 SQL remediation fix copied');
  }).catch(function(err) {
    showToast('❌ Failed to copy: ' + err.message);
  });
}

function downloadRemediationScript() {
  if (!currentLintResults || !currentLintResults.remediationScript) return;
  const blob = new Blob([currentLintResults.remediationScript], { type: 'text/sql;charset=utf-8;' });
  downloadQuickBlob(blob, 'schema_remediation_' + Date.now() + '.sql');
  showToast(currentLang === 'ar' ? '💾 تم تنزيل سكربت المعالجة' : '💾 Remediation script downloaded');
}

// ------------------------- 2. SCHEMA DIFF & MIGRATION -------------------------

function populateDiffSelectors() {
  const srcSel = document.getElementById('diffSourceSelect');
  const tgtSel = document.getElementById('diffTargetSelect');
  if (!srcSel || !tgtSel) return;

  const isRTL = currentLang === 'ar';
  const prevSrc = srcSel.value;
  const prevTgt = tgtSel.value;

  srcSel.innerHTML = '';
  tgtSel.innerHTML = '';

  // 1. Current Active Diagram
  const optCurrent = document.createElement('option');
  optCurrent.value = 'current';
  optCurrent.textContent = isRTL ? '⭐ المخطط الحالي النشط (Active Diagram)' : '⭐ Active Diagram Canvas';
  srcSel.appendChild(optCurrent.cloneNode(true));
  tgtSel.appendChild(optCurrent.cloneNode(true));

  // 2. Open Workspace Tabs
  if (Array.isArray(workspaces) && workspaces.length > 0) {
    workspaces.forEach(function(w, idx) {
      const isCurrent = w.id === activeWorkspaceId;
      const opt = document.createElement('option');
      opt.value = 'ws_' + w.id;
      const count = (w.tablesData ? Object.keys(w.tablesData).length : 0);
      opt.textContent = '📑 ' + (w.name || ('Tab ' + (idx + 1))) + ' [' + count + ' ' + (isRTL ? 'جدول' : 'tables') + ']' + (isCurrent ? (isRTL ? ' (الحالي)' : ' (Active)') : '');
      srcSel.appendChild(opt.cloneNode(true));
      tgtSel.appendChild(opt.cloneNode(true));
    });
  }

  // 3. Live connected DB if present
  if (window._liveSchema && Object.keys(window._liveSchema).length > 0) {
    const optLive = document.createElement('option');
    optLive.value = 'live_db';
    optLive.textContent = isRTL ? '🗄️ قاعدة البيانات المتصلة (Live DB Cache)' : '🗄️ Connected Database Schema';
    srcSel.appendChild(optLive.cloneNode(true));
    tgtSel.appendChild(optLive.cloneNode(true));
  }

  if (prevSrc && srcSel.querySelector('option[value="' + prevSrc + '"]')) {
    srcSel.value = prevSrc;
  } else if (workspaces.length > 1) {
    srcSel.value = 'ws_' + workspaces[0].id;
  } else {
    srcSel.value = 'current';
  }

  if (prevTgt && tgtSel.querySelector('option[value="' + prevTgt + '"]')) {
    tgtSel.value = prevTgt;
  } else if (workspaces.length > 1 && workspaces[1]) {
    tgtSel.value = 'ws_' + workspaces[1].id;
  } else {
    tgtSel.value = 'current';
  }
}

function resolveSchemaFromOption(val) {
  if (val === 'current') {
    const dia = currentDiagramSchema();
    if (dia.tablesData && Object.keys(dia.tablesData).length > 0) return dia;
    return { tablesData: tablesData, fkList: fkList };
  }
  if (val && val.startsWith('ws_')) {
    const wsId = val.replace('ws_', '');
    const w = workspaces.find(function(x) { return String(x.id) === String(wsId); });
    if (w) {
      if (w.id === activeWorkspaceId) {
        return { tablesData: tablesData, fkList: fkList };
      }
      return { tablesData: w.tablesData || {}, fkList: w.fkList || [] };
    }
  }
  if (val === 'live_db' && window._liveSchema) {
    return { tablesData: window._liveSchema, fkList: window._liveFkList || [] };
  }
  return { tablesData: tablesData, fkList: fkList };
}

function handleDiffSourceChange() {}
function handleDiffTargetChange() {}

async function runSchemaDiff() {
  const isRTL = currentLang === 'ar';
  try {
    const srcVal = document.getElementById('diffSourceSelect').value;
    const tgtVal = document.getElementById('diffTargetSelect').value;
    const dialect = document.getElementById('diffDialectSelect').value || 'oracle';

    if (srcVal === tgtVal) {
      showToast(isRTL ? '⚠️ يرجى اختيار مخطّطين مختلفين للمقارنة' : '⚠️ Please select two different schemas to compare');
      return;
    }

    const srcSchema = resolveSchemaFromOption(srcVal);
    const tgtSchema = resolveSchemaFromOption(tgtVal);

    if (!srcSchema.tablesData || Object.keys(srcSchema.tablesData).length === 0) {
      showToast(isRTL ? '⚠️ المخطط الأساسي فارغ ولا يحتوي على جداول' : '⚠️ Source schema is empty');
      return;
    }
    if (!tgtSchema.tablesData || Object.keys(tgtSchema.tablesData).length === 0) {
      showToast(isRTL ? '⚠️ المخطط المستهدف فارغ ولا يحتوي على جداول' : '⚠️ Target schema is empty');
      return;
    }

    showToast(isRTL ? '⏳ جاري حساب الفروقات وتوليد سكربتات الترقية...' : '⏳ Comparing schemas & generating migration...');

    const res = await fetch('/api/audit/diff', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sourceSchema: srcSchema,
        targetSchema: tgtSchema,
        dialect: dialect
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(function() { return {}; });
      throw new Error(err.detail || 'Diff comparison failed');
    }

    const data = await res.json();
    currentDiffResult = data;
    diffMigrationMode = 'forward';

    renderDiffResults(data);
    showToast(isRTL ? '✅ تم اكتشاف الفروقات وتوليد سكربت الترقية' : '✅ Diff complete & migration script generated');
  } catch (err) {
    console.error('runSchemaDiff error:', err);
    showToast('❌ ' + err.message);
  }
}

function renderDiffResults(data) {
  const resultsContainer = document.getElementById('diffResultsContainer');
  if (!resultsContainer) return;
  resultsContainer.style.display = 'block';

  const isRTL = currentLang === 'ar';
  const s = data.summary || {};
  const diff = data.diff || {};

  // Summary Chips
  const chipsContainer = document.getElementById('diffSummaryChips');
  if (chipsContainer) {
    chipsContainer.innerHTML = 
      '<span class="diff-chip added">+ ' + (s.addedTablesCount || 0) + ' ' + (isRTL ? 'جداول مضافة' : 'tables added') + '</span>' +
      '<span class="diff-chip dropped">- ' + (s.droppedTablesCount || 0) + ' ' + (isRTL ? 'جداول محذوفة' : 'tables dropped') + '</span>' +
      '<span class="diff-chip modified">~ ' + (s.modifiedTablesCount || 0) + ' ' + (isRTL ? 'جداول معدلة' : 'tables modified') + '</span>' +
      '<span class="diff-chip added">+ ' + (s.addedFksCount || 0) + ' ' + (isRTL ? 'علاقات مضافة' : 'FKs added') + '</span>' +
      '<span class="diff-chip dropped">- ' + (s.droppedFksCount || 0) + ' ' + (isRTL ? 'علاقات محذوفة' : 'FKs dropped') + '</span>';
  }

  // Visual Tree
  const treeContainer = document.getElementById('diffTreeContainer');
  if (treeContainer) {
    const hasChanges = data.hasChanges || (s.totalChanges && s.totalChanges > 0);
    if (!hasChanges) {
      treeContainer.innerHTML = 
        '<div class="audit-empty-state clean-state">' +
          '<div style="font-size:30px; margin-bottom:6px;">✨</div>' +
          '<div style="font-weight:700; color:#10b981;">' + (isRTL ? 'المخططان متطابقان تماماً ولا توجد أية فروقات!' : 'Both schemas are completely identical. No changes detected.') + '</div>' +
        '</div>';
    } else {
      let treeHtml = '';

      // Added Tables (diff.addedTables is array of table names)
      (diff.addedTables || []).forEach(function(tblName) {
        treeHtml += 
          '<div class="diff-table-card border-added">' +
            '<div class="diff-table-head head-added">' +
              '<span>+ <b>CREATE TABLE</b> ' + tblName + '</span>' +
              '<span class="badge-added">New Table</span>' +
            '</div>' +
          '</div>';
      });

      // Dropped Tables (diff.droppedTables is array of table names)
      (diff.droppedTables || []).forEach(function(tblName) {
        treeHtml += 
          '<div class="diff-table-card border-dropped">' +
            '<div class="diff-table-head head-dropped">' +
              '<span>- <b>DROP TABLE</b> ' + tblName + '</span>' +
              '<span class="badge-dropped">Dropped</span>' +
            '</div>' +
          '</div>';
      });

      // Modified Tables
      const modifiedTables = diff.modifiedTables || {};
      for (const tblName in modifiedTables) {
        const mod = modifiedTables[tblName];
        treeHtml += 
          '<div class="diff-table-card border-modified">' +
            '<div class="diff-table-head head-modified">' +
              '<span>~ <b>ALTER TABLE</b> ' + tblName + '</span>' +
              '<span class="badge-modified">Modified</span>' +
            '</div>' +
            '<div class="diff-table-body">' +
              (mod.addedColumns || []).map(function(c) {
                return '<div class="diff-change-item added">+ ADD COLUMN ' + c.name + ' <span class="col-type-muted">' + c.type + '</span></div>';
              }).join('') +
              (mod.droppedColumns || []).map(function(c) {
                return '<div class="diff-change-item dropped">- DROP COLUMN ' + (c.name || c) + '</div>';
              }).join('') +
              (mod.alteredColumns || []).map(function(c) {
                const changesStr = (c.changes || []).map(function(ch) { return ch.property + ': ' + ch.old + ' ➔ <b>' + ch.new + '</b>'; }).join(', ');
                return '<div class="diff-change-item modified">~ ALTER COLUMN ' + c.name + ' (' + changesStr + ')</div>';
              }).join('') +
              (mod.pkChanged ? ('<div class="diff-change-item modified">~ PK CHANGED: [' + (mod.oldPks || []).join(', ') + '] ➔ [<b>' + (mod.newPks || []).join(', ') + '</b>]</div>') : '') +
            '</div>' +
          '</div>';
      }

      // Added FKs
      (diff.addedFks || []).forEach(function(f) {
        treeHtml += 
          '<div class="diff-table-card border-added">' +
            '<div class="diff-table-head head-added">' +
              '<span>+ <b>ADD CONSTRAINT</b> ' + (f.name || 'FK') + '</span>' +
              '<span class="badge-added">Foreign Key</span>' +
            '</div>' +
            '<div class="diff-table-body">' +
              '<div class="diff-change-item added">' + (f.child || '') + ' (' + (f.cols || f.childCol || '') + ') ➔ ' + (f.parent || '') + ' (' + (f.parentCol || '') + ')</div>' +
            '</div>' +
          '</div>';
      });

      // Dropped FKs
      (diff.droppedFks || []).forEach(function(f) {
        treeHtml += 
          '<div class="diff-table-card border-dropped">' +
            '<div class="diff-table-head head-dropped">' +
              '<span>- <b>DROP CONSTRAINT</b> ' + (f.name || 'FK') + '</span>' +
              '<span class="badge-dropped">Dropped FK</span>' +
            '</div>' +
          '</div>';
      });

      treeContainer.innerHTML = treeHtml;
    }
  }

  updateMigrationEditor();
}

function updateMigrationEditor() {
  const editor = document.getElementById('migrationCodeEditor');
  const title = document.getElementById('migrationTitleText');
  const btn = document.getElementById('btnToggleRollback');
  const isRTL = currentLang === 'ar';

  if (!currentDiffResult) return;

  if (diffMigrationMode === 'forward') {
    if (title) title.textContent = isRTL ? 'سكربت الترقية التزايدي (Forward Migration Script)' : 'Incremental Forward Migration (ALTER TABLE)';
    if (editor) editor.value = currentDiffResult.migrationScript || '-- No forward changes required';
    if (btn) btn.innerHTML = isRTL ? '<span>تبديل لسكربت التراجع (Rollback)</span>' : '<span>Switch to Rollback Script</span>';
  } else {
    if (title) title.textContent = isRTL ? 'سكربت التراجع المعكوس (Rollback Migration Script)' : 'Rollback Down-Migration Script';
    if (editor) editor.value = currentDiffResult.rollbackScript || '-- No rollback script available';
    if (btn) btn.innerHTML = isRTL ? '<span>تبديل لسكربت الترقية (Forward)</span>' : '<span>Switch to Forward Script</span>';
  }
}

function toggleMigrationScriptType() {
  diffMigrationMode = (diffMigrationMode === 'forward') ? 'rollback' : 'forward';
  updateMigrationEditor();
}

function copyMigrationScript() {
  const editor = document.getElementById('migrationCodeEditor');
  if (!editor || !editor.value) return;
  navigator.clipboard.writeText(editor.value).then(function() {
    showToast(currentLang === 'ar' ? '📋 تم نسخ سكربت الترقية' : '📋 Migration script copied');
  });
}

function downloadMigrationScript() {
  const editor = document.getElementById('migrationCodeEditor');
  if (!editor || !editor.value) return;
  const dialect = (document.getElementById('diffDialectSelect') ? document.getElementById('diffDialectSelect').value : 'sql') || 'sql';
  const prefix = diffMigrationMode === 'forward' ? 'migration_up' : 'migration_down';
  const blob = new Blob([editor.value], { type: 'text/sql;charset=utf-8;' });
  downloadQuickBlob(blob, prefix + '_' + dialect + '_' + Date.now() + '.sql');
  showToast(currentLang === 'ar' ? '💾 تم تنزيل السكربت' : '💾 Script downloaded');
}

// ------------------------- 3. SMART MOCK DATA GENERATOR -------------------------

async function runGenerateMockData() {
  const isRTL = currentLang === 'ar';
  try {
    const scope = document.getElementById('mockScopeSelect').value;
    const count = parseInt(document.getElementById('mockCountSelect').value, 10) || 10;
    const dialect = document.getElementById('mockDialectSelect').value || 'oracle';
    const locale = document.getElementById('mockLangSelect').value || 'ar';

    let schema = currentDiagramSchema();
    if (!schema.tablesData || Object.keys(schema.tablesData).length === 0) {
      schema = { tablesData: tablesData, fkList: fkList };
    }
    if (!schema.tablesData || Object.keys(schema.tablesData).length === 0) {
      showToast(isRTL ? '⚠️ لا توجد جداول لتوليد البيانات لها' : '⚠️ No tables found');
      return;
    }

    let finalTables = schema.tablesData;
    let finalFks = schema.fkList || [];
    if (scope === 'selected' && typeof selectedTables !== 'undefined' && selectedTables.size > 0) {
      finalTables = {};
      selectedTables.forEach(function(t) {
        if (schema.tablesData[t]) finalTables[t] = schema.tablesData[t];
      });
      finalFks = (schema.fkList || []).filter(function(f) {
        return finalTables[f.child] && finalTables[f.parent];
      });
    }

    showToast(isRTL ? '⏳ جاري ترتيب الجداول طوبولوجياً وتوليد البيانات المتناسقة...' : '⏳ Generating realistic mock data with FK integrity...');

    const res = await fetch('/api/audit/mock-data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tablesData: finalTables,
        fkList: finalFks,
        rowCount: count,
        dialect: dialect,
        lang: locale
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(function() { return {}; });
      throw new Error(err.detail || 'Mock data generation failed');
    }

    const data = await res.json();
    currentMockResult = data;

    const container = document.getElementById('mockDataResultsContainer');
    if (container) container.style.display = 'block';

    const editor = document.getElementById('mockCodeEditor');
    if (editor) editor.value = data.script || '';

    const summary = document.getElementById('mockSummaryText');
    if (summary) {
      summary.textContent = isRTL 
        ? ('✅ تم توليد ' + data.totalRows + ' سجل عبر ' + data.tableCount + ' جدول بترتيب تكامل المفاتيح الخارجية (DAG)')
        : ('✅ Generated ' + data.totalRows + ' rows across ' + data.tableCount + ' tables in topological DAG order');
    }

    showToast(isRTL ? ('✅ تم توليد ' + data.totalRows + ' سجل بنجاح') : ('✅ Generated ' + data.totalRows + ' mock rows'));
  } catch (err) {
    console.error('runGenerateMockData error:', err);
    showToast('❌ ' + err.message);
  }
}

function copyMockDataScript() {
  const editor = document.getElementById('mockCodeEditor');
  if (!editor || !editor.value) return;
  navigator.clipboard.writeText(editor.value).then(function() {
    showToast(currentLang === 'ar' ? '📋 تم نسخ بيانات INSERT التجريبية' : '📋 Mock INSERT statements copied');
  });
}

function downloadMockDataScript() {
  const editor = document.getElementById('mockCodeEditor');
  if (!editor || !editor.value) return;
  const dialect = (document.getElementById('mockDialectSelect') ? document.getElementById('mockDialectSelect').value : 'sql') || 'sql';
  const blob = new Blob([editor.value], { type: 'text/sql;charset=utf-8;' });
  downloadQuickBlob(blob, 'mock_data_' + dialect + '_' + Date.now() + '.sql');
  showToast(currentLang === 'ar' ? '💾 تم تنزيل سكربت البيانات التجريبية' : '💾 Mock data script downloaded');
}
