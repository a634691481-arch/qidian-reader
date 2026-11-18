// 详情与目录
import { computed, ref } from 'vue';
import * as api from '../api';
import { err, fail, loading, tab } from './core';
import { scanState } from './scan';

export const current = ref(null);
export const catalogQ = ref('');

export const volumes = computed(() => {
  const book = current.value;
  if (!book) return [];
  const flat = book.chapters || [];
  const list = book.volumes?.length
    ? book.volumes
    : [{ name: '全部章节', count: flat.length, chapters: flat }];
  const q = catalogQ.value.trim();
  if (!q) return list;
  return list
    .map((v) => ({ ...v, chapters: (v.chapters || []).filter((x) => x.name.includes(q)) }))
    .filter((v) => v.chapters.length);
});

export async function openBook(bookId) {
  loading.value = true;
  err.value = '';
  try {
    const r = await api.book(bookId);
    if (!r.ok) {
      err.value = r.note || `HTTP ${r.status}`;
      return;
    }
    current.value = r;
    catalogQ.value = '';
    // 换书就清掉上一本的探测结果
    chapterMarks.value = {};
    scanState.value = { on: false, done: 0, total: 0, rescued: 0, locked: 0 };
    tab.value = 'book';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (e) {
    fail(e);
  } finally {
    loading.value = false;
  }
}