# 月报自动化 v1 架构升级说明

## 升级目标
1. 输入输出标准化。
2. 架构分层与扩展点清晰化。
3. CLI/脚本/UI 三种使用方式统一。
4. 测试与文档覆盖关键路径。

## 阶段交付

### Phase A
1. 新增 CLI 子命令：`run / validate / doctor`。
2. 新增 `--emit-manifest` 输出运行清单。
3. 主流程输出契约固定化。

### Phase B
1. 引入 profile schema 校验模块：`core/profile_schema.py`。
2. 引入 derived builder 注册表：`INDICATOR_BUILDERS`。
3. `run` 与 `validate` 统一依赖注册表，避免动态反射漂移。

### Phase C
1. `scripts/run_report.py` 改为薄封装，统一调用主 CLI 流程。
2. 新增 README 快速上手与运行手册补充。

### Phase D
1. 新增轻量任务面板：`scripts/task_panel.py`。
2. 新增稳定启动脚本：`scripts/start_task_panel.bat`。
3. 非命令行同学可用网页提交任务。

## 数据口径修复
1. 修复 `1-7全首借CPS` 手工花费计入（促申完 + RTA）。
2. 手工输入字段名容错（空格、大小写差异）。
3. 当 `_manual_inputs` 缺失时，支持 `manual_inputs_csv` 兜底。
4. 精准转化相关百分比格式统一为两位小数。

## 文档清单
1. `README.md`
2. `docs/architecture.md`
3. `docs/input_output_contract.md`
4. `docs/runbook.md`
5. `docs/add_indicator.md`
6. `docs/project_workflow.md`

## 验证
1. 核心回归测试通过（orchestrator / cps / indicator adjustments / task panel）。
2. `doctor / validate / run` 命令完成实测。
3. 生成产物包含 `manifest.json`，满足追溯。
