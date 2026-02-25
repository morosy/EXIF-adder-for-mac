import { useMemo, useState } from "react";
import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

type PythonRunResult = {
    output_path: string;
    log: string;
    exif_ok: boolean;
};

type AspectOption = "16:9" | "3:4" | "4:5" | "1:1";

function basename(path: string): string {
    const parts = path.split("/");
    return parts[parts.length - 1] || path;
}

function App() {
    const [inputPath, setInputPath] = useState("");
    const [inputName, setInputName] = useState("未選択");
    const [outputDir, setOutputDir] = useState("");
    const [outputDirText, setOutputDirText] = useState("未選択");

    const [aspect, setAspect] = useState<AspectOption>("3:4");

    const [previewPath, setPreviewPath] = useState("");
    const [log, setLog] = useState("");

    const previewUrl = useMemo(() => {
        if (!previewPath) {
            return "";
        }
        return `${convertFileSrc(previewPath)}?t=${Date.now()}`;
    }, [previewPath]);

    const pickInput = async () => {
        let selected: string | string[] | null;

        try {
            selected = await open({
                multiple: false,
                directory: false,
                filters: [
                    {
                        name: "Images",
                        extensions: ["jpg", "jpeg", "png"],
                    },
                ],
            });
        } catch (e) {
            setLog(`画像選択ダイアログの表示に失敗: ${String(e)}`);
            return;
        }

        if (typeof selected !== "string") {
            return;
        }

        setInputPath(selected);
        setInputName(basename(selected));
        setLog("プレビュー生成中...");

        try {
            const generated = await invoke<PythonRunResult>("generate_preview", {
                inputPath: selected,
                aspect,
            });

            setPreviewPath(generated.output_path);
            setLog(generated.log);

            if (!generated.exif_ok) {
                window.alert("EXIF情報を読み込めませんでした（N/Aとして表示します）。");
            }
        } catch (e) {
            setLog(String(e));
        }
    };

    const pickOutputDir = async () => {
        let selected: string | string[] | null;

        try {
            selected = await open({
                multiple: false,
                directory: true,
            });
        } catch (e) {
            setLog(`出力先選択ダイアログの表示に失敗: ${String(e)}`);
            return;
        }

        if (typeof selected !== "string") {
            return;
        }

        setOutputDir(selected);
        setOutputDirText(selected);
    };

    const exportImage = async () => {
        if (!inputPath || !outputDir) {
            return;
        }

        setLog("出力中...");

        try {
            const out = await invoke<PythonRunResult>("export_image", {
                inputPath,
                outputDir,
                aspect,
            });

            setPreviewPath(out.output_path);
            setLog(out.log);

            if (!out.exif_ok) {
                window.alert("EXIF情報を読み込めませんでした（N/Aとして出力します）。");
            }
        } catch (e) {
            setLog(String(e));
        }
    };

    const leftTitleStyle: React.CSSProperties = {
        width: "100%",
        textAlign: "left",
        fontSize: 14,
        fontWeight: 600,
    };

    const leftCenterBlockStyle: React.CSSProperties = {
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
    };

    const actionButtonStyle: React.CSSProperties = {
        width: 160,
        height: 56,
        fontSize: 15,
        fontWeight: 700,
        borderRadius: 10,
        cursor: "pointer",
    };

    const statusTextStyle: React.CSSProperties = {
        width: "100%",
        textAlign: "center",
        fontSize: 12,
        color: "#444",
        wordBreak: "break-all",
    };

    const selectStyle: React.CSSProperties = {
        width: 160,
        height: 44,
        fontSize: 14,
        fontWeight: 600,
        borderRadius: 10,
        padding: "0 10px",
        cursor: "pointer",
    };

    return (
        <div
            style={{
                display: "flex",
                height: "100vh",
                fontFamily: "sans-serif",
            }}
        >
            {/* 左側 */}
            <div
                style={{
                    width: 280,
                    padding: 20,
                    borderRight: "1px solid #ddd",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    gap: 26,
                }}
            >
                {/* 1. 画像を選択 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={leftTitleStyle}>
                        1. 画像を選択
                    </div>

                    <div style={leftCenterBlockStyle}>
                        <button
                            onClick={pickInput}
                            style={actionButtonStyle}
                        >
                            画像を選択
                        </button>

                        <div style={statusTextStyle}>
                            {inputName}
                        </div>
                    </div>
                </div>

                {/* 2. 出力先フォルダを選択 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={leftTitleStyle}>
                        2. 出力先フォルダを選択
                    </div>

                    <div style={leftCenterBlockStyle}>
                        <button
                            onClick={pickOutputDir}
                            style={actionButtonStyle}
                        >
                            出力先選択
                        </button>

                        <div style={statusTextStyle}>
                            {outputDirText}
                        </div>
                    </div>
                </div>

                {/* 3. 出力画像の縦横比 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={leftTitleStyle}>
                        3. 出力画像の縦横比
                    </div>

                    <div style={leftCenterBlockStyle}>
                        <select
                            value={aspect}
                            onChange={(e) => {
                                setAspect(e.target.value as AspectOption);
                            }}
                            style={selectStyle}
                        >
                            <option value="16:9">16:9</option>
                            <option value="3:4">3:4</option>
                            <option value="4:5">4:5</option>
                            <option value="1:1">1:1</option>
                        </select>

                        <div style={statusTextStyle}>
                            選択中: {aspect}
                        </div>
                    </div>
                </div>
            </div>

            {/* 右側 */}
            <div
                style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    padding: 20,
                }}
            >
                <div
                    style={{
                        flex: 1,
                        border: "1px solid #ccc",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        backgroundColor: "#f8f8f8",
                        overflow: "hidden",
                    }}
                >
                    {previewUrl ? (
                        <img
                            src={previewUrl}
                            alt="preview"
                            onError={() => {
                                setLog(`プレビュー表示に失敗しました: ${previewPath}`);
                            }}
                            style={{
                                maxWidth: "100%",
                                maxHeight: "100%",
                                objectFit: "contain",
                            }}
                        />
                    ) : (
                        <div>プレビューなし</div>
                    )}
                </div>

                <button
                    onClick={exportImage}
                    disabled={!inputPath || !outputDir}
                    style={{
                        marginTop: 16,
                        height: 44,
                        fontSize: 16,
                        fontWeight: 800,
                        borderRadius: 10,
                        cursor: "pointer",
                    }}
                >
                    出力
                </button>

                <pre
                    style={{
                        marginTop: 12,
                        fontSize: 12,
                        background: "#f5f5f5",
                        padding: 8,
                        height: 120,
                        overflow: "auto",
                        whiteSpace: "pre-wrap",
                    }}
                >
                    {log}
                </pre>
            </div>
        </div>
    );
}

export default App;
