#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理项目临时文件和缓存"""

from pathlib import Path
import shutil
import sys


def clean_temp_files(dry_run: bool = False) -> dict:
    """
    清理项目根目录的临时文件和目录

    Args:
        dry_run: 如果为True，只列出将要删除的文件，不实际删除

    Returns:
        清理统计信息
    """
    root = Path(__file__).parent.parent
    stats = {
        'pytest_dirs': 0,
        'temp_files': 0,
        'cache_dirs': 0,
        'log_files': 0,
    }

    # 1. 清理 pytest 临时目录
    print("\n[1/4] 检查 pytest 临时目录...")
    pytest_dirs = list(root.glob('pytest-cache-files-*'))
    if pytest_dirs:
        for d in pytest_dirs:
            if dry_run:
                print(f"  [DRY RUN] 将删除: {d.name}/")
            else:
                shutil.rmtree(d, ignore_errors=True)
                print(f"  [OK] 已删除: {d.name}/")
            stats['pytest_dirs'] += 1
    else:
        print("  [OK] 无需清理")

    # 2. 清理临时文件
    print("\n[2/4] 检查临时文件...")
    temp_patterns = ['nul', '*.stackdump', 'temp_*.csv', 'temp_*.xlsx']
    for pattern in temp_patterns:
        for f in root.glob(pattern):
            if f.is_file():
                if dry_run:
                    print(f"  [DRY RUN] 将删除: {f.name}")
                else:
                    f.unlink()
                    print(f"  [OK] 已删除: {f.name}")
                stats['temp_files'] += 1
    if stats['temp_files'] == 0:
        print("  [OK] 无需清理")

    # 3. 清理日志文件
    print("\n[3/4] 检查日志文件...")
    log_patterns = ['task_panel.*.log', '*.out.log', '*.err.log']
    for pattern in log_patterns:
        for f in root.glob(pattern):
            if f.is_file():
                if dry_run:
                    print(f"  [DRY RUN] 将删除: {f.name}")
                else:
                    f.unlink()
                    print(f"  [OK] 已删除: {f.name}")
                stats['log_files'] += 1
    if stats['log_files'] == 0:
        print("  [OK] 无需清理")

    # 4. 清理 Python 缓存
    print("\n[4/4] 检查 Python 缓存...")
    pycache_dirs = list(root.rglob('__pycache__'))
    # 排除虚拟环境目录
    pycache_dirs = [d for d in pycache_dirs if 'venv' not in str(d) and '.venv' not in str(d)]
    if pycache_dirs:
        for d in pycache_dirs:
            if dry_run:
                print(f"  [DRY RUN] 将删除: {d.relative_to(root)}")
            else:
                shutil.rmtree(d, ignore_errors=True)
                print(f"  [OK] 已删除: {d.relative_to(root)}")
            stats['cache_dirs'] += 1
    else:
        print("  [OK] 无需清理")

    return stats


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='清理项目临时文件')
    parser.add_argument('--dry-run', action='store_true',
                       help='只列出将要删除的文件，不实际删除')
    args = parser.parse_args()

    print("=" * 60)
    print("项目临时文件清理工具")
    print("=" * 60)

    if args.dry_run:
        print("\n[!] DRY RUN 模式：不会实际删除文件\n")

    stats = clean_temp_files(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("清理统计:")
    print(f"  - Pytest 临时目录: {stats['pytest_dirs']} 个")
    print(f"  - 临时文件: {stats['temp_files']} 个")
    print(f"  - 日志文件: {stats['log_files']} 个")
    print(f"  - Python 缓存目录: {stats['cache_dirs']} 个")
    total = sum(stats.values())
    print(f"  总计: {total} 项")
    print("=" * 60)

    if args.dry_run:
        print("\n提示: 移除 --dry-run 参数以实际执行清理")
    else:
        print("\n[OK] 清理完成！")


if __name__ == '__main__':
    main()
