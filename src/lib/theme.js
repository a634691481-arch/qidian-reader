// 主题：语义色板 + 切换。组件只依赖语义 token，不写死颜色。
import { computed, ref, watch } from 'vue';

export const THEMES = ['dark', 'sepia', 'light'];

export const TOKENS = {
  dark: {
    bg: 'bg-zinc-950',
    fg: 'text-zinc-100',
    panel: 'bg-zinc-900/60',
    solid: 'bg-zinc-900',
    border: 'border-zinc-800',
    borderSoft: 'border-zinc-800/60',
    sub: 'text-zinc-400',
    dim: 'text-zinc-500',
    faint: 'text-zinc-600',
    input: 'bg-zinc-900 border-zinc-700 text-zinc-100 placeholder:text-zinc-600',
    btn: 'border-zinc-700 hover:bg-zinc-800 text-zinc-200',
    btnSolid: 'bg-zinc-100 text-zinc-900 hover:bg-white',
    chip: 'bg-zinc-800 text-zinc-300',
    hover: 'hover:bg-zinc-900',
    headerBg: 'bg-zinc-950/85',
    stickyBg: 'bg-zinc-950/90',
    separator: 'bg-zinc-800',
  },
  sepia: {
    bg: 'bg-[#f6ecd9]',
    fg: 'text-[#3a2f22]',
    panel: 'bg-[#fbf5e8]',
    solid: 'bg-[#fbf5e8]',
    border: 'border-[#e2d5ba]',
    borderSoft: 'border-[#e2d5ba]/70',
    sub: 'text-[#6b5942]',
    dim: 'text-[#8a7659]',
    faint: 'text-[#a08b6c]',
    input: 'bg-[#fffdf7] border-[#d9c8a8] text-[#3a2f22] placeholder:text-[#b3a184]',
    btn: 'border-[#d9c8a8] hover:bg-[#f0e4cc] text-[#4a3b28]',
    btnSolid: 'bg-[#3a2f22] text-[#fbf5e8] hover:bg-[#241d15]',
    chip: 'bg-[#ede0c6] text-[#6b5942]',
    hover: 'hover:bg-[#f0e4cc]',
    headerBg: 'bg-[#f6ecd9]/90',
    stickyBg: 'bg-[#fbf5e8]/90',
    separator: 'bg-zinc-200',
  },
  light: {
    bg: 'bg-zinc-50',
    fg: 'text-zinc-900',
    panel: 'bg-white',
    solid: 'bg-white',
    border: 'border-zinc-200',
    borderSoft: 'border-zinc-200/80',
    sub: 'text-zinc-600',
    dim: 'text-zinc-500',
    faint: 'text-zinc-400',
    input: 'bg-white border-zinc-300 text-zinc-900 placeholder:text-zinc-400',
    btn: 'border-zinc-300 hover:bg-zinc-100 text-zinc-700',
    btnSolid: 'bg-zinc-900 text-white hover:bg-zinc-800',
    chip: 'bg-zinc-100 text-zinc-600',
    hover: 'hover:bg-zinc-100',
    headerBg: 'bg-white/85',
    stickyBg: 'bg-white/90',
    separator: 'bg-zinc-200',
  },
};

const STORAGE_KEY = 'qd.theme';
const theme = ref(localStorage.getItem(STORAGE_KEY) || 'dark');
watch(theme, (v) => localStorage.setItem(STORAGE_KEY, v));

const label = computed(() => ({ dark: '夜间', sepia: '纸黄', light: '日间' })[theme.value]);
const c = computed(() => TOKENS[theme.value]);

function cycle() {
  theme.value = THEMES[(THEMES.indexOf(theme.value) + 1) % THEMES.length];
}

export function useTheme() {
  return { theme, c, label, cycle };
}
