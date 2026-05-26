---
title: "Как Proshli находит твои матчи: технически"
description: "Embedding резюме, cosine similarity, semantic ranking — что под капотом."
publishDate: 2026-05-26
tags: ["engineering", "ai"]
---

Когда ты загружаешь резюме, на сервере происходит следующее:

1. **Извлечение текста.** PDF/DOCX парсится через `pypdf` / `python-docx`. Если резюме на скане — fallback на OCR (Tesseract).
2. **Embedding.** Текст резюме (до 8000 символов) идёт в embedding-модель — получаем 1024-мерный вектор. Сейчас используем Voyage-3.
3. **Хранение.** Вектор кладётся в Postgres с pgvector. На каждую новую вакансию тоже считаем embedding (заголовок + первые 500 символов описания).
4. **Match-score.** При показе списка вакансий считаем cosine similarity между твоим резюме и каждой вакансией: `1 - (resume <=> vacancy)`. Шкала 0-100%.

Дальше — пороги: 80+ показываем как high-match, 60-80 как relevant, ниже — без бейджа. Можно фильтровать.

Весь пайплайн работает на одном VPS с Postgres + pgvector. Никаких Pinecone, Weaviate или других managed vector DB — для наших объёмов (десятки тысяч вакансий) pgvector хватает с запасом, а latency на cosine similarity — единицы миллисекунд.
