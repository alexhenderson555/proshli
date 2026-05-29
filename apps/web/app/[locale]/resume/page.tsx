"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, Plus, Sparkles, AlertCircle, Save, Loader2, RefreshCw } from "lucide-react";

import { Link } from "@/i18n/navigation";
import { Button, Input, Textarea } from "@/components/ui";
import { FadeIn, Stagger } from "@proshli/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { ResumeVersionOut } from "@/lib/types";
import { AppShell } from "@/components/app-shell";

export default function ResumePage() {
  const t = useTranslations("settings"); // Reuse some translations or hardcode
  const [token, setTokenValue] = useState<string | null>(null);
  
  const [versions, setVersions] = useState<ResumeVersionOut[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  
  const [name, setName] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [experience, setExperience] = useState("");
  const [education, setEducation] = useState("");
  const [skills, setSkills] = useState("");
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<{ summary: string; suggestions: string[] } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const tId = setTimeout(() => setTokenValue(getToken()), 0);
    return () => clearTimeout(tId);
  }, []);

  const loadVersions = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.resumeVersions(token);
      setVersions(data);
      if (data.length > 0 && !activeId && data[0]) {
        selectVersion(data[0]);
      }
    } catch {
      setError("Failed to load resumes");
    } finally {
      setLoading(false);
    }
  }, [token, activeId]);

  useEffect(() => {
    if (!token) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadVersions();
  }, [token, loadVersions]);

  function selectVersion(v: ResumeVersionOut) {
    setActiveId(v.id);
    setName(v.name);
    setTargetRole(v.target_role);
    setExperience((v.content.experience as string) || "");
    setEducation((v.content.education as string) || "");
    setSkills((v.content.skills as string) || "");
    setAiResult(null);
  }

  function createNew() {
    setActiveId(null);
    setName("Новое резюме");
    setTargetRole("");
    setExperience("");
    setEducation("");
    setSkills("");
    setAiResult(null);
  }

  async function handleSave() {
    if (!token) return;
    setSaving(true);
    try {
      const v = await api.createResumeVersion(token, {
        name,
        target_role: targetRole,
        content: {
          experience,
          education,
          skills
        }
      });
      await loadVersions();
      setActiveId(v.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error saving");
    } finally {
      setSaving(false);
    }
  }

  async function handleAiImprove() {
    if (!token || !activeId) return;
    setAiLoading(true);
    setError("");
    try {
      const res = await api.improveResumeVersion(token, activeId, {
        target_role: targetRole,
        focus: "Улучшить описания опыта и сделать их более продающими."
      });
      setAiResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI Error");
    } finally {
      setAiLoading(false);
    }
  }

  if (!token && !loading) {
    return (
      <div className="relative min-h-screen flex items-center justify-center">
        <div className="absolute inset-0 bg-canvas z-0" />
        <div className="relative z-10 mx-auto flex max-w-md flex-col items-center gap-4 rounded-lg border border-border/80 bg-surface/80 backdrop-blur-md p-8 text-center shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
          <AlertCircle className="h-10 w-10 text-accent" />
          <h2 className="text-[18px] font-[600] text-white">Требуется авторизация</h2>
          <Link href="/auth">
            <Button className="px-6 py-2 bg-accent hover:bg-accent-hover text-white rounded">
              {t("ctaLogin")}
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <AppShell activeTab="resume" role="seeker">
      <div className="flex h-[calc(100vh-80px)] gap-6 overflow-hidden">
        
        {/* Left Sidebar: Versions */}
        <div className="w-[280px] flex-shrink-0 flex flex-col gap-4 border-r border-border/60 pr-6 overflow-y-auto">
          <div className="flex items-center justify-between pb-2">
            <h2 className="text-[14px] font-[600] uppercase tracking-[0.08em] text-text-tertiary">
              Мои резюме
            </h2>
            <button onClick={createNew} className="p-1.5 rounded bg-surface/50 hover:bg-surface border border-border/60 text-white transition-colors">
              <Plus className="h-4 w-4" />
            </button>
          </div>
          
          <div className="flex flex-col gap-2">
            {versions.map(v => (
              <button
                key={v.id}
                onClick={() => selectVersion(v)}
                className={`flex flex-col items-start p-3 rounded-lg border transition-all text-left ${
                  activeId === v.id 
                    ? 'bg-accent/10 border-accent/30 shadow-[0_0_12px_rgba(99,102,241,0.1)]' 
                    : 'bg-surface/30 border-border/60 hover:bg-surface/50'
                }`}
              >
                <div className="text-[14px] font-[510] text-white truncate w-full">{v.name}</div>
                <div className="text-[12px] text-text-tertiary truncate w-full mt-0.5">
                  {v.target_role || "Без позиции"}
                </div>
              </button>
            ))}
            {versions.length === 0 && !loading && (
              <div className="text-[13px] text-text-tertiary p-4 text-center border border-dashed border-border/60 rounded-lg">
                Нет сохраненных резюме. Нажмите + чтобы создать.
              </div>
            )}
          </div>
        </div>

        {/* Main Editor */}
        <div className="flex-1 overflow-y-auto pb-20 pr-4">
          <FadeIn y={10} duration={0.3} immediate>
            <div className="flex items-center justify-between mb-6 border-b border-border/60 pb-5">
              <div className="flex flex-col gap-1.5">
                <h1 className="text-[26px] font-[600] leading-tight tracking-[-0.02em] text-white flex items-center gap-2">
                  <FileText className="h-6 w-6 text-accent" /> Редактор
                </h1>
                <p className="text-[13px] text-text-secondary">
                  Создавайте разные версии резюме под разные вакансии.
                </p>
              </div>
              <div className="flex items-center gap-3">
                {activeId && (
                  <Button 
                    onClick={handleAiImprove} 
                    disabled={aiLoading}
                    className="bg-accent hover:bg-accent-hover text-white flex items-center gap-2 px-5"
                  >
                    {aiLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    AI Улучшение
                  </Button>
                )}
                <Button 
                  onClick={handleSave} 
                  disabled={saving}
                  className="bg-white text-black hover:bg-white/90 flex items-center gap-2 px-5"
                >
                  {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {activeId ? "Создать копию" : "Сохранить"}
                </Button>
              </div>
            </div>

            {error && (
              <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[13px]">
                {error}
              </div>
            )}

            {aiResult && (
              <Stagger step={0.1} immediate className="mb-8 p-6 rounded-lg border border-accent/30 bg-accent/5 backdrop-blur-sm relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-accent" />
                <h3 className="text-[14px] font-[600] text-accent flex items-center gap-2 mb-3">
                  <Sparkles className="h-4 w-4" /> AI Анализ
                </h3>
                <p className="text-[14px] leading-[1.6] text-white mb-4">
                  {aiResult.summary}
                </p>
                <div className="flex flex-col gap-2">
                  <h4 className="text-[12px] font-[600] uppercase tracking-[0.05em] text-text-tertiary">Предложения:</h4>
                  <ul className="flex flex-col gap-2">
                    {aiResult.suggestions.map((s, i) => (
                      <li key={i} className="text-[13px] text-text-secondary flex items-start gap-2">
                        <span className="text-accent mt-0.5">•</span> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              </Stagger>
            )}

            <Stagger step={0.05} immediate className="flex flex-col gap-6 max-w-3xl">
              <div className="grid grid-cols-2 gap-6">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                    Название версии
                  </label>
                  <Input 
                    value={name} 
                    onChange={setName} 
                    placeholder="Например: Frontend Developer (React)" 
                    className="bg-surface/50 border-border/80 text-[14px] h-11" 
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                    Целевая должность
                  </label>
                  <Input 
                    value={targetRole} 
                    onChange={setTargetRole} 
                    placeholder="Frontend Engineer" 
                    className="bg-surface/50 border-border/80 text-[14px] h-11" 
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                  Опыт работы
                </label>
                <Textarea 
                  value={experience} 
                  onChange={setExperience} 
                  placeholder="Опишите ваш опыт работы..." 
                  rows={8} 
                  className="bg-surface/50 border-border/80 text-[14px] leading-[1.6]" 
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                  Навыки (Skills)
                </label>
                <Textarea 
                  value={skills} 
                  onChange={setSkills} 
                  placeholder="React, TypeScript, Next.js..." 
                  rows={3} 
                  className="bg-surface/50 border-border/80 text-[14px]" 
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                  Образование
                </label>
                <Textarea 
                  value={education} 
                  onChange={setEducation} 
                  placeholder="Университет, специальность, год выпуска..." 
                  rows={3} 
                  className="bg-surface/50 border-border/80 text-[14px]" 
                />
              </div>
            </Stagger>
          </FadeIn>
        </div>
      </div>
    </AppShell>
  );
}
