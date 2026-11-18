// 令牌铸造与状态
import { ref } from 'vue';
import * as api from '../api';
import { notify } from '../lib/toast';
import { fail, loading } from './core';

export const token = ref({ ok: false, len: 0, age: null, ttl: 480 });

export async function refreshToken(force = false) {
  loading.value = true;
  try {
    token.value = await api.getToken(force);
    if (force) notify('令牌已重铸');
  } catch (e) {
    fail(e);
  } finally {
    loading.value = false;
  }
}