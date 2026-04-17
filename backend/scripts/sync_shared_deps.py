#!/usr/bin/env python3
"""
自动同步系统Python包到共享依赖目录

这个脚本会自动将系统中已安装的常用Python包同步到共享依赖目录，
确保agent的代码执行环境能够访问这些包。
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 常用需要同步的包列表
COMMON_PACKAGES = [
    # 数据科学
    "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    # 机器学习
    "scikit-learn", "xgboost", "lightgbm",
    # 网络请求
    "requests", "aiohttp", "httpx", "urllib3",
    # 文件处理
    "openpyxl", "xlrd", "python-docx", "PyPDF2", "pdfplumber", "pillow",
    # 网页解析
    "beautifulsoup4", "lxml", "html5lib",
    # 数据验证
    "pydantic", "validators",
    # 工具库
    "python-dateutil", "pytz", "click", "tqdm",
    # 其他常用
    "openai", "anthropic", "redis", "asyncpg",
]

def check_package_installed(package_name):
    """检查包是否已安装在系统中"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def sync_package_to_shared(package_name, shared_deps_dir):
    """将包同步到共享依赖目录"""
    print(f"📦 同步包: {package_name}")

    try:
        # 使用pip install --target来安装到共享目录
        # 不使用--no-deps，让pip自动处理依赖关系，确保版本兼容性
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--target", str(shared_deps_dir),
             "--upgrade", package_name],
            capture_output=True,
            text=True,
            timeout=120  # 增加超时时间，因为要处理依赖
        )

        if result.returncode == 0:
            print(f"  ✅ {package_name} 同步成功")
            return True
        else:
            print(f"  ❌ {package_name} 同步失败: {result.stderr[:100]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ⏱️ {package_name} 同步超时")
        return False
    except Exception as e:
        print(f"  ❌ {package_name} 同步异常: {str(e)}")
        return False

def main():
    """主函数"""
    # 获取共享依赖目录
    settings = os.environ.get("SHARED_DEPS_DIR", "/data/shared-deps")
    shared_deps_dir = Path(settings) / "pip"

    # 确保目录存在
    shared_deps_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔧 开始同步Python包到共享依赖目录: {shared_deps_dir}")
    print(f"📋 计划同步 {len(COMMON_PACKAGES)} 个常用包")

    success_count = 0
    failed_packages = []

    for package in COMMON_PACKAGES:
        # 先检查包是否已安装
        if not check_package_installed(package):
            print(f"⚠️  {package} 未安装在系统中，跳过")
            continue

        # 同步到共享目录
        if sync_package_to_shared(package, shared_deps_dir):
            success_count += 1
        else:
            failed_packages.append(package)

    # 输出总结
    print(f"\n📊 同步完成:")
    print(f"  ✅ 成功: {success_count}/{len(COMMON_PACKAGES)}")
    print(f"  📁 目标目录: {shared_deps_dir}")

    if failed_packages:
        print(f"  ❌ 失败: {len(failed_packages)}")
        for pkg in failed_packages:
            print(f"     - {pkg}")

    # 设置目录权限（确保agent用户可以读取）
    try:
        os.chmod(str(shared_deps_dir), 0o755)
        for item in shared_deps_dir.iterdir():
            if item.is_dir():
                os.chmod(str(item), 0o755)
    except Exception as e:
        print(f"⚠️  设置权限失败: {e}")

    print("🎉 依赖同步完成")

if __name__ == "__main__":
    main()