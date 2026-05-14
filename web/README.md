# Best7DaysMula — Web

Next.js 14 (App Router, TypeScript) frontend for the Best7DaysMula multi-agent
stock screener. Talks to the FastAPI backend over JSON with cookie auth.

## Install

```bash
cd web
npm install
```

## Develop

```bash
npm run dev
```

Open http://localhost:3000.

## Test

```bash
npm test
```

Vitest + React Testing Library, jsdom env. The `fetch` global is mocked per-test.

## Build

```bash
npm run build
```

## Required environment

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend. All requests include credentials (cookies). |

Copy `.env.local.example` to `.env.local` and adjust as needed.

## Backend contract

The frontend expects these endpoints (see `lib/api.ts`):

- `GET /api/auth/me`, `GET /api/auth/login/google`, `POST /api/auth/logout`
- `GET|POST /api/tickers`, `PATCH|DELETE /api/tickers/{symbol}`
- `GET /api/news/market`, `GET /api/news/ticker/{symbol}`
- `POST /api/screener/run`

## Aesthetic

Green-on-black mono "gstack" terminal vibe. Square borders, pill buttons,
ASCII banner, uppercase labels prefixed with `>`.
