"use client";

import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export type DropdownOption = {
  value: string;
  label: string;
  description?: string;
};

type DropdownProps = {
  options: DropdownOption[];
  value: string | null;
  onChange: (value: string) => void;
  /** النص المعروض على الزرار لما مفيش اختيار (أو خليه يعرض الـlabel المختار). */
  placeholder: string;
  /** empty state إلزامي لما القائمة فاضية (Design-System: Dropdown) — النص جاي من الـfeature. */
  emptyLabel: string;
  ariaLabel: string;
  disabled?: boolean;
  className?: string;
};

type ListboxCoords = {
  position: "fixed";
  left: number;
  width: number;
  top?: number;
  bottom?: number;
};

/**
 * dropdown من الـDesign-System: bg-surface + border + radius-md، hover على
 * الخيارات بـprimary-subtle، والعنصر المختار عليه علامة ✓. بيفتح/يتقفل بالنقر،
 * والكيبورد (أسهم/Enter/Escape) مدعوم، وبيتقفل مع النقر بره أو Blur.
 *
 * القايمة list بتتكشط لو حطيناها absolute جوه حاويات overflow (الجدول/
 * المودال) — فبنموضعها fixed بإحداثيات مقيسة من الزرار نفسه، وبنختار
 * الاتجاه (تحت فوق مايتقفلوش) وبنعيد القياس مع الـscroll/resize.
 */
export function Dropdown({
  options,
  value,
  onChange,
  placeholder,
  emptyLabel,
  ariaLabel,
  disabled = false,
  className = "",
}: DropdownProps) {
  const listboxId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [listCoords, setListCoords] = useState<ListboxCoords | null>(null);

  const selected = options.find((option) => option.value === value) ?? null;

  function measureCoords(): ListboxCoords {
    const rect = triggerRef.current!.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    // بنفتح تحت افتراضياً، وفوق بس لو المساحة تحت مش كفاية والفوق أحسن منها.
    const openUpward = spaceBelow < 180 && spaceAbove > spaceBelow;
    return openUpward
      ? { position: "fixed", left: rect.left, width: rect.width, bottom: window.innerHeight - rect.top }
      : { position: "fixed", left: rect.left, width: rect.width, top: rect.bottom };
  }

  useEffect(() => {
    if (!open) return;
    function reposition() {
      setListCoords(measureCoords());
    }
    // scroll capture: الـscroll جوه حاويات مبيعملش bubble — بنسمع على أ stage الـdocument.
    document.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    return () => {
      document.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  function openListbox() {
    if (options.length === 0) return;
    setActiveIndex(Math.max(0, options.findIndex((option) => option.value === value)));
    setListCoords(measureCoords());
    setOpen(true);
  }

  function commit(index: number) {
    const option = options[index];
    if (!option) return;
    onChange(option.value);
    setOpen(false);
  }

  function handleKeyDown(event: React.KeyboardEvent) {
    if (!open) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === "Enter") {
        event.preventDefault();
        openListbox();
      }
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(options.length - 1, index + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(0, index - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      commit(activeIndex);
    }
  }

  return (
    <div ref={rootRef} className={`relative ${className}`} onKeyDown={handleKeyDown}>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => (open ? setOpen(false) : openListbox())}
        className="flex h-9 w-full items-center justify-between gap-2 rounded-[var(--radius-md)] border border-border bg-surface px-3 text-sm text-foreground
          hover:border-border-strong focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30
          disabled:pointer-events-none disabled:opacity-50"
      >
        <span className="truncate">{selected ? selected.label : placeholder}</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("size-4 shrink-0 text-muted transition-transform", open && "rotate-180")}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && listCoords ? (
        <ul
          id={listboxId}
          role="listbox"
          aria-label={ariaLabel}
          aria-activedescendant={`${listboxId}-${activeIndex}`}
          style={listCoords}
          className="absolute z-50 max-h-64 overflow-y-auto rounded-[var(--radius-md)] border border-border bg-surface p-1 shadow-lg"
        >
          {options.length === 0 ? (
            <li className="px-3 py-2 text-sm text-muted">{emptyLabel}</li>
          ) : null}
          {options.map((option, index) => (
            <li
              key={option.value}
              id={`${listboxId}-${index}`}
              role="option"
              aria-selected={option.value === value}
              onMouseEnter={() => setActiveIndex(index)}
            >
              <button
                type="button"
                tabIndex={-1}
                onClick={() => commit(index)}
                className={cn(
                  "flex w-full items-start justify-between gap-2 rounded-[var(--radius-sm)] px-3 py-2 text-start text-sm",
                  index === activeIndex ? "bg-primary-subtle" : "",
                  option.value === value ? "font-medium text-foreground" : "text-foreground"
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate">{option.label}</span>
                  {option.description ? (
                    <span className="block truncate text-xs text-muted">{option.description}</span>
                  ) : null}
                </span>
                {option.value === value ? (
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    className="mt-0.5 size-4 shrink-0 text-primary"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="m5 13 4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
