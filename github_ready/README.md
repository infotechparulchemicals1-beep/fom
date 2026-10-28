# Offline GPS Tracking & Route Mapping Application

A full-stack offline-first GPS tracking application with an **Expo (React Native)** mobile app and a **FastAPI** backend.

## Monorepo Structure

```
location_mobile/
├── mobile/     # Expo app (React Native)
└── backend/    # FastAPI + Supabase backend
```

---

## Mobile App (`/mobile`)

### Setup

```bash
cd mobile
cp .env.example .env        # fill in your Supabase and API values
npm install
npx expo install expo-location expo-sqlite expo-task-manager expo-router \
  zustand @react-native-community/netinfo @maplibre/maplibre-react-native
```

### Run

```bash
# Start Expo dev server
npx expo start

# Run on Android
npx expo run:android
```

### Key Features
- 30-second GPS tracking (foreground & background)
- Offline SQLite storage (survives restarts)
- Haversine distance calculation with drift/accuracy filtering
- MapLibre offline map rendering with route polyline
- Automatic batch sync when connectivity returns
- Trip history with full location replay

### Environment Variables

| Variable | Description |
|---|---|
| `EXPO_PUBLIC_API_URL` | FastAPI backend URL |
| `EXPO_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `EXPO_PUBLIC_MAP_STYLE_URL` | MapLibre style JSON URL |

---

## Backend (`/backend`)

### Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
cp .env.example .env         # fill in your Supabase credentials
```

### Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migration

1. Open your [Supabase SQL Editor](https://supabase.com/dashboard)
2. Run the contents of `backend/supabase_migration.sql`

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/sessions` | Create tracking session |
| `GET` | `/api/v1/sessions` | List user sessions |
| `GET` | `/api/v1/sessions/{id}` | Get session details |
| `POST` | `/api/v1/sessions/{id}/finish` | Finish a session |
| `POST` | `/api/v1/sessions/{id}/locations/batch` | Batch upload points |
| `GET` | `/api/v1/sessions/{id}/locations` | Get route points |

Auto-generated docs at `http://localhost:8000/docs`

### Environment Variables

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (for server-side ops) |
| `JWT_SECRET` | Supabase JWT secret (from project settings) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |

---

## Architecture

```
Device (Expo)                      Server (FastAPI + Supabase)
─────────────────────────────      ──────────────────────────────
GPS → Location Service             POST /sessions
  ↓                                POST /sessions/{id}/locations/batch
SQLite (offline store)     ──────→ Supabase PostgreSQL
  ↓
Sync Service (on connect)
  ↓
Zustand Store → UI
```

### Offline-First Principles
- All GPS data written to SQLite first, regardless of connectivity
- Sync service checks actual backend reachability (not just network)
- Idempotent UUIDs prevent duplicate records on retry
- Failed uploads stay in `pending` state and retry on next sync
- Map tiles must be pre-downloaded for offline map use

---

## Development Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ | Core tracking: GPS, SQLite, dashboard |
| 2 | ✅ | Distance calculation, MapLibre, route visualization |
| 3 | ✅ | FastAPI backend, Supabase, batch sync |
| 4 | 🚧 | Trip history, background hardening, settings |
| 5 | 🔜 | Polish, security review, production deployment |
