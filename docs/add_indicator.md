# 新增指标SOP

## 步骤
1. 在 profile 增加指标配置
- 设置 `indicator_id`
- 设置 `data_source_type`
- 设置 `chart_type`
- 设置 `categories`
- 设置 `slide_order`

2. 如为 `derived`，实现 builder
- 在 `core/data_processor.py` 增加：
```python
def build_<indicator_id>_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    ...
```

3. 选择图表类型
- 复用已有 `chart_type`，或在 `config/chart_types.py` 新增渲染器。

4. 增加分析模板（可选）
- 在 `config/analysis_templates.py` 增加模板函数，并在 profile 指定 `analysis_template`。

5. 增加测试
- 至少包含：
1. builder 行为测试（口径、过滤、周期）
2. orchestrator 可找到 builder 的测试

6. 执行校验与生成
```bash
python generate_report.py validate --excel <excel> --profile <profile>
python generate_report.py run --excel <excel> --profile <profile> --output <ppt>
```
