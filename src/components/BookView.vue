<script setup>
import { useTheme } from '../lib/theme';
import {
  catalogQ,
  chapterData,
  chapterMarks,
  continueRead,
  current,
  download,
  hasLast,
  loading,
  openChapter,
  scanBook,
  scanState,
  stopScan,
  tab,
  volumes,
} from '../store';

const { c } = useTheme();

// 一章到底能不能读：探测结果优先，没探过就退回目录里的 VIP 标记
function badge(ch) {
  const m = chapterMarks.value[ch.chapterId];
  if (m) {
    if (m.mark === 'free') return { text: '免费', cls: 'border-emerald-600/50 text-emerald-500' };
    if (m.mark === 'rescue') return { text: (m.ratio && m.ratio < 0.9) ? '已解锁·残' : '已解锁', cls: 'border-emerald-500/60 text-emerald-400' };
    return { text: '锁定', cls: 'border-zinc-500/40 text-zinc-400' };
  }
  return ch.free === false ? { text: 'VIP', cls: 'border-amber-600/50 text-amber-500' } : null;
}
</script>

<template>
  <section v-if="current" class="grid gap-6 lg:grid-cols-[268px_1fr]">
    <aside class="lg:sticky lg:top-16 lg:self-start">
      <div class="flex gap-4">
        <img
          v-if="current.cover"
          :src="current.cover"
          :alt="current.title"
          referrerpolicy="no-referrer"
          class="h-[148px] w-[111px] shrink-0 rounded-lg object-cover shadow-lg ring-1 ring-black/10"
        />
        <div class="min-w-0 flex-1">
          <h1 class="text-[17px] font-semibold leading-snug">{{ current.title }}</h1>
          <p :class="['mt-1 text-xs', c.sub]">{{ current.author || '—' }}</p>
          <div class="mt-2 flex flex-wrap gap-1">
            <span v-if="current.cat" :class="['rounded px-1.5 py-0.5 text-[10px]', c.chip]">{{ current.cat }}</span>
            <span v-if="current.bookStatus" :class="['rounded px-1.5 py-0.5 text-[10px]', c.chip]">{{ current.bookStatus }}</span>
            <span v-if="current.words" :class="['rounded px-1.5 py-0.5 text-[10px]', c.chip]">{{ current.words }}字</span>
          </div>
        </div>
      </div>

      <p :class="['mt-3 line-clamp-4 text-[11.5px] leading-relaxed', c.dim]">{{ current.intro || '（暂无简介）' }}</p>

      <div class="mt-4 flex flex-col gap-2">
        <button
          class="rounded-lg bg-emerald-500 py-2 text-xs font-medium text-zinc-950 transition hover:bg-emerald-400"
          @click="continueRead"
        >{{ hasLast ? '继续阅读' : '开始阅读' }}</button>
        <div class="flex gap-2">
          <button :class="['flex-1 rounded-lg border py-1.5 text-[11px] transition', c.btn]" @click="tab = 'search'">返回搜索</button>
          <button
            :class="['relative flex-1 overflow-hidden rounded-lg border py-1.5 text-[11px] transition disabled:cursor-not-allowed', c.btn]"
            :disabled="loading || exportState?.running"
            @click="download"
          >
            <span v-if="exportState?.running" class="absolute inset-0 bg-emerald-500/20 transition-[width] duration-300" :style="{ width: (exportPercent ?? 0) + '%' }"></span>
            <span class="relative">
              {{ exportState?.running ? `导出中 ${exportPercent}%` : '导出 TXT' }}
            </span>
          </button>
        </div>

        <div v-if="exportState?.running" class="flex items-center gap-2 text-[10px]" :class="c.dim">
          <span class="tabular-nums">{{ exportState?.done ?? 0 }}/{{ exportState?.total ?? 0 }} 章</span>
          <span>·</span>
          <span class="tabular-nums">{{ exportState?.chars ?? 0 }} 字</span>
          <button class="ml-auto transition hover:text-rose-500" @click="cancelExport">取消</button>
        </div>
      </div>

      <div :class="['mt-4 rounded-lg border p-2.5 text-[11px] leading-relaxed', c.border, c.panel]">
        <div class="flex justify-between"><span :class="c.dim">目录</span><span>{{ current.chapterCount }} 章</span></div>
        <div v-if="current.source" class="mt-1 flex justify-between">
          <span :class="c.dim">数据源</span><span class="truncate pl-2">{{ current.source }}</span>
        </div>
      </div>
    </aside>

    <div>
      <div :class="['sticky top-12 z-10 -mx-2 mb-2 flex items-center gap-2 px-2 py-2', c.bg]">
        <input
          v-model="catalogQ"
          :class="['h-8 flex-1 rounded-lg border px-2.5 text-[11px] outline-none transition focus:ring-2 focus:ring-emerald-500/25', c.input]"
          placeholder="搜索章节标题…"
        />
        <button
          v-if="!scanState.on"
          :class="['h-8 shrink-0 rounded-lg border border-emerald-600/50 px-2.5 text-[11px] font-medium text-emerald-500 transition hover:bg-emerald-500/10']"
          title="逐章探测：能读的标免费，需要订阅的找可读来源，标为已解锁或锁定"
          @click="scanBook(20)"
        >🔓 解锁 VIP</button>
        <button
          v-else
          :class="['h-8 shrink-0 rounded-lg border border-amber-600/50 px-2.5 text-[11px] text-amber-500 transition hover:bg-amber-500/10']"
          @click="stopScan"
        >停止</button>
        <span :class="['shrink-0 text-[11px] tabular-nums', c.faint]">{{ current.chapterCount }} 章</span>
      </div>

      <!-- 探测进度 -->
      <div v-if="scanState.total" class="mb-2 flex items-center gap-2">
        <div :class="['h-1 flex-1 overflow-hidden rounded-full', c.border, 'bg-current/10']">
          <div
            class="h-full rounded-full bg-emerald-500 transition-all"
            :style="{ width: (scanState.done / scanState.total) * 100 + '%' }"
          ></div>
        </div>
        <span :class="['shrink-0 text-[10px] tabular-nums', c.faint]">
          {{ scanState.done }}/{{ scanState.total }}
          <span class="text-emerald-500">· 解锁 {{ scanState.done - scanState.locked }}</span>
          <span v-if="scanState.locked"> · 锁定 {{ scanState.locked }}</span>
        </span>
      </div>

      <!-- 仅目录区滚动 -->
      <div :class="['overflow-hidden rounded-xl border', c.border]">
        <div v-for="vol in volumes" :key="vol.name">
          <div :class="['sticky top-0 z-[1] flex items-center justify-between border-b px-3 py-1.5 text-[11px] font-medium backdrop-blur',
                       c.border, c.stickyBg]">
            <span class="truncate">{{ vol.name }}</span>
            <span :class="['ml-2 shrink-0 tabular-nums', c.faint]">{{ vol.chapters.length }}</span>
          </div>

          <button
            v-for="ch in vol.chapters"
            :key="ch.chapterId"
            :class="['flex w-full items-center gap-3 border-b px-3 py-2 text-left text-[12.5px] transition last:border-0',
                     c.borderSoft, c.hover,
                     chapterData?.chapterId === ch.chapterId ? 'bg-emerald-500/10 text-emerald-500' : '']"
            @click="openChapter(ch)"
          >
            <span class="line-clamp-1 flex-1">{{ ch.name }}</span>
            <span v-if="ch.words" :class="['shrink-0 text-[10px] tabular-nums', c.faint]">{{ ch.words }}字</span>
            <span
              v-if="badge(ch)"
              :class="['shrink-0 rounded border px-1 text-[9px]', badge(ch).cls]"
            >{{ badge(ch).text }}</span>
          </button>

          <div v-if="!vol.chapters.length" :class="['px-3 py-3 text-[11px]', c.faint]">无匹配章节</div>
        </div>
      </div>
    </div>
  </section>
</template>
