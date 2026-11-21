# fsclean

[![CI](https://github.com/Ecishy/fsclean/actions/workflows/ci.yml/badge.svg)](https://github.com/Ecishy/fsclean/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Tidy a messy folder — like your Downloads — by moving loose files into category folders.**
Dry-run by default, so you always see the plan before anything moves. Pure standard library, no dependencies.

```
$ fsclean ~/Downloads
Would move: 14 file(s), 1.3 GiB  (dry run - add --apply to move for real)

documents (3):
  report-final.pdf  ->  documents/report-final.pdf
  ...

images (4):
  beach.jpg  ->  images/beach.jpg
  ...

left in place: 2 file(s) with unknown extension
```

## Why it's safe

- **Dry run is the default.** Nothing moves until you pass `--apply`.
- **Non-recursive by design** — only loose files directly inside the folder are touched; your nested directory structure is never walked into.
- Unknown extensions stay put. Hidden files, symlinks and `--exclude` patterns are skipped.
- Name collisions resolve to `name (1).ext` instead of overwriting.
- Files are moved (renamed), never copied or deleted — undo is a simple move back.

## Categories

`images`, `documents`, `archives`, `audio`, `video`, `code`, `fonts`, `executables`, `data` — about 80 common extensions out of the box. Route anything else yourself:

```bash
fsclean ~/Downloads -r log=logs -r crdownload=downloads
```

## Install

```bash
pip install .
# or run straight from the source tree:
python -m fsclean ~/Downloads
```

## Usage

```
fsclean [PATH] [options]

  -a, --apply        actually move the files (default is a dry-run preview)
  -d, --dest DIR     move into category folders under DIR instead of PATH
  -r, --rule E=D     route extension E to folder D (repeatable, wins over builtins)
  -e, --exclude PAT  skip files matching an fnmatch pattern (repeatable)
  -V, --version      print version
```

**Examples**

```bash
# preview what would happen
fsclean ~/Downloads

# happy with the plan? apply it
fsclean ~/Downloads --apply

# sort into a separate tree, keeping Downloads itself flat
fsclean ~/Downloads --apply --dest ~/Sorted

# never touch installers or anything ending in .tmp
fsclean ~/Downloads --exclude '*.exe' --exclude '*.msi' --exclude '*.tmp'
```

**Exit codes:** `0` — finished (moved or previewed); `2` — usage or I/O error.

## Use as a library

```python
from fsclean import plan_moves, apply_moves

moves, unknown = plan_moves("~/Downloads", rules=("log=logs",), exclude=("*.tmp",))
print(f"{len(moves)} planned, {unknown} unknown")
apply_moves(moves)
```

## 中文说明

`fsclean` 是一个零依赖的目录整理命令行工具（Python 3.9+ 标准库实现），专治乱糟糟的下载文件夹。

- **默认只预览不移动**，确认计划无误后加 `--apply` 才真正执行；文件只会被移动（重命名），绝不复制或删除，撤销就是移回去。
- **非递归扫描**：只处理目标文件夹第一层的散落文件，不会动你的子目录结构；未知扩展名、隐藏文件、符号链接一律不碰。
- **重名自动改名** `name (1).ext`，永不覆盖。
- **内置 9 大类约 80 种扩展名**，还可以自定义规则：

```bash
fsclean ~/Downloads                     # 预览
fsclean ~/Downloads --apply             # 执行
fsclean ~/Downloads -r log=logs         # 自定义：.log 归到 logs/
```

## Development

```bash
pip install .
python -m unittest discover -s tests -v   # stdlib only
```

CI runs the same suite on Linux / macOS / Windows across Python 3.9–3.13.

## License

[MIT](LICENSE) © Ecishy
