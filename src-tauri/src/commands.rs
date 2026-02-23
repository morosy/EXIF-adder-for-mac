use std::process::Command;

#[tauri::command]
pub fn run_python(input_path: String, output_path: String) -> Result<String, String> {
    let python_path = "py/.venv/bin/python3";

    let output = Command::new(python_path)
        .arg("py/main.py")
        .arg(&input_path)
        .arg(&output_path)
        .output()
        .map_err(|e| format!("Failed to start python: {e}"))?;

    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).to_string());
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}
