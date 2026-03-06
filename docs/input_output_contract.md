# 输入输出契约

## 输入契约
1. 主输入：Excel 文件（推荐放在 `Data/`）。
2. 配置输入：profile YAML（推荐 `config/profiles/`）。
3. 可选输入：`manual_inputs_csv`（在 profile 中声明）。

## profile 最小字段
1. `report_month`
2. `indicators[]`
- `indicator_id`
- `chart_type`
- `data_source_type` (`single` 或 `derived`)
- `slide_order`
- `categories`

## 输出契约
执行 `run` 后固定输出：
1. PPT：`<root>/ppt/*.pptx`
2. 单页HTML：`<root>/html/*.html`
3. 汇总HTML：`<root>/html/月报汇总浏览.html`
4. 图表PNG：`<root>/charts/*.png`
5. run manifest（可选）：`<root>/manifest.json`

`root` 由 `--output` 或 `--workspace` 推导。

## manifest 字段
1. `generated_at`
2. `excel_path`
3. `profile_path`
4. `indicator_ids`
5. `indicator_count`
6. `ppt_path`
7. `combined_html_path`
8. `chart_paths`
9. `html_paths`
10. `workspace`
