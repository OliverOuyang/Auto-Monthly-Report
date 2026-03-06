#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装 Git Hooks 到本地仓库"""

from pathlib import Path
import shutil
import stat
import sys


def install_hooks():
    """安装 pre-commit hook"""
    # 项目根目录
    root = Path(__file__).parent.parent

    # hooks 模板目录
    hooks_template_dir = root / 'hooks'

    # Git hooks 目录
    git_hooks_dir = root / '.git' / 'hooks'

    if not git_hooks_dir.exists():
        print("[ERROR] .git/hooks 目录不存在")
        print("        请确保在 Git 仓库根目录运行此脚本")
        return False

    print("=" * 60)
    print("Git Hooks 安装工具")
    print("=" * 60)

    # 检测操作系统，选择对应的hook文件
    import platform
    is_windows = platform.system() == 'Windows'

    # 安装 pre-commit hook
    hook_name = 'pre-commit'
    if is_windows:
        # Windows: 安装一个wrapper脚本，调用Python版本
        wrapper_content = f"""#!/usr/bin/env bash
# Windows Git Hook Wrapper
python "{root}/hooks/pre-commit.py"
exit $?
"""
        dst = git_hooks_dir / hook_name
        dst.write_text(wrapper_content, encoding='utf-8')
        print(f"[OK] 已安装: {hook_name} (Windows wrapper)")
    else:
        # Unix/Linux/Mac: 安装bash脚本
        src = hooks_template_dir / hook_name
        dst = git_hooks_dir / hook_name

        if not src.exists():
            print(f"[ERROR] 模板文件不存在: {src}")
            return False

        # 备份已存在的 hook
        if dst.exists():
            backup = git_hooks_dir / f'{hook_name}.backup'
            shutil.copy2(dst, backup)
            print(f"[OK] 已备份现有 hook 到: {backup.name}")

        # 复制 hook 文件
        shutil.copy2(src, dst)

        # 设置可执行权限
        try:
            st = dst.stat()
            dst.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"[OK] 已安装: {hook_name}")
        except Exception as e:
            print(f"[WARN] 权限设置失败: {e}")
            print(f"       但文件已复制到: {dst}")

    print("\n" + "=" * 60)
    print("安装完成！")
    print("=" * 60)
    print("\nPre-commit hook 会在每次提交前自动执行:")
    print("  1. 清理临时文件")
    print("  2. 检查 Python 语法")
    print("  3. 验证依赖包完整性")
    print("\n如需禁用 hook，可以:")
    print("  - 临时禁用: git commit --no-verify")
    print(f"  - 永久禁用: 删除 .git/hooks/{hook_name}")
    print("=" * 60)

    return True


def uninstall_hooks():
    """卸载 Git hooks"""
    root = Path(__file__).parent
    git_hooks_dir = root / '.git' / 'hooks'
    hook_name = 'pre-commit'
    dst = git_hooks_dir / hook_name

    if dst.exists():
        dst.unlink()
        print(f"[OK] 已卸载: {hook_name}")

        # 恢复备份
        backup = git_hooks_dir / f'{hook_name}.backup'
        if backup.exists():
            shutil.copy2(backup, dst)
            backup.unlink()
            print(f"[OK] 已恢复备份")
    else:
        print(f"[WARN] Hook 不存在: {hook_name}")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='管理 Git Hooks')
    parser.add_argument('action', choices=['install', 'uninstall'],
                       default='install', nargs='?',
                       help='install: 安装 hooks, uninstall: 卸载 hooks')

    args = parser.parse_args()

    if args.action == 'install':
        success = install_hooks()
        sys.exit(0 if success else 1)
    elif args.action == 'uninstall':
        uninstall_hooks()
        sys.exit(0)


if __name__ == '__main__':
    main()
