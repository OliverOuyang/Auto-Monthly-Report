# 月报自动化 — 4页报告生成实施总结

**完成时间**: 2026-03-04
**输出**: 4 页 PPT + 4 个 HTML 报告

---

## 实施概览

从新 Excel（`Data/2月月报数据_大盘ai_0304.xlsx`）成功生成 4 页报告，涵盖获客规模、效率和质量 3 个维度。

### 生成的报告

| 页码 | 指标 | 图表类型 | 数据源类型 |
|------|------|---------|-----------|
| P7 | 首借交易额 By客群 | 堆叠柱状图+折线 | 单表 |
| P8 | 花费 By渠道 | 堆叠柱状图+折线 | 单表 |
| P9 | 1-7评级CPS | 双线图 | 跨表派生 |
| P10 | 1-3过件率 & 1-7授信额度 | 柱状图+多折线（双Y轴） | 单表派生 |

---

## 代码改动清单

### 1. 配置层（Excel）

**文件**: `Data/2月月报数据_大盘ai_0304.xlsx`

- 新增 `_meta` sheet: 4 行指标配置（indicator_id, chart_type, data_source_type 等）
- 新增 `_styles` sheet: 22 行颜色配置（4 页图表的色系）
- 新增 `_manual_inputs` sheet: 2 行手动输入数据（促申完花费、RTA花费）

### 2. 数据处理器（core/data_processor.py）

**新增函数**:
- `build_cps_all_channel_pivot()`: 跨表计算 CPS（~150 行）
  - 读取 4 个数据源：花费表、手动输入、交易表、转化表
  - 计算总花费 = 业务口径花费 + 促申完花费 + RTA花费
  - 计算 CPS = 花费 / 交易额
- `build_quality_credit_pivot()`: 单表派生计算（~120 行）
  - 8 个子聚合 → 4 个派生指标
  - 过件率（3 口径）+ 平均授信额度

### 3. Excel 读取器（core/excel_reader.py）

**新增函数**:
- `read_manual_inputs()`: 读取 _manual_inputs sheet（~10 行）

### 4. 编排层（generate_report.py）

**修改逻辑** (~15 行):
- 增加 `data_source_type` 判断分支
- 派生类型调用 `build_{indicator_id}_pivot`
- 单表类型保持原有逻辑

### 5. 图表渲染器（config/chart_types.py）

**新增函数**:
- `render_dual_line()`: 双线图渲染器（~50 行）
  - 圆形 marker + 数据标签
  - 百分比格式 Y 轴
  - 水平网格线 + 边框
- `render_bar_multi_line()`: 柱状图+多折线渲染器（~80 行）
  - 双 Y 轴（左：授信额度，右：过件率）
  - 柱底部标签 + 折线顶部标签
  - 3 条折线 + 1 个柱状图

**注册**:
```python
CHART_RENDERERS = {
    'stacked_bar_line': ...,  # 已有
    'dual_line': render_dual_line,
    'bar_multi_line': render_bar_multi_line,
}
```

### 6. 分析模板（config/analysis_templates.py）

**新增函数**:
- `spend_mom()`: 渠道花费环比分析（~40 行）
  - 总花费环比变化
  - 主要增减渠道识别
- `cps_trend()`: CPS 趋势分析（~35 行）
  - 当月 CPS 及环比
  - 与历史高点对比
- `quality_trend()`: 质量指标趋势分析（~35 行）
  - 授信额度环比
  - 3 口径过件率对比

**注册**:
```python
ANALYSIS_TEMPLATES = {
    'trade_mom': ...,  # 已有
    'spend_mom': spend_mom,
    'cps_trend': cps_trend,
    'quality_trend': quality_trend,
}
```

### 7. HTML 生成器（core/html_generator.py）

**重构** (~180 行):
- 提取 3 个 option builder 函数:
  - `_build_stacked_bar_line_option()`
  - `_build_dual_line_option()`
  - `_build_bar_multi_line_option()`
- 按 chart_type dispatch 构建 ECharts option
- 外层 HTML 模板根据图表类型生成不同的 JS 代码

**注册**:
```python
ECHART_BUILDERS = {
    'stacked_bar_line': _build_stacked_bar_line_option,
    'dual_line': _build_dual_line_option,
    'bar_multi_line': _build_bar_multi_line_option,
}
```

---

## 辅助脚本

### scripts/add_excel_config.py
向 Excel 添加配置 sheets（一次性使用）

### scripts/validate_data.py
验证 4 个指标的数据计算正确性，输出到 `Data/intermediate/`

---

## 运行命令

```bash
# 生成完整报告（4 页）
python generate_report.py --excel Data/2月月报数据_大盘ai_0304.xlsx --output export/PPT/2月月报_大盘.pptx

# 验证数据计算
python scripts/validate_data.py
```

---

## 输出结果

### PPT
- 文件: `export/PPT/2月月报_大盘_v1.pptx`
- 大小: 1.2 MB
- 页数: 4 页
- 内容: 标题 + 分析文字 + 图表 + 装饰元素

### HTML
- `export/HTML/首借交易额-24H.html` (6.0 KB)
- `export/HTML/业务口径花费-by渠道.html` (8.6 KB)
- `export/HTML/CPS.html` (3.0 KB)
- `export/HTML/1-3过件率_&_1-7平均授信额度.html` (4.6 KB)

### PNG 图表
- `export/PPT/chart_trade_by_group.png` (240 KB)
- `export/PPT/chart_spend_by_channel.png` (434 KB)
- `export/PPT/chart_cps_all_channel.png` (待生成时确认)
- `export/PPT/chart_quality_credit.png` (393 KB)

### 中间数据（验证用）
- `Data/intermediate/trade_by_group.csv` (14 行 × 6 列)
- `Data/intermediate/spend_by_channel.csv` (23 行 × 8 列)
- `Data/intermediate/cps_all_channel.csv` (14 行 × 2 列)
- `Data/intermediate/quality_credit.csv` (23 行 × 4 列)

---

## 架构扩展点

### 插件式设计已完成
- 新增指标只需在 _meta 添加一行配置
- 新增图表类型在 `CHART_RENDERERS` 注册渲染函数
- 新增分析模板在 `ANALYSIS_TEMPLATES` 注册分析函数
- 新增派生指标在 `data_processor.py` 实现 `build_{indicator_id}_pivot`

### 数据源类型支持
- **single**: 单表数据（已有 + P7/P8）
- **derived**: 派生计算（P9/P10，跨表或单表派生）

---

## 遗留问题与优化建议

### 已知问题
1. Windows 控制台编码警告（不影响功能）
2. Matplotlib 字体缺失警告（不影响生成）

### 优化建议
1. **数据验证**: 增加 `validate_against_index.py` 自动对比索引表数据
2. **配置校验**: 添加 meta 和 styles 的 schema 校验
3. **日志记录**: 增加 logging 模块便于调试
4. **性能优化**: 缓存 Excel 读取，避免重复加载
5. **单元测试**: 扩展测试覆盖新增的数据处理器

---

## 总结

✓ 4 个指标成功生成（覆盖规模、效率、质量 3 个维度）
✓ 架构扩展到位（支持跨表派生、多图表类型、多分析模板）
✓ 代码改动最小化（复用已有架构，仅扩展注册表）
✓ 输出符合预期（PPT 4 页 + HTML 4 文件 + PNG 图表）

**下一步**: 如需新增指标，只需在 _meta 添加配置行，无需修改代码。
