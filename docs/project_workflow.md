# 项目工作流与关键说明

## 1. 总体流程
1. 输入：Excel 源数据 + profile 配置。
2. 校验：`validate` 检查配置完整性与 derived builder 映射。
3. 计算：`data_processor` 产出指标透视结果。
4. 渲染：输出图表 PNG、单页 HTML、汇总 HTML。
5. 打包：输出 PPT，并写入 `manifest.json`。

## 2. 标准命令
1. 环境检查  
`python generate_report.py doctor`
2. 配置校验  
`python generate_report.py validate --excel <excel> --profile <profile>`
3. 报告生成  
`python generate_report.py run --excel <excel> --profile <profile> --output <ppt> --emit-manifest`
4. 脚本封装入口  
`python scripts/run_report.py --excel <excel> --profile <profile> --run-id <run_id>`
5. 本地交互页  
`scripts/start_task_panel.bat` 或 `python scripts/task_panel.py`

## 3. 关键模块职责
1. `generate_report.py`
- 命令分发（run/validate/doctor）。
- 主流程编排与 manifest 输出。
2. `core/profile_schema.py`
- profile 元数据 schema 校验（必填字段、类型、source 约束）。
3. `core/data_processor.py`
- 指标计算与 derived builder 注册表（`INDICATOR_BUILDERS`）。
4. `core/excel_reader.py`
- 统一读取与元字段规范化（bool / json / list）。
5. `scripts/run_report.py`
- 标准输出目录结构封装（`export/runs/<run_id>/...`）。
6. `scripts/task_panel.py`
- 轻量网页任务面板，便于非命令行使用者。

## 4. 输出结构规范
每次运行建议落在独立 run 目录：
1. `export/runs/<run_id>/ppt/report.pptx`
2. `export/runs/<run_id>/html/月报汇总浏览.html`
3. `export/runs/<run_id>/manifest.json`
4. `export/runs/<run_id>/charts/*.png`

`manifest.json` 是关键追溯文件，记录输入参数、输出位置与指标数量。

## 5. 新增指标标准步骤
1. 在 profile 添加指标配置（`indicator_id/chart_type/data_source_type/categories/slide_order`）。
2. 若为 derived：在 `data_processor` 增加 `build_<id>_pivot`，并注册到 `INDICATOR_BUILDERS`。
3. 添加测试（builder 与 orchestrator）。
4. `validate` + `run` 回归。

## 6. 版本管理策略
1. 每个逻辑块单独 commit（修复、架构、文档、UI 分开）。
2. 先测试后提交，至少保证关键回归通过。
3. 不把输出产物与临时日志纳入 git。
4. 通过 `manifest` 对每次结果可追溯。

## 7. 常见问题
1. PPT 写入权限错误：目标文件正在打开，关闭后重试。
2. `Derived builder not found`：profile 和 builder 注册表不一致。
3. 页面打不开：请用 `start_task_panel.bat` 本地常驻启动。
