// 章节可读性标记：探测结果 → { mark, label, cls } 的唯一来源
export const MARK_CLS = {
  free: 'border-emerald-600/50 text-emerald-500',
  rescue: 'border-emerald-500/60 text-emerald-400',
  locked: 'border-zinc-500/40 text-zinc-400',
  vip: 'border-amber-600/50 text-amber-500',
};

/** 把 api.chapter 的返回归类成标记 */
export function markOf(res) {
  if (res?.fallback) {
    return { mark: 'rescue', chars: res.chars || 0, source: res.source, ratio: res.ratio };
  }
  if (res?.body && !res?.paid && !res?.teaser) {
    return { mark: 'free', chars: res.chars || 0, source: res.source };
  }
  return { mark: 'locked', chars: res?.chars || 0, paid: !!res?.paid, source: res?.source };
}

/** 目录行的角标：探测结果优先，未探测过则退回目录自带 VIP 标记 */
export function badgeOf(chapter, mark) {
  if (mark) {
    if (mark.mark === 'free') return { text: '免费', cls: MARK_CLS.free };
    if (mark.mark === 'rescue') {
      const partial = mark.ratio && mark.ratio < 0.9;
      return { text: partial ? '已解锁·残' : '已解锁', cls: MARK_CLS.rescue };
    }
    return { text: '锁定', cls: MARK_CLS.locked };
  }
  return chapter?.free === false ? { text: 'VIP', cls: MARK_CLS.vip } : null;
}
