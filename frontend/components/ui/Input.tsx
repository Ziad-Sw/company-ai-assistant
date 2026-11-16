/**
 * حقل إدخال من الـDesign-System: خلفية bg-input، حدود border، radius-md،
 * والـfocus بحد primary مع ring خفيف.
 */
export function Input({ className = "", ...rest }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-10 w-full rounded-[var(--radius-md)] border border-border-strong bg-input px-3 text-base text-foreground
        placeholder:text-muted focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30 focus-visible:border-primary
        disabled:opacity-50 ${className}`}
      {...rest}
    />
  );
}
