import { createApp } from 'vue';
import App from './App.vue';
import { err } from './store';
import './style.css';

const app = createApp(App);

// 渲染异常不再白屏：写到全局错误条，便于定位
app.config.errorHandler = (e) => {
  err.value = '渲染异常：' + String(e?.message || e);
};

app.mount('#app');
