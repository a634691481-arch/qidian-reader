// 聚合出口：组件统一从 '../store' 引入，无需关心内部拆分
export * from './core';
export * from './token';
export * from './search';
export * from './book';
export * from './reader';
export * from './scan';
export * from './export';
export * from './task';
export * from './login';

import * as api from '../api';
import { chan, fail } from './core';
import { loadLoginState } from './login';
import { refreshToken } from './token';

/** 启动初始化：通道标识 + 令牌 + 登录态 */
export async function bootstrap() {
  chan.value = api.channel();
  try {
    await refreshToken();
    await loadLoginState();
  } catch (e) {
    fail(e);
  }
}
