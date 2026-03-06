# 运行手册

## 1. 环境检查
```bash
python generate_report.py doctor
```

## 2. 配置校验
```bash
python generate_report.py validate --excel <excel_path> --profile <profile_path>
```

## 3. 生成报告
```bash
python generate_report.py run \
  --excel <excel_path> \
  --profile <profile_path> \
  --output <ppt_path> \
  --emit-manifest
```

## 4. 仅生成部分指标
```bash
python generate_report.py run \
  --excel <excel_path> \
  --profile <profile_path> \
  --indicators id_a,id_b,id_c \
  --output <ppt_path>
```

## 5. 常见故障
1. `PermissionError` 写PPT失败：目标PPT文件被打开，先关闭后重试。
2. `Derived builder not found`：profile 配置了 derived 指标但未实现 `build_{indicator_id}_pivot`。
3. `No indicators found`：indicator 过滤后为空或 profile 读取失败。
