use serde::Serialize;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize)]
pub struct PythonRunResult {
    pub output_path: String,
    pub log: String,
    pub exif_ok: bool,
}

fn project_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")))
        .to_path_buf()
}

fn python_path() -> PathBuf {
    project_root().join("py/.venv/bin/python3")
}

fn script_path() -> PathBuf {
    project_root().join("py/main.py")
}

fn now_millis() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis()
}

fn file_stem_from_path(input_path: &str) -> String {
    Path::new(input_path)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("image")
        .to_string()
}

fn parse_exif_ok(log: &str) -> bool {
    for line in log.lines() {
        let t = line.trim();
        if t == "[EXIF_OK] true" {
            return true;
        }
        if t == "[EXIF_OK] false" {
            return false;
        }
    }
    false
}

fn run_python(input_path: &str, output_path: &str, aspect: Option<String>) -> Result<String, String> {
    let python = python_path();
    let script = script_path();

    if !python.is_file() {
        return Err(format!("Python runtime not found: {}", python.to_string_lossy()));
    }

    if !script.is_file() {
        return Err(format!("Python script not found: {}", script.to_string_lossy()));
    }

    let mut cmd = Command::new(&python);
    cmd.arg(&script)
        .arg(input_path)
        .arg(output_path);

    if let Some(a) = aspect {
        cmd.arg("--aspect").arg(a);
    }

    let output = cmd
        .output()
        .map_err(|e| format!("Failed to start python: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if !output.status.success() {
        if stderr.trim().is_empty() {
            return Err(stdout);
        }
        return Err(stderr);
    }

    let mut log = stdout;
    if !stderr.trim().is_empty() {
        log.push_str("\n[WARN] stderr:\n");
        log.push_str(&stderr);
    }

    Ok(log)
}

#[tauri::command]
pub fn generate_preview(input_path: String, aspect: Option<String>) -> Result<PythonRunResult, String> {
    let stem = file_stem_from_path(&input_path);
    let filename = format!("{stem}_preview_{}.jpg", now_millis());

    let mut out: PathBuf = std::env::temp_dir();
    out.push("exif-adder-for-mac");
    std::fs::create_dir_all(&out).map_err(|e| format!("Failed to create temp dir: {e}"))?;
    out.push(filename);

    let out_str = out.to_string_lossy().to_string();
    let log = run_python(&input_path, &out_str, aspect)?;
    let exif_ok = parse_exif_ok(&log);

    Ok(PythonRunResult {
        output_path: out_str,
        log,
        exif_ok,
    })
}

#[tauri::command]
pub fn export_image(
    input_path: String,
    output_dir: String,
    aspect: Option<String>,
) -> Result<PythonRunResult, String> {
    let stem = file_stem_from_path(&input_path);
    let filename = format!("{stem}_exif.jpg");

    let out_dir = Path::new(&output_dir);
    if !out_dir.is_dir() {
        return Err("Output directory is not a directory.".to_string());
    }

    let out_path = out_dir.join(filename);
    let out_str = out_path.to_string_lossy().to_string();

    let log = run_python(&input_path, &out_str, aspect)?;
    let exif_ok = parse_exif_ok(&log);

    Ok(PythonRunResult {
        output_path: out_str,
        log,
        exif_ok,
    })
}
