#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::mpsc::{self, Receiver};
use std::sync::{Arc, Mutex};

/// 单条命令最长等待。导出分片最重：几十个章节 × 每章一次请求 + 节流，取 10 分钟上限。
const CMD_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(600);

struct Core {
    _child: Child,
    stdin: ChildStdin,
    /// 常驻读线程把内核响应行送进来；recv_timeout 超时即可判定内核卡死
    rx: Receiver<String>,
    seq: u64,
    script: PathBuf,
    mtime: Option<std::time::SystemTime>,
}

impl Drop for Core {
    fn drop(&mut self) {
        // 子进程 Drop 不会自动 kill，重启内核前必须显式清掉，否则 Python 进程泄漏
        let _ = self._child.kill();
        let _ = self._child.wait();
    }
}

impl Core {
    fn spawn() -> Result<Self, String> {
        let root = project_root();
        let script = root.join("server").join("core.py");
        if !script.exists() {
            return Err(format!("找不到内核脚本: {}", script.display()));
        }
        let log_path = std::env::temp_dir().join("qidian-core.log");
        let err_file = std::fs::File::create(&log_path).ok();
        let mut child = Command::new(python_bin())
            .arg(script.to_string_lossy().to_string())
            .current_dir(&root)
            .env("PYTHONIOENCODING", "utf-8")
            .env("PYTHONUTF8", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(err_file.map(Stdio::from).unwrap_or_else(Stdio::null))
            .spawn()
            .map_err(|e| format!("启动内核失败: {e}"))?;

        let stdin = child.stdin.take().ok_or("no stdin")?;
        let stdout = child.stdout.take().ok_or("no stdout")?;
        let mtime = std::fs::metadata(&script).and_then(|m| m.modified()).ok();

        // 读线程：阻塞 read_line 不占用调用方，超时判断靠 channel
        let (tx, rx) = mpsc::channel::<String>();
        std::thread::spawn(move || {
            let mut reader = BufReader::new(stdout);
            let mut buf = String::new();
            loop {
                buf.clear();
                match reader.read_line(&mut buf) {
                    Ok(0) => break, // 内核退出
                    Ok(_) => {
                        if tx.send(buf.clone()).is_err() {
                            break;
                        }
                    }
                    Err(_) => break,
                }
            }
        });

        Ok(Self { _child: child, stdin, rx, seq: 0, script, mtime })
    }

    /// 内核脚本被改动过 => 需要重启子进程（开发期热更新）
    fn stale(&self) -> bool {
        let now = std::fs::metadata(&self.script).and_then(|m| m.modified()).ok();
        now != self.mtime
    }

    fn call(&mut self, cmd: &str, params: Value) -> Result<Value, String> {
        self.seq += 1;
        let id = self.seq;
        let req = json!({ "id": id, "cmd": cmd, "params": params });
        let line = serde_json::to_string(&req).map_err(|e| e.to_string())?;
        writeln!(self.stdin, "{line}").map_err(|e| format!("写入内核失败: {e}"))?;
        self.stdin.flush().ok();

        // 跳过可能残留的旧响应（对不上 id 的行），直到等到本次请求的响应或超时
        let deadline = std::time::Instant::now() + CMD_TIMEOUT;
        loop {
            let remain = deadline.saturating_duration_since(std::time::Instant::now());
            if remain.is_zero() {
                return Err("内核响应超时（可能卡死）".into());
            }
            let line = self.rx.recv_timeout(remain).map_err(|_| "内核响应超时（可能卡死）".to_string())?;
            if line.trim().is_empty() {
                continue;
            }
            let v: Value = serde_json::from_str(&line)
                .map_err(|e| format!("响应解析失败: {e} | {line}"))?;
            if v.get("id").and_then(|x| x.as_u64()) == Some(id) {
                return Ok(v);
            }
            // 旧请求的迟到响应：丢弃继续等
        }
    }
}

fn python_bin() -> String {
    std::env::var("QH_PYTHON").unwrap_or_else(|_| "python".to_string())
}

/// 开发态取 src-tauri 的上级目录；打包后取可执行文件所在目录
fn project_root() -> PathBuf {
    if cfg!(debug_assertions) {
        let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        p.pop();
        p
    } else {
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|x| x.to_path_buf()))
            .unwrap_or_else(|| PathBuf::from("."))
    }
}

#[tauri::command]
async fn qidian(
    state: tauri::State<'_, Arc<Mutex<Option<Core>>>>,
    cmd: String,
    params: Option<Value>,
) -> Result<Value, String> {
    // 阻塞式 stdin/stdout 读写必须放到线程池，否则会卡住 UI 主线程
    let shared = state.inner().clone();
    let payload = params.unwrap_or_else(|| json!({}));
    tauri::async_runtime::spawn_blocking(move || run_command(shared, cmd, payload))
        .await
        .map_err(|e| format!("任务失败: {e}"))?
}

fn run_command(
    shared: Arc<Mutex<Option<Core>>>,
    cmd: String,
    payload: Value,
) -> Result<Value, String> {
    let mut guard = shared.lock().map_err(|e| e.to_string())?;
    if let Some(core) = guard.as_ref() {
        if core.stale() {
            *guard = None; // 脚本已更新，丢弃旧进程
        }
    }
    if guard.is_none() {
        *guard = Some(Core::spawn()?);
    }
    let core = guard.as_mut().ok_or("内核未就绪")?;
    match core.call(&cmd, payload.clone()) {
        Ok(v) => Ok(v),
        Err(_e) => {
            // 进程可能已退出：重建后重试一次
            *guard = None;
            let mut fresh = Core::spawn()?;
            let v = fresh.call(&cmd, payload)?;
            *guard = Some(fresh);
            Ok(v)
        }
    }
}

#[tauri::command]
async fn save_text(app: tauri::AppHandle, default_name: String, content: String) -> Result<Option<String>, String> {
    let (tx, rx) = std::sync::mpsc::channel::<Result<Option<String>, String>>();
    // rfd 的 Win32 对话框必须在主线程（含 COM STA）弹出，放到工作线程会静默失败
    app.run_on_main_thread(move || {
        let picked = rfd::FileDialog::new()
            .set_title("导出 TXT")
            .set_file_name(&default_name)
            .add_filter("文本文件", &["txt"])
            .save_file();
        let result = match picked {
            Some(path) => std::fs::write(&path, content.as_bytes())
                .map(|_| Some(path.display().to_string()))
                .map_err(|e| format!("写入失败: {e}")),
            None => Ok(None),
        };
        let _ = tx.send(result);
    })
    .map_err(|e| format!("无法调度到主线程: {e}"))?;

    rx.recv_timeout(std::time::Duration::from_secs(600))
        .map_err(|e| format!("等待保存对话框超时: {e}"))?
}

fn main() {
    tauri::Builder::default()
        .manage(Arc::new(Mutex::new(None::<Core>)))
        .invoke_handler(tauri::generate_handler![qidian, save_text])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
