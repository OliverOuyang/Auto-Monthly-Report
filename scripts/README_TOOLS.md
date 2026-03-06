# 项目维护工具

## 1. 临时文件清理工具 (`clean_temp_files.py`)

自动清理项目中的临时文件和缓存目录。

### 使用方法

**预览模式（推荐先运行）**：
```bash
python scripts/clean_temp_files.py --dry-run
```

**实际清理**：
```bash
python scripts/clean_temp_files.py
```

### 清理内容

- ✓ Pytest 临时目录 (`pytest-cache-files-*/`)
- ✓ Windows 临时文件 (`nul`, `*.stackdump`)
- ✓ CSV/Excel 临时文件 (`temp_*.csv`, `temp_*.xlsx`)
- ✓ 日志文件 (`task_panel.*.log`, `*.out.log`, `*.err.log`)
- ✓ Python 缓存目录 (`__pycache__/`, `*.pyc`)

---

## 2. 项目健康检查工具 (`health_check.py`)

全面检查项目状态和配置有效性。

### 使用方法

```bash
python scripts/health_check.py
```

### 检查项目

1. **依赖包检查**: 验证 pandas, openpyxl, matplotlib, pptx, yaml 是否安装
2. **临时文件检查**: 统计需要清理的临时文件数量
3. **配置有效性**: 验证 Excel 和 YAML profile 配置
4. **测试状态**: 检查测试是否可运行
5. **Git 状态**: 检查工作区是否有未提交的改动

### 输出示例

```
============================================================
项目健康检查
============================================================

[1/5] 检查依赖包...
OK: True
pandas: OK
openpyxl: OK
...

[2/5] 检查临时文件...
  [OK] 无临时文件

[3/5] 检查配置有效性...
  [OK] 配置有效

[4/5] 检查测试...
  [OK] 发现 7 个测试

[5/5] 检查 Git 状态...
  [OK] 工作区干净

============================================================
检查结果汇总:
  依赖包: [OK] 正常
  临时文件: [OK] 干净
  配置: [OK] 有效
  测试: [OK] 可运行
  Git: [OK] 干净
============================================================
```

---

## 建议工作流

### 日常开发前
```bash
# 1. 检查项目健康状态
python scripts/health_check.py

# 2. 清理临时文件（如果需要）
python scripts/clean_temp_files.py
```

### 提交代码前
```bash
# 1. 清理所有临时文件
python scripts/clean_temp_files.py

# 2. 运行测试
pytest tests/ -v

# 3. 检查 Git 状态
git status

# 4. 提交代码
git add .
git commit -m "your message"
```

### 定期维护
建议每周运行一次清理工具，保持项目目录整洁。
