# 起点阅读器

Tauri 2 桌面端 + 纯 Python 协议内核。无浏览器、无端口、无第三方 Cookie 导入。

## 启动

```bash
npm run desktop     # 桌面端（自动清端口 + 起 vite + 编译 Rust）
```

仅调试 UI（浏览器）时：

```bash
python server/app.py    # HTTP 适配层 :8788，仅供浏览器访问
```

## 架构

```
Tauri 窗口 (webview)
   │  invoke('qidian', {cmd, params})        ← 生产通道，无端口
   ▼
src-tauri/src/main.rs  常驻子进程 + JSON 行协议
   ▼
server/core.py         命令路由（COMMANDS 表）
   ├─ qidian.py        搜索 / 目录 / 详情 / 正文 / 导出
   ├─ login.py         微信扫码（qrconnect → weixinlogin → weixincallback）
   ├─ slider.py        滑块缺口定位 + 拟人轨迹
   ├─ parse.py         HTML → 结构（纯函数，无 IO）
   ├─ net.py           HTTP：注入 w_tsfp / cookie / UA，自动重试
   ├─ tsfp.py          令牌铸造（V8 跑 probev3.js）与 TTL 缓存
   ├─ paywall.py       付费墙判定 / 试读比例 / 残缺检测
   ├─ source_*.py      外部书源：抓取后端 + 规则适配 + 注册表与缓存
   ├─ store.py         cookie 读写
   └─ config.py        常量集中管理
```

`server/app.py` 只是 HTTP 适配层（调 `api_http.py`），与 `core.py` 共用同一套业务函数。

## 付费墙与外部书源回落

起点对**未购买**的 VIP 章只下发试读片段（实测：4040 字的章节，`chapterInfo.content` 只有 133 字，
`vipStatus=1 / isBuy=0 / price=20`）。QQ 阅读同章同样截断，说明是内容库级限制，与 UA、登录态无关。

因此正文链路是：

```
chapter(bookId, chapterId)
  ├─ 起点 SSR JSON 取正文 + 购买状态
  ├─ paywall.verdict()：paid / ratio / incomplete
  └─ 命中付费墙或正文残缺 -> source_registry.resolve()
        ├─ 按书名到 data/sources.json 里各启用源搜索
        ├─ 目录里按章节名（去「第N章 / 括号注释」后比对）或序号定位
        ├─ 抓正文，过质量闸（≥300 字且 ≥ 全章字数 40%）
        └─ 命中写 data/cache/<bookId>/<chapterId>.json，二次调用直接读缓存
```

返回体多了四个字段：`paid`（是否付费墙）、`ratio`（已下发比例）、`fallback`（是否由外部源补全）、
`source`（正文来源：`qidian` / `cache` / 源名）。导出的 `sources` 字段按源统计章数。

配置 `data/sources.json` 即可接入任何站（字段见该文件的 `_readme`）；抓取后端优先用 `curl_cffi`
（Chrome TLS 指纹），可用 `SOURCE_PROXY` 或源级 `proxy` 走代理。内置源当前状态：

| 源 | 状态 | 说明 |
|---|---|---|
| 壁落小说 `biquluo.info` | ✅ 已验证 | 搜索 `.novelslist2 li span.s2 a` / 目录 `#list dd a` / 正文 `#content`，VIP 章实测 4231 字 |
| 笔下文学 `bxwx8.la` | 备用（未启用） | 搜索命中，正文待校准 |
| 快眼看书 `booksky.cc` | 备用（未启用） | 搜索命中，正文待校准 |

实测（《荒野狩猎，从综艺开始起号》bookId 1048541850）：

```
起点第87章  试读 133 字 / 全章 4040 字   ratio 0.033  → 回落成功 4231 字  ratio 1.0
起点第88章  试读         → 回落 4114 字
起点第89章  试读         → 回落 4185 字
起点第90章  试读         → 回落 4184 字
```

命令行自检：

```bash
python -c "import sys;sys.path.insert(0,'server');import qidian,json;print(json.dumps(qidian.scan_free('1048541850',5,2),ensure_ascii=False)[:400])"
```

`scan_free` 会逐章探测哪些章当前能直接读（免费 / 限免 / 已购），连续 `stopAfter` 章不可读即判定进入 VIP 段并停止。
找源的经验：盗版站域名换代很快，硬编码域名清单命中率极低；有效做法是拉现成的 Legado 书源合集
（如 `shidahuilang/shuyuan-bak` 的 `good.json`，含近 3000 条已验证源），把其中的 `searchUrl` 模板
`{{key}}` 替换成书名批量探测，命中后再校准选择器。

## 前端结构

```
src/
  api.js                双通道：Tauri IPC 优先，浏览器回退 HTTP
  store.js              全局状态与动作（搜索/详情/正文/登录/导出）
  lib/theme.js          三套语义色板（dark / sepia / light）
  lib/toast.js          全局提示
  components/
    AppHeader.vue       顶栏：令牌 / 登录 / 导出 / 主题
    SearchView.vue      搜索、骨架、结果卡、无限滚动
    BookView.vue        详情 + 目录（按卷分组、可搜索、撑满高度）
    ReaderView.vue      正文排版、沉浸模式、翻章
    LoginModal.vue      扫码弹窗
  App.vue               编排层：布局、快捷键、进度条
```

## 关键技术结论

| 项 | 结论 |
|---|---|
| 风控闸门 | cookie `w_tsfp`（212/256 字符），缺失即 202 空壳 |
| 生成方式 | `probev3.js`（腾讯 Chaos VM）在 py_mini_racer(V8) 中执行，130~340ms，零网络 |
| 必要宿主补丁 | `document.cookie` 覆写、`btoa/atob`、`crypto.getRandomValues`、canvas/webgl 假上下文、navigator 指纹、定时器 |
| 有效期 | 分钟级，`TOKEN_TTL` 默认 480s，非 200 自动重铸重试 |
| 目录 | 官方 JSON：`GET /ajax/book/category?bookId=&_csrfToken=` |
| 搜索 / 正文 | 仅 SSR HTML，无 JSON 接口（`/ajax/search`、`/ajax/chapter/content` 均 404） |
| 登录 | 微信原生 `qrconnect` → `weixinlogin`(取 uuid) → `weixincallback`(取 alk) → `sublogin`(换 qidian cookie) |

## 配置项

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `TOKEN_TTL` | 480 | 令牌缓存秒数 |
| `QD_TIMEOUT` | 20 | 单请求超时 |
| `QD_DELAY` | 0.35 | 批量抓章节间隔 |
| `QD_MAX_EXPORT` | 80 | 导出章节上限 |
| `PORT` | 8788 | HTTP 调试端口 |
