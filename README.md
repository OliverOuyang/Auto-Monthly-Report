# 月报自动化（Monthly Report Automation）

本项目用于将月报源数据自动生成：
1. 中间透视结果
2. 图表（PNG + HTML）
3. 汇总浏览HTML
4. PPT报告

---

## 快速开始

### 1. 环境检查
```bash
python generate_report.py doctor
```

### 2. 配置校验
```bash
python generate_report.py validate --excel "<excel路径>" --profile config/profiles/monthly_report_v2_full.yaml
```

### 3. 生成报告（标准入口）
```bash
python generate_report.py run \
  --excel "<excel路径>" \
  --profile config/profiles/monthly_report_v2_full.yaml \
  --output export/latest/ppt/report.pptx \
  --emit-manifest
```

### 4. 一键脚本入口（封装 run）
```bash
python scripts/run_report.py --excel "<excel路径>" --profile config/profiles/monthly_report_v2_full.yaml
```

### 5. 轻量交互页（本地任务面板）
```bash
python scripts/task_panel.py --host 127.0.0.1 --port 8765
```
浏览器访问 `http://127.0.0.1:8765`。

默认输出结构：
1. `export/runs/<run_id>/ppt/report.pptx`
2. `export/runs/<run_id>/html/月报汇总浏览.html`
3. `export/runs/<run_id>/manifest.json`

---

## 核心结构

1. `generate_report.py`：主编排入口（run/validate/doctor）
2. `core/excel_reader.py`：读取 profile / excel 配置与数据
3. `core/data_processor.py`：指标计算（含 builder 注册表）
4. `core/chart_renderer.py` + `config/chart_types.py`：图表渲染
5. `core/html_generator.py` / `core/ppt_generator.py`：HTML/PPT 输出
6. `tests/`：核心回归测试

---

## 文档

1. `docs/architecture.md`
2. `docs/input_output_contract.md`
3. `docs/runbook.md`
4. `docs/add_indicator.md`
