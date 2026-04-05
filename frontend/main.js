const API_URL = "http://127.0.0.1:8000";
const tokenKey = "jobskout_token";

const logEl = document.getElementById("log");
const aiResultEl = document.getElementById("aiResult");
const vacanciesEl = document.getElementById("vacancies");
const digestPreviewEl = document.getElementById("digestPreview");
const resumeResultEl = document.getElementById("resumeResult");
const tgLinkCodeResultEl = document.getElementById("tgLinkCodeResult");
const myVacanciesEl = document.getElementById("myVacancies");
const myVacancyAnalyticsEl = document.getElementById("myVacancyAnalytics");
const myVacancyActionsEl = document.getElementById("myVacancyActions");
const myVacPageInfoEl = document.getElementById("myVacPageInfo");
const editVacancyIdEl = document.getElementById("editVacancyId");
const editVacancyTitleEl = document.getElementById("editVacancyTitle");
const editVacancyLocationEl = document.getElementById("editVacancyLocation");
const editVacancyApplicationsEl = document.getElementById("editVacancyApplications");
const editVacancyDescriptionEl = document.getElementById("editVacancyDescription");
let myVacCurrentPage = 1;
const myVacPageSize = 10;

function setVacancyEditor(item) {
  editVacancyIdEl.value = item.id ?? "";
  editVacancyTitleEl.value = item.title ?? "";
  editVacancyLocationEl.value = item.location ?? "";
  editVacancyApplicationsEl.value = item.applications_count ?? 0;
  editVacancyDescriptionEl.value = item.description ?? "";
}

function getToken() {
  return localStorage.getItem(tokenKey);
}

function setToken(token) {
  localStorage.setItem(tokenKey, token);
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function log(message, payload = null) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  logEl.textContent = `${line}\n${payload ? JSON.stringify(payload, null, 2) : ""}\n\n${logEl.textContent}`;
}

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...authHeaders(),
    ...(options.headers || {}),
  };
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
}

document.getElementById("registerBtn").addEventListener("click", async () => {
  const payload = {
    email: document.getElementById("regEmail").value,
    password: document.getElementById("regPassword").value,
    role: document.getElementById("regRole").value,
  };
  try {
    const data = await request("/auth/register", { method: "POST", body: JSON.stringify(payload) });
    setToken(data.access_token);
    log("Пользователь зарегистрирован, токен сохранен.");
  } catch (err) {
    log(`Ошибка регистрации: ${err.message}`);
  }
});

document.getElementById("loginBtn").addEventListener("click", async () => {
  const payload = {
    email: document.getElementById("loginEmail").value,
    password: document.getElementById("loginPassword").value,
  };
  try {
    const data = await request("/auth/login", { method: "POST", body: JSON.stringify(payload) });
    setToken(data.access_token);
    log("Вход выполнен, токен сохранен.");
  } catch (err) {
    log(`Ошибка входа: ${err.message}`);
  }
});

document.getElementById("tgLinkCodeBtn").addEventListener("click", async () => {
  try {
    const data = await request("/auth/telegram/link-code", { method: "POST" });
    tgLinkCodeResultEl.textContent = `Код: ${data.code}\nДействует до: ${data.expires_at}`;
    log("Сгенерирован код привязки Telegram.", data);
  } catch (err) {
    log(`Ошибка генерации Telegram кода: ${err.message}`);
  }
});

document.getElementById("aiBtn").addEventListener("click", async () => {
  const payload = { message: document.getElementById("aiMessage").value };
  try {
    const data = await request("/ai/chat", { method: "POST", body: JSON.stringify(payload) });
    aiResultEl.textContent = JSON.stringify(data, null, 2);
    log("AI запрос обработан.", data);
  } catch (err) {
    log(`Ошибка AI: ${err.message}`);
  }
});

document.getElementById("digestBtn").addEventListener("click", async () => {
  const payload = {
    frequency: document.getElementById("digestFrequency").value,
    via_telegram: document.getElementById("digestTg").checked,
    via_email: document.getElementById("digestEmail").checked,
    telegram_chat_id: document.getElementById("tgChatId").value || null,
  };
  try {
    const data = await request("/digest/preferences", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    log("Настройки дайджеста сохранены.", data);
  } catch (err) {
    log(`Ошибка настроек дайджеста: ${err.message}`);
  }
});

document.getElementById("searchBtn").addEventListener("click", async () => {
  const location = document.getElementById("filterLocation").value;
  const stack = document.getElementById("filterStack").value;
  const params = new URLSearchParams();
  if (location) params.append("location", location);
  if (stack) params.append("stack", stack);
  try {
    const data = await request(`/vacancies?${params.toString()}`);
    vacanciesEl.innerHTML = "";
    data.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `${item.title} | ${item.company} | ${item.location} | ${item.salary_from || "-"}-${item.salary_to || "-"} ${item.currency}`;
      vacanciesEl.appendChild(li);
    });
    log(`Найдено вакансий: ${data.length}`);
  } catch (err) {
    log(`Ошибка поиска: ${err.message}`);
  }
});

document.getElementById("ingestBtn").addEventListener("click", async () => {
  const source = document.getElementById("ingestSource").value;
  try {
    const data = await request(`/ingest/${source}`, { method: "POST" });
    log("Ingestion завершен.", data);
  } catch (err) {
    log(`Ошибка ingestion: ${err.message}`);
  }
});

document.getElementById("schedulerBtn").addEventListener("click", async () => {
  const frequency = document.getElementById("schedulerFrequency").value;
  try {
    const data = await request(`/admin/run-scheduler?frequency=${encodeURIComponent(frequency)}`, {
      method: "POST",
    });
    log("Scheduler выполнен.", data);
  } catch (err) {
    log(`Ошибка scheduler: ${err.message}`);
  }
});

document.getElementById("digestPreviewBtn").addEventListener("click", async () => {
  try {
    const data = await request("/digest/preview");
    const lines = data.items.map(
      (item, idx) =>
        `${idx + 1}. ${item.title} | ${item.company} | ${item.location}\n   Причина: ${item.score_reason}`
    );
    digestPreviewEl.textContent = `Частота: ${data.frequency}\nКаналы: ${data.channels.join(", ")}\n\n${lines.join("\n\n")}`;
    log("Digest preview получен.", { items: data.items.length });
  } catch (err) {
    log(`Ошибка digest preview: ${err.message}`);
  }
});

document.getElementById("resumeUploadBtn").addEventListener("click", async () => {
  const name = document.getElementById("resumeName").value.trim();
  const fileInput = document.getElementById("resumeFile");
  const file = fileInput.files && fileInput.files[0];
  if (!name || !file) {
    log("Для загрузки резюме укажи название и выбери файл.");
    return;
  }
  const form = new FormData();
  form.append("name", name);
  form.append("file", file);
  try {
    const data = await request("/resumes/upload", { method: "POST", body: form });
    resumeResultEl.textContent = JSON.stringify(data, null, 2);
    log("Резюме успешно загружено.", data);
  } catch (err) {
    log(`Ошибка загрузки резюме: ${err.message}`);
  }
});

document.getElementById("resumeVersionCreateBtn").addEventListener("click", async () => {
  const name = document.getElementById("resumeVersionName").value.trim();
  const target_role = document.getElementById("resumeVersionRole").value.trim();
  const contentRaw = document.getElementById("resumeVersionJson").value.trim();
  if (!name || !contentRaw) {
    log("Нужны name и JSON content для версии резюме.");
    return;
  }
  let content;
  try {
    content = JSON.parse(contentRaw);
  } catch (err) {
    log("Невалидный JSON в версии резюме.");
    return;
  }
  try {
    const data = await request("/resumes/versions", {
      method: "POST",
      body: JSON.stringify({ name, target_role, content }),
    });
    resumeResultEl.textContent = JSON.stringify(data, null, 2);
    log("Версия резюме создана.", data);
  } catch (err) {
    log(`Ошибка создания версии резюме: ${err.message}`);
  }
});

document.getElementById("saveSeekerProfileBtn").addEventListener("click", async () => {
  const payload = {
    full_name: document.getElementById("seekerFullName").value.trim(),
    target_role: document.getElementById("seekerTargetRole").value.trim(),
    location: document.getElementById("seekerLocation").value.trim(),
    about: document.getElementById("seekerAbout").value.trim(),
    skills: document
      .getElementById("seekerSkills")
      .value.split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };
  try {
    const data = await request("/profiles/seeker", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    log("Профиль соискателя сохранен.", data);
  } catch (err) {
    log(`Ошибка профиля соискателя: ${err.message}`);
  }
});

document.getElementById("saveEmployerProfileBtn").addEventListener("click", async () => {
  const payload = {
    company_name: document.getElementById("employerCompanyName").value.trim(),
    website: document.getElementById("employerWebsite").value.trim(),
    description: document.getElementById("employerDescription").value.trim(),
  };
  try {
    const data = await request("/profiles/employer", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    log("Профиль работодателя сохранен.", data);
  } catch (err) {
    log(`Ошибка профиля работодателя: ${err.message}`);
  }
});

async function loadMyVacancies() {
  const status = document.getElementById("myVacStatusFilter").value;
  const sortBy = document.getElementById("myVacSortBy").value;
  const order = document.getElementById("myVacSortOrder").value;
  const params = new URLSearchParams({
    status,
    sort_by: sortBy,
    order,
    page: String(myVacCurrentPage),
    page_size: String(myVacPageSize),
  });
  const paged = await request(`/vacancies/my/page?${params.toString()}`);
  const data = paged.items;
  myVacPageInfoEl.textContent = `page ${paged.page} / ${Math.max(1, Math.ceil(paged.total / paged.page_size))}`;
  myVacanciesEl.innerHTML = "";
  data.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.title} | ${item.company} | ${item.location} | ${
      item.is_active ? "active" : "archived"
    }`;
    const archiveBtn = document.createElement("button");
    archiveBtn.textContent = "Архив";
    archiveBtn.style.marginTop = "8px";
    archiveBtn.addEventListener("click", async () => {
      try {
        await request(`/vacancies/${item.id}/archive`, { method: "POST" });
        log("Вакансия архивирована.", { vacancyId: item.id });
        await loadMyVacancies();
      } catch (err) {
        log(`Ошибка архивации вакансии: ${err.message}`);
      }
    });
    const publishBtn = document.createElement("button");
    publishBtn.textContent = "Публиковать";
    publishBtn.style.marginTop = "8px";
    publishBtn.addEventListener("click", async () => {
      try {
        await request(`/vacancies/${item.id}/publish`, { method: "POST" });
        log("Вакансия опубликована.", { vacancyId: item.id });
        await loadMyVacancies();
      } catch (err) {
        log(`Ошибка публикации вакансии: ${err.message}`);
      }
    });
    const btn = document.createElement("button");
    btn.textContent = "Удалить";
    btn.style.marginTop = "8px";
    btn.addEventListener("click", async () => {
      try {
        await request(`/vacancies/${item.id}`, { method: "DELETE" });
        log("Вакансия удалена.", { vacancyId: item.id });
        await loadMyVacancies();
      } catch (err) {
        log(`Ошибка удаления вакансии: ${err.message}`);
      }
    });
    const editBtn = document.createElement("button");
    editBtn.textContent = "Редактировать";
    editBtn.style.marginTop = "8px";
    editBtn.addEventListener("click", () => {
      setVacancyEditor(item);
      log("Вакансия загружена в редактор.", { vacancyId: item.id });
    });
    li.appendChild(document.createElement("br"));
    li.appendChild(editBtn);
    li.appendChild(document.createElement("br"));
    li.appendChild(archiveBtn);
    li.appendChild(document.createElement("br"));
    li.appendChild(publishBtn);
    li.appendChild(document.createElement("br"));
    li.appendChild(btn);
    myVacanciesEl.appendChild(li);
  });
  log("Список моих вакансий обновлен.", {
    count: data.length,
    total: paged.total,
    page: paged.page,
  });
}

document.getElementById("createMyVacancyBtn").addEventListener("click", async () => {
  const payload = {
    source: "manual",
    external_id: `manual-ui-${Date.now()}`,
    title: document.getElementById("myVacTitle").value.trim(),
    company: document.getElementById("myVacCompany").value.trim() || "Unknown Company",
    location: document.getElementById("myVacLocation").value.trim() || "Unknown",
    employment_type: "full-time",
    experience_level: "middle",
    salary_from: null,
    salary_to: null,
    currency: "RUB",
    description: document.getElementById("myVacDescription").value.trim(),
    applications_count: 0,
  };
  if (!payload.title) {
    log("Для создания вакансии нужен title.");
    return;
  }
  try {
    const created = await request("/vacancies", { method: "POST", body: JSON.stringify(payload) });
    log("Моя вакансия создана.", created);
    await loadMyVacancies();
  } catch (err) {
    log(`Ошибка создания вакансии: ${err.message}`);
  }
});

document.getElementById("loadMyVacanciesBtn").addEventListener("click", async () => {
  try {
    myVacCurrentPage = 1;
    await loadMyVacancies();
  } catch (err) {
    log(`Ошибка загрузки моих вакансий: ${err.message}`);
  }
});

document.getElementById("myVacPrevPageBtn").addEventListener("click", async () => {
  if (myVacCurrentPage <= 1) return;
  myVacCurrentPage -= 1;
  try {
    await loadMyVacancies();
  } catch (err) {
    log(`Ошибка пагинации вакансий: ${err.message}`);
  }
});

document.getElementById("myVacNextPageBtn").addEventListener("click", async () => {
  myVacCurrentPage += 1;
  try {
    await loadMyVacancies();
  } catch (err) {
    myVacCurrentPage = Math.max(1, myVacCurrentPage - 1);
    log(`Ошибка пагинации вакансий: ${err.message}`);
  }
});

document.getElementById("myVacancyAnalyticsBtn").addEventListener("click", async () => {
  try {
    const data = await request("/vacancies/my/analytics");
    myVacancyAnalyticsEl.textContent = JSON.stringify(data, null, 2);
    log("Аналитика работодателя загружена.", data);
  } catch (err) {
    log(`Ошибка загрузки аналитики работодателя: ${err.message}`);
  }
});

document.getElementById("myVacancyActionsBtn").addEventListener("click", async () => {
  try {
    const action = document.getElementById("myVacActionFilter").value;
    const from = document.getElementById("myVacActionsFrom").value;
    const to = document.getElementById("myVacActionsTo").value;
    const params = new URLSearchParams({ limit: "30" });
    if (action) params.append("action", action);
    if (from) params.append("created_from", new Date(from).toISOString());
    if (to) params.append("created_to", new Date(to).toISOString());
    const data = await request(`/vacancies/my/actions?${params.toString()}`);
    myVacancyActionsEl.textContent = JSON.stringify(data, null, 2);
    log("Логи действий работодателя загружены.", { count: data.length });
  } catch (err) {
    log(`Ошибка загрузки action logs: ${err.message}`);
  }
});

document.getElementById("myVacancyActionsExportBtn").addEventListener("click", async () => {
  try {
    const action = document.getElementById("myVacActionFilter").value;
    const params = new URLSearchParams({ limit: "200" });
    if (action) params.append("action", action);
    const token = getToken();
    if (!token) {
      log("Нужен JWT токен для экспорта.");
      return;
    }
    const res = await fetch(`${API_URL}/vacancies/my/actions/export?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "employer-actions.csv";
    a.click();
    URL.revokeObjectURL(url);
    log("CSV действий выгружен.");
  } catch (err) {
    log(`Ошибка экспорта CSV: ${err.message}`);
  }
});

document.getElementById("saveVacancyEditBtn").addEventListener("click", async () => {
  const id = Number(editVacancyIdEl.value);
  if (!id) {
    log("Сначала выбери вакансию кнопкой Редактировать.");
    return;
  }
  const payload = {
    title: editVacancyTitleEl.value.trim(),
    location: editVacancyLocationEl.value.trim(),
    applications_count: Number(editVacancyApplicationsEl.value || "0"),
    description: editVacancyDescriptionEl.value.trim(),
  };
  try {
    const data = await request(`/vacancies/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    log("Изменения вакансии сохранены.", data);
    await loadMyVacancies();
  } catch (err) {
    log(`Ошибка сохранения вакансии: ${err.message}`);
  }
});
