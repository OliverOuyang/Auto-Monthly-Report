# -*- coding: utf-8 -*-
"""ECharts HTML 生成"""

import json
import pandas as pd
from pathlib import Path


def generate(pivot, meta: dict, styles: dict, lines: list[str],
             output_dir: str | Path) -> Path:
    """
    生成 ECharts HTML 文件。
    pivot: 透视表（原始值）
    返回 HTML 文件路径。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    categories = meta['categories']
    unit_divisor = meta.get('unit_divisor', 1)
    unit = meta.get('unit', '')
    chart_title = meta.get('chart_title', '')
    slide_title = meta.get('slide_title', '')
    colors = styles.get('colors', {})
    global_styles = styles.get('global', {})
    title_color = global_styles.get('title_color', '#8B4513')
    label_color = global_styles.get('label_color', '#5A5A5A')
    line_color = global_styles.get('total_line_color', '#FF0000')

    pivot_d = pivot / unit_divisor

    # 月份标签
    month_labels = [d.strftime('%b-%y') for d in pivot_d.index]

    def fmt_unit(v):
        return f"{v:.2f}{unit}" if abs(v) >= 0.15 else ""

    ec_data = {c: [round(float(v), 4) for v in pivot_d[c]] for c in categories}
    if '总计' in pivot_d.columns:
        ec_data['总计'] = [round(float(v), 4) for v in pivot_d['总计']]

    ec_labels = {c: [fmt_unit(v) for v in pivot_d[c]] for c in categories}
    if '总计' in pivot_d.columns:
        ec_labels['总计'] = [fmt_unit(v) for v in pivot_d['总计']]

    summary_html = "<br/>".join(lines)

    # 构建 series JSON
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

    # 标签格式化需要在 JS 中处理，这里用模板
    ec_labels_json = json.dumps(ec_labels, ensure_ascii=False)
    series_json = json.dumps(series_items, ensure_ascii=False)
    months_json = json.dumps(month_labels)
    cats_json = json.dumps(categories, ensure_ascii=False)
    legend_json = json.dumps(legend_data, ensure_ascii=False)

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
var cats = {cats_json};
var labels = {ec_labels_json};
var rawSeries = {series_json};

// 注入 label formatter（需要引用 labels 字典）
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

    html_path = output_dir / f"{chart_title.replace(' ', '_')}.html"
    html_path.write_text(html, encoding='utf-8')
    return html_path
