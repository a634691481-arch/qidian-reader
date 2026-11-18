// 正文阅读
import { computed, ref, watch } from 'vue';
import * as api from '../api';
import { err, fail, loading, tab } from './core';
import { current } from './book';
import { chapterMarks } from './scan';
import { markOf } from '../lib/marks';

export const chapterData = ref(null);

export const curIdx = computed(() => {
  if (!current.value || !chapterData.value) return -1;
  return current.value.chapters.findIndex((x) => x.chapterId === chapterData.value.chapterId);
});

export const progress = computed(() => {
  const total = current.value?.chapters?.length || 0;
  return total && curIdx.value >= 0 ? ((curIdx.value + 1) / total) * 100 : 0;
});

export const paragraphs = computed(() =>
  String(chapterData.value?.body || '')
    .split('\n')
    .filter((x) => x.trim()),
);

export async function openChapter(chapter) {
  loading.value = true;
  err.value = '';
  try {
    const r = await api.chapter(current.value.bookId, chapter.chapterId);
    if (!r.ok) err.value = r.note || `HTTP ${r.status} · ${r.chars || 0} 字`;
    chapterData.value = { ...r, chapterId: chapter.chapterId, name: chapter.name, words: chapter.words };
    // 读过的章顺手把标记补上，省得再探
    chapterMarks.value[chapter.chapterId] = markOf(r);   // 只触发该行重渲染
    tab.value = 'reader';
    window.scrollTo({ top: 0 });
  } catch (e) {
    fail(e);
  } finally {
    loading.value = false;
  }
}

export function step(dir) {
  const book = current.value;
  if (!book) return;
  const next = curIdx.value + dir;
  if (next < 0 || next >= book.chapters.length) return;
  openChapter(book.chapters[next]);
}

const lastKey = (bookId) => 'qd.last.' + bookId;
export const hasLast = computed(() => {
  const book = current.value;
  const id = book ? localStorage.getItem(lastKey(book.bookId)) : null;
  return !!id && !!book?.chapters?.some((x) => x.chapterId === id);
});

export function continueRead() {
  const book = current.value;
  if (!book?.chapters?.length) return;
  const id = localStorage.getItem(lastKey(book.bookId));
  const target = book.chapters.find((x) => x.chapterId === id) || book.chapters[0];
  openChapter(target);
}

watch(chapterData, (d) => {
  if (d?.chapterId && current.value) localStorage.setItem(lastKey(current.value.bookId), d.chapterId);
});