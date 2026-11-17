import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

/**
 * أدوات الـnavigation بتاعة next-intl — الـusePathname بيرجّع المسار من غير
 * بادئة الـlocale، والـuseRouter بيحط البادئة الصح حسب الـlocale المطلوب.
 */
export const { Link, usePathname, useRouter } = createNavigation(routing);
