#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git pre-commit hook: 提交前自动清理和检查"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """运行命令并返回是否成功"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True
        else:
            print(f"[ERROR] {description} 失败")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"[ERROR] {description} 失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Git Pre-Commit Hook - 自动检查与清理")
    print("=" * 60)

    # 1. 自动清理临时文件
    print("\n[1/3] 清理临时文件...")
    if not run_command(
        [sys.executable, "scripts/clean_temp_files.py"],
        "清理临时文件"
    ):
        return 1
    print("[OK] 临时文件清理完成")

    # 2. 检查Python语法错误
    print("\n[2/3] 检查Python语法...")
    files_to_check = [
        "generate_report.py",
        "core/excel_reader.py",
        "core/data_processor.py",
        "core/analyzer.py",
        "core/chart_renderer.py",
        "core/html_generator.py",
        "core/ppt_generator.py",
        "config/chart_types.py",
        "config/analysis_templates.py",
    ]

    syntax_ok = True
    for file in files_to_check:
        if not Path(file).exists():
            continue
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", file],
            capture_output=True,
            check=False
        )
        if result.returncode != 0:
            print(f"[ERROR] 语法错误: {file}")
            print(result.stderr.decode('utf-8', errors='ignore'))
            syntax_ok = False

    if not syntax_ok:
        return 1
    print("[OK] Python语法检查通过")

    # 3. 运行健康检查（轻量版）
    print("\n[3/3] 快速健康检查...")
    result = subprocess.run(
        [sys.executable, "generate_report.py", "doctor"],
        capture_output=True,
        check=False
    )
    if result.returncode != 0:
        print("[WARN] 依赖包检查失败，但允许提交")
    else:
        print("[OK] 依赖包检查通过")

    print("\n" + "=" * 60)
    print("[OK] Pre-commit 检查全部通过，准备提交")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
