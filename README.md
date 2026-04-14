# BookIQ — Intelligent Book Discovery Platform

> Full-stack AI-powered book discovery with RAG Q&A, semantic search, and real-time scraping.

---

## Screenshots

> *(Add screenshots after running locally)*
> - `docs/screenshot-library.png` — Library dashboard with book grid, filters, AI badges
> - `docs/screenshot-detail.png` — Book detail with AI summary, sentiment, recommendations
> - `docs/screenshot-ask.png` — Chat Q&A interface with citations and chat history
> - `docs/screenshot-scrape.png` — Scrape page with live WebSocket progress log

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│               Next.js 14 + Tailwind CSS             │
│   Dashboard · Book Detail · Q&A Chat · Scrape UI   │
└────────────────────┬────────────────────────────────┘
                     │ REST + WebSocket
┌────────────────────▼────────────────────────────────┐
│            Django REST Framework (Daphne ASGI)      │
│   /api/books/  /api/rag/ask/  /api/scraper/start/  │
└──────┬────────────────┬────────────────┬────────────┘
       │                │                │
  ┌────▼────┐    ┌──────▼──────┐  ┌──────▼──────┐
  │  MySQL  │    │ Celery+Redis│  │  ChromaDB   │
  │metadata │    │async jobs · │  │  vectors +  │
  │         │    │cache (24hr) │  │  BM25 index │
  └─────────┘    └──────┬──────┘  └─────────────┘
                        │
               ┌────────▼────────┐
               │  Claude API     │
               │ (Sonnet)        │
               │ Summary·Genre·  │
               │ Sentiment·RAG   │
               └─────────────────┘
```

---

## Standout Features

| Feature | Detail |
|---|---|
| **Hybrid search** | BM25 sparse + dense vector retrieval, fused via Reciprocal Rank Fusion |
| **Semantic chunking** | Sentence-boundary chunking with 50-token overlap (not fixed-size splits) |
| **Redis caching** | RAG answers cached 24hr by `hash(question + book_id)` — avoids repeat API calls |
| **WebSocket progress** | Scrape job streams live per-book progress via Django Channels |
| **Multi-turn chat** | Last 3 conversation turns passed to Claude for context continuity |
| **Embedding recommendations** | Mean-pool book embeddings → cosine similarity matrix → top-5 neighbours |
| **Open Library enrichment** | Falls back to Open Library API for author name + first sentence |
| **Dark mode** | System-preference aware, persisted to localStorage |

---

## Setup

### Prerequisites
- Docker + Docker Compose
- Anthropic API key (`claude-sonnet-4-20250514`)

### Quick Start (Docker)

```bash
git clone <your-repo>
cd bookiq

cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and DB_PASSWORD

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/

### Manual Setup (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Start MySQL and Redis locally, then:
cp ../.env.example .env  # edit values

python manage.py migrate
daphne -b 0.0.0.0 -p 8000 bookiq_project.asgi:application

# In a separate terminal:
celery -A bookiq_project worker --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

---

## API Documentation

### Books

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/books/` | List all books. Query: `?search=&genre=&ordering=` |
| GET | `/api/books/<id>/` | Full book details + AI insights + recommendations |
| GET | `/api/books/<id>/recommendations/` | Top-5 similar books by embedding similarity |
| GET | `/api/books/genres/` | Distinct AI-classified genre list |
| GET | `/api/books/history/<session_id>/` | Chat history for a session |
| POST | `/api/books/upload/` | Manually add a book and trigger AI processing |

### RAG

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/ask/` | Q&A over books. Body: `{question, session_id, book_id?}` |

### Scraper

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scraper/start/` | Start async scrape. Body: `{max_books: 50}` |
| WS | `ws://host/ws/scrape/<job_id>/` | Live progress stream |

---

## Sample Q&A

**Q:** What mystery books are available?  
**A:** Based on the library, several mystery titles are available. *A Light in the Attic* [1] and similar titles have been classified in the Mystery genre. For darker crime fiction, *Sharp Objects* [2] offers a psychological thriller tone...

**Q:** Recommend books with positive sentiment  
**A:** Books with strongly positive tones include *The Selfish Gene* [1] which has an enthusiastic, engaging description, and *Sapiens* [2] which is described with optimistic language about human potential...

**Q:** Which books are suitable for young adults?  
**A:** The Young Adult section contains titles like *The Hunger Games* [1] and *Divergent* [2]. Both have been classified with positive sentiment scores above 0.7...

---

## Bonus Features Implemented

- [x] Redis caching for AI responses (24hr TTL, keyed by question hash)
- [x] Embedding-based similarity (ChromaDB cosine + mean-pool book vectors)
- [x] Async processing (Celery + Redis for scraping and insight generation)
- [x] Multi-page scraping (paginates through all catalogue pages)
- [x] Loading states + UX polish (skeleton loaders, progress bars, animated chat bubbles)
- [x] Advanced chunking (semantic sentence-boundary chunks with overlap)
- [x] Chat history (persisted in MySQL, restored per session_id)
- [x] WebSocket live progress (Django Channels)
- [x] Hybrid BM25 + vector search with Reciprocal Rank Fusion
- [x] Open Library API enrichment for author + descriptions
