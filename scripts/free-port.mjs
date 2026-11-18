// 释放被占用的开发端口（Windows：netstat + taskkill）
import { execSync } from 'node:child_process';

const port = process.argv[2] || process.env.PORT || '5174';

function pidsOnPort(p) {
  try {
    const out = execSync(`netstat -ano -p tcp`, { encoding: 'utf8', windowsHide: true });
    return [
      ...new Set(
        out
          .split(/\r?\n/)
          .filter((l) => l.includes(`:${p}`) && /LISTENING/i.test(l))
          .map((l) => l.trim().split(/\s+/).pop())
          .filter((x) => x && x !== '0'),
      ),
    ];
  } catch {
    return [];
  }
}

const pids = pidsOnPort(port);
if (!pids.length) {
  console.log(`[port] ${port} free`);
  process.exit(0);
}
for (const pid of pids) {
  try {
    execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore', windowsHide: true });
    console.log(`[port] killed pid ${pid} on ${port}`);
  } catch {
    console.log(`[port] failed to kill ${pid}`);
  }
}
