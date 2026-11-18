// 通用状态：页面、加载、错误、通道
import { ref } from 'vue';

export const tab = ref('search'); // search | book | reader
export const loading = ref(false);
export const err = ref('');
export const chan = ref('');

export function clearError() {
  err.value = '';
}
export function fail(e) {
  err.value = String(e?.message || e || '未知错误');
}