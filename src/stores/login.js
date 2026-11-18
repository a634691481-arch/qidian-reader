// 扫码登录
import { ref } from 'vue';
import * as api from '../api';
import { notify } from '../lib/toast';
import { fail } from './core';
import { refreshToken } from './token';

export const login = ref({
  open: false,
  image: '',
  status: 'idle',
  msg: '',
  sid: '',
  loggedIn: false,
  ywopenid: '',
});

let loginTimer = null;
let loginBusy = false;

export async function openLogin() {
  login.value = { open: true, image: '', status: 'pending', msg: '', sid: '', loggedIn: false, ywopenid: '' };
  clearTimeout(loginTimer);
  let r;
  try {
    r = await api.loginQr();
  } catch (e) {
    login.value.status = 'expired';
    login.value.msg = String(e?.message || e);
    fail(e);
    return;
  }
  if (!r.ok) {
    login.value.status = 'expired';
    login.value.msg = r.msg || '二维码获取失败';
    return;
  }
  login.value.image = r.image;
  login.value.sid = r.sid;
  login.value.msg = r.msg || '';
  loginTimer = setTimeout(tickLogin, 800);
}

async function tickLogin() {
  const sid = login.value.sid;
  if (!sid || loginBusy || !login.value.open) return;
  loginBusy = true;
  let r = {};
  try {
    r = await api.loginPoll(sid);
  } finally {
    loginBusy = false;
  }
  if (!login.value.open) return;
  login.value.status = r.status || 'pending';
  login.value.msg = r.msg || '';
  if (r.status === 'pending' || r.status === 'scanned') loginTimer = setTimeout(tickLogin, 1200);
  if (r.status === 'confirmed') {
    clearTimeout(loginTimer);
    login.value.loggedIn = true;
    login.value.ywopenid = r.user?.ywopenid || '';
    await refreshToken(true);
    setTimeout(async () => {
      await loadLoginState();
      closeLogin();
      notify('登录成功');
    }, 900);
  }
}

export function closeLogin() {
  clearTimeout(loginTimer);
  login.value.open = false;
}

export async function loadLoginState() {
  const r = await api.loginState();
  login.value.loggedIn = !!r.loggedIn;
  login.value.ywopenid = r.ywopenid || '';
}

export async function doLogout() {
  await api.logout();
  await loadLoginState();
  await refreshToken(true);
  notify('已退出登录', 'warn');
}