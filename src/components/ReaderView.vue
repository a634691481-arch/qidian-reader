<script setup>
import { ref, watch } from 'vue';
import { useTheme } from '../lib/theme';
import { chapterData, curIdx, current, paragraphs, step, tab } from '../store';
import { notify } from '../lib/toast';

const { c } = useTheme();
const fontSize = ref(Number(localStorage.getItem('qd.font') || 18));
const immersive = ref(false);

watch(fontSize, (v) => localStorage.setItem('qd.font', String(v)));
watch(tab, (v) => {
  if (v !== 'reader') immersive.value = false;
});

defineExpose({
  toggleImmersive: () => (immersive.value = !immersive.value),
  exitImmersive: () => (immersive.value = false),
  get immersive() {
    return immersive.value;
  },
});

function go(dir) {
  step(dir);
}

async function copyLink() {
  const url = `https://www.qidian.com/chapter/${current.value?.bookId}/${chapterData.value?.chapterId}/`;
  try {
    await navigator.clipboard.writeText(url);
    notify('章节链接已复制');
  } catch {
    notify('复制失败', 'warn');
  }
}
</script>

<template>
  <section v-if="chapterData">
    <!-- 工具栏吸顶 -->
    <div v-if="!immersive"
         :class="['sticky top-12 z-20 -mx-4 mb-5 flex flex-wrap items-center gap-2 border-b px-4 py-2', c.solid, c.borderSoft]">
      <button :class="['rounded-lg border px-2.5 py-1.5 text-[11px] transition', c.btn]" @click="tab = 'book'">← 目录</button>

      <div :class="['flex overflow-hidden rounded-lg border', c.border]">
        <button :class="['px-2.5 py-1.5 text-[11px] transition disabled:opacity-30', c.hover]" :disabled="curIdx <= 0" @click="go(-1)">上一章</button>
        <div :class="['w-px', c.separator]"></div>
        <button
          :class="['px-2.5 py-1.5 text-[11px] transition disabled:opacity-30', c.hover]"
          :disabled="curIdx < 0 || curIdx >= (current?.chapters?.length || 0) - 1"
          @click="go(1)"
        >下一章</button>
      </div>

      <span :class="['text-[11px] tabular-nums', c.faint]">
        {{ curIdx + 1 }} / {{ current?.chapters?.length }} · {{ chapterData.chars }} 字
      </span>

      <div class="ml-auto flex items-center gap-1">
        <div :class="['flex overflow-hidden rounded-lg border', c.border]">
          <button :class="['px-2 py-1.5 text-[11px]', c.hover]" @click="fontSize = Math.max(14, fontSize - 1)">A−</button>
          <div :class="['w-px', c.separator]"></div>
          <button :class="['px-2 py-1.5 text-[11px]', c.hover]" @click="fontSize = Math.min(26, fontSize + 1)">A＋</button>
        </div>
        <button :class="['rounded-lg border px-2 py-1.5 text-[11px] transition', c.btn]" title="沉浸模式（F）" @click="immersive = true">沉浸</button>
      </div>
    </div>

    <article class="mx-auto max-w-[680px]">
      <h2 class="mb-1 text-center text-[19px] font-semibold tracking-tight">{{ chapterData.name || chapterData.title }}</h2>
      <div :class="['mb-7 flex items-center justify-center gap-2 text-[11px]', c.faint]">
        <span>{{ current?.title }}</span>
        <span>·</span>
        <span>{{ chapterData.words || chapterData.chars }} 字</span>
        <span
          v-if="chapterData.source && chapterData.source !== 'qidian'"
          class="rounded border border-emerald-600/50 px-1.5 py-0.5 text-[10px] text-emerald-500"
          title="付费章由外部书源补全"
        >来源：{{ chapterData.source === 'cache' ? '本地缓存' : chapterData.source }}</span>
      </div>

      <!-- 未订阅：试读提示 -->
      <div
        v-if="chapterData.teaser"
        :class="['mb-4 flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-lg border border-amber-600/40 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-500']"
      >
        <span class="font-medium">试读片段</span>
        <span :class="c.dim">共 {{ chapterData.words }} 字，已显示 {{ chapterData.chars }} 字</span>
        <span v-if="chapterData.price" :class="c.dim">· 需 {{ chapterData.price }} 起点币订阅</span>
        <span v-if="chapterData.paid && chapterData.fallback === false" :class="c.dim">· 外部书源未命中</span>
        <button class="ml-auto rounded border border-amber-600/50 px-2 py-0.5 transition hover:bg-amber-500/15" @click="copyLink">复制章节链接</button>
      </div>

      <div v-if="!paragraphs.length" :class="['rounded-xl border px-4 py-10 text-center text-xs', c.border, c.dim]">
        本章未下发正文（VIP 未订阅，或令牌已过期）
      </div>

      <div v-else class="reader-body" :style="{ fontSize: fontSize + 'px' }">
        <p v-for="(para, i) in paragraphs" :key="i" :class="i === 0 ? 'no-indent' : ''">{{ para }}</p>
      </div>

      <div :class="['mt-10 flex items-center justify-between gap-3 border-t pt-5', c.border]">
        <button :class="['rounded-lg border px-3 py-2 text-xs transition disabled:opacity-30', c.btn]" :disabled="curIdx <= 0" @click="go(-1)">← 上一章</button>
        <button
          class="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-medium text-zinc-950 transition hover:bg-emerald-400 disabled:opacity-30"
          :disabled="curIdx < 0 || curIdx >= (current?.chapters?.length || 0) - 1"
          @click="go(1)"
        >下一章 →</button>
      </div>

      <p :class="['mt-3 text-center text-[10px]', c.faint]">快捷键：← → 翻章 · F 沉浸 · T 主题 · Esc 返回目录</p>
    </article>
  </section>
</template>

<style scoped>
.reader-body p {
  margin: 0;
  line-height: 1.92;
  letter-spacing: 0.01em;
  text-indent: 2em;
  word-break: break-word;
}
.reader-body p + p {
  margin-top: 0.22em;
}
.reader-body p.no-indent {
  text-indent: 0;
}
</style>
