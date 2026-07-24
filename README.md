# 🕵️‍♂️ Junior Job Notifier

A robust, production-ready asynchronous job vacancy scraper built with **Scrapy**. It automatically tracks, filters, and collects job openings directly from individual companies' career pages, stores the structured data in a **PostgreSQL (Supabase)** database, and matches them against per-user search profiles — with results delivered through [**junior_job_notifier_bot**](https://github.com/Roman-Sokolov-V/junior_job_notifier_bot) on Telegram.

The entire scraping workflow is fully automated using **GitHub Actions**, powered by **`uv`** for blazing-fast dependency management and smart caching.

---

### 📢 Full Disclosure & Motivation
**I am actively looking for a job as a Python Backend Developer.** This project was born out of a personal need to automate and optimize my own job hunt — specifically, to track openings directly on individual companies' career pages rather than the major job boards, where competition for junior roles is fierce. I am building and maintaining this system for myself, and I will continuously refine it until I land my next role. *Ironically, I sincerely hope to find a great job way before I manage to implement every complex feature planned for this tool!* 😄

---

## 🔗 Related Project

User registration, search profile management, and browsing matched vacancies are handled by a companion Telegram bot:

👉 [**junior_job_notifier_bot**](https://github.com/Roman-Sokolov-V/junior_job_notifier_bot)

This repository is responsible for scraping and matching only — it has no user-facing interface of its own.

---

## 🚀 Features

- **Automated Scraping:** Scheduled or manual runs using GitHub Actions, targeting individual companies' own career pages rather than aggregator sites.
- **Asynchronous Architecture:** Built on Scrapy for high-performance concurrent requests.
- **Relational Storage & Deduplication:** Integrated with PostgreSQL (hosted on Supabase) to store job descriptions and filter out duplicate entries, ensuring users only receive unique, newly posted vacancies.
- **Per-User Search Profiles:** Each registered user can create an unlimited number of search profiles, each combining:
  - **Include keywords** — a vacancy's title must contain at least one of these to pass.
  - **Exclude keywords** — a vacancy's title is rejected if it contains any of these.
  - **AI semantic matching** — a `query_text` field used to semantically match vacancies that survive the keyword filters, via vector embeddings (`sentence-transformers` + **pgvector**), not an LLM. For best results, this should be a list of technologies/skills rather than free-form text: matching is currently performed against a *fragment* of the vacancy (essentially `requirements` + `nice_to_have`), not the full description, due to the embedding model's limited context window — so a natural-language prompt tends to match less precisely than a concise stack listing.

  All three criteria are optional, but at least one must be set per profile.
- **Bot-Driven Registration:** Users register, create/edit/delete profiles, and browse matched vacancies entirely through [junior_job_notifier_bot](https://github.com/Roman-Sokolov-V/junior_job_notifier_bot) — no manual database entry required.
- **Instant Alerts:** New matches are delivered to users via the Telegram bot.
- **Modern Python Tooling:** Managed entirely via `uv` for deterministic, lightning-fast dependency resolution and isolated virtual environments.
- **Cloud-Native CI/CD:** Fully automated daily execution utilizing GitHub Actions with a custom caching layer.

---

## 🛠️ Project Architecture

```
junior_job_notifier/
├── alembic/
│   ├── versions/              # Database migrations
│   ├── env.py
│   └── script.py.mako
├── db/
│   └── ai_schema.sql
├── docker/
│   └── entrypoint.sh
├── scrap_vac/                 # Core Scrapy project directory
│   ├── db/
│   │   ├── base.py
│   │   ├── crud.py
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── schemas.py
│   │   └── session.py
│   ├── spiders/
│   │   ├── anderson.py
│   │   ├── breezy.py
│   │   ├── common.py
│   │   ├── conversion_rate.py
│   │   ├── gen_tech.py
│   │   ├── newxel.py
│   │   ├── sigma_technology.py
│   │   ├── star_global.py
│   │   ├── thingsboard.py
│   │   └── tieto.py
│   ├── items.py
│   ├── middlewares.py
│   ├── pipelines.py
│   └── settings.py
├── telegram/
│   └── notification.py        # Sends matched vacancies to the bot's users
├── Dockerfile
├── alembic.ini
├── docker-compose.yml
├── exam_batch.py
├── match_new_batch.py         # Runs profile-based  matching against newly scraped vacancies
├── profile.yaml
├── pyproject.toml
├── run.py                     # Main entrypoint
└── uv.lock
```

---

## 🔧 Setup & Installation

This project runs via **Docker Compose**, which provisions both the app and a PostgreSQL database and takes care of running migrations automatically — no local Python environment setup required.

### 1. Clone the Repository

```bash
git clone https://github.com/Roman-Sokolov-V/junior_job_notifier.git
cd junior_job_notifier
```

### 2. Configuration

```bash
cp .env.docker.example .env.docker
```

Populate `.env.docker` with your credentials:

```
TELEGRAM_BOT_TOKEN="the same token as for junior_job_notifier_bot"
```

`DATABASE_URL` is set inside `docker-compose.yml` for the app service and doesn't need to be provided separately — Compose provisions its own PostgreSQL instance for local runs.

### 3. Build and Run

Two services: **`db`** (Postgres 16) and **`app`** (this project). On start, the app runs **`alembic upgrade head`** then your command (default: `uv run run.py`).

```bash
docker compose --env-file .env.docker build   # first build is slow (torch + Playwright)
docker compose --env-file .env.docker up
```

**Note:** the image includes Chromium for **scrapy-playwright**. It is large by design. For production you can later split "scraper" and "matcher" images or use a slimmer base if you drop Playwright from a service.

Users, their search profiles, and matching results all live in Supabase and are managed exclusively through [junior_job_notifier_bot](https://github.com/Roman-Sokolov-V/junior_job_notifier_bot) — manual editing of the `users` / `user_profiles` tables is no longer necessary or recommended.

---

## 🤖 GitHub Actions CI/CD Automation

The project includes a pre-configured GitHub Actions workflow that executes the scraping routine daily at 09:00 UTC (12:00 EET / 11:00 EEST), or anytime manually.

Operationalizing in GitHub:

**Push Everything:** Ensure `pyproject.toml` and `uv.lock` are committed to your GitHub repository so that the pipeline can mirror your exact local environment.

**Configure Encrypted Secrets:**

Go to your repository on GitHub: Settings ➡️ Secrets and variables ➡️ Actions.

Click **New repository secret** and add the following keys:

- `TELEGRAM_BOT_TOKEN`
- `AI_MODEL_NAME`
- `DATABASE_URL`

**Triggering:** Check the Actions tab on GitHub to see execution logs, test manually via **Run workflow**, or leave it to run autonomously according to the cron schedule.

---

### 📅 Roadmap & Upcoming Features (To-Do)

We are actively working on expanding and improving the scraper. The following milestones are planned for future releases:

1. **✅ Vector Search Migration (done):** Semantic matching now runs database-native via **pgvector**, with vacancy embeddings computed once at scrape time and cached in Postgres, and similarity search/top-K ranking pushed down to SQL. Current limitation: due to the embedding model's small context window, matching is done against a fragment of the vacancy (`requirements` + `nice_to_have`) rather than the full description — see the caveat above.

2. **🧠 LLM-Based Full-Text Matching:** Add an LLM-powered matching pass over the *entire* vacancy description (not just a fragment), to complement or replace the current embedding-fragment approach and remove the context-window limitation described above.

3. **🌐 Multi-Platform Expansion:** Continue adding new spiders to cover more individual companies' career pages.

4. **🎯 Semantic Resume Match Score:** Develop a custom matching system that compares scraped vacancy descriptions against a user's CV/Resume using vector embeddings, calculating a "Match Score (%)" to prioritize the best opportunities.

5. **📝 Smart Vacancy Summarization:** Implement automated text summarization to condense long job descriptions into concise, bulleted core requirements (key skills, salary, tech stack) directly within the Telegram alert.

---

### 📝 License

This project is open-source and available under the MIT License.

---

### 📬 Contact & Connect

If you have any questions, suggestions, or would like to collaborate on this project, feel free to reach out:

- **Telegram:** [@Roman_Sokolo_v](https://t.me/Roman_Sokolo_v)
- **LinkedIn:** [roman-sokolov](https://www.linkedin.com/in/roman-sokolov-a7614330b/)
- **Email:** roman.sokolov.developer@gmail.com
