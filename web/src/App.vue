<script setup lang="ts">
// learn: SFC + <script setup lang="ts"> — основной формат компонента Vue 3.5.
// Заглушка M1; реальный UI (список ригов, статус, Grafana-iframe) — на M3.
const title = "Stoker"
</script>

<template>
  <main class="flex min-h-screen flex-col items-center justify-center gap-2 text-center">
    <h1 class="text-4xl font-semibold tracking-tight">{{ title }}</h1>
    <p class="text-gray-500">Мониторинг и управление майнинг-ригами</p>
    <span class="text-sm text-gray-400">M1 skeleton</span>
  </main>
</template>
