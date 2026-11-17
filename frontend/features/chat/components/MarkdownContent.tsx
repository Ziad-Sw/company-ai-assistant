"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

/**
 * عارض الـmarkdown لردود الـAI — رد الموديل untrusted (LLM05)، والسلوك
 * الافتراضي لـreact-markdown آمن بالتصميم: بيحوّل الـmarkdown لعناصر React
 * من غير innerHTML، الـHTML الخام بيتم تجاهله، والـhrefs الخطيرة
 * (javascript: وغيرها) بتتشال. الصور ممنوعة عمداً — مافيش حاجة تفتش
 * URLs من متصفح الموظف (tracking/SSRF من جهة العميل).
 */

const HEADING = "my-2 text-base font-semibold text-foreground";

const MARKDOWN_COMPONENTS: Components = {
  p: ({ children }) => <p className="my-2 break-words leading-6 text-foreground">{children}</p>,
  h1: ({ children }) => <h3 className={HEADING}>{children}</h3>,
  h2: ({ children }) => <h3 className={HEADING}>{children}</h3>,
  h3: ({ children }) => <h4 className={HEADING}>{children}</h4>,
  h4: ({ children }) => <h5 className={HEADING}>{children}</h5>,
  h5: ({ children }) => <h6 className={HEADING}>{children}</h6>,
  h6: ({ children }) => <h6 className={HEADING}>{children}</h6>,
  ul: ({ children }) => (
    <ul className="my-2 list-disc space-y-1 ps-5 marker:text-muted">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 list-decimal space-y-1 ps-5 marker:text-muted">{children}</ol>
  ),
  li: ({ children }) => <li className="break-words leading-6 text-foreground">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline underline-offset-2 hover:text-primary-hover"
    >
      {children}
    </a>
  ),
  code: ({ children, className }) => (
    <code
      className={cn(
        "rounded-[var(--radius-sm)] bg-input px-1 py-0.5 font-mono text-sm text-foreground",
        className
      )}
    >
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre
      className="my-2 overflow-x-auto rounded-[var(--radius-md)] bg-input p-3
        [&>code]:bg-transparent [&>code]:p-0"
    >
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-s-2 border-border ps-3 text-muted">{children}</blockquote>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border bg-page px-2 py-1 text-start font-medium">{children}</th>
  ),
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
  hr: () => <hr className="my-3 border-border" />,
  img: () => null,
};

/** فقاعات الرد — أول وآخر block بدون هوامش عشان الـpadding بتاع الفقاعة يبقى كافي. */
export function MarkdownContent({ content }: { content: string }) {
  return (
    <div
      className="text-base text-foreground [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
