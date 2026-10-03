# Blog Management Platform (REST API)

A robust, production-grade, multi-author Blog Management Platform built with **Django 5.1**, **Django REST Framework 3.17**, and **PostgreSQL 16+**.

The platform is engineered as a **Modular Monolith** adhering to strict architectural boundaries, explicit service and selector layers, automated quality controls, and database-level integrity guards.

[![CI](https://github.com/Humpty94/Blog_Management_system/actions/workflows/ci.yml/badge.svg)](https://github.com/Humpty94/Blog_Management_system/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Django 5.1](https://img.shields.io/badge/django-5.1-green.svg)](https://www.djangoproject.com/)
[![PostgreSQL 16+](https://img.shields.io/badge/postgresql-16+-blue.svg)](https://www.postgresql.org/)
[![Next.js 15](https://img.shields.io/badge/next.js-15.5-black.svg)](https://nextjs.org/)
[![Tailwind CSS v4](https://img.shields.io/badge/tailwind-v4-38bdf8.svg)](https://tailwindcss.com/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Coverage](https://img.shields.io/badge/coverage-93.8%25-brightgreen.svg)]()

---

## Application Showcase (Ghost-Inspired Interface)

GhostPRESS pairs high-contrast editorial minimalism with a distraction-free creator studio.

### 1. Publication Landing Page
> Editorial hero header, dynamic category taxonomy pills, real-time debounced search, featured story card, and responsive publication feed.

![Publication Landing Page](docs/images/publication_landing.png)

### 2. Distraction-Free Article Reader
> Long-form prose typography, author byline, floating engagement bar (likes, private bookmarks, sharing), and 1-level threaded discussion engine.

![Article Reader](docs/images/article_reader.png)

### 3. Ghost Admin Creator Studio (Dashboard Analytics)
> Ghost Admin sidebar, real-time metrics cards (Total Articles, Published, Active Drafts, Reader Likes), and recent drafts manager.

![Creator Studio Dashboard](docs/images/creator_studio_dashboard.png)

### 4. Split-Pane Markdown Editor with Live Preview
> Distraction-free authoring with live character/word counters, synchronized HTML rendering, category selector, and email-verification publishing gates.

![Split-Pane Markdown Editor](docs/images/split_pane_editor.png)

---

## End-to-End System Architecture

The system is architected as an asynchronous single-page frontend consuming a strictly modular Django 5.1 backend:

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Client Layer (Next.js 15 App Router & React 19)"]
        Landing["Publication Feed (/)\n• Hero & Featured Story\n• Category Taxonomy Pills\n• Debounced Live Search\n• Editorial Grid & Pagination"]
        Reader["Article Reader (/posts/[slug])\n• Prose Typography\n• Floating Engagement Bar\n• Self-Like Prevention UI\n• 1-Level Discussion Engine"]
        Studio["Ghost Admin Studio (/workspace)\n• Sidebar Navigation\n• Real-Time Metric Stat Cards\n• Posts Manager (Draft/Publish)\n• Private Bookmarks List\n• Profile & Deactivation"]
        Editor["Split-Pane Editor (/workspace?tab=editor)\n• Real-Time Markdown Input\n• Live Synchronized HTML Preview\n• Word Counter & Taxonomies\n• Email-Verified Gate Check"]
        AuthContext["AuthContext & API Client (lib/api.ts)\n• LocalStorage Token Pair Storage\n• Auto Token Refresh on 401\n• Cross-Tab Auth Synchronization"]
    end

    subgraph TransportLayer["REST API Transport Layer (DRF 3.17)"]
        AuthEndpoints["/api/v1/auth/\n• register/\n• login/\n• refresh/\n• verify-email/"]
        UsersEndpoints["/api/v1/users/\n• me/\n• me/posts/\n• me/bookmarks/\n• me/deactivate/"]
        PostsEndpoints["/api/v1/posts/\n• CRUD & Slug Routing\n• publish/ & unpublish/\n• like/ & bookmark/\n• comments/"]
        CategoriesEndpoints["/api/v1/categories/\n• Taxonomy Listing\n• Slug Filtering"]
    end

    subgraph ServiceLayer["Modular Monolith Domain Layer"]
        subgraph AccountsDomain["accounts app"]
            UserManager["Custom UserManager\n• Case-insensitive Lower()\n• Argon2id Hashing"]
            TokenFamily["Token Family Engine\n• Refresh Token Trees\n• Replay Attack Detection"]
            Anonymizer["In-Place Anonymizer\n• Drafts & Bookmarks Purge\n• Identity Redaction"]
        end

        subgraph BlogDomain["blog app"]
            PostServices["Post Services & Selectors\n• Slug Generation & Collision Retries\n• Server Word Boundary Excerpts\n• Email Verification Gate Check"]
            MarkdownEngine["Markdown Sanitizer\n• markdown-it-py AST\n• nh3 Tag/Attribute Allowlist"]
            SearchEngine["PostgreSQL Search Engine\n• Weighted TSVector Index\n• Full-Text Query Execution"]
        end

        subgraph CommentsDomain["comments app"]
            CommentTree["1-Level Discussion Engine\n• Root + Single Reply Constraint\n• Soft-Delete Placeholder Redaction"]
        end

        subgraph EngagementDomain["engagement app"]
            EngagementServices["Engagement Services\n• Atomic Like Increments\n• Self-Like Prohibition Check\n• Private User Bookmarks"]
        end
    end

    subgraph DatabaseLayer["Database Authority (PostgreSQL 16+)"]
        Postgres[(PostgreSQL 16 Enterprise DB\n• Partial Unique Indexes\n• Database Check Constraints\n• Foreign Keys & PROTECT\n• tsvector Search Vectors\n• ACID Atomic Transactions)]
    end

    Landing --> AuthContext
    Reader --> AuthContext
    Studio --> AuthContext
    Editor --> AuthContext
    AuthContext --> TransportLayer

    TransportLayer --> ServiceLayer
    ServiceLayer --> DatabaseLayer
```

---

## Relational Database Schema (ER Diagram)

All domain rules and business invariants are enforced as the final authority in PostgreSQL via constraints, foreign keys, and partial indexes:

```mermaid
erDiagram
    accounts_user ||--|| accounts_profile : "has"
    accounts_user ||--o{ accounts_emailverificationtoken : "issued"
    accounts_user ||--o{ accounts_refreshtokenrecord : "sessions"
    accounts_user ||--o{ blog_post : "authors"
    accounts_user ||--o{ comments_comment : "writes"
    accounts_user ||--o{ engagement_like : "likes"
    accounts_user ||--o{ engagement_bookmark : "saves"

    blog_category ||--o{ blog_post : "categorizes (PROTECT)"
    blog_post ||--o{ comments_comment : "has"
    blog_post ||--o{ engagement_like : "receives"
    blog_post ||--o{ engagement_bookmark : "bookmarked"

    comments_comment ||--o{ comments_comment : "replies (max 1 level)"

    accounts_user {
        bigint id PK
        varchar email UK "Lower(email) unique"
        varchar username UK "Lower(username) unique"
        varchar password "Argon2id hashed"
        boolean is_active
        boolean is_staff
        boolean is_superuser
        timestamptz email_verified_at "null if unverified"
        timestamptz deactivated_at "null if active"
        timestamptz date_joined
        timestamptz last_login
    }

    accounts_profile {
        bigint id PK
        bigint user_id FK,UK "One-to-One"
        varchar display_name
        text bio
        timestamptz created_at
        timestamptz updated_at
    }

    accounts_emailverificationtoken {
        bigint id PK
        bigint user_id FK
        varchar token_hash UK "SHA-256 hashed"
        timestamptz expires_at
        boolean is_used
        timestamptz created_at
    }

    accounts_refreshtokenrecord {
        bigint id PK
        bigint user_id FK
        uuid family_id "Tracked family branch"
        varchar token_jti UK "Unique JWT identifier"
        varchar parent_jti "Previous rotated token"
        boolean is_revoked "True on replay detection"
        timestamptz expires_at
        timestamptz created_at
    }

    blog_category {
        bigint id PK
        varchar name UK
        varchar slug UK
        text description
        timestamptz created_at
        timestamptz updated_at
    }

    blog_post {
        bigint id PK
        bigint author_id FK
        bigint category_id FK
        varchar title
        varchar slug UK "Immutable URL identifier"
        varchar status "draft | published"
        text excerpt "Word-boundary truncated"
        text content_markdown "Raw author markdown"
        text content_text "Derived plain text"
        timestamptz published_at "null if draft"
        integer like_count "Atomic counter"
        tsvector search_vector "Title(A) + Content(B)"
        timestamptz created_at
        timestamptz updated_at
    }

    comments_comment {
        bigint id PK
        bigint post_id FK
        bigint author_id FK "nullable for deleted users"
        bigint parent_id FK "nullable, self-reference max 1 level"
        text body "Redacted if is_deleted"
        boolean is_deleted "Soft-delete placeholder"
        timestamptz deleted_at
        timestamptz created_at
        timestamptz updated_at
    }

    engagement_like {
        bigint id PK
        bigint user_id FK
        bigint post_id FK
        timestamptz created_at
    }

    engagement_bookmark {
        bigint id PK
        bigint user_id FK
        bigint post_id FK
        timestamptz created_at
    }
```

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
