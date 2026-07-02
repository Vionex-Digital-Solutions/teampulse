# TeamPulse Web (Frontend)

Next.js 14 (App Router) + TypeScript + Tailwind. Talks to the FastAPI backend.

## Run it

```bash
cd web
npm install
cp .env.example .env      # points to http://localhost:8000 by default
npm run dev
```

Open http://localhost:3000

> Make sure the backend is running too (see ../backend/README or the root README).

## Structure

```
web/
  app/
    layout.tsx       nav + shell
    page.tsx         home
    pulse/page.tsx   ✅ working check-in form (POSTs to backend)
    standup/page.tsx 🚧 starter stub — build me
    kudos/page.tsx   🚧 starter stub — build me
  lib/
    api.ts           API client for the backend
  tailwind.config.ts
```

## Notes

- The Pulse form already POSTs to `/api/v1/pulse`. That backend endpoint is
  still a stub, so it will return a 500 until the backend team implements it.
  That's expected — frontend and backend are built in parallel.
- Standup and Kudos pages are intentionally left as stubs for you to build.
