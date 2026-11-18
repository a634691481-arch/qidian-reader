// 导出 TXT：分片抓取 + 进度 + 取消
import { computed, ref } from 'vue';
import * as api from '../api';
import { notify } from '../lib/toast';
import { err, fail } from './core';
import { current } from './book';

export const exportState = ref({ running: false, done: 0, total: 0, chars: 0, title: '' });
export const exportPercent = computed(() => {
  const { done, total } = exportState.value;
  return total ? Math.round((done / total) * 100) : 0;
});

const CHUNK_SIZE = 6;
let exportAbort = false;

// 运行令牌：每次 download() 递增；cancelExport() 再递增使旧循环作废。
// 分片循环里每个 await 后必须检查 run !== exportRun，否则取消会迟一整个分片。
let exportRun = 0;

export function cancelExport() {
  exportAbort = true;
  exportRun += 1;
  exportState.value = { ...exportState.value, running: false }; // 遮罩立即消失
}

export async function download() {
  const book = current.value;
  if (!book || exportState.value.running) return;

  exportAbort = false;
  const run = ++exportRun;
  exportState.value = { running: true, done: 0, total: 0, chars: 0, title: book.title };
  err.value = '';
  notify('正在获取目录…');

  try {
    const plan = await api.exportPlan(book.bookId, 80);
    if (!plan.ok) {
      err.value = plan.error || '导出失败';
      return;
    }

    exportState.value.total = plan.total;
    const chunks = [];
    for (let i = 0; i < plan.chapters.length; i += CHUNK_SIZE) {
      if (exportAbort || run !== exportRun) {
        notify('已取消导出', 'warn');
        return;
      }
      const slice = plan.chapters.slice(i, i + CHUNK_SIZE);
      const part = await api.exportChunk(book.bookId, slice);
      if (!part.ok) {
        err.value = part.error || '抓取中断';
        return;
      }
      chunks.push(part.text);
      exportState.value.done += slice.length;
      exportState.value.chars += part.text.length;
    }

    const header = `${plan.title}
作者：${plan.author}
来源：https://www.qidian.com/book/${book.bookId}/
`;
    const saved = await api.saveText(`${plan.title}.txt`, header + chunks.join(''));
    if (saved.path === null) {
      notify('已取消保存', 'warn');
      return;
    }
    if (saved.fallback) {
      notify('保存对话框不可用，已改为浏览器下载', 'warn');
    } else {
      notify(`已保存 ${exportState.value.total} 章 · ${saved.path}`);
    }
  } catch (e) {
    fail(e);
  } finally {
    if (run === exportRun) exportState.value.running = false;
  }
}