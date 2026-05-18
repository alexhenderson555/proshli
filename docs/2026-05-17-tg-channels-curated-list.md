# Telegram Channels — Curated Source List

Curated public Telegram channels the ingestion pipeline scrapes for vacancies.
Channel handles are the bare `@name` (no `https://t.me/` prefix). Anything that
isn't strictly a job channel (general news, memes, dev advice) is excluded.

The Telethon connector reads this list at startup via `settings.tg_channels_list`
(comma-separated env var) — the YAML below is the source of truth for the env.

## Backend — Python

- @python_jobs_feed
- @djangojobs
- @python_jobs
- @async_python_jobs
- @ru_python_jobs

## Backend — Go / Rust / Java / Kotlin / .NET / Node

- @golang_jobs
- @golang_jobs_ru
- @rust_jobs_feed
- @java_jobs_feed
- @kotlinjobs
- @dotnet_jobs
- @node_js_jobs
- @php_jobs_feed

## Frontend / Web

- @frontend_jobs
- @frontend_jobs_ru
- @react_jobs
- @vuejs_jobs
- @typescript_jobs
- @web_jobs_ru

## Mobile — iOS / Android / Flutter / RN

- @ios_jobs_feed
- @android_jobs_feed
- @flutter_jobs_ru
- @react_native_jobs

## Data / ML / AI

- @ml_jobs_feed
- @data_science_jobs
- @data_engineer_jobs
- @ai_ml_jobs_ru
- @analyst_jobs

## DevOps / SRE / Cloud

- @devops_jobs_feed
- @sre_jobs_ru
- @k8s_jobs
- @cloud_jobs_ru
- @platform_jobs

## QA / Testing

- @qa_jobs_feed
- @automation_qa_jobs
- @qa_ru

## Design / UX / Product Design

- @uxui_jobs
- @design_jobs_ru
- @product_designer_jobs

## Product Management / Project Management

- @product_jobs_ru
- @pm_jobs_feed
- @project_jobs_ru

## Analytics — Product / Business / BI

- @analytics_jobs_ru
- @bi_jobs_feed
- @business_analyst_jobs

## Web3 / Crypto / Blockchain

- @web3_jobs_feed
- @crypto_jobs_ru
- @blockchain_jobs_feed
- @solidity_jobs

## Gamedev

- @gamedev_jobs_ru
- @unity_jobs
- @unreal_jobs

## Security / InfoSec

- @infosec_jobs_ru
- @security_jobs_feed
- @pentest_jobs

## Marketing / SMM / Content

- @marketing_jobs_ru
- @smm_jobs_ru
- @content_jobs_ru
- @copywriter_jobs_ru

## Sales / Support / Customer Success

- @sales_jobs_ru
- @support_jobs_ru
- @cs_jobs_ru

## HR / Recruitment

- @hr_jobs_ru
- @recruiter_jobs

## Relocation / Remote

- @relocation_jobs
- @remote_jobs_ru
- @work_abroad_it

## Niche & Mixed IT

- @it_jobs_ru
- @ru_it_jobs
- @jobs_in_it
- @it_remote_jobs
- @it_jobs_feed
- @ru_jobs_remote
- @startup_jobs_ru
- @c_plus_plus_jobs
- @embedded_jobs
- @scala_jobs
- @ruby_jobs_feed
- @1c_jobs_ru
- @data_jobs_ru
- @ml_engineers_jobs
- @llm_engineer_jobs
- @prompt_jobs
- @ai_research_jobs

## Notes

- The list is hand-curated; channels with <500 subscribers or last post >60 days
  are pruned at quarterly review.
- Heuristics in `apps/api/app/connectors/telegram_channels.py` (vacancy
  detection) drop non-vacancy posts (digests, polls, ads) automatically.
- Channels marked deprecated upstream (renamed/banned) are left in the list and
  silently skipped by Telethon's `entity not found` error path.
