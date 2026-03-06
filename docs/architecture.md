# 月报自动化架构说明

## 目标
将“源数据 -> 中间表 -> 图表 -> PPT/HTML”流程标准化，降低新增指标与交接成本。

## 分层
1. 编排层：`generate_report.py`
- 负责命令入口、流程编排、输出目录解析、manifest写入。

2. 数据输入层：`core/excel_reader.py`
- 从 Excel 或 profile 读取 `meta/styles/pivot/raw`。

3. 指标构建层：`core/data_processor.py`
- 负责 `build_{indicator}_pivot` 派生计算。
- `single` 来源走 `build_pivot`；`derived` 走显式 builder。

4. 分析层：`core/analyzer.py`
- 将 pivot 转换为结论文案。

5. 渲染层：`core/chart_renderer.py` + `config/chart_types.py`
- Matplotlib 图表渲染，按 `chart_type` 分发。

6. 输出层：`core/html_generator.py` + `core/ppt_generator.py`
- 输出单页HTML、汇总HTML、PPT。

## 扩展点
1. 新增指标：在 `core/data_processor.py` 增加 `build_{indicator_id}_pivot`。
2. 新增图型：在 `config/chart_types.py` 注册新 `chart_type`。
3. 新增文案模板：在 `config/analysis_templates.py` 注册模板函数。

## 运行命令
1. 生成：`python generate_report.py run ...`
2. 校验：`python generate_report.py validate ...`
3. 环境检查：`python generate_report.py doctor`
