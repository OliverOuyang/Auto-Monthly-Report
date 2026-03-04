# -*- coding: utf-8 -*-
"""ECharts HTML 生成"""

import json
import pandas as pd
from pathlib import Path


def _build_stacked_bar_line_option(pivot_d, meta, styles):
    """构建堆叠柱状图 + 总计折线的 ECharts option"""
    categories = meta['categories']
    unit = meta.get('unit', '')
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})
    global_styles = styles.get('global', {})
    label_color = global_styles.get('label_color', '#5A5A5A')
    line_color = global_styles.get('total_line_color', '#FF0000')

    month_labels = [d.strftime('%b-%y') for d in pivot_d.index]

    def fmt_unit(v):
        return f"{v:.2f}{unit}" if abs(v) >= 0.15 else ""

    ec_data = {c: [round(float(v), 4) for v in pivot_d[c]] for c in categories}
    if '总计' in pivot_d.columns:
        ec_data['总计'] = [round(float(v), 4) for v in pivot_d['总计']]

    ec_labels = {c: [fmt_unit(v) for v in pivot_d[c]] for c in categories}
    if '总计' in pivot_d.columns:
        ec_labels['总计'] = [fmt_unit(v) for v in pivot_d['总计']]

    # 构建 series
    series_items = []
    for c in categories:
        series_items.append({
            'name': c, 'type': 'bar', 'stack': 't', 'barWidth': '50%',
            'itemStyle': {'color': colors.get(c, '#999')},
            'data': ec_data[c],
            'label': {
                'show': True, 'position': 'insideRight',
                'fontSize': 10, 'color': label_color, 'fontWeight': 'bold'
            }
        })

    if '总计' in ec_data:
        series_items.append({
            'name': '总计', 'type': 'line', 'data': ec_data['总计'],
            'symbol': 'circle', 'symbolSize': 6,
            'lineStyle': {'color': line_color, 'width': 3},
            'itemStyle': {'color': line_color},
            'label': {
                'show': True, 'position': 'top',
                'fontSize': 11, 'color': line_color, 'fontWeight': 'bold'
            },
            'z': 10
        })

    legend_data = categories + (['总计'] if '总计' in ec_data else [])

    return {
        'month_labels': month_labels,
        'series': series_items,
        'legend_data': legend_data,
        'ec_labels': ec_labels,
        'chart_title': chart_title,
        'unit': unit
    }


def _build_dual_line_option(pivot_d, meta, styles):
    """构建双线图的 ECharts option（CPS）"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    month_labels = [d.strftime('%b-%y') for d in pivot_d.index]

    # CPS 数据（百分比格式，1位小数）
    ec_data = {c: [round(float(v) * 100, 1) for v in pivot_d[c]] for c in categories}

    series_items = []
    for cat in categories:
        series_items.append({
            'name': cat, 'type': 'line', 'data': ec_data[cat],
            'symbol': 'circle', 'symbolSize': 6,
            'lineStyle': {'color': colors.get(cat, '#4472C4'), 'width': 3},
            'itemStyle': {'color': colors.get(cat, '#4472C4')},
            'label': {
                'show': True, 'position': 'top',
                'fontSize': 10, 'fontWeight': 'bold',
                'formatter': '{c}%'  # 1位小数由 ec_data 已处理
            }
        })

    return {
        'month_labels': month_labels,
        'series': series_items,
        'legend_data': categories,
        'chart_title': chart_title,
        'yaxis_formatter': "'{value}%'"
    }


def _build_bar_multi_line_option(pivot_d, meta, styles):
    """构建柱状图 + 多折线（双Y轴）的 ECharts option"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    month_labels = [d.strftime('%b-%y') for d in pivot_d.index]

    # 第一个指标：柱状图（授信额度）
    bar_col = categories[0]
    bar_data = [round(float(v), 2) for v in pivot_d[bar_col]]

    # 其余指标：折线（过件率，百分比，1位小数）
    line_cols = categories[1:]
    line_data = {c: [round(float(v) * 100, 1) for v in pivot_d[c]] for c in line_cols}

    series_items = []

    # 柱状图
    series_items.append({
        'name': bar_col, 'type': 'bar', 'data': bar_data,
        'barWidth': '40%',
        'itemStyle': {'color': colors.get(bar_col, '#FFC000')},
        'yAxisIndex': 0,
        'label': {
            'show': True, 'position': 'inside',
            'fontSize': 9, 'fontWeight': 'bold',
            'formatter': '{c}'
        }
    })

    # 折线
    for cat in line_cols:
        series_items.append({
            'name': cat, 'type': 'line', 'data': line_data[cat],
            'symbol': 'circle', 'symbolSize': 5,
            'lineStyle': {'color': colors.get(cat, '#4472C4'), 'width': 2.5},
            'itemStyle': {'color': colors.get(cat, '#4472C4')},
            'yAxisIndex': 1,
            'label': {
                'show': True, 'position': 'top',
                'fontSize': 9, 'fontWeight': 'bold',
                'formatter': '{c}%'
            }
        })

    return {
        'month_labels': month_labels,
        'series': series_items,
        'legend_data': categories,
        'chart_title': chart_title,
        'dual_yaxis': True,
        'yaxis1_name': bar_col,
        'yaxis2_name': '过件率'
    }


# ECharts option builders registry
ECHART_BUILDERS = {
    'stacked_bar_line': _build_stacked_bar_line_option,
    'dual_line': _build_dual_line_option,
    'bar_multi_line': _build_bar_multi_line_option,
}


def generate(pivot, meta: dict, styles: dict, lines: list[str],
             output_dir: str | Path) -> Path:
    """
    生成 ECharts HTML 文件。
    pivot: 透视表（原始值）
    返�� HTML 文件路径。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    unit_divisor = meta.get('unit_divisor', 1)
    chart_title = meta.get('chart_title', '')
    slide_title = meta.get('slide_title', '')
    chart_type = meta.get('chart_type', 'stacked_bar_line')
    global_styles = styles.get('global', {})
    title_color = global_styles.get('title_color', '#8B4513')

    pivot_d = pivot / unit_divisor

    # 根据 chart_type 选择 builder
    builder = ECHART_BUILDERS.get(chart_type)
    if builder is None:
        raise ValueError(f"未注册的 ECharts builder: {chart_type}")

    option_data = builder(pivot_d, meta, styles)

    summary_html = "<br/>".join(lines)

    # ===== 生成 HTML =====

    # 通用模板
    if chart_type == 'stacked_bar_line':
        # 使用原有的 label formatter 逻辑
        ec_labels_json = json.dumps(option_data['ec_labels'], ensure_ascii=False)
        series_json = json.dumps(option_data['series'], ensure_ascii=False)
        months_json = json.dumps(option_data['month_labels'])
        legend_json = json.dumps(option_data['legend_data'], ensure_ascii=False)
        unit = option_data['unit']

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{chart_title}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Microsoft YaHei','SimHei',sans-serif; background:#fff; }}
.page {{ max-width:1200px; margin:0 auto; padding:40px 50px; }}
.title {{ font-size:22px; font-weight:bold; color:{title_color}; }}
.line {{ height:3px; background:linear-gradient(to right,#DAA520,#F0E68C); margin:6px 0 18px; }}
.summary {{ font-size:15px; color:#333; line-height:1.9; margin-bottom:10px; }}
#chart {{ width:100%; height:500px; }}
.bar {{ height:6px; background:linear-gradient(to right,#C0392B,#F5B7B1,#FADBD8); margin-top:25px; border-radius:2px; }}
</style>
</head>
<body>
<div class="page">
  <div class="title">{slide_title}</div>
  <div class="line"></div>
  <div class="summary">{summary_html}</div>
  <div id="chart"></div>
  <div class="bar"></div>
</div>
<script>
var chart = echarts.init(document.getElementById('chart'));
var months = {months_json};
var labels = {ec_labels_json};
var rawSeries = {series_json};

// 注入 label formatter
rawSeries.forEach(function(s) {{
  var name = s.name;
  if (labels[name]) {{
    s.label.formatter = function(p) {{ return labels[name][p.dataIndex]; }};
  }}
}});

chart.setOption({{
  title:{{ text:'{chart_title}', left:'center', top:0,
           textStyle:{{ fontSize:15, fontWeight:'bold', color:'#333' }} }},
  tooltip:{{
    trigger:'axis', axisPointer:{{ type:'shadow' }},
    formatter: function(ps) {{
      var h='<b>'+ps[0].axisValue+'</b><br/>', t=0;
      ps.forEach(function(p){{
        if(p.seriesName!=='总计'){{
          h+=p.marker+' '+p.seriesName+': '+p.value.toFixed(2)+'{unit}<br/>'; t+=p.value;
        }}
      }});
      return h+'<b>总计: '+t.toFixed(2)+'{unit}</b>';
    }}
  }},
  legend:{{ bottom:0, data:{legend_json},
            itemWidth:14, itemHeight:10, textStyle:{{ fontSize:11 }} }},
  grid:{{ left:'2%', right:'2%', top:45, bottom:45, containLabel:true }},
  xAxis:{{ type:'category', data:months,
           axisLabel:{{ fontSize:11, color:'#555' }},
           axisTick:{{ alignWithLabel:true }} }},
  yAxis:{{ type:'value', show:false }},
  series: rawSeries
}});
window.addEventListener('resize', function(){{ chart.resize(); }});
</script>
</body>
</html>"""

    elif chart_type == 'dual_line':
        # 双线图
        series_json = json.dumps(option_data['series'], ensure_ascii=False)
        months_json = json.dumps(option_data['month_labels'])
        legend_json = json.dumps(option_data['legend_data'], ensure_ascii=False)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{chart_title}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Microsoft YaHei','SimHei',sans-serif; background:#fff; }}
.page {{ max-width:1200px; margin:0 auto; padding:40px 50px; }}
.title {{ font-size:22px; font-weight:bold; color:{title_color}; }}
.line {{ height:3px; background:linear-gradient(to right,#DAA520,#F0E68C); margin:6px 0 18px; }}
.summary {{ font-size:15px; color:#333; line-height:1.9; margin-bottom:10px; }}
#chart {{ width:100%; height:500px; }}
.bar {{ height:6px; background:linear-gradient(to right,#C0392B,#F5B7B1,#FADBD8); margin-top:25px; border-radius:2px; }}
</style>
</head>
<body>
<div class="page">
  <div class="title">{slide_title}</div>
  <div class="line"></div>
  <div class="summary">{summary_html}</div>
  <div id="chart"></div>
  <div class="bar"></div>
</div>
<script>
var chart = echarts.init(document.getElementById('chart'));
chart.setOption({{
  title:{{ text:'{chart_title}', left:'center', top:0,
           textStyle:{{ fontSize:15, fontWeight:'bold', color:'#333' }} }},
  tooltip:{{ trigger:'axis', axisPointer:{{ type:'line' }} }},
  legend:{{ bottom:0, data:{legend_json},
            itemWidth:14, itemHeight:10, textStyle:{{ fontSize:11 }} }},
  grid:{{ left:'3%', right:'3%', top:45, bottom:45, containLabel:true }},
  xAxis:{{ type:'category', data:{months_json},
           axisLabel:{{ fontSize:11, color:'#555' }} }},
  yAxis:{{ type:'value',
           axisLabel:{{ formatter:{option_data['yaxis_formatter']}, fontSize:10, color:'#555' }},
           splitLine:{{ show:true, lineStyle:{{ color:'#DDDDDD', type:'solid' }} }} }},
  series: {series_json}
}});
window.addEventListener('resize', function(){{ chart.resize(); }});
</script>
</body>
</html>"""

    elif chart_type == 'bar_multi_line':
        # 柱状图 + 多折线（双Y轴）
        series_json = json.dumps(option_data['series'], ensure_ascii=False)
        months_json = json.dumps(option_data['month_labels'])
        legend_json = json.dumps(option_data['legend_data'], ensure_ascii=False)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{chart_title}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Microsoft YaHei','SimHei',sans-serif; background:#fff; }}
.page {{ max-width:1200px; margin:0 auto; padding:40px 50px; }}
.title {{ font-size:22px; font-weight:bold; color:{title_color}; }}
.line {{ height:3px; background:linear-gradient(to right,#DAA520,#F0E68C); margin:6px 0 18px; }}
.summary {{ font-size:15px; color:#333; line-height:1.9; margin-bottom:10px; }}
#chart {{ width:100%; height:500px; }}
.bar {{ height:6px; background:linear-gradient(to right,#C0392B,#F5B7B1,#FADBD8); margin-top:25px; border-radius:2px; }}
</style>
</head>
<body>
<div class="page">
  <div class="title">{slide_title}</div>
  <div class="line"></div>
  <div class="summary">{summary_html}</div>
  <div id="chart"></div>
  <div class="bar"></div>
</div>
<script>
var chart = echarts.init(document.getElementById('chart'));
chart.setOption({{
  title:{{ text:'{chart_title}', left:'center', top:0,
           textStyle:{{ fontSize:15, fontWeight:'bold', color:'#333' }} }},
  tooltip:{{ trigger:'axis', axisPointer:{{ type:'shadow' }} }},
  legend:{{ bottom:0, data:{legend_json},
            itemWidth:14, itemHeight:10, textStyle:{{ fontSize:11 }} }},
  grid:{{ left:'3%', right:'3%', top:45, bottom:45, containLabel:true }},
  xAxis:{{ type:'category', data:{months_json},
           axisLabel:{{ fontSize:11, color:'#555' }} }},
  yAxis:[
    {{ type:'value', name:'{option_data["yaxis1_name"]}',
       axisLabel:{{ fontSize:10, color:'#555' }},
       splitLine:{{ show:true, lineStyle:{{ color:'#EEEEEE' }} }} }},
    {{ type:'value', name:'{option_data["yaxis2_name"]}',
       axisLabel:{{ formatter:'{{value}}%', fontSize:10, color:'#555' }},
       splitLine:{{ show:false }} }}
  ],
  series: {series_json}
}});
window.addEventListener('resize', function(){{ chart.resize(); }});
</script>
</body>
</html>"""

    else:
        raise ValueError(f"未实现的 HTML 模板: {chart_type}")

    html_path = output_dir / f"{chart_title.replace(' ', '_')}.html"
    html_path.write_text(html, encoding='utf-8')
    return html_path
