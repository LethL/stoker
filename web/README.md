# web — Stoker UI

Vue 3.5 SPA (Vite + TypeScript + Tailwind). Управляющий UI: список ригов,
статус подключения, embedded Grafana панели через iframe. State — Pinia,
server-state — TanStack Vue Query, роутинг — Vue Router (подключаются на M3).

**Статус: M1** — shell со страницей-заглушкой. Реальный UI — M3.

## Запуск (dev)

```bash
pnpm install
pnpm dev          # http://localhost:5173
```

## Проверки

```bash
pnpm lint         # ESLint (Vue + TS)
pnpm typecheck    # vue-tsc
pnpm test         # vitest
pnpm build        # прод-сборка (vue-tsc + vite build)
```

Стек: Vue 3.5 `<script setup>`, Vite 8, Tailwind v4, Vitest + @vue/test-utils.
Обоснование выбора Vue (а не React) — `docs/decisions/0007-ui-framework-vue.md`.
