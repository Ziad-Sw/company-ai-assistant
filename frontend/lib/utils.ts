/** cn() helper — Tech-Stack.md قسم 9 (lib/utils.ts). */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
