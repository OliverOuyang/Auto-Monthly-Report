#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目健康检查工具"""

from pathlib import Path
import subprocess
import sys


def check_dependencies() -> bool:
    """检查依赖包是否安装"""
    print("\n[1/5] 检查依赖包...")
    try:
        result = subprocess.run(
            [sys.executable, 'generate_report.py', 'doctor'],
            capture_output=True,
            text=True,
            check=False
        )
        print(result.stdout)
        return 'OK: True' in result.stdout
    except Exception as e:
        print(f"  ✗ 检查失败: {e}")
        return False


def check_temp_files() -> dict:
    """检查临时文件数量"""
    print("\n[2/5] 检查临时文件...")
    root = Path(__file__).parent.parent

    stats = {
        'pytest_dirs': len(list(root.glob('pytest-cache-files-*'))),
        'temp_files': len(list(root.glob('nul'))) + len(list(root.glob('*.stackdump'))),
        'log_files': len(list(root.glob('task_panel.*.log'))),
    }

    total = sum(stats.values())
    if total == 0:
        print("  [OK] 无临时文件")
    else:
        print(f"  [WARN] 发现 {total} 个临时文件/目录")
        for key, count in stats.items():
            if count > 0:
                print(f"     - {key}: {count}")
        print("  提示: 运行 python scripts/clean_temp_files.py 进行清理")

    return stats


def check_config() -> bool:
    """检查配置有效性"""
    print("\n[3/5] 检查配置有效性...")
    root = Path(__file__).parent.parent
    excel_file = root / "Data" / "2月月报数据_输入ai_0304_完整.xlsx"
    profile_file = root / "config" / "profiles" / "monthly_report_v2_full.yaml"

    if not excel_file.exists():
        print(f"  [WARN] Excel 文件不存在: {excel_file.name}")
        return False

    if not profile_file.exists():
        print(f"  [ERROR] Profile 文件不存在: {profile_file}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, 'generate_report.py', 'validate',
             '--excel', str(excel_file),
             '--profile', str(profile_file)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )

        if 'OK: True' in result.stdout:
            print("  [OK] 配置有效")
            return True
        else:
            print("  [ERROR] 配置验证失败")
            print(result.stdout)
            return False
    except subprocess.TimeoutExpired:
        print("  [WARN] 配置验证超时")
        return False
    except Exception as e:
        print(f"  [ERROR] 检查失败: {e}")
        return False


def check_tests() -> bool:
    """检查测试是否可运行"""
    print("\n[4/5] 检查测试...")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', '--collect-only', '-q'],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )

        if 'error' in result.stdout.lower() or result.returncode != 0:
            print("  [WARN] 测试收集有问题")
            print(result.stdout[:200])
            return False

        # 提取测试数量
        lines = result.stdout.strip().split('\n')
        test_count = 0
        for line in lines:
            if 'test' in line:
                test_count += 1

        print(f"  [OK] 发现 {test_count} 个测试")
        return True
    except subprocess.TimeoutExpired:
        print("  [WARN] 测试收集超时")
        return False
    except Exception as e:
        print(f"  [WARN] 无法运行测试: {e}")
        return False


def check_git_status() -> dict:
    """检查 Git 状态"""
    print("\n[5/5] 检查 Git 状态...")
    try:
        # 检查是否有未提交的改动
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            print("  [WARN] 不是 Git 仓库或 Git 不可用")
            return {'clean': False, 'modified': 0, 'untracked': 0}

        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        modified = sum(1 for line in lines if line.startswith(' M') or line.startswith('M '))
        untracked = sum(1 for line in lines if line.startswith('??'))

        if not lines or (len(lines) == 1 and not lines[0]):
            print("  [OK] 工作区干净")
            return {'clean': True, 'modified': 0, 'untracked': 0}
        else:
            print(f"  [WARN] 工作区有变动: {modified} 个已修改, {untracked} 个未跟踪")
            return {'clean': False, 'modified': modified, 'untracked': untracked}
    except Exception as e:
        print(f"  [WARN] 无法检查 Git 状态: {e}")
        return {'clean': False, 'modified': 0, 'untracked': 0}


def main():
    """主函数"""
    print("=" * 60)
    print("项目健康检查")
    print("=" * 60)

    results = {
        'dependencies': check_dependencies(),
        'temp_files': check_temp_files(),
        'config': check_config(),
        'tests': check_tests(),
        'git': check_git_status(),
    }

    print("\n" + "=" * 60)
    print("检查结果汇总:")
    print(f"  依赖包: {'[OK] 正常' if results['dependencies'] else '[ERROR] 异常'}")
    print(f"  临时文件: {'[OK] 干净' if sum(results['temp_files'].values()) == 0 else '[WARN] 需清理'}")
    print(f"  配置: {'[OK] 有效' if results['config'] else '[ERROR] 无效'}")
    print(f"  测试: {'[OK] 可运行' if results['tests'] else '[WARN] 有问题'}")
    print(f"  Git: {'[OK] 干净' if results['git']['clean'] else '[WARN] 有变动'}")
    print("=" * 60)

    # 返回退出码
    all_ok = all([
        results['dependencies'],
        sum(results['temp_files'].values()) == 0,
        results['config'],
    ])
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
