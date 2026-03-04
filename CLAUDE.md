# 月报自动化项目说明

## 目标
- 从结构化 Excel 自动生成月报图表与分析结果。
- 输出 HTML（ECharts）与 PPT（python-pptx）。
- 支持通过 `_meta` 配置多指标扩展，避免在脚本中硬编码指标逻辑。

## 当前架构
- `generate_report.py`: 编排层入口（读取配置、逐指标处理、输出结果）。
- `core/excel_reader.py`: 读取 `_meta`、`_styles`、结构表与原始表。
- `core/data_processor.py`: 当结构表缺失时，从 raw 表按配置生成 pivot。
- `core/analyzer.py`: 根据模板生成分析文字。
- `core/chart_renderer.py`: 根据 `chart_type` 渲染 matplotlib 图。
- `core/html_generator.py`: 生成 ECharts HTML。
- `core/ppt_generator.py`: 组装并保存 PPT。
- `config/chart_types.py`: 图表渲染函数注册表。
- `config/analysis_templates.py`: 分析模板函数注册表。

## 运行方式
```bash
python generate_report.py --excel <excel_path> [--indicators a,b,c] [--output <ppt_path>]
```

示例：
```bash
python generate_report.py --excel Data/2月月报数据_大盘交易aiV2.xlsx --indicators shoujie_trade_24h --output export/PPT/首借交易额_24H_v3.pptx
```

## Excel 关键约定
- `_meta`: 每行一个指标配置（包含 `indicator_id`、`chart_type`、`analysis_template`、`raw_sheet` 等）。
- `_styles`: 颜色与全局样式。
- `{indicator_id}`: 指标结构表（优先读取）。
- `raw_*`: 原始数据表（结构表缺失时回退构建）。

## 回归验证建议
- 运行单测：
```bash
python -m unittest tests/test_generate_report_orchestrator.py -v
```
- 运行脚本并检查：
  - PPT 是否生成；
  - HTML 是否生成；
  - 图表与文案是否与预期一致。
