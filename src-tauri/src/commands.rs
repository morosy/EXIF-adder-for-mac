use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

fn project_root() -> PathBuf {
    // `CARGO_MANIFEST_DIR` points to `src-tauri`, so go up one level to project root.
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

fn run_python(input_path: &str, output_path: &str) -> Result<String, String> {
    let python = python_path();
    let script = script_path();

    if !python.is_file() {
        return Err(format!(
            "Python runtime not found: {}",
            python.to_string_lossy()
        ));
    }

    if !script.is_file() {
        return Err(format!(
            "Python script not found: {}",
            script.to_string_lossy()
        ));
    }

    let output = Command::new(&python)
        .arg(&script)
        .arg(input_path)
        .arg(output_path)
        .output()
        .map_err(|e| format!("Failed to start python: {e}"))?;

    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).to_string());
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

/// プレビュー用：一時フォルダに処理後画像を生成して、そのパスを返す
#[tauri::command]
pub fn generate_preview(input_path: String) -> Result<String, String> {
    let stem = file_stem_from_path(&input_path);
    let filename = format!("{stem}_preview_{}.jpg", now_millis());

    let mut out: PathBuf = std::env::temp_dir();
    out.push("exif-adder-for-mac");
    std::fs::create_dir_all(&out).map_err(|e| format!("Failed to create temp dir: {e}"))?;
    out.push(filename);

    let out_str = out.to_string_lossy().to_string();
    run_python(&input_path, &out_str)?;
    Ok(out_str)
}

/// 実出力用：出力先フォルダに保存して、そのパスを返す
#[tauri::command]
pub fn export_image(input_path: String, output_dir: String) -> Result<String, String> {
    let stem = file_stem_from_path(&input_path);
    let filename = format!("{stem}_exif.jpg");

    let out_dir = Path::new(&output_dir);
    if !out_dir.is_dir() {
        return Err("Output directory is not a directory.".to_string());
    }

    let out_path = out_dir.join(filename);
    let out_str = out_path.to_string_lossy().to_string();

    run_python(&input_path, &out_str)?;
    Ok(out_str)
}
