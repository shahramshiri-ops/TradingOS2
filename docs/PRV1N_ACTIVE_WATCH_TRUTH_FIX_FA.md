# PRV1N — Active Watch Truth + Canonical Lifecycle Store Patch

این patch مشکل باقی‌ماندن پیام قدیمی «کندل کامل کافی بعد از trigger وجود ندارد» را هدف می‌گیرد.

## مشکل
در نسخه‌های قبلی، post-refresh lifecycle update فایل‌های post-refresh را می‌ساخت، اما canonical SOT02 lifecycle store را که مراحل بعدی و پنل از آن مصرف می‌کردند، الزاماً به‌روزرسانی نمی‌کرد. نتیجه این بود که پنل می‌توانست reason قدیمی را نشان بدهد، حتی وقتی cache تازه‌تر وجود داشت.

## اصلاح
- lifecycle updater حالا cache را recursive می‌خواند؛
- active lifecycleها را دوباره طبقه‌بندی می‌کند؛
- اگر post-trigger bar وجود داشته باشد، اجازه نمی‌دهد reason قدیمی `no_completed_post_trigger_bars_available_yet` باقی بماند؛
- از canonical lifecycle store backup می‌گیرد؛
- canonical `state/sot02_current/shadow_lifecycle_state_store.json` را به‌روزرسانی می‌کند تا candidate detection و dashboard همان حقیقت را مصرف کنند.

## مرزها
این patch سیگنال، خرید/فروش، ورود/خروج، target/stop، broker، execution، PnL، validation verdict یا production readiness اضافه نمی‌کند.
