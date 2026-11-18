// 双通道：Tauri 内走 IPC（无端口、无 HTTP），浏览器内回退到 HTTP（仅调试用）
const BASE = '/api';

function getInvoke() {
  if (typeof window === 'undefined') return null;
  const t = window.__TAURI__;
  const inv = t?.core?.invoke || t?.tauri?.invoke || window.__TAURI_INTERNALS__?.invoke;
  return typeof inv === 'function' ? inv : null;
}

const hasTauri = () => !!getInvoke();

let lastError = '';
export const channel = () => (getInvoke() ? 'ipc' : 'http');

async function call(cmd, params = {}) {
  const invoke = getInvoke();
  if (invoke) {
    try {
      const r = await invoke('qidian', { cmd, params });
      lastError = '';
      return r;
    } catch (e) {
      lastError = `IPC ${cmd} 失败: ${String(e?.message || e)}`;
      throw new Error(lastError);
    }
  }
  return httpFallback(cmd, params);
}

async function httpFallback(cmd, params) {
  const j = async (url, opt) => {
    const r = await fetch(BASE + url, opt);
    const t = await r.text();
    try {
      return JSON.parse(t);
    } catch {
      return { ok: false, error: t.slice(0, 200) };
    }
  };
  const post = (url) =>
    j(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  const postJson = (url, body) =>
    j(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

  switch (cmd) {
    case 'ping':
      return { ok: true, pong: true, via: 'http' };
    case 'token':
      return j('/token' + (params.force ? '?force=1' : ''));
    case 'search':
      return j('/search?kw=' + encodeURIComponent(params.kw || '') + '&page=' + (params.page || 1));
    case 'book':
      return j('/book?bookId=' + encodeURIComponent(params.bookId || ''));
    case 'chapter':
      return j(`/chapter?bookId=${encodeURIComponent(params.bookId)}&chapterId=${encodeURIComponent(params.chapterId)}`);
    case 'login_qr':
      return post('/login/qr');
    case 'login_poll':
      return j('/login/poll?sid=' + encodeURIComponent(params.sid || ''));
    case 'sources':
      return j('/sources');
    case 'login_state':
      return j('/login/state');
    case 'logout':
      return post('/logout');
    case 'export_plan':
      return j(`/export/plan?bookId=${encodeURIComponent(params.bookId)}&max=${params.max || 80}`);
    case 'export_chunk':
      return postJson('/export/chunk', { bookId: params.bookId, items: params.items || [] });
    default:
      return { ok: false, error: 'unknown cmd ' + cmd };
  }
}

export const health = () => call('login_state');
export const getToken = (force) => call('token', { force: !!force });
export const search = (kw, page = 1) => call('search', { kw, page });
export const book = (bookId) => call('book', { bookId });
export const chapter = (bookId, chapterId) => call('chapter', { bookId, chapterId });
export const loginQr = () => call('login_qr', {});
export const loginPoll = (sid) => call('login_poll', { sid });
export const loginState = () => call('login_state', {});
export const logout = () => call('logout', {});
export async function saveText(defaultName, content) {
  const invoke = getInvoke();
  if (invoke) {
    try {
      const path = await invoke('save_text', { defaultName, content });
      return { ok: true, path }; // path === null 表示用户取消
    } catch (e) {
      console.warn('save_text 失败，回退下载', e);
      return { ok: true, ...(await blobDownload(defaultName, content)), fallback: true, error: String(e?.message || e) };
    }
  }
  return { ok: true, ...(await blobDownload(defaultName, content)), fallback: true };
}

async function blobDownload(name, content) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
  return { path: name };
}

export const exportPlan = (bookId, max = 80) => call('export_plan', { bookId, max });
export const exportChunk = (bookId, items) => call('export_chunk', { bookId, items });
export const sources = () => call('sources');
export const viaTauri = hasTauri;
