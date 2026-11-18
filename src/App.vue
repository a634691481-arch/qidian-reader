<script setup>
import { onMounted, ref } from 'vue';
import AppHeader from './components/AppHeader.vue';
import BookView from './components/BookView.vue';
import LoginModal from './components/LoginModal.vue';
import ReaderView from './components/ReaderView.vue';
import TaskOverlay from './components/TaskOverlay.vue';
import SearchView from './components/SearchView.vue';
import { useTheme } from './lib/theme';
import { toast } from './lib/toast';
import { bootstrap, clearError, closeLogin, current, err, loading, login, progress, step, tab } from './store';

const { c, cycle } = useTheme();
const searchRef = ref(null);
const readerRef = ref(null);
const showTop = ref(false);

function onKey(e) {
  const typing = /INPUT|TEXTAREA/.test(document.activeElement?.tagName || '');

  if (e.key === '/' && !typing) {
    e.preventDefault();
    tab.value = 'search';
    searchRef.value?.focus();
    return;
  }
  if (login.value.open) {
    if (e.key === 'Escape') closeLogin();
    return;
  }
  if (typing) return;

  if (e.key.toLowerCase() === 't') cycle();

  if (tab.value !== 'reader') return;
  if (e.key === 'ArrowRight') step(1);
  if (e.key === 'ArrowLeft') step(-1);
  if (e.key === 'Escape') {
    tab.value = 'book';
    readerRef.value?.exitImmersive();
  }
  if (e.key.toLowerCase() === 'f') readerRef.value?.toggleImmersive();
}

onMounted(() => {
  window.addEventListener('keydown', onKey);
  window.addEventListener('scroll', () => (showTop.value = window.scrollY > 600), { passive: true });
  bootstrap();
});

function scrollTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>

<template>
  <div :class="['min-h-screen antialiased', c.bg, c.fg]">
    <AppHeader />

    <div v-if="tab === 'reader'" class="h-0.5 w-full">
      <div class="h-full bg-emerald-500 transition-[width] duration-300" :style="{ width: progress + '%' }"></div>
    </div>

    <main
      :class="[
        'mx-auto px-4',
        tab === 'reader' ? 'max-w-[860px] pt-6 pb-10' : 'max-w-[1180px] pt-5 pb-16',
      ]"
    >
      <Transition name="fade">
        <div
          v-if="err"
          class="mb-4 flex items-start gap-2 rounded-lg border border-rose-700/50 bg-rose-950/40 px-3 py-2 text-xs text-rose-300"
        >
          <span class="mt-px">⚠</span>
          <span class="flex-1 leading-relaxed">{{ err }}</span>
          <button class="text-rose-400/70 hover:text-rose-300" @click="clearError">✕</button>
        </div>
      </Transition>

      <SearchView v-show="tab === 'search'" ref="searchRef" />
      <BookView v-if="tab === 'book' && current" />
      <div v-else-if="tab === 'book'" class="flex flex-col items-center gap-3 py-24 text-center">
        <p :class="['text-xs', c.dim]">{{ loading ? '正在加载目录…' : '未取到目录数据' }}</p>
        <button :class="['rounded-lg border px-3 py-1.5 text-[11px]', c.btn]" @click="tab = 'search'">返回搜索</button>
      </div>
      <ReaderView v-if="tab === 'reader'" ref="readerRef" />
    </main>

    <Transition name="fade">
      <button
        v-if="showTop"
        :class="['fixed bottom-6 right-6 z-40 flex h-10 w-10 items-center justify-center rounded-full border shadow-lg backdrop-blur transition hover:-translate-y-0.5', c.border, c.solid]"
        @click="scrollTop"
      >↑</button>
    </Transition>

    <Transition name="toast">
      <div
        v-if="toast.show"
        :class="['fixed right-5 top-14 z-[60] rounded-lg border px-3 py-2 text-[11px] shadow-xl backdrop-blur',
                 toast.kind === 'warn'
                   ? 'border-amber-600/50 bg-amber-950/70 text-amber-300'
                   : 'border-emerald-600/50 bg-emerald-950/70 text-emerald-300']"
      >{{ toast.text }}</div>
    </Transition>

    <TaskOverlay />
    <LoginModal />
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.toast-enter-active,
.toast-leave-active {
  transition: all 0.22s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
