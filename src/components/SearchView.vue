<script setup>
import { nextTick, onMounted, ref, watch } from 'vue';
import { useTheme } from '../lib/theme';
import {
  clearSearch,
  doSearch,
  hasMore,
  kw,
  loadMore,
  loading,
  loadingMore,
  openBook,
  page,
  recent,
  results,
} from '../store';

const { c } = useTheme();
const inputRef = ref(null);
const sentinel = ref(null);
let observer = null;

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) loadMore();
    },
    { rootMargin: '320px' },
  );
  watch(sentinel, (el, old) => {
    if (old) observer?.unobserve(old);
    if (el) observer?.observe(el);
  });
});

function submit(word) {
  doSearch(word);
  nextTick(() => inputRef.value?.blur());
}

defineExpose({ focus: () => inputRef.value?.focus() });
</script>

<template>
  <section>
    <!-- 有结果时搜索区吸顶 -->
    <div :class="results.length
                    ? ['sticky top-12 z-20 -mx-4 mb-1 px-4 py-2.5 backdrop-blur-md border-b', c.headerBg, c.borderSoft]
                    : 'mx-auto max-w-[720px] mt-[10vh]'">
      <div :class="results.length ? 'mx-auto max-w-[720px]' : ''">
      <template v-if="!results.length">
        <h1 class="mb-1 text-center text-[26px] font-semibold tracking-tight">找一本想读的书</h1>
        <p :class="['mb-6 text-center text-xs', c.dim]">输入书名或作者，直接从起点官方搜索</p>
      </template>

      <div class="relative">
        <span :class="['pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sm', c.faint]">⌕</span>
        <input
          ref="inputRef"
          v-model="kw"
          :class="['h-12 w-full rounded-xl border pl-9 pr-24 text-sm outline-none transition focus:ring-2 focus:ring-emerald-500/30', c.input]"
          placeholder="书名 / 作者，例如：荒野狩猎"
          @keyup.enter="submit()"
        />
        <button
          v-if="kw"
          class="absolute right-[86px] top-1/2 -translate-y-1/2 rounded px-1 text-xs text-zinc-400 transition hover:text-zinc-200"
          title="清空"
          @click="kw = ''"
        >✕</button>
        <div class="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1.5">
          <kbd :class="['hidden rounded border px-1.5 py-0.5 text-[10px] sm:block', c.border, c.faint]">/</kbd>
          <button
            class="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-medium text-zinc-950 transition hover:bg-emerald-400 disabled:opacity-50"
            :disabled="loading"
            @click="submit()"
          >{{ loading ? '搜索中' : '搜索' }}</button>
        </div>
      </div>

      </div>

      <div v-if="!results.length && recent.length" class="mt-4 flex flex-wrap items-center gap-1.5">
        <span :class="['text-[11px]', c.faint]">最近</span>
        <button
          v-for="word in recent"
          :key="word"
          :class="['rounded-full px-2.5 py-1 text-[11px] transition hover:opacity-80', c.chip]"
          @click="submit(word)"
        >{{ word }}</button>
      </div>

      <div v-if="!results.length && !loading" class="mt-14 flex flex-col items-center gap-2 text-center">
        <div :class="['flex h-14 w-14 items-center justify-center rounded-2xl border', c.border, c.panel]">
          <span :class="['text-xl', c.faint]">📖</span>
        </div>
        <p :class="['text-xs', c.dim]">搜索后会显示封面、作者、分类、字数与最新章节</p>
      </div>
    </div>

    <!-- 骨架 -->
    <div v-if="loading && !results.length" class="mx-auto mt-8 max-w-[860px] space-y-3">
      <div v-for="i in 4" :key="i" :class="['flex gap-4 rounded-xl border p-3', c.border, c.panel]">
        <div :class="['h-[128px] w-[96px] shrink-0 animate-pulse rounded-md', c.chip]"></div>
        <div class="flex-1 space-y-2 py-1">
          <div :class="['h-4 w-1/3 animate-pulse rounded', c.chip]"></div>
          <div :class="['h-3 w-1/2 animate-pulse rounded', c.chip]"></div>
          <div :class="['h-3 w-full animate-pulse rounded', c.chip]"></div>
          <div :class="['h-3 w-4/5 animate-pulse rounded', c.chip]"></div>
        </div>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="results.length" class="mt-5">
      <div class="mb-2 flex items-center justify-between">
        <span :class="['text-[11px]', c.dim]">「{{ kw }}」共 {{ results.length }} 条</span>
        <button :class="['text-[11px] transition hover:opacity-70', c.faint]" @click="clearSearch">清空</button>
      </div>

      <div class="grid gap-3 lg:grid-cols-2">
        <button
          v-for="(book, i) in results"
          :key="book.bookId"
          :class="['group flex gap-4 rounded-xl border p-3 text-left transition duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20',
                   c.border, c.panel, c.hover]"
          @click="openBook(book.bookId)"
        >
          <div class="relative shrink-0 overflow-hidden rounded-md ring-1 ring-black/10">
            <img
              v-if="book.cover"
              :src="book.cover"
              :alt="book.name"
              loading="lazy"
              referrerpolicy="no-referrer"
              class="h-[128px] w-[96px] object-cover transition duration-300 group-hover:scale-[1.03]"
            />
            <div v-else :class="['flex h-[128px] w-[96px] items-center justify-center text-[10px]', c.chip, c.faint]">无封面</div>
          </div>

          <div class="min-w-0 flex-1">
            <div class="flex items-start gap-2">
              <span :class="['mt-[3px] w-6 shrink-0 text-right text-[11px] font-semibold tabular-nums', c.faint]">{{ i + 1 }}</span>
              <h3 class="line-clamp-1 flex-1 text-[15px] font-semibold leading-snug transition group-hover:text-emerald-500">{{ book.name }}</h3>
              <span
                v-if="book.status"
                :class="['shrink-0 rounded px-1.5 py-0.5 text-[10px]',
                         book.status === '完结' ? c.chip : 'bg-emerald-500/15 text-emerald-500']"
              >{{ book.status }}</span>
            </div>

            <div :class="['mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px]', c.dim]">
              <span :class="c.sub">{{ book.author || '佚名' }}</span>
              <span v-if="book.cat" :class="['rounded px-1.5 py-px text-[10px]', c.chip]">{{ book.cat }}</span>
              <span v-if="book.words">{{ book.words }}字</span>
              <span v-if="book.recommend">{{ book.recommend }}推荐</span>
              <span v-if="book.date" class="hidden sm:inline">{{ book.date }}</span>
            </div>

            <p :class="['mt-1.5 line-clamp-2 text-[11.5px] leading-relaxed', c.dim]">{{ book.intro || '（暂无简介）' }}</p>

            <div class="mt-1.5 flex items-center gap-1.5 text-[11px]">
              <span :class="['shrink-0', c.faint]">最新</span>
              <span :class="['truncate', c.sub]">{{ book.latest || '—' }}</span>
            </div>
          </div>
        </button>
      </div>

      <div ref="sentinel" class="mt-4 flex items-center justify-center py-4">
        <div v-if="loadingMore" :class="['flex items-center gap-2 text-[11px]', c.dim]">
          <span class="h-3 w-3 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent"></span>
          正在加载第 {{ page + 1 }} 页…
        </div>
        <button v-else-if="hasMore" :class="['text-[11px] transition hover:opacity-70', c.faint]" @click="loadMore">加载更多</button>
        <span v-else :class="['text-[11px]', c.faint]">已经到底了 · 共 {{ results.length }} 部</span>
      </div>
    </div>
  </section>
</template>
