"use client";

import { useEffect, useState, useTransition } from "react";
import { Command } from "cmdk";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import {
  Search,
  LayoutGrid,
  FileText,
  CreditCard,
  Settings,
  Sun,
  Moon,
  Zap,
  Monitor,
  LogOut,
  ArrowRight,
  Briefcase,
} from "lucide-react";

import { Dialog, DialogContent } from "@proshli/ui-v2";
import { api } from "@/lib/api";
import type { Vacancy } from "@/lib/types";
import { usePathname } from "@/i18n/navigation";

export function CommandMenu() {
  const t = useTranslations("commandMenu");
  const router = useRouter();
  const pathname = usePathname();
  const { setTheme } = useTheme();
  
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [isPending, startTransition] = useTransition();

  // Toggle command menu with Cmd+K or Ctrl+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Debounced search for vacancies
  useEffect(() => {
    if (!search.trim()) {
      setVacancies([]);
      return;
    }
    
    const handler = setTimeout(() => {
      startTransition(async () => {
        try {
          // Pass the query as stack filter to search title/description
          const results = await api.vacancies({ stack: search });
          setVacancies(results.slice(0, 5));
        } catch {
          // Degrading silently
        }
      });
    }, 200);

    return () => clearTimeout(handler);
  }, [search]);

  const runCommand = (command: () => void) => {
    command();
    setOpen(false);
  };

  const navigateTo = (path: string) => {
    runCommand(() => {
      router.push(path);
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-xl p-0 overflow-hidden bg-surface border border-border rounded-lg shadow-lg">
        <Command label="Global Command Menu" className="flex flex-col h-full max-h-[450px]">
          <div className="flex items-center border-b border-border px-3.5" cmdk-input-wrapper="">
            <Search className="h-4 w-4 shrink-0 text-text-tertiary" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder={t("placeholder")}
              className="flex h-12 w-full rounded-md bg-transparent py-3 pl-2.5 pr-2 text-[14px] text-text-primary placeholder:text-text-tertiary outline-none border-0"
            />
          </div>
          <Command.List className="overflow-y-auto p-2 scrollbar-none">
            <Command.Empty className="py-6 text-center text-[13px] text-text-tertiary">
              {isPending ? "Поиск..." : t("empty")}
            </Command.Empty>

            {vacancies.length > 0 && (
              <Command.Group heading={t("vacancies")} className="px-2 py-1.5 text-[11px] font-mono tracking-wider uppercase text-text-tertiary">
                {vacancies.map((v) => (
                  <Command.Item
                    key={v.id}
                    value={`vacancy-${v.id}-${v.title}`}
                    onSelect={() => navigateTo(`/vacancies/${v.id}`)}
                    className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
                  >
                    <Briefcase className="h-4 w-4 shrink-0 text-text-tertiary" />
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="truncate font-medium">{v.title}</span>
                      <span className="truncate text-[11px] text-text-tertiary">{v.company} · {v.location}</span>
                    </div>
                    <ArrowRight className="h-3 w-3 shrink-0 opacity-0 aria-selected:opacity-100 text-accent transition-opacity" />
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            <Command.Group heading={t("pages")} className="px-2 py-1.5 mt-2 text-[11px] font-mono tracking-wider uppercase text-text-tertiary">
              <Command.Item
                value="page-vacancies"
                onSelect={() => navigateTo("/vacancies")}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <Search className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("pageVacancies")}</span>
              </Command.Item>
              <Command.Item
                value="page-dashboard"
                onSelect={() => navigateTo("/dashboard")}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <LayoutGrid className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("pageDashboard")}</span>
              </Command.Item>
              <Command.Item
                value="page-resume"
                onSelect={() => navigateTo("/resume")}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <FileText className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("pageResume")}</span>
              </Command.Item>
              <Command.Item
                value="page-billing"
                onSelect={() => navigateTo("/billing")}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <CreditCard className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("pageBilling")}</span>
              </Command.Item>
              <Command.Item
                value="page-settings"
                onSelect={() => navigateTo("/settings")}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <Settings className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("pageSettings")}</span>
              </Command.Item>
            </Command.Group>

            <Command.Group heading={t("actions")} className="px-2 py-1.5 mt-2 text-[11px] font-mono tracking-wider uppercase text-text-tertiary border-t border-border/40">
              <Command.Item
                value="theme-light"
                onSelect={() => runCommand(() => setTheme("light"))}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <Sun className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("actionThemeLight")}</span>
              </Command.Item>
              <Command.Item
                value="theme-dark"
                onSelect={() => runCommand(() => setTheme("dark"))}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <Moon className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("actionThemeDark")}</span>
              </Command.Item>
              <Command.Item
                value="theme-oled"
                onSelect={() => runCommand(() => setTheme("oled"))}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <Zap className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("actionThemeOled")}</span>
              </Command.Item>
              <Command.Item
                value="theme-system"
                onSelect={() => runCommand(() => setTheme("system"))}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <Monitor className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("actionThemeSystem")}</span>
              </Command.Item>
              <Command.Item
                value="action-logout"
                onSelect={() => runCommand(async () => {
                  await api.logout();
                  window.localStorage.removeItem("proshli_web_token");
                  window.localStorage.removeItem("jobskout_web_token");
                  window.dispatchEvent(new Event("storage"));
                  router.push("/auth?mode=login");
                })}
                className="flex items-center gap-2 px-2.5 py-2.5 rounded-md text-[13px] text-text-secondary aria-selected:bg-elevated aria-selected:text-text-primary cursor-pointer select-none transition-colors"
              >
                <LogOut className="h-4 w-4 shrink-0 text-text-tertiary" />
                <span>{t("actionLogout")}</span>
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
