<script setup>
import { computed } from 'vue';
import { useTheme } from '../lib/theme';
import {
  chan,
  current,
  doLogout,
  download,
  exportPercent,
  exportState,
  loading,
  login,
  openLogin,
  refreshToken,
  tab,
  token,
} from '../store';

const { c, label, cycle, theme } = useTheme();
const hasBook = computed(() => !!current.value?.chapters?.length);
</script>

<template>
  <header :class="['sticky top-0 z-30 border-b backdrop-blur-md', c.border, c.headerBg]">
    <div class="mx-auto flex h-12 max-w-[1180px] items-center gap-3 px-4">
      <button class="flex items-center gap-2" @click="tab = 'search'">
        <span class="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500 text-[13px] font-bold text-zinc-950">起</span>
        <span class="text-sm font-semibold tracking-tight">起点阅读器</span>
      </button>

      <span
        :class="['hidden rounded-full border border-emerald-600/40 px-2 py-0.5 text-[10px] font-medium text-emerald-500 sm:inline',
                 theme === 'dark' ? 'bg-emerald-500/10' : 'bg-emerald-500/5']"
      >纯算 · 无浏览器</span>
      <span v-if="chan" :class="['rounded-full border px-2 py-0.5 text-[10px]', c.border, c.faint]">{{ chan }}</span>

      <div class="ml-auto flex items-center gap-1.5">
        <button
          :class="['group flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] transition', c.btn]"
          :title="token.ok ? `w_tsfp ${token.len} 字符 · ${token.age}s 前生成，点击重铸` : '点击铸造 w_tsfp'"
          :disabled="loading"
          @click="refreshToken(true)"
        >
          <span :class="['h-1.5 w-1.5 rounded-full', token.ok ? 'bg-emerald-500' : 'bg-rose-500']"></span>
          <span :class="c.sub">{{ token.ok ? '令牌' : '待铸' }}</span>
          <span v-if="token.ok" :class="['tabular-nums', c.dim]">{{ token.len }}</span>
        </button>

        <button
          v-if="!login.loggedIn"
          class="rounded-md bg-emerald-500 px-2.5 py-1 text-[11px] font-medium text-zinc-950 transition hover:bg-emerald-400"
          @click="openLogin"
        >微信登录</button>

        <div
          v-else
          :class="['flex items-center gap-1 rounded-md border border-emerald-600/40 px-2 py-1 text-[11px]',
                   theme === 'dark' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-emerald-500/10 text-emerald-600']"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          <span class="max-w-[92px] truncate">{{ login.ywopenid || '已登录' }}</span>
          <button :class="['ml-0.5 transition hover:text-rose-500', c.dim]" title="退出登录" @click="doLogout">退出</button>
        </div>

        <button
          v-if="hasBook && tab !== 'search'"
          :class="['hidden rounded-md border px-2 py-1 text-[11px] transition sm:block', c.btn]"
          :disabled="loading || exportState?.running"
          @click="download"
        >{{ exportState?.running ? `${exportPercent ?? 0}%` : '导出' }}</button>

        <button
          :class="['rounded-md border px-2 py-1 text-[11px] transition', c.btn]"
          :title="`主题：${label}（T 切换）`"
          @click="cycle"
        >{{ label }}</button>
      </div>
    </div>
  </header>
</template>
