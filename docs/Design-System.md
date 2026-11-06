# Design System — Company AI Assistant

> **وصف الملف:** نظام التصميم الكامل للمشروع — الألوان (Modern Slate Blue)، الـTypography، الـSpacing، وتعليمات بناء المكونات المتكررة. أي component بيتكرر استخدامه في أكتر من مكان لازم يتعمل له Component مستقل ويتسحب من هنا، مش يتكرر تعريفه.

---

## 1. Color Tokens

### Brand / Primary

| Token | Light | Dark | الاستخدام |
|---|---|---|---|
| `primary` | `#2563A3` | `#4D8FD6` | أزرار أساسية، links، active states، الـlogo |
| `primary-hover` | `#1E5188` | `#6BA3E0` | hover على عناصر الـprimary |
| `primary-subtle` | `#E8F0F9` | `#1A2A3D` | خلفية خفيفة للعناصر الـselected (زي المحادثة النشطة في الـsidebar) |

### Backgrounds

| Token | Light | Dark | الاستخدام |
|---|---|---|---|
| `bg-page` | `#F7F8FA` | `#13181F` | خلفية الصفحة الأساسية |
| `bg-surface` | `#FFFFFF` | `#1B212B` | كروت، الشات bubble، المودالز |
| `bg-sidebar` | `#EEF1F5` | `#10151C` | خلفية الـsidebar |
| `bg-input` | `#FFFFFF` | `#1F2630` | خلفية حقول الإدخال |

### Text

| Token | Light | Dark | الاستخدام |
|---|---|---|---|
| `text-primary` | `#13181F` | `#F2F4F7` | نصوص أساسية |
| `text-secondary` | `#5B6472` | `#9AA4B2` | نصوص ثانوية، timestamps، placeholders |
| `text-on-primary` | `#FFFFFF` | `#FFFFFF` | نص فوق خلفية الـprimary (زرار أساسي) |

### Borders & Dividers

| Token | Light | Dark | الاستخدام |
|---|---|---|---|
| `border` | `#E2E6EB` | `#262D38` | فواصل، حدود الكروت |
| `border-strong` | `#C9CFD8` | `#38424F` | حدود عناصر تفاعلية (input focus state الأساسي قبل الـring) |

### Status Colors

| Token | Light | Dark | الاستخدام |
|---|---|---|---|
| `success` | `#1E8E5A` | `#3FBE82` | عمليات ناجحة (رفع مستند تم، موافقة HITL) |
| `success-subtle` | `#E6F4ED` | `#163626` | خلفية رسائل النجاح |
| `warning` | `#B07D1E` | `#D9A23E` | تنبيهات (حد الـrequests قرّب يخلص) |
| `warning-subtle` | `#FBF1DF` | `#352A14` | خلفية رسائل التحذير |
| `error` | `#C0392B` | `#E35B4C` | أخطاء، رفض الصلاحية، فشل العملية |
| `error-subtle` | `#FBEAE8` | `#3A1917` | خلفية رسائل الخطأ |

### Interaction

| Token | Light | Dark | الاستخدام |
|---|---|---|---|
| `focus-ring` | `#2563A3` بشفافية 30% | نفسه | الـfocus state على كل العناصر القابلة للتفاعل |

**ملاحظة إلزامية:** كل زوج نص/خلفية لازم يحقق WCAG AA contrast ratio (4.5:1 على الأقل للنص العادي). `text-secondary` على `bg-sidebar` في Dark Mode لازم يتفحص خصوصاً لأنه الأضعف تبايناً.

---

## 2. Typography

| Token | القيمة | الاستخدام |
|---|---|---|
| `font-family-base` | Inter (English) / IBM Plex Sans Arabic (عربي) | كل النصوص — يتبدّل تلقائي حسب لغة next-intl |
| `text-xs` | 12px / line-height 16px | timestamps، labels صغيرة |
| `text-sm` | 14px / line-height 20px | نص المحادثة الثانوي، أوصاف |
| `text-base` | 16px / line-height 24px | نص المحادثة الأساسي، أزرار |
| `text-lg` | 18px / line-height 28px | عناوين الأقسام الفرعية |
| `text-xl` | 22px / line-height 30px | عناوين الصفحات (Chat title، Admin page titles) |
| `font-weight-regular` | 400 | النص العادي |
| `font-weight-medium` | 500 | أزرار، labels |
| `font-weight-semibold` | 600 | عناوين |

---

## 3. Spacing & Radius

| Token | القيمة |
|---|---|
| `space-1` → `space-8` | 4px, 8px, 12px, 16px, 20px, 24px, 32px, 48px (نظام مضاعفات الـ4px) |
| `radius-sm` | 6px — أزرار صغيرة، badges |
| `radius-md` | 10px — كروت، inputs، الشات bubble |
| `radius-lg` | 16px — مودالز، الـsidebar panel |
| `radius-full` | 999px — avatars، pills |

---

## 4. Components (إلزامي التحويل لـComponent عند التكرار)

**القاعدة:** أي عنصر UI بيظهر في أكتر من feature واحد (Button، Dropdown، Sidebar، Modal، Avatar) لازم يتعرّف مرة واحدة بس في `components/ui/` أو `components/shared/` (حسب `Tech-Stack.md`)، وكل الـfeatures تسحب منه. ممنوع نسخ نفس الـJSX في أكتر من feature.

### Button
- **Variants:** `primary` (خلفية `primary`)، `secondary` (خلفية `bg-surface` + حدود `border`)، `ghost` (بدون خلفية، للأيقونات)، `danger` (خلفية `error`)
- **Sizes:** `sm` (32px height)، `md` (40px height، الافتراضي)، `lg` (48px height)
- **States إلزامية:** default، hover، focus (`focus-ring`)، disabled (opacity 50%)، loading (spinner بدل النص)

### Dropdown (Model Selector وغيره)
- خلفية `bg-surface`، حدود `border`، radius `radius-md`
- كل خيار له hover state بخلفية `primary-subtle`
- العنصر المختار له علامة ✓ أو تمييز بصري واضح
- **إلزامي:** لو القائمة فاضية (مفيش موديلات متاحة حالياً) → empty state برسالة واضحة، مش قائمة فاضية بدون تفسير

### Sidebar
- خلفية `bg-sidebar`، عرض ثابت (مثال: 280px) مع إمكانية الطي على الموبايل
- كل عنصر محادثة: عنوان مختصر + hover state، والمحادثة النشطة حالياً عليها `primary-subtle`
- زرار "+ New Chat" ثابت فوق القائمة دايماً

### Chat Message Bubble
- رسالة الموظف: محاذاة يمين (أو شمال حسب اللغة)، خلفية `primary`، نص `text-on-primary`
- رسالة الـAI: محاذاة عكسية، خلفية `bg-surface`، حدود `border`
- **streaming state:** مؤشر كتابة متحرك (3 نقاط) لحد ما الرد يبدأ يظهر
- **مصدر الإجابة:** يظهر أسفل رسالة الـAI كـbadge صغير (اسم المستند) قابل للضغط

### Permission Denied Message (حالة خاصة بالمشروع)
- خلفية `error-subtle`، نص `error`، أيقونة قفل
- نص واضح يسمي السبب (مطابق لقرار UX في الـPRD) — مش رسالة خطأ عامة

### Modal
- خلفية `bg-surface`، radius `radius-lg`، overlay غامق شفاف خلف المودال
- يُستخدم في: تأكيد HITL approval، عرض كريدنشيالز الموظف الجديد مرة واحدة

### Avatar
- دائرة (`radius-full`)، لون خلفية مشتق من اسم المستخدم، أول حرفين من الاسم

---

## 5. Dark Mode

كل الـtokens فوق معرّفة بقيمتين (Light/Dark). التبديل بين الوضعين عن طريق `prefers-color-scheme` أو toggle يدوي يتخزن في `localStorage` (تفضيل العرض بس، مش بيانات حساسة).
