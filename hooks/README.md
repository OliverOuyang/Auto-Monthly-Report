# Git Hooks 使用说明

## 概述

项目已配置 Git pre-commit hook，会在每次提交前自动执行检查和清理。

---

## 安装 Hooks

### 初次使用

克隆仓库后，需要手动安装 hooks：

```bash
python scripts/install_hooks.py install
```

### 卸载 Hooks

```bash
python scripts/install_hooks.py uninstall
```

---

## Pre-commit Hook 执行内容

每次 `git commit` 时会自动执行以下检查：

### 1. 清理临时文件
- 删除 pytest 临时目录 (`pytest-cache-files-*/`)
- 删除 Python 缓存 (`__pycache__/`)
- 删除临时文件 (`nul`, `*.stackdump`, `*.log`)

### 2. Python 语法检查
- 检查核心 Python 文件的语法错误
- 文件列表：
  - `generate_report.py`
  - `core/*.py`
  - `config/*.py`

### 3. 依赖包检查
- 验证必要的 Python 包是否安装
- 包括: pandas, openpyxl, matplotlib, pptx, yaml

---

## 跳过 Hook

### 临时跳过（单次提交）

```bash
git commit --no-verify -m "commit message"
# 或简写
git commit -n -m "commit message"
```

### 永久禁用

删除 hook 文件：
```bash
rm .git/hooks/pre-commit
```

或使用卸载脚本：
```bash
python scripts/install_hooks.py uninstall
```

---

## Hook 文件位置

- **模板文件**（提交到仓库）:
  - `hooks/pre-commit` - Bash 版本（Unix/Linux/Mac）
  - `hooks/pre-commit.py` - Python 版本（跨平台）

- **实际 hook 文件**（不提交，本地生效）:
  - `.git/hooks/pre-commit`

---

## 故障排查

### Hook 没有执行

1. 检查 hook 是否已安装：
   ```bash
   ls -la .git/hooks/pre-commit
   ```

2. 检查 hook 是否有执行权限（Unix/Linux/Mac）：
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

3. 重新安装 hook：
   ```bash
   python scripts/install_hooks.py install
   ```

### Hook 执行失败

1. 手动运行 hook 查看错误信息：
   ```bash
   # Windows
   python hooks/pre-commit.py

   # Unix/Linux/Mac
   bash .git/hooks/pre-commit
   ```

2. 检查依赖包是否完整：
   ```bash
   python generate_report.py doctor
   ```

3. 临时跳过 hook 提交代码：
   ```bash
   git commit --no-verify
   ```

---

## Windows 特别说明

在 Windows 环境下，Git Bash 会调用 Python 版本的 hook：
- `.git/hooks/pre-commit` 是一个 wrapper 脚本
- 实际执行的是 `hooks/pre-commit.py`

如果遇到编码问题，确保：
1. Python 脚本使用 UTF-8 编码
2. 输出信息避免使用特殊字符（Emoji等）

---

## 团队协作建议

### 新成员入职

在项目 README 中提醒新成员：
```bash
# 克隆仓库后
git clone <repo-url>
cd <project>

# 安装 Git hooks
python scripts/install_hooks.py install
```

### CI/CD 集成

在 CI 流程中也可以运行相同的检查：
```yaml
# .github/workflows/ci.yml 示例
- name: Clean and Check
  run: |
    python scripts/clean_temp_files.py
    python generate_report.py doctor
```

---

## 扩展 Hook

如需添加更多检查项，编辑以下文件：
- `hooks/pre-commit.py` (跨平台版本)
- `hooks/pre-commit` (Bash版本)

添加检查后，团队成员需要重新安装 hook：
```bash
python scripts/install_hooks.py install
```
