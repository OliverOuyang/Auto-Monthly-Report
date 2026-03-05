 月报自动化 - 架构优化方案                                                                │
│                                                                                          │
│ Context                                                                                  │
│                                                                                          │
│ 当前项目是一个 400 行的单体脚本                                                          │
│ generate_report.py，能处理一个指标（首借交易额）。用户计划：                             │
│ 1. 扩展到多个指标（多个 raw data、多种图表类型）                                         │
│ 2. 做成可复用的 Claude Code skill                                                        │
│ 3. 未来可能用 MCP 自动生成 Excel 数据源                                                  │
│                                                                                          │
│ 核心问题：所有配置硬编码在 Python 里，Excel 缺乏结构化元数据，无法扩展。                 │
│                                                                                          │
│ ---                                                                                      │
│ 一、Excel 架构重构                                                                       │
│                                                                                          │
│ 1.1 Sheet 分层结构（3层）                                                                │
│                                                                                          │
│ Sheet 1: _meta          ← 配置层：每行 = 一个图表/指标的完整配置                         │
│ Sheet 2: _styles         ← 样式层：颜色、字体等全局样式                                  │
│ Sheet 3~N: {指标ID}      ← 结构表层：已处理好的透视表（chart直接读取）                   │
│ Sheet N+1~M: raw_{来源}   ← 原数据层：未加工的源数据                                     │
│                                                                                          │
│ 1.2 _meta Sheet 设计（核心）                                                             │
│                                                                                          │
│ 每行定义一个要生成的图表，Claude 读此 sheet 即知道"要做什么"。                           │
│ 列: A                                                                                    │
│ 字段名: indicator_id                                                                     │
│ 示例值: shoujie_trade_24h                                                                │
│ 说明: 唯一ID，对应结构表 sheet 名                                                        │
│ ────────────────────────────────────────                                                 │
│ 列: B                                                                                    │
│ 字段名: report_month                                                                     │
│ 示例值: 2026-02                                                                          │
│ 说明: 报告月份                                                                           │
│ ────────────────────────────────────────                                                 │
│ 列: C                                                                                    │
│ 字段名: section                                                                          │
│ 示例值: 获客规模                                                                         │
│ 说明: PPT 所属章节                                                                       │
│ ────────────────────────────────────────                                                 │
│ 列: D                                                                                    │
│ 字段名: slide_title                                                                      │
│ 示例值: 获客规模指标：1-7评级首借交易 By客群                                             │
│ 说明: 幻灯片标题                                                                         │
│ ────────────────────────────────────────                                                 │
│ 列: E                                                                                    │
│ 字段名: chart_title                                                                      │
│ 示例值: 首借交易额-24H                                                                   │
│ 说明: 图表标题                                                                           │
│ ────────────────────────────────────────                                                 │
│ 列: F                                                                                    │
│ 字段名: chart_type                                                                       │
│ 示例值: stacked_bar_line                                                                 │
│ 说明: 图表类型（见下表）                                                                 │
│ ────────────────────────────────────────                                                 │
│ 列: G                                                                                    │
│ 字段名: unit                                                                             │
│ 示例值: 亿                                                                               │
│ 说明: 显示单位                                                                           │
│ ────────────────────────────────────────                                                 │
│ 列: H                                                                                    │
│ 字段名: unit_divisor                                                                     │
│ 示例值: 100000000                                                                        │
│ 说明: 原始值 ÷ 此值 = 显示值                                                             │
│ ────────────────────────────────────────                                                 │
│ 列: I                                                                                    │
│ 字段名: value_column                                                                     │
│ 示例值: loan_principal_amount                                                            │
│ 说明: 聚合字段                                                                           │
│ ────────────────────────────────────────                                                 │
│ 列: J                                                                                    │
│ 字段名: agg_func                                                                         │
│ 示例值: sum                                                                              │
│ 说明: 聚合函数                                                                           │
│ ────────────────────────────────────────                                                 │
│ 列: K                                                                                    │
│ 字段名: group_column                                                                     │
│ 示例值: user_group                                                                       │
│ 说明: 分组字段                                                                           │
│ ────────────────────────────────────────                                                 │
│ 列: L                                                                                    │
│ 字段名: time_column                                                                      │
│ 示例值: month                                                                            │
│ 说明: 时间轴字段                                                                         │
│ ────────────────────────────────────────                                                 │
│ 列: M                                                                                    │
│ 字段名: categories                                                                       │
│ 示例值: 当月首登M0,存量首登M0,初审M1+,非初审,API回流                                     │
│ 说明: 有序分类列表                                                                       │
│ ────────────────────────────────────────                                                 │
│ 列: N                                                                                    │
│ 字段名: filter_exclude                                                                   │
│ 示例值: 其他                                                                             │
│ 说明: 过滤掉的值                                                                         │
│ ────────────────────────────────────────                                                 │
│ 列: O                                                                                    │
│ 字段名: merge_rules                                                                      │
│ 示例值: 非初审-重申->非初审;非初审-重审及其他->非初审                                    │
│ 说明: 合并规则                                                                           │
│ ────────────────────────────────────────                                                 │
│ 列: P                                                                                    │
│ 字段名: show_total_line                                                                  │
│ 示例值: TRUE                                                                             │
│ 说明: 是否显示总计折线                                                                   │
│ ────────────────────────────────────────                                                 │
│ 列: Q                                                                                    │
│ 字段名: analysis_template                                                                │
│ 示例值: trade_mom                                                                        │
│ 说明: 分析模板名称                                                                       │
│ ────────────────────────────────────────                                                 │
│ 列: R                                                                                    │
│ 字段名: raw_sheet                                                                        │
│ 示例值: raw_首借交易                                                                     │
│ 说明: 源数据 sheet 名                                                                    │
│ ────────────────────────────────────────                                                 │
│ 列: S                                                                                    │
│ 字段名: slide_order                                                                      │
│ 示例值: 1                                                                                │
│ 说明: 幻灯片排序                                                                         │
│ 1.3 _styles Sheet 设计                                                                   │
│                                                                                          │
│ 分类颜色区域（每行一个分类）：                                                           │
│ ┌────────────┬───────────┬──────┐                                                        │
│ │ style_key  │ hex_color │ role │                                                        │
│ ├────────────┼───────────┼──────┤                                                        │
│ │ 当月首登M0 │ #4472C4   │ bar  │                                                        │
│ ├────────────┼───────────┼──────┤                                                        │
│ │ 存量首登M0 │ #ED7D31   │ bar  │                                                        │
│ ├────────────┼───────────┼──────┤                                                        │
│ │ 初审M1+    │ #FFC000   │ bar  │                                                        │
│ ├────────────┼───────────┼──────┤                                                        │
│ │ 非初审     │ #70AD47   │ bar  │                                                        │
│ ├────────────┼───────────┼──────┤                                                        │
│ │ API回流    │ #9DC3E6   │ bar  │                                                        │
│ └────────────┴───────────┴──────┘                                                        │
│ 全局样式区域：                                                                           │
│ ┌──────────────────┬─────────────────┐                                                   │
│ │       key        │      value      │                                                   │
│ ├──────────────────┼─────────────────┤                                                   │
│ │ total_line_color │ #FF0000         │                                                   │
│ ├──────────────────┼─────────────────┤                                                   │
│ │ label_color      │ #5A5A5A         │                                                   │
│ ├──────────────────┼─────────────────┤                                                   │
│ │ title_color      │ #8B4513         │                                                   │
│ ├──────────────────┼─────────────────┤                                                   │
│ │ font_family      │ Microsoft YaHei │                                                   │
│ └──────────────────┴─────────────────┘                                                   │
│ 1.4 结构表 Sheet（如 shoujie_trade_24h）                                                 │
│                                                                                          │
│ 已处理好的透视表，图表渲染器直接读取：                                                   │
│                                                                                          │
│ Row 1: month | 当月首登M0 | 存量首登M0 | 初审M1+ | 非初审 | API回流 | 总计               │
│ Row 2: 2025-01 | 900139442 | 250285011 | 185056096 | 121544073 | 38847992 | 1495872614   │
│ Row 3: 2025-02 | ...                                                                     │
│                                                                                          │
│ - 过滤、合并规则已应用                                                                   │
│ - 可由脚本从 raw data 自动生成，也可手动修正                                             │
│ - 是图表渲染的"唯一数据源"                                                               │
│                                                                                          │
│ 1.5 原数据 Sheet（如 raw_首借交易）                                                      │
│                                                                                          │
│ 保持现有格式不变，sheet 名加 raw_ 前缀。                                                 │
│                                                                                          │
│ ---                                                                                      │
│ 二、文件夹架构重构                                                                       │
│                                                                                          │
│ 月报自动化/                                                                              │
│ ├── .claude/                                                                             │
│ │   └── commands/                                                                        │
│ │       └── monthly-report.md       # Skill 定义文件                                     │
│ │                                                                                        │
│ ├── core/                            # 核心模块                                          │
│ │   ├── __init__.py                                                                      │
│ │   ├── excel_reader.py              # 读取 _meta, _styles, 结构表                       │
│ │   ├── data_processor.py            # raw → 结构表 转换                                 │
│ │   ├── analyzer.py                  # 分析文本生成（模板注册）                          │
│ │   ├── chart_renderer.py            # matplotlib 图表渲染（类型分发）                   │
│ │   ├── html_generator.py            # ECharts HTML 生成                                 │
│ │   └── ppt_generator.py             # PPT 幻灯片组装                                    │
│ │                                                                                        │
│ ├── config/                                                                              │
│ │   ├── chart_types.py               # 图表类型注册表                                    │
│ │   └── analysis_templates.py        # 分析模板注册表                                    │
│ │                                                                                        │
│ ├── Data/                                                                                │
│ │   ├── {月份}月月报数据.xlsx          # 结构化 Excel                                    │
│ │   ├── pic/                          # 参考图片                                         │
│ │   └── Report/                       # 参考报告                                         │
│ │                                                                                        │
│ ├── export/                                                                              │
│ │   ├── HTML/                                                                            │
│ │   └── PPT/                                                                             │
│ │                                                                                        │
│ ├── generate_report.py               # 主入口（薄编排层）                                │
│ ├── CLAUDE.md                         # 项目级记忆                                       │
│ └── .gitignore                                                                           │
│                                                                                          │
│ 模块职责                                                                                 │
│ 模块: excel_reader                                                                       │
│ 职责: 解析 Excel 三层结构                                                                │
│ 输入: xlsx 路径                                                                          │
│ 输出: meta list, styles dict, DataFrame                                                  │
│ ────────────────────────────────────────                                                 │
│ 模块: data_processor                                                                     │
│ 职责: 按 meta 规则从 raw 生成结构表                                                      │
│ 输入: raw DataFrame + meta                                                               │
│ 输出: pivot DataFrame                                                                    │
│ ────────────────────────────────────────                                                 │
│ 模块: analyzer                                                                           │
│ 职责: 按模板生成分析文字                                                                 │
│ 输入: pivot DataFrame + meta                                                             │
│ 输出: list[str]                                                                          │
│ ────────────────────────────────────────                                                 │
│ 模块: chart_renderer                                                                     │
│ 职责: 按 chart_type 渲染图表                                                             │
│ 输入: pivot + meta + styles                                                              │
│ 输出: PNG 路径                                                                           │
│ ────────────────────────────────────────                                                 │
│ 模块: html_generator                                                                     │
│ 职责: 生成 ECharts HTML                                                                  │
│ 输入: pivot + meta + styles + 文字                                                       │
│ 输出: HTML 文件                                                                          │
│ ────────────────────────────────────────                                                 │
│ 模块: ppt_generator                                                                      │
│ 职责: 组装 PPT 幻灯片                                                                    │
│ 输入: chart PNG + 文字 + meta + styles                                                   │
│ 输出: PPT 文件                                                                           │
│ ---                                                                                      │
│ 三、generate_report.py 重构为编排层                                                      │
│                                                                                          │
│ def main(excel_path, indicator_ids=None):                                                │
│     # 1. 读配置                                                                          │
│     meta_list = excel_reader.read_meta(excel_path)                                       │
│     styles = excel_reader.read_styles(excel_path)                                        │
│                                                                                          │
│     # 2. 按指标过滤                                                                      │
│     if indicator_ids:                                                                    │
│         meta_list = [m for m in meta_list if m['indicator_id'] in indicator_ids]         │
│                                                                                          │
│     # 3. 逐指标处理                                                                      │
│     for meta in sorted(meta_list, key=lambda m: m['slide_order']):                       │
│         # 读结构表（优先）或从 raw 生成                                                  │
│         pivot = excel_reader.read_pivot(excel_path, meta['indicator_id'])                │
│         if pivot is None:                                                                │
│             raw = excel_reader.read_raw(excel_path, meta['raw_sheet'])                   │
│             pivot = data_processor.build_pivot(raw, meta)                                │
│                                                                                          │
│         # 生成分析文字                                                                   │
│         lines = analyzer.analyze(pivot, meta)                                            │
│                                                                                          │
│         # 渲染图表                                                                       │
│         chart_path = chart_renderer.render(pivot, meta, styles)                          │
│                                                                                          │
│         # 输出 HTML                                                                      │
│         html_generator.generate(pivot, meta, styles, lines)                              │
│                                                                                          │
│         # 添加 PPT 页                                                                    │
│         ppt_generator.add_slide(prs, meta, styles, chart_path, lines)                    │
│                                                                                          │
│     # 4. 保存                                                                            │
│     ppt_generator.save(prs, output_path)                                                 │
│                                                                                          │
│ ---                                                                                      │
│ 四、Skill 集成                                                                           │
│                                                                                          │
│ 触发方式                                                                                 │
│                                                                                          │
│ - /monthly-report [excel路径]                                                            │
│ - /月报 [excel路径]                                                                      │
│                                                                                          │
│ Skill 工作流                                                                             │
│                                                                                          │
│ 1. 读取 Excel _meta sheet → 了解全部任务                                                 │
│ 2. 调用 python generate_report.py --excel <path> 执行                                    │
│ 3. 验证输出文件                                                                          │
│ 4. 汇报结果                                                                              │
│                                                                                          │
│ ---                                                                                      │
│ 五、实施步骤                                                                             │
│                                                                                          │
│ 用户选择：混合模式（Claude 首次自动生成 _meta，之后可手动微调）+ Excel 和代码一起重构    │
│                                                                                          │
│ Step 1：重构 Excel 数据文件                                                              │
│                                                                                          │
│ - 在现有 xlsx 中添加 _meta sheet（Claude 根据现有数据和参考��自动填写首行配置）          │
│ - 添加 _styles sheet（全局颜色/样式定义）                                                │
│ - 现有 首借交易源数据 sheet 重命名为 raw_首借交易                                        │
│ - 添加结构表 sheet shoujie_trade_24h（透视表，已处理）                                   │
│ - 清理/删除旧的 图表+透视表 sheet                                                        │
│                                                                                          │
│ Step 2：创建 core/ 模块                                                                  │
│                                                                                          │
│ - core/__init__.py                                                                       │
│ - core/excel_reader.py — 解析 _meta, _styles, 读结构表/raw                               │
│ - core/data_processor.py — 按 meta 规则执行 filter/merge/pivot                           │
│ - core/analyzer.py — 当前 analyze() 函数提取为 trade_mom 模板 + 模板注册机制             │
│ - core/chart_renderer.py — 当前 matplotlib 绘图逻辑提取 + chart_type 分发                │
│ - core/html_generator.py — 当前 ECharts HTML 逻辑提取                                    │
│ - core/ppt_generator.py — 当前 PPT 组装逻辑提取                                          │
│                                                                                          │
│ Step 3：创建 config/ 注册表                                                              │
│                                                                                          │
│ - config/chart_types.py — chart_type 与渲染函数的映射                                    │
│ - config/analysis_templates.py — analysis_template 与分析函数的映射                      │
│                                                                                          │
│ Step 4：重写 generate_report.py                                                          │
│                                                                                          │
│ - 从 ~400 行单体 → ~60 行编排层                                                          │
│ - 支持命令行参数：--excel, --indicators, --output                                        │
│ - 读 _meta → 逐指标处理 → 输出                                                           │
│                                                                                          │
│ Step 5：验证 + CLAUDE.md                                                                 │
│                                                                                          │
│ - 运行新脚本，对比输出与 v2 版本一致（数据、图表、文字、PPT）                            │
│ - 创建项目级 CLAUDE.md                                                                   │
│ - Git commit 保存                                                                        │
│                                                                                          │
│ 涉及文件：                                                                               │
│ - 修改：Data/2月月报数据_大盘交易aiV2.xlsx                                               │
│ - 新增：core/ 7 个文件, config/ 2 个文件                                                 │
│ - 重写：generate_report.py                                                               │
│ - 新增：CLAUDE.md                                                                        │
│                                                                                          │
│ 后续（Phase 2-3，本次不做）                                                              │
│                                                                                          │
│ - Phase 2：新增更多 chart_type 渲染器和 analysis_template                                │
│ - Phase 3：Skill 定义 + MCP 集成                                                         │
│                                                                                          │
│ ---                                                                                      │
│ 六、验证方式                                                                             │
│                                                                                          │
│ 1. 数据一致性：从 raw 重建的结构表 vs 手工透视表，全字段全月份比对                       │
│ 2. 图表一致性：生成的图表与 Data/pic/1_首借交易.png 像素级对比                           │
│ 3. 文字质量：分析文字包含总量、环比、驱动因素、趋势四要素                                │
│ 4. PPT 排版：与 Data/Report/获客首借1月报全文_final.pdf 第7页对比                        │
│ 5. 回归测试：修改任何模块后，运行 python generate_report.py 确认输出不变