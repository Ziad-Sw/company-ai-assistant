# Demo Accounts — Company AI Assistant

> **وصف الملف:** حسابات تجريبية جاهزة (seeded في Supabase وقت إعداد Phase 0) لتجربة الأدوار الثلاثة. دي بيانات وهمية بالكامل (ملهاش علاقة بأي نظام إيميل حقيقي) — مفيش مشكلة ترفع على GitHub، على عكس ملف `.env` اللي فيه الـAPI keys الحقيقية.

| Role | Email | Password | يشوف إيه |
|---|---|---|---|
| **Admin** | `admin@reelestate.demo` | `Demo@2026!` | كل الـcategories + Document Management + Add Employee |
| **Sales** | `sales@reelestate.demo` | `Demo@2026!` | `property_listings`, `payment_policies`, `company_info_support` |
| **HR** | `hr@reelestate.demo` | `Demo@2026!` | `company_info_support` فقط |

## ملاحظات

- الحسابات دي بتتعمل seed مباشرة في جدول `profiles` + Supabase Auth وقت الإعداد الأولي (Phase 0)، مش عن طريق واجهة الـAdmin — عشان تبقى جاهزة من أول تشغيل للمشروع.
- أي حساب إضافي (للتجربة أو للـdemo video) بيتضاف بعد كده من واجهة **Add Employee** (موضحة في `PRD.md`، قسم 10.6) باستخدام حساب الـAdmin ده.
- الدومين `@reelestate.demo` دومين وهمي بالكامل — مش بيستقبل إيميلات حقيقية، ومتعمدين استخدامه بدل `gmail.com` عشان الواقعية (موظف شركة حقيقية بيكون عنده إيميل بدومين الشركة).
