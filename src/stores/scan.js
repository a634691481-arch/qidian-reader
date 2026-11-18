// 可读性探测：逐章判断 free / rescue / locked
import { ref } from 'vue';
import * as api from '../api';
import { notify } from '../lib/toast';
import { markOf } from '../lib/marks';
import { current } from './book';

// 每章状态：free=起点直接可读，rescue=外部书源补全，locked=两边都拿不到
export const chapterMarks = ref({});
export const scanState = ref({ on: false, done: 0, total: 0, rescued: 0, locked: 0 });
let scanAbort = false;


let scanRun = 0;

export function stopScan() {
  scanAbort = true;
  scanRun += 1;                                   // 作废正在跑的循环
  scanState.value = { ...scanState.value, on: false };  // 遮罩立即消失
}

/** 逐章探一遍：优先 VIP 章，结果写进 chapterMarks，目录里即时点亮。 */
export async function scanBook(limit = 20) {
  const book = current.value;
  if (!book?.chapters?.length) return;
  if (scanState.value.on) return;

  const targets = book.chapters.filter((c) => c.free === false).slice(0, limit);
  const list = targets.length ? targets : book.chapters.slice(0, limit);

  scanAbort = false;
  const run = ++scanRun;
  scanState.value = { on: true, done: 0, total: list.length, rescued: 0, locked: 0 };
  let rescued = 0;
  let locked = 0;
  let cursor = 0;

  // 每章要打起点 + 外部书源，串行要两三分钟；并发 2 既不慢也不至于踩风控
  async function worker() {
    while (!scanAbort && run === scanRun && cursor < list.length) {
      const ch = list[cursor++];
      let m;
      try {
        m = markOf(await api.chapter(book.bookId, ch.chapterId));
        if (m.mark === 'rescue') rescued += 1;
        if (m.mark === 'locked') locked += 1;
      } catch (e) {
        m = { mark: 'locked', err: String(e?.message || e) };
        locked += 1;
      }
      if (run !== scanRun) return;   // 已被取消，别把遮罩顶回来
      chapterMarks.value[ch.chapterId] = m;
      scanState.value = {
        ...scanState.value,
        done: scanState.value.done + 1,
        total: list.length,
        rescued,
        locked,
      };
    }
  }
  await Promise.all([worker(), worker()]);
  if (run !== scanRun) return;   // 取消后不再弹完成提示

  scanState.value = { ...scanState.value, on: false };
  notify(
    scanState.value.done
      ? `探测 ${scanState.value.done} 章：可读 ${scanState.value.done - locked}，锁定 ${locked}`
      : '探测已停止',
    locked ? 'warn' : 'ok',
  );
}
