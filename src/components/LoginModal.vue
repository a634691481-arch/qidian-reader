<script setup>
import { useTheme } from '../lib/theme';
import { closeLogin, login, openLogin } from '../store';

const { c } = useTheme();
</script>

<template>
  <div v-if="login.open" class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 p-4" @click="closeLogin">
    <div :class="['w-[400px] overflow-hidden rounded-2xl border shadow-2xl', c.border, c.solid]" @click.stop>
      <div :class="['flex items-center justify-between border-b px-4 py-2.5', c.borderSoft]">
        <div class="text-[13px] font-medium">微信扫码登录</div>
        <button
          type="button"
          aria-label="关闭"
          :class="['flex h-8 w-8 items-center justify-center rounded-md text-lg leading-none transition hover:bg-zinc-500/15', c.dim]"
          @click.stop="closeLogin"
        >✕</button>
      </div>

      <div class="flex flex-col items-center px-6 py-6">
        <div class="relative flex h-[220px] w-[220px] items-center justify-center rounded-xl bg-white p-1.5">
          <img v-if="login.image" :src="login.image" alt="微信二维码" class="h-full w-full object-contain" />
          <div v-else class="text-[11px] text-zinc-500">二维码生成中…</div>
          <div v-if="login.status === 'scanned'" class="absolute inset-0 flex items-center justify-center rounded-xl bg-black/55 text-[11px] text-white">
            已扫码，请在手机确认
          </div>
          <div v-if="login.status === 'expired'" class="absolute inset-0 flex items-center justify-center rounded-xl bg-black/75">
            <button class="rounded-md bg-white px-3 py-1.5 text-[11px] text-zinc-900" @click.stop="openLogin">刷新二维码</button>
          </div>
        </div>

        <p :class="['mt-3 max-w-[280px] text-center text-[11px] leading-relaxed', c.dim]">
          {{ login.msg || '打开微信 · 扫一扫（微信原生确认页）' }}
        </p>
        <button :class="['mt-3 text-[11px] transition hover:opacity-70', c.faint]" @click.stop="openLogin">重新生成</button>
      </div>
    </div>
  </div>
</template>
