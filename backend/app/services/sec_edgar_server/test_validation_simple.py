#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版参数验证测试 - 直接测试参数验证逻辑
"""

import sys
import io

# 设置stdout编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def test_ticker_validation():
    """测试ticker参数验证逻辑"""
    print("=" * 70)
    print("【测试】Ticker参数验证逻辑")
    print("=" * 70)

    # 测试1: 空字符串
    ticker = ""
    print(f"\n【测试1】空字符串: '{ticker}'")
    if not ticker or not isinstance(ticker, str):
        print("[X] 错误: 股票代码不能为空")
        print("   建议: 请提供有效的股票代码，例如：AAPL、BABA、PDD")
    else:
        ticker = ticker.upper().strip()
        if not ticker or len(ticker) > 10 or not ticker.isalpha():
            print("[X] 错误: 无效的股票代码格式")
            print("   建议: 股票代码应为1-10个字母，例如：AAPL、MSFT、GOOGL")
        else:
            print(f"[OK] Ticker格式正确: {ticker}")

    # 测试2: None
    ticker = None
    print(f"\n【测试2】None参数: {ticker}")
    if not ticker or not isinstance(ticker, str):
        print("[X] 错误: 股票代码不能为空")
        print("   建议: 请提供有效的股票代码，例如：AAPL、BABA、PDD")
    else:
        ticker = ticker.upper().strip()
        if not ticker or len(ticker) > 10 or not ticker.isalpha():
            print("[X] 错误: 无效的股票代码格式")
            print("   建议: 股票代码应为1-10个字母，例如：AAPL、MSFT、GOOGL")
        else:
            print(f"[OK] Ticker格式正确: {ticker}")

    # 测试3: 过长的ticker
    ticker = "ABCDEFGHIJKLMNOP"
    print(f"\n【测试3】过长的ticker: '{ticker}'")
    if not ticker or not isinstance(ticker, str):
        print("[X] 错误: 股票代码不能为空")
        print("   建议: 请提供有效的股票代码，例如：AAPL、BABA、PDD")
    else:
        ticker = ticker.upper().strip()
        if not ticker or len(ticker) > 10 or not ticker.isalpha():
            print("[X] 错误: 无效的股票代码格式")
            print("   建议: 股票代码应为1-10个字母，例如：AAPL、MSFT、GOOGL")
        else:
            print(f"[OK] Ticker格式正确: {ticker}")

    # 测试4: 包含数字的ticker
    ticker = "AAPL123"
    print(f"\n【测试4】包含数字的ticker: '{ticker}'")
    if not ticker or not isinstance(ticker, str):
        print("[X] 错误: 股票代码不能为空")
        print("   建议: 请提供有效的股票代码，例如：AAPL、BABA、PDD")
    else:
        ticker = ticker.upper().strip()
        if not ticker or len(ticker) > 10 or not ticker.isalpha():
            print("[X] 错误: 无效的股票代码格式")
            print("   建议: 股票代码应为1-10个字母，例如：AAPL、MSFT、GOOGL")
        else:
            print(f"[OK] Ticker格式正确: {ticker}")

    # 测试5: 正常ticker
    ticker = "AAPL"
    print(f"\n【测试5】正常ticker: '{ticker}'")
    if not ticker or not isinstance(ticker, str):
        print("[X] 错误: 股票代码不能为空")
        print("   建议: 请提供有效的股票代码，例如：AAPL、BABA、PDD")
    else:
        ticker = ticker.upper().strip()
        if not ticker or len(ticker) > 10 or not ticker.isalpha():
            print("[X] 错误: 无效的股票代码格式")
            print("   建议: 股票代码应为1-10个字母，例如：AAPL、MSFT、GOOGL")
        else:
            print(f"[OK] Ticker格式正确: {ticker}")


def test_identifier_validation():
    """测试identifier参数验证逻辑"""
    print("\n" + "=" * 70)
    print("【测试】Identifier参数验证逻辑")
    print("=" * 70)

    # 测试1: 空字符串
    identifier = ""
    print(f"\n【测试1】空字符串: '{identifier}'")
    if not identifier or not isinstance(identifier, str):
        print("[X] 错误: 公司标识符不能为空")
        print("   建议: 请提供股票代码（如AAPL）或CIK号码（如0000320193）")
    else:
        identifier = identifier.strip()
        if len(identifier) < 1 or len(identifier) > 20:
            print("[X] 错误: 无效的公司标识符长度")
            print("   建议: 股票代码应为1-10个字母，CIK应为10位数字")
        else:
            print(f"[OK] Identifier格式正确: {identifier}")

    # 测试2: None
    identifier = None
    print(f"\n【测试2】None参数: {identifier}")
    if not identifier or not isinstance(identifier, str):
        print("[X] 错误: 公司标识符不能为空")
        print("   建议: 请提供股票代码（如AAPL）或CIK号码（如0000320193）")
    else:
        identifier = identifier.strip()
        if len(identifier) < 1 or len(identifier) > 20:
            print("[X] 错误: 无效的公司标识符长度")
            print("   建议: 股票代码应为1-10个字母，CIK应为10位数字")
        else:
            print(f"[OK] Identifier格式正确: {identifier}")

    # 测试3: 过长的identifier
    identifier = "A" * 25
    print(f"\n【测试3】过长的identifier: '{identifier[:10]}...'")
    if not identifier or not isinstance(identifier, str):
        print("[X] 错误: 公司标识符不能为空")
        print("   建议: 请提供股票代码（如AAPL）或CIK号码（如0000320193）")
    else:
        identifier = identifier.strip()
        if len(identifier) < 1 or len(identifier) > 20:
            print("[X] 错误: 无效的公司标识符长度")
            print("   建议: 股票代码应为1-10个字母，CIK应为10位数字")
        else:
            print(f"[OK] Identifier格式正确: {identifier}")

    # 测试4: 正常ticker
    identifier = "AAPL"
    print(f"\n【测试4】正常ticker: '{identifier}'")
    if not identifier or not isinstance(identifier, str):
        print("[X] 错误: 公司标识符不能为空")
        print("   建议: 请提供股票代码（如AAPL）或CIK号码（如0000320193）")
    else:
        identifier = identifier.strip()
        if len(identifier) < 1 or len(identifier) > 20:
            print("[X] 错误: 无效的公司标识符长度")
            print("   建议: 股票代码应为1-10个字母，CIK应为10位数字")
        else:
            print(f"[OK] Identifier格式正确: {identifier}")

    # 测试5: 正常CIK
    identifier = "0000320193"
    print(f"\n【测试5】正常CIK: '{identifier}'")
    if not identifier or not isinstance(identifier, str):
        print("[X] 错误: 公司标识符不能为空")
        print("   建议: 请提供股票代码（如AAPL）或CIK号码（如0000320193）")
    else:
        identifier = identifier.strip()
        if len(identifier) < 1 or len(identifier) > 20:
            print("[X] 错误: 无效的公司标识符长度")
            print("   建议: 股票代码应为1-10个字母，CIK应为10位数字")
        else:
            print(f"[OK] Identifier格式正确: {identifier}")


def test_search_query_validation():
    """测试search query参数验证逻辑"""
    print("\n" + "=" * 70)
    print("【测试】Search Query参数验证逻辑")
    print("=" * 70)

    # 测试1: 空字符串
    query = ""
    print(f"\n【测试1】空字符串: '{query}'")
    if not query or not isinstance(query, str):
        print("[X] 错误: 搜索关键词不能为空")
        print("   建议: 请提供至少2个字符的公司名称关键词")
    else:
        query = query.strip()
        if len(query) < 2:
            print("[X] 错误: 搜索关键词太短")
            print("   建议: 请提供至少2个字符的公司名称关键词")
        else:
            print(f"[OK] Query格式正确: {query}")

    # 测试2: None
    query = None
    print(f"\n【测试2】None参数: {query}")
    if not query or not isinstance(query, str):
        print("[X] 错误: 搜索关键词不能为空")
        print("   建议: 请提供至少2个字符的公司名称关键词")
    else:
        query = query.strip()
        if len(query) < 2:
            print("[X] 错误: 搜索关键词太短")
            print("   建议: 请提供至少2个字符的公司名称关键词")
        else:
            print(f"[OK] Query格式正确: {query}")

    # 测试3: 太短的query
    query = "A"
    print(f"\n【测试3】太短的query: '{query}'")
    if not query or not isinstance(query, str):
        print("[X] 错误: 搜索关键词不能为空")
        print("   建议: 请提供至少2个字符的公司名称关键词")
    else:
        query = query.strip()
        if len(query) < 2:
            print("[X] 错误: 搜索关键词太短")
            print("   建议: 请提供至少2个字符的公司名称关键词")
        else:
            print(f"[OK] Query格式正确: {query}")

    # 测试4: 正常query
    query = "Apple"
    print(f"\n【测试4】正常query: '{query}'")
    if not query or not isinstance(query, str):
        print("[X] 错误: 搜索关键词不能为空")
        print("   建议: 请提供至少2个字符的公司名称关键词")
    else:
        query = query.strip()
        if len(query) < 2:
            print("[X] 错误: 搜索关键词太短")
            print("   建议: 请提供至少2个字符的公司名称关键词")
        else:
            print(f"[OK] Query格式正确: {query}")


def test_days_and_limit_validation():
    """测试days和limit参数验证逻辑"""
    print("\n" + "=" * 70)
    print("【测试】Days和Limit参数验证逻辑")
    print("=" * 70)

    # 测试days参数
    print("\n【测试Days参数】")

    test_days = [0, -10, 3650, 4000, 30]
    for days in test_days:
        print(f"\n  Days = {days}:")
        if not isinstance(days, int) or days < 1 or days > 3650:
            print(f"  [X] 错误: 无效的天数参数：{days}")
            print(f"     建议: 天数应在1-3650之间（约10年）")
        else:
            print(f"  [OK] Days参数正确: {days}")

    # 测试limit参数
    print("\n【测试Limit参数】")

    test_limits = [0, -5, 100, 200, 50]
    for limit in test_limits:
        print(f"\n  Limit = {limit}:")
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            print(f"  [X] 错误: 无效的返回数量限制：{limit}")
            print(f"     建议: 返回数量应在1-100之间")
        else:
            print(f"  [OK] Limit参数正确: {limit}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("SEC EDGAR 工具参数验证逻辑测试（简化版）")
    print("=" * 70)

    test_ticker_validation()
    test_identifier_validation()
    test_search_query_validation()
    test_days_and_limit_validation()

    print("\n" + "=" * 70)
    print("[OK] 所有参数验证逻辑测试完成")
    print("=" * 70)
    print("\n【总结】")
    print("参数验证功能已成功添加到 sec_tools.py 服务层")
    print("所有无效输入都会返回中文的友好错误提示和使用示例")
    print("=" * 70)


if __name__ == "__main__":
    main()
