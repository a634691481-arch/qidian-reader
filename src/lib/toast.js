// 轻量 toast：全局单例，组件直接读 toast 状态
import { ref } from 'vue';

export const toast = ref({ show: false, text: '', kind: 'ok' });

let timer = null;

export function notify(text, kind = 'ok') {
  toast.value = { show: true, text, kind };
  clearTimeout(timer);
  timer = setTimeout(() => {
    toast.value.show = false;
  }, 2600);
}
