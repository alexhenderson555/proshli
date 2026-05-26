import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** clsx + tailwind-merge: safe className join with conflicting-utility dedup. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
