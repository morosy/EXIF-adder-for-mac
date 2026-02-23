import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

function App() {
    const [inputPath, setInputPath] = useState("");
    const [outputPath, setOutputPath] = useState("");
    const [log, setLog] = useState("");

    const pickInput = async () => {
        const selected = await open({
            multiple: false,
            directory: false,
            filters: [
                {
                    name: "Images",
                    extensions: ["jpg", "jpeg", "png"],
                },
            ],
        });

        if (typeof selected === "string") {
            setInputPath(selected);
        }
    };

    const pickOutput = async () => {
        const selected = await open({
            multiple: false,
            directory: false,
            defaultPath: "output.jpg",
        });

        if (typeof selected === "string") {
            setOutputPath(selected);
        }
    };

    const run = async () => {
        setLog("Running...");

        try {
            const result = await invoke<string>("run_python", {
                inputPath,
                outputPath,
            });

            setLog(result);
        } catch (e) {
            setLog(String(e));
        }
    };

    return (
        <div style={{ padding: 16, fontFamily: "sans-serif" }}>
            <h1>EXIF adder for mac</h1>

            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <button onClick={pickInput}>画像を選択</button>
                <div>{inputPath || "(未選択)"}</div>
            </div>

            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <button onClick={pickOutput}>出力先を選択</button>
                <div>{outputPath || "(未選択)"}</div>
            </div>

            <button
                onClick={run}
                disabled={!inputPath || !outputPath}
            >
                実行
            </button>

            <pre
                style={{
                    marginTop: 16,
                    background: "#f5f5f5",
                    padding: 12,
                }}
            >
                {log}
            </pre>
        </div>
    );
}

export default App;
