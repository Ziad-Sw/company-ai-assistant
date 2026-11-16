/**
 * 404 عام لأي مسار مش متطابق (مثلاً /login من غير locale) — Next بيرندره
 * مباشرة من غير الـlayout عشان كده بيجمع الستايل هنا بنفسه.
 */
import "./globals.css";

export default function GlobalNotFound() {
  return (
    <html lang="en">
      <body style={{ fontFamily: "sans-serif", display: "grid", placeItems: "center", minHeight: "100vh" }}>
        <p>Page not found — الصفحة مش موجودة.</p>
      </body>
    </html>
  );
}
