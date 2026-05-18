# Curated Telegram Channels for IT Job Aggregation (RU/CIS)

Reference doc for the Proshli ingestion parser. Compiled 2026-05-17 from aggregator articles (huntflow.media, potok.io, vc.ru, geekjob.ru), TGStat / Telemetr.io listings, and category-specific roundups (skillfactory, habr, partnerkin).

## Caveats and operational notes

- **Landscape is volatile.** Channel handles, admins, and posting cadence change frequently. Roughly 15-25% of IT job channels mentioned in 2024-vintage roundups are now dead, migrated, or paid-only. Re-validate the list every 4-6 weeks via TGStat.
- **Subscriber counts are approximate.** Numbers below are pulled from TGStat / Telemetr.io / aggregator articles and may be 1-12 months stale. Rough ranges, not point estimates.
- **Public/parseable check needed at ingestion time.** Every channel listed is public at the time of compilation, but admins occasionally flip channels to private or restrict via `+joinchat`. The parser should soft-fail and log when a handle becomes inaccessible, not crash.
- **MTProto pool required for rate limiting.** Telegram's flood limits hit hard at scale (50+ channels polled every few minutes). Rotate through at least 3-5 MTProto sessions, back off on `FloodWaitError`, and cache `messages.getHistory` cursors so we resume from the last seen `message_id` instead of refetching.
- **Aggregator vs. original.** Many GeekJob / Inflow / NewHR channels are auto-cross-posted from their parent job-board database; expect substantial duplication across handles in the same network. Dedupe by canonicalized job title + company + city, or by the trailing apply URL when present.
- **Chats excluded.** Only one-way broadcast channels are listed. Group chats (`@*_chat`, `@*_jobs` that are groups) are skipped per the spec — the parser model assumes append-only message streams.
- **Language and audience.** Primary language is Russian; some relocation channels and English-speaking-companies channels post in English. The job model should not assume Russian content.
- **Niche tag is the primary one.** Many channels post adjacent roles (e.g. a Python channel will surface ML/DS positions). Treat niche as a hint for the parser's classification model, not ground truth.

## Channel list

Sorted by niche (alphabetical), then by approximate subscribers descending. Subs are rounded to nearest K.

| handle | subs | niche | frequency | notes |
|--------|------|-------|-----------|-------|
| @analyst_jobs_feed | ~14K | analytics | daily | Data/business/system analyst roles. Auto-feed style, light moderation. Aggregator. |
| @foranalysts | ~12K | analytics | few-per-week | NewHR-run, Job for Analysts & Data Scientists; hand-picked. Original. |
| @biheadhunter | ~8K | analytics (BI) | sporadic | Business Intelligence HeadHunter; Power BI / Tableau / Qlik / DWH. Community-posted. |
| @data_analysis_jobs | ~5K | analytics | few-per-week | Data analyst niche, often Russian companies. |
| @forbackend | ~14K | backend | daily | GeekJob backend channel; .NET, Java, C#, C++, Go, Rust. Aggregator. |
| @forpython | ~13K | backend (python) | daily | GeekJob Python channel; covers backend + DS-adjacent. Aggregator. |
| @forgoandrust | ~6K | backend (go/rust) | few-per-week | GeekJob Go & Rust handle. Aggregator. |
| @jobforphp | ~5K | backend (php) | sporadic | GeekJob PHP channel; lower volume. |
| @alljvmjobs | ~5K | backend (jvm) | few-per-week | GeekJob Java, Scala, Clojure feed. |
| @forruby | ~3K | backend (ruby) | sporadic | GeekJob Ruby & Elixir. Low volume but high signal-to-noise. |
| @forcsharp | ~3K | backend (.net) | few-per-week | GeekJob C#/.NET channel. |
| @forcpp | ~2K | backend (c++) | sporadic | GeekJob C/C++. Often gamedev / systems crossover. |
| @job_web3 | ~10K | blockchain/web3 | daily | Web 3.0 Job — крипто вакансии; hand-picked, mostly English-speaking companies hiring RU. |
| @workingincrypto | ~9K | blockchain/web3 | few-per-week | Блокчейн Hunter; sister channel @cryptoheadhunter. |
| @cryptojobsmarket | ~7K | blockchain/web3 | few-per-week | Crypto Jobs Market — blockchain/ICO/web3, all role types. |
| @web30job | ~6K | blockchain/web3 | few-per-week | Inflow's web3 handle; relocation/remote skew. |
| @workers_tg | ~5K | blockchain/web3 | few-per-week | CryptoJobs — работа в криптовалюте. Remote-heavy. |
| @forblockchain | ~3K | blockchain/web3 | sporadic | GeekJob blockchain feed. |
| @jun_hi_vacancies | ~14K | design (ui/ux) | daily | Aggregates ~8 design vacancies/day from 40+ sources. Aggregator. |
| @designer_ru | ~12K | design | daily | Ищу_дизайнера — partner of large designer FB community. Hand-curated. |
| @uiux_jobs_resumes | ~8K | design (ui/ux) | few-per-week | UI/UX Jobs — saved vacancies + resume cross-posts. |
| @fordesigners | ~7K | design | few-per-week | GeekJob designers channel. |
| @fordevops | ~13K | devops/sre | daily | GeekJob — Job for Sysadmin & DevOps. Aggregator. |
| @devops_jobs_feed | ~18K | devops/sre | daily | DevOps Jobs (auto-feed); high volume, lower curation. Aggregator. |
| @datasciencejobs | ~28K | data/ml | daily | Largest DS/ML/AI channel in RU; RKN-registered. |
| @datajob | ~22K | data/ml | daily | Data jobs — DS, analytics, AI; hand-picked. |
| @datascienceml_jobs | ~15K | data/ml | daily | Data Science Jobs (proglib network). Aggregator. |
| @ai_rabota | ~9K | data/ml (ai) | few-per-week | AI Работа — DS/ML/LLM-focused. |
| @data_science_job | ~7K | data/ml | few-per-week | Older but active DS feed. |
| @de_rabota | ~4K | data/ml (DE) | few-per-week | Data Engineering niche. |
| @forfrontend | ~21K | frontend | daily | GeekJob — Job for Frontend (JS + Node.js). Aggregator. |
| @javascript_jobs | ~14K | frontend | daily | JavaScript vacancies, all levels. |
| @forweb | ~16K | frontend | daily | For Web — frontend + web design + programming. Mixed. |
| @reactjs_jobs | ~10K | frontend (react) | few-per-week | React-specific. |
| @javascript_jobs_feed | ~8K | frontend | daily | Auto-feed JS vacancies. Aggregator. |
| @nodejs_jobs_feed | ~7K | frontend/backend | few-per-week | Node.js Jobs; migrated to @nodejsjobsfeed in some sources — verify on first parse. |
| @gamedevjob | ~40K | gamedev | daily | Работа в геймдеве — by far the largest gamedev channel. Hand-moderated, paid + free posts. |
| @forgamedev | ~9K | gamedev | few-per-week | GeekJob gamedev feed; Unity, Unreal, animators, 3D. |
| @geekjob_it | ~37K | general it | daily | GeekJob's flagship channel; all IT roles, testers to CTO. Aggregator across their network. |
| @forallit | ~25K | general it | daily | Cross-niche aggregator. |
| @vladimirskaya | ~22K | general it (senior) | few-per-week | Vacancies hand-picked by Alyona Vladimirskaya (top RU headhunter). High signal. |
| @it_vakansii_jobs | ~15K | general it | daily | СЕТИ — IT & Digital вакансии; direct HR contacts. |
| @workayte | ~12K | general it | daily | Работа в ИТ — broad RU + remote + abroad. |
| @inflow_jobs | ~10K | general it | daily | Inflow flagship; cross-posts to niche Inflow handles. Aggregator. |
| @holder_job_devs | ~8K | general it (senior) | few-per-week | Senior/middle developer roles; web3 crossover. |
| @forallmobile | ~12K | mobile | daily | GeekJob — Job for Mobile (iOS, Android, RN). Aggregator. |
| @mobile_jobs | ~21K | mobile | daily | Mobile Dev Jobs — vacancies + resumes; iOS, Android, Xamarin, Flutter. Aggregator. |
| @mobiledevjob | ~5K | mobile | few-per-week | Библиотека программиста's mobile channel; hand-picked. |
| @forproducts | ~24K | product/pm | daily | Job for Products and Projects (NewHR); PM, PO, CPO, Project Mgr. Hand-picked. |
| @hireproproduct | ~14K | product/pm | few-per-week | Hire ProProduct — product vacancies RU + abroad. |
| @product_jobs | ~12K | product/pm | daily | Auto-feed PM vacancies. Aggregator. |
| @projects_jobs_feed | ~8K | project mgmt | daily | Management Jobs — project, risk, PMP. Aggregator. |
| @jobfortm | ~8K | leadership (CTO) | few-per-week | Job for IT-TOP — CTO, CIO, Head of Dev/QA/DevOps. NewHR. |
| @forallqa | ~15K | qa | daily | GeekJob — Job for QA; manual + auto + TestOps. Aggregator. |
| @testerrjob | ~14K | qa | daily | QA — testing, manual, autotests. Heavy volume. |
| @qa_jobs | ~8K | qa | few-per-week | QA-focused, mid-size. |
| @relocats | ~26K | relocation | daily | Inflow — IT Relocation; RU/CIS-to-abroad with sponsorship. Aggregator. |
| @remoteit | ~42K | remote | daily | Inflow — Remote IT; one of the largest remote feeds for RU-speaking devs. Aggregator. |
| @remocate | ~30K | relocation/remote | daily | Remocate — relocation/remote across digital; USD/EUR salaries. |
| @remocatedevs | ~12K | relocation/remote | few-per-week | Remocate's dev-only sub-channel. |
| @opento_relocate | ~10K | relocation | few-per-week | wantapply.com network — all-role relocation. |
| @opento_dev | ~8K | relocation (dev) | few-per-week | wantapply — devs, DevOps, Python relocation. |
| @opento_data | ~6K | relocation (data) | few-per-week | wantapply — DE/ML/DS/CV relocation. |
| @opento_cyprus | ~5K | relocation (cyprus) | few-per-week | Cyprus-specific office + relocation. |
| @evacuatejobs | ~9K | relocation | few-per-week | Relocation/remote/abroad mix; Russian-speaking. |
| @itfinland | ~4K | relocation (FI) | sporadic | Finland-specific IT relocation channel. |
| @youritjob | ~5K | relocation (serbia) | sporadic | Serbia IT jobs + remote. |
| @goutstaff | ~6K | remote (outstaff) | few-per-week | Outstaff vacancies for non-RU/BY residents; remote. |
| @jobfeeds | ~10K | remote | daily | Inflow's everywhere-aggregator. Aggregator. |
| @remotejun | ~7K | remote (junior) | few-per-week | Inflow — remote junior/intern IT. |
| @jobforjunior | ~22K | junior/intern | daily | Job for Junior — internships + junior across IT/digital. Aggregator. |
| @rfounders_jobs | ~15K | startup | few-per-week | R-Founders — vacancies from 300+ foreign cos with RU-speaking founders (InDrive, Revolut, JetBrains). High signal. |
| @startuprussia_jobs | ~6K | startup | sporadic | Startup Russia community jobs feed. |
| @job41c | ~7K | 1C | few-per-week | Inflow's 1C-specific channel; RU enterprise. |
| @prompten | ~5K | ai/prompt eng | few-per-week | Prompt Engineer / AI tooling jobs. |
| @rabota_v_digital | ~9K | digital/marketing-adj | daily | Digital roles, often crossover into IT product/PM. |
| @fromlinked | ~8K | remote (linked) | daily | Fresh LinkedIn IT + gamedev pulls; auto. Aggregator. |
| @cvflow | ~5K | resumes (reverse) | daily | Inflow — candidates posting CVs; useful for understanding supply side. Skip if parser is jobs-only. |

## Operational checklist for the parser

1. Hash each channel handle and persist `last_message_id` to resume safely across restarts.
2. On `ChannelPrivateError` or `UsernameNotOccupiedError`, mark the channel as `inactive`, alert (Slack/log), and continue.
3. Sample one channel per niche initially to tune the deduper before going full-fleet.
4. Aggregator channels (marked above) should be deprioritized in the dedupe tiebreaker — prefer original-source channels as the canonical record.
5. Rebuild this list quarterly from TGStat's career/technologies rankings: https://tgstat.ru/en/career and https://tgstat.ru/en/ratings/channels/tech.

## Sources

- https://huntflow.media/it-vacancies-chats-and-channels/ — 75 IT vacancy channels
- https://geekjob.ru/content/channels — GeekJob network catalogue
- https://potok.io/blog/hr-howto/telegram-channels-and-chats-with-vacancies-it-digital/ — 101 channels
- https://vc.ru/hr/2295219-300-telegram-kanalov-s-vakansiyami — 300+ channels mega-list
- https://habr.com/ru/articles/919520/ — relocation channels roundup
- https://www.im-konsalting.ru/blog/50-telegram-kanalov-dlya-poiska-raboty/ — 50 job channels 2026
- https://tgstat.ru/en/career — TGStat career ranking
- https://tgstat.ru/en/ratings/channels/tech — TGStat tech ranking
- https://telemetr.me/ — channel-level subscriber and post-frequency stats
- https://huntflow.media/products-and-projects/ — product/project manager channels
- https://huntflow.media/design-vacancies-chats-and-channels/ — design channels
- https://huntflow.media/telegram-for-analysts/ — analyst channels
- https://blog.skillfactory.ru/gde-iskat-rabotu-v-telegram/ — frontend-leaning roundup
