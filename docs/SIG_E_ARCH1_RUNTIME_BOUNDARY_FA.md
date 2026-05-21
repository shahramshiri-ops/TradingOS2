# SIG-E-ARCH1 — مرز runtime و ممنوعیت‌های اجرایی

این سند مرزهای اجرای فعلی را برای هدف معماری E ثبت می‌کند.

## مجاز در این مرحله

```text
architecture contract
schema/contract definition
static validation
research shadow
forward observation/evidence logging
manual-review architecture design
```

## غیرمجاز در این مرحله

```text
live signal
buy/sell recommendation
entry zone
stop level
target level
position size
broker order
execution routing
auto execution
self-learning deployment
live profitability claim
```

## تغییر معنی NOT_SIGNAL در معماری E

در معماری قبلی، پروژه فقط display-only بود و عبارت `NOT_SIGNAL` کافی بود.

در معماری E، هدف آینده ممکن است ساخت `signal_candidate` باشد؛ بنابراین مرز دقیق‌تر این است:

```text
CURRENT_RUNTIME_NOT_SIGNAL
SIGNAL_CANDIDATE_LAYER_NOT_YET_ACTIVE
TRADE_PLAN_DRAFT_LAYER_NOT_YET_ACTIVE
NO_AUTO_EXECUTION_ALWAYS
MANUAL_REVIEW_REQUIRED_ALWAYS
```

یعنی سیستم فعلی هنوز signal ندارد، اما مسیر آینده برای signal candidate تحت gateهای جداگانه تعریف شده است.

## قانون manual review

هر trade plan آینده، حتی اگر ساخته شود، باید این ویژگی‌ها را داشته باشد:

```text
manual_review_required = true
non_execution_statement = true
broker_execution_authorized = false
automatic_position_opening_authorized = false
```

## قانون ارتقا

هیچ memory، shadow candidate، setup، trigger یا quality vector فعلی حق ندارد بدون gate جداگانه به trade plan یا signal تبدیل شود.
