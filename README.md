# EXIF adder for mac
## 起動方法
`npm run tauri dev`

```zsh
> exif-adder-for-mac@0.1.0 tauri
> tauri dev

failed to run 'cargo metadata' command to get workspace directory: failed to run command cargo metadata --no-deps --format-version 1: No such file or directory (os error 2)
       Error failed to run 'cargo metadata' command to get workspace directory: failed to run command cargo metadata --no-deps --format-version 1: No such file or directory (os error 2)
```
と表示された場合は以下を実行  
`source "$HOME/.cargo/env"`

# Tauri + React + Typescript

This template should help get you started developing with Tauri, React and Typescript in Vite.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
