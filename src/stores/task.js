// 全局任务聚合：导出 / 解锁 共用一条展示
import { computed } from 'vue';
import { cancelExport, exportPercent, exportState } from './export';
import { scanState, stopScan } from './scan';

export const globalTask = computed(() => {
  if (exportState.value.running) {
    const { done, total } = exportState.value;
    return {
      kind: 'export',
      label: '导出 TXT',
      percent: exportPercent.value,
      detail: done ? `${done}/${total} 章` : '正在获取目录…',
      sub: exportState.value.chars ? `已抓取 ${exportState.value.chars.toLocaleString()} 字` : '',
      cancelLabel: '取消导出',
      cancel: cancelExport,
    };
  }
  const scan = scanState.value;
  if (scan.on && scan.total) {
    return {
      kind: 'scan',
      label: '解锁 VIP',
      percent: Math.round((scan.done / scan.total) * 100),
      detail: `${scan.done} / ${scan.total} 章`,
      sub: `已解锁 ${scan.rescued}${scan.locked ? ` · 锁定 ${scan.locked}` : ''}`,
      cancelLabel: '停止解锁',
      cancel: stopScan,
    };
  }
  return null;
});