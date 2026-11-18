// 搜索与分页
import { ref, watch } from 'vue';
import * as api from '../api';
import { notify } from '../lib/toast';
import { err, fail, loading, tab } from './core';

const RECENT_KEY = 'qd.recent';
export const kw = ref('');
export const results = ref([]);
export const page = ref(1);
export const hasMore = ref(false);
export const loadingMore = ref(false);
export const recent = ref(JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'));

let seenIds = new Set();
watch(recent, (v) => localStorage.setItem(RECENT_KEY, JSON.stringify(v.slice(0, 8))), { deep: true });

function appendItems(items) {
  for (const item of items) {
    if (!item?.bookId || seenIds.has(item.bookId)) continue;
    seenIds.add(item.bookId);
    results.value.push(item);
  }
}

export async function doSearch(word) {
  const q = String(word ?? kw.value).trim();
  if (!q) return;
  kw.value = q;
  loading.value = true;
  err.value = '';
  results.value = [];
  page.value = 1;
  hasMore.value = false;
  seenIds = new Set();
  try {
    const r = await api.search(q, 1);
    if (!r.ok) {
      err.value = r.note || `HTTP ${r.status}`;
    } else {
      appendItems(r.items || []);
      hasMore.value = !!r.hasMore;
      if (!results.value.length) {
        err.value = '没有匹配的作品，换个关键词试试';
      } else {
        recent.value = [q, ...recent.value.filter((x) => x !== q)];
        notify(`找到 ${results.value.length} 部作品`);
      }
    }
    tab.value = 'search';
  } catch (e) {
    fail(e);
  } finally {
    loading.value = false;
  }
}

export async function loadMore() {
  if (!hasMore.value || loadingMore.value || loading.value || !kw.value.trim()) return;
  loadingMore.value = true;
  try {
    const next = page.value + 1;
    const r = await api.search(kw.value.trim(), next);
    if (!r.ok) {
      hasMore.value = false;
      return;
    }
    const before = results.value.length;
    appendItems(r.items || []);
    page.value = next;
    hasMore.value = !!r.hasMore && results.value.length > before;
  } catch {
    hasMore.value = false;
  } finally {
    loadingMore.value = false;
  }
}

export function clearSearch() {
  results.value = [];
  kw.value = '';
  page.value = 1;
  hasMore.value = false;
  seenIds = new Set();
}