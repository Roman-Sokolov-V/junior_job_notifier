# 🕵️‍♂️ Vacancy Auto Scraper

A robust, production-ready asynchronous job vacancy scraper built with **Scrapy**. It automatically tracks, filters, and collects job openings, stores the structured data in a **PostgreSQL (Supabase)** database, and sends instant automated notifications via a **Telegram bot**.

The entire workflow is fully automated using **GitHub Actions**, powered by **`uv`** for blazing-fast dependency management and smart caching.

---

### 📢 Full Disclosure & Motivation
**I am actively looking for a job as a Python Backend Developer.** This project was born out of a personal need to automate and optimize my own job hunt. I am building and maintaining this system for myself, and I will continuously refine it until I land my next role. *Ironically, I sincerely hope to find a great job way before I manage to implement every complex feature planned for this tool!* 😄

---

## 🚀 Features

- **Automated Scraping:** Scheduled or manual runs using GitHub Actions.
- **Asynchronous Architecture:** Built on Scrapy for high-performance concurrent requests.
- **Relational Storage & Deduplication:** Integrated with PostgreSQL (hosted on Supabase) to store job descriptions and filter out duplicate entries, ensuring users only receive unique, newly posted vacancies.
- **Instant Alerts:** Telegram bot integration for real-time notifications about new job opportunities.
- **Modern Python Tooling:** Managed entirely via `uv` for deterministic, lightning-fast dependency resolution and isolated virtual environments.
- **Cloud-Native CI/CD:** Fully automated daily execution utilizing GitHub Actions with custom caching layer.

---

## 🛠️ Project Architecture  
‼️ outdated ‼️
```angular2html
├── .github/
│   └── workflows/
│       └── scrape.yml        # GitHub Actions automation workflow
├── scraper/                  # Core Scrapy project directory
│   ├── spiders/              # Job vacancy spiders
│   ├── items.py              # Scrapy item data models
│   ├── pipelines.py          # Database & clean-up pipelines
│   └── settings.py           # Scrapy configuration settings
├── .python-version           # Explicit Python version pinned by uv
├── pyproject.toml            # Modern project metadata & dependencies declaration
├── run.py                    # Main script orchestration entrypoint
└── uv.lock                   # Cryptographically locked dependency graph
```

---

## 🔧 Local Setup & Installation

This project utilizes [uv](https://github.com/astral-sh/uv), an extremely fast Python package and project manager written in Rust.

### 1. Prerequisites

Ensure you have `uv` installed on your machine. If not, install it via:
#### On Linux/macOS
```bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

### 2. Clone the Repository

```bash
git clone [https://github.com/yourusername/vacancy-auto-scraper.git](https://github.com/yourusername/vacancy-auto-scraper.git)
cd vacancy-auto-scraper
```

### 3. Install Dependencies & Setup Environment

Run the following command to automatically discover the required Python version, create a localized .venv, and synchronize all locked dependencies:
```bash
uv sync
```
### 4. Configuration

Create a .env file in the root directory (or export them in your shell session) and populate it with your credentials:

```angular2html
TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
TELEGRAM_CHAT_ID="your_telegram_chat_id_or_channel_id"
DATABASE_URL="postgresql://user:password@your-supabase-host:5432/postgres"
AI_MODE="0"  для роботи без ШІ, "1" - в режимі ШІ
```


### Docker (PostgreSQL + app)

Two services: **`db`** (Postgres 16) and **`app`** (this project). On start, the app runs **`alembic upgrade head`** then your command (default: `uv run run.py`).

```bash
# Optional: set AI_MODE / Telegram in a file and pass it to Compose (see .env.docker.example)
cp .env.docker.example .env.docker
docker compose --env-file .env.docker build   # first build is slow (torch + Playwright)
docker compose --env-file .env.docker up
```

Or put `AI_MODE`, `TELEGRAM_*` in a `.env` file next to `docker-compose.yml` (Compose reads it for `${VAR}` substitution).

`DATABASE_URL` is set inside `docker-compose.yml` for the app service. Override only if you use another DB.

One-off commands:

```bash
docker compose run --rm app uv run match_new_batch.py
docker compose run --rm app uv run scrapy crawl breezy_ai -O /tmp/breezy.csv
```

**Note:** the image includes Chromium for **scrapy-playwright**. It is large by design. For production you can later split “scraper” and “matcher” images or use a slimmer base if you drop Playwright from a service.

### Running the Scraper Locally

#### Database schema (SQLAlchemy + Alembic)

Tables and constraints are defined as ORM models under `scrap_vac/db/` and applied with Alembic (no hand-written SQL in pipelines).

With `DATABASE_URL` set in `.env` (or exported in the shell):

```bash
uv run alembic upgrade head
```

Run this once on a new database, and after you pull new migrations. Scrapy pipelines only insert data; they do not 
create tables.  


‼️For AI mod. In the future, it is planned to make the program available to many users using a telegram bot ,
which has not yet been implemented, so for correct operation it is necessary to manually https://supabase.com 
enter your data, in the table 'users' - your telegram_user_id and username, in table 'user_profiles' - user_id which 
will be generated in the table 'users', 'include_keywords' - the words of which are strictly required in the vacancy,
for example ["python", "junior"] 'exclude_keywords' - the presence of which in the text of the vacancy will exclude it from the search result
'query_text' - free-form text for AI analysis for additional filtering for example ‼️  

To execute the main entrypoint script inside the isolated virtual environment managed by uv:

```bash
uv run run.py
```
The mode of operation (AI not AI) is defined in .env by a variable AI_MODE ("1" with AI "0" without) or just run like this:
```bash
AI_MODE=0 uv run run.py
```
```
AI_MODE=1 uv run run.py
```

🤖 GitHub Actions CI/CD Automation

The project includes a pre-configured GitHub Actions workflow that executes the scraping routine daily at 09:00 UTC (12:00 EET / 11:00 EEST), or anytime manually.
Operationalizing in GitHub:

Push Everything: Ensure pyproject.toml and uv.lock are committed to your GitHub repository so that the pipeline can mirror your exact local environment.

Configure Encrypted Secrets:

Go to your repository on GitHub: Settings ➡️ Secrets and variables ➡️ Actions.

Click New repository secret and add the following keys:

    TELEGRAM_BOT_TOKEN

    TELEGRAM_CHAT_ID

    DATABASE_URL

Triggering: Check the Actions tab on GitHub to see execution logs, test manually via Run workflow, or leave it to run autonomously according to the cron schedule.  

---

### 📅 Roadmap & Upcoming Features (To-Do)

We are actively working on expanding and improving the scraper. The following milestones are planned for future releases:

1. **🌐 Multi-Platform Expansion:** Develop and deploy additional Scrapy spiders to aggregate data from a wider range of regional and global job boards, maximizing vacancy coverage.

2. **🤖 AI-Powered Job Classification:** Integrate LLM processing to accurately classify job seniority (e.g., distinguishing *Junior*, *Middle*, and *Senior* roles) and tech stacks, bypassing messy or inaccurate tags provided by job boards.

3. **📝 Smart Vacancy Summarization:** Implement automated text summarization using OpenAI/Anthropic APIs to condense long job descriptions into concise, bulleted core requirements (key skills, salary, tech stack) directly within the Telegram alert.

4. **🎯 Semantic Resume Match Score:** Develop a custom matching system that compares scraped vacancy descriptions against a user's CV/Resume using vector embeddings, calculating a "Match Score (%)" to prioritize the best opportunities.

---

### 📝 License

This project is open-source and available under the MIT License.

---

### 📬 Contact & Connect

If you have any questions, suggestions, or would like to collaborate on this project, feel free to reach out:

- **Telegram:** [@Roman_Sokolo_v](https://t.me/Roman_Sokolo_v)
- **LinkedIn:** [roman-sokolov](https://www.linkedin.com/in/roman-sokolov-a7614330b/)
- **Email:** [roman.sokolov.developer@gmail.com](roman.sokolov.developer@gmail.com)
