<script setup>
import { computed, onUnmounted, ref, watch } from 'vue';
import { useTheme } from '../lib/theme';
import { globalTask } from '../store';

const { c } = useTheme();
const elapsed = ref(0);
let timer = null;

watch(
  () => !!globalTask.value,
  (on) => {
    clearInterval(timer);
    timer = null;
    if (on) {
      elapsed.value = 0;
      timer = setInterval(() => (elapsed.value += 1), 1000);
    }
  },
  { immediate: true },
);
onUnmounted(() => clearInterval(timer));

const clock = computed(() => {
  const m = String(Math.floor(elapsed.value / 60)).padStart(2, '0');
  const s = String(elapsed.value % 60).padStart(2, '0');
  return `${m}:${s}`;
});
</script>

<template>
  <Transition name="fade">
    <div v-if="globalTask" class="fixed inset-0 z-[9990] flex items-center justify-center bg-black/65 backdrop-blur-sm">
      <div :class="['w-[380px] rounded-2xl border p-6 shadow-2xl', c.border, c.solid]">
        <div class="flex items-center gap-2">
          <span class="h-2 w-2 animate-pulse rounded-full bg-emerald-500"></span>
          <span class="text-[13px] font-medium">{{ globalTask.label }}</span>
          <span :class="['ml-auto text-[11px] tabular-nums', c.faint]">已用 {{ clock }}</span>
        </div>

        <div class="mt-5 text-center">
          <div class="text-3xl font-semibold tabular-nums tracking-tight">
            {{ globalTask.percent }}<span :class="['text-base', c.dim]">%</span>
          </div>
          <div :class="['mt-1 text-[11px]', c.dim]">{{ globalTask.detail }}</div>
        </div>

        <div :class="['mt-4 h-1.5 overflow-hidden rounded-full', c.chip]">
          <div class="h-full rounded-full bg-emerald-500 transition-[width] duration-300" :style="{ width: globalTask.percent + '%' }"></div>
        </div>

        <div v-if="globalTask.sub" :class="['mt-3 text-center text-[11px] tabular-nums', c.faint]">
          {{ globalTask.sub }}
        </div>

        <button
          :class="['mt-6 w-full rounded-lg border py-2 text-[11px] transition hover:border-rose-600/60 hover:text-rose-500', c.btn]"
          @click="globalTask.cancel()"
        >{{ globalTask.cancelLabel }}</button>

        <p :class="['mt-3 text-center text-[10px]', c.faint]">任务在后台继续，请勿关闭窗口</p>
      </div>
    </div>
  </Transition>
</template>
