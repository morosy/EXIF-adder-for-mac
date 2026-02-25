import { useEffect, useMemo, useRef, useState } from "react";
import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

type PythonRunResult = {
    output_path: string;
    log: string;
    exif_ok: boolean;
};

type AspectOption = "16:9" | "9:16" | "4:3" | "3:4" | "5:4" | "4:5" | "1:1";

function basename(path: string): string {
    const parts = path.split("/");
    return parts[parts.length - 1] || path;
}

function stemname(path: string): string {
    const base = basename(path);
    const dot = base.lastIndexOf(".");
    if (dot <= 0) {
        return base;
    }
    return base.slice(0, dot);
}

function App() {
    const [inputPath, setInputPath] = useState("");
    const [inputName, setInputName] = useState("未選択");

    const [outputDir, setOutputDir] = useState("");
    const [outputDirText, setOutputDirText] = useState("未選択");

    const [outputName, setOutputName] = useState("");

    const [aspect, setAspect] = useState<AspectOption>("3:4");

    const [previewPath, setPreviewPath] = useState("");
    const [log, setLog] = useState("");

    const lastPreviewRequestId = useRef(0);

    const previewUrl = useMemo(() => {
        if (!previewPath) {
            return "";
        }
        return `${convertFileSrc(previewPath)}?t=${Date.now()}`;
    }, [previewPath]);

    const runPreview = async (path: string, aspectValue: AspectOption) => {
        const requestId = ++lastPreviewRequestId.current;

        setLog("プレビュー生成中...");

        try {
            const generated = await invoke<PythonRunResult>("generate_preview", {
                inputPath: path,
                aspect: aspectValue,
            });

            if (requestId !== lastPreviewRequestId.current) {
                return;
            }

            setPreviewPath(generated.output_path);
            setLog(generated.log);

            if (!generated.exif_ok) {
                window.alert("EXIF情報を読み込めませんでした（N/Aとして表示します）。");
            }
        } catch (e) {
            if (requestId !== lastPreviewRequestId.current) {
                return;
            }
            setLog(String(e));
        }
    };

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
        setOutputName(stemname(selected));

        await runPreview(selected, aspect);
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
                outputName: outputName.trim() ? outputName.trim() : null,
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

    useEffect(() => {
        if (!inputPath) {
            return;
        }

        const timer = window.setTimeout(() => {
            void runPreview(inputPath, aspect);
        }, 200);

        return () => {
            window.clearTimeout(timer);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [aspect]);

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

    const inputStyle: React.CSSProperties = {
        width: 200,
        height: 44,
        fontSize: 14,
        fontWeight: 600,
        borderRadius: 10,
        padding: "0 10px",
        boxSizing: "border-box",
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
                            <option value="9:16">9:16</option>
                            <option value="4:3">4:3</option>
                            <option value="3:4">3:4</option>
                            <option value="5:4">5:4</option>
                            <option value="4:5">4:5</option>
                            <option value="1:1">1:1</option>
                        </select>

                        <div style={statusTextStyle}>
                            選択中: {aspect}
                        </div>
                    </div>
                </div>

                {/* 4. 出力ファイル名 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={leftTitleStyle}>
                        4. 出力ファイル名
                    </div>

                    <div style={leftCenterBlockStyle}>
                        <input
                            value={outputName}
                            onChange={(e) => {
                                setOutputName(e.target.value);
                            }}
                            placeholder="例: DSC_3294"
                            style={inputStyle}
                        />

                        <div style={statusTextStyle}>
                            ※「.jpg」は自動で付与されます
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
                        height: 140,
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
