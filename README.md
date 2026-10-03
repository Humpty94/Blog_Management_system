# Blog Management Platform (REST API)

A robust, production-grade, multi-author Blog Management Platform built with **Django 5.1**, **Django REST Framework 3.17**, and **PostgreSQL 16+**.

The platform is engineered as a **Modular Monolith** adhering to strict architectural boundaries, explicit service and selector layers, automated quality controls, and database-level integrity guards.

[![CI](https://github.com/Humpty94/Blog_Management_system/actions/workflows/ci.yml/badge.svg)](https://github.com/Humpty94/Blog_Management_system/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Django 5.1](https://img.shields.io/badge/django-5.1-green.svg)](https://www.djangoproject.com/)
[![PostgreSQL 16+](https://img.shields.io/badge/postgresql-16+-blue.svg)](https://www.postgresql.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Coverage](https://img.shields.io/badge/coverage-93.8%25-brightgreen.svg)]()

---

## Architecture & Design Principles

```mermaid
flowchart LR
    subgraph Modular Monolith
        engagement["engagement"] --> blog["blog"]
        comments["comments"] --> blog
        engagement --> accounts["accounts"]
        comments --> accounts
        blog --> accounts
        engagement --> common["common"]
        comments --> common
        blog --> common
        accounts --> common
    end
```

1. **Modular Monolith**: One deployable Django project partitioned into clean apps (`common`, `accounts`, `blog`, `comments`, `engagement`) with strict one-way dependency enforcement.
2. **Thin Transport, Explicit Business Layer**:
   - **Views (`views.py`)**: Thin HTTP handlers for routing, status codes, and input/output mapping.
   - **Services (`services.py`)**: All state-mutating business logic and explicit `transaction.atomic` blocks.
   - **Selectors (`selectors.py`)**: Optimized read queries, annotations, and visibility rules.
3. **Database as the Final Authority**: Uniqueness, foreign keys, and business invariants are enforced in PostgreSQL via check constraints and partial indexes.
4. **Session Security & Reuse Detection**: Refresh tokens are tracked in token families with automatic family-wide revocation upon reuse detection.
5. **Sanitized Content Pipeline**: Markdown is rendered with raw HTML disabled and sanitized using `nh3` allowlisting. Excerpts are truncated at word boundaries.
6. **In-Place Irreversible Anonymization**: Deactivating an account anonymizes identity (`deleted-<id>@deleted.invalid`), purges private drafts and bookmarks, while preserving published posts, comments, and likes.

---

## Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.12+ | Modern syntax and runtime performance |
| **Framework** | Django 5.1 LTS | Robust ORM, migrations, and battle-tested security |
| **API Layer** | Django REST Framework 3.17 | Declarative serializers, viewsets, and throttles |
| **Database** | PostgreSQL 16+ via `psycopg` 3 | Check constraints, partial indexes, Full-Text Search |
| **Auth & Tokens** | `argon2-cffi` + `simplejwt` | Argon2id password hashing + custom refresh token family tracking |
| **Markdown** | `markdown-it-py` + `nh3` | Defense-in-depth HTML sanitization |
| **Frontend** | Next.js 15 + TypeScript + Tailwind CSS | Ghost-inspired publication & creator studio |
| **Icons** | `lucide-react` | Clean editorial iconography |
| **API Contract** | `drf-spectacular` | OpenAPI 3.0 schema generation |
| **Code Quality** | `ruff`, `pytest`, `pytest-cov`, ESLint | Fast linting, formatting, and high-coverage testing |

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm 10+
- PostgreSQL 16+ running on `127.0.0.1:5432`

### 1. Clone & Set Up Backend Virtual Environment

```bash
git clone https://github.com/Humpty94/Blog_Management_system.git
cd Blog_Management_system

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Configure Backend Environment

Copy the example environment configuration:

```bash
cp .env.example .env
```

Ensure your PostgreSQL service is running and create the databases:

```sql
CREATE DATABASE blog_db;
CREATE DATABASE test_blog_db;
```

### 3. Run Migrations & Seed Data

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Start Backend Server

```bash
python manage.py runserver
```

The Django REST API is accessible at `http://127.0.0.1:8000/api/v1/`.

### 5. Start Frontend (Ghost-inspired Publication & Studio)

In a separate terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

The Ghost publication is accessible at `http://localhost:3000`:
- **Landing Page (`/`)**: Ghost hero header, category filter pills, live debounced search, featured post, and editorial grid.
- **Article Reader (`/posts/[slug]`)**: Editorial prose typography, live like/bookmark toggles with self-like protection, and 1-level discussion engine with soft-deletion placeholders.
- **Ghost Admin Studio (`/workspace`)**: Sidebar navigation, metrics dashboard, post table with draft/published status badges, distraction-free split-pane Markdown editor with live preview, private bookmarks, and profile/security settings.

---

## Testing & Quality Assurance

### Run the Test Suite with Coverage

```bash
pytest --cov --cov-fail-under=85
```

*119 unit and integration tests passing with 93.8% code coverage.*

### Code Style & Linting

```bash
ruff check .
ruff format --check .
```

### Validate OpenAPI 3 Contract

```bash
python manage.py spectacular --validate --fail-on-warn
```

### Production Deployment Check

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy
```

---

## API Catalog (`/api/v1/`)

### Authentication & Identity (`accounts`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register/` | Register new user account |
| `POST` | `/api/v1/auth/login/` | Authenticate and issue JWT token pair |
| `POST` | `/api/v1/auth/verify-email/` | Verify email with single-use token |
| `POST` | `/api/v1/auth/resend-verification/` | Resend verification token email |
| `POST` | `/api/v1/auth/refresh/` | Rotate refresh token with reuse detection |
| `POST` | `/api/v1/auth/logout/` | Revoke current refresh token |
| `GET` | `/api/v1/users/me/` | Current user profile |
| `PATCH` | `/api/v1/users/me/` | Update profile (display name, bio) |
| `POST` | `/api/v1/users/me/deactivate/` | Deactivate & irreversibly anonymize account |
| `GET` | `/api/v1/users/<username>/` | Public user profile |

### Content & Taxonomy (`blog`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/categories/` | List all categories |
| `GET` | `/api/v1/categories/<slug>/` | Category details |
| `GET` | `/api/v1/posts/` | Browse published posts (filters: `category`, `search`, `ordering`) |
| `POST` | `/api/v1/posts/` | Create a new draft post |
| `GET` | `/api/v1/posts/<slug>/` | Post details (sanitized HTML, excerpt, author) |
| `PATCH` | `/api/v1/posts/<slug>/` | Update post (title, content, category) |
| `DELETE` | `/api/v1/posts/<slug>/` | Delete post |
| `POST` | `/api/v1/posts/<slug>/publish/` | Publish post (verified email required) |
| `POST` | `/api/v1/posts/<slug>/unpublish/` | Revert post to draft |
| `GET` | `/api/v1/users/me/posts/` | List own posts (drafts and published) |
| `GET` | `/api/v1/users/<username>/posts/` | List author's public published posts |

### Comments & Discussions (`comments`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/posts/<slug>/comments/` | List comments and nested replies for post |
| `POST` | `/api/v1/posts/<slug>/comments/` | Create root comment or 1-level reply |
| `DELETE` | `/api/v1/comments/<id>/` | Delete comment (placeholder if replies exist) |

### Reader Engagement (`engagement`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/posts/<slug>/like/` | Idempotent post like toggle |
| `DELETE` | `/api/v1/posts/<slug>/like/` | Idempotent post unlike |
| `POST` | `/api/v1/posts/<slug>/bookmark/` | Idempotent bookmark post |
| `DELETE` | `/api/v1/posts/<slug>/bookmark/` | Idempotent remove bookmark |
| `GET` | `/api/v1/users/me/bookmarks/` | List current user's private bookmarks |

### Operational
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health/` | Service & database health check |

---

## Core Invariants Enforced

1. **Strict Draft Privacy**: Unpublished posts return `404 Not Found` to non-authors and anonymous viewers.
2. **Verified-Email Publishing Gate**: An author cannot transition a post to `published` without a verified email address.
3. **One-Reply-Level Constraint**: Comments support exactly root comments and direct replies. Nested replies to replies are rejected (`400 Bad Request`).
4. **Placeholder Deletions**: Deleting a root comment with replies sets `is_deleted=True`, blanks the body, and redacts the author (`[This comment has been deleted]`), preserving replies. Standalone comments and replies are hard-deleted.
5. **Self-Like Prohibition**: Authors cannot like their own posts (`self_like_prohibited`).
6. **Private Bookmarks**: Bookmarks are strictly private to the user who created them.
7. **Idempotency**: Like and bookmark toggles are safe against concurrent and duplicate calls.
8. **Token Reuse Detection**: Attempting to replay an already-rotated refresh token instantly revokes all active tokens in that family.
9. **Category Deletion Protection**: Categories with posts cannot be deleted (`PROTECT`). Posts must be reassigned first via Django Admin.
