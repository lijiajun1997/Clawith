#!/usr/bin/env python3
"""
测试 SEC EDGAR 工具的参数验证功能

测试各种无效输入参数，确保返回友好的中文错误提示
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.sec_edgar_server.sec_tools import SECEdgarTools


def test_get_cik_by_ticker_validation():
    """测试 get_cik_by_ticker 的参数验证"""
    print("=" * 70)
    print("【测试】get_cik_by_ticker 参数验证")
    print("=" * 70)

    tools = SECEdgarTools()

    # 测试1: 空字符串
    print("\n【测试1】空字符串：")
    result = tools.get_cik_by_ticker("")
    print(f"结果: {result}")

    # 测试2: None
    print("\n【测试2】None参数：")
    result = tools.get_cik_by_ticker(None)  # type: ignore
    print(f"结果: {result}")

    # 测试3: 过长的ticker
    print("\n【测试3】过长的ticker：")
    result = tools.get_cik_by_ticker("ABCDEFGHIJKLMNOP")
    print(f"结果: {result}")

    # 测试4: 包含数字的ticker
    print("\n【测试4】包含数字的ticker：")
    result = tools.get_cik_by_ticker("AAPL123")
    print(f"结果: {result}")

    # 测试5: 正常ticker（如果本地缓存有数据）
    print("\n【测试5】正常ticker（AAPL）：")
    result = tools.get_cik_by_ticker("AAPL")
    print(f"结果: {result}")


def test_get_company_info_validation():
    """测试 get_company_info 的参数验证"""
    print("\n" + "=" * 70)
    print("【测试】get_company_info 参数验证")
    print("=" * 70)

    tools = SECEdgarTools()

    # 测试1: 空字符串
    print("\n【测试1】空字符串：")
    result = tools.get_company_info("")
    print(f"结果: {result}")

    # 测试2: None
    print("\n【测试2】None参数：")
    result = tools.get_company_info(None)  # type: ignore
    print(f"结果: {result}")

    # 测试3: 过长的identifier
    print("\n【测试3】过长的identifier：")
    result = tools.get_company_info("A" * 25)
    print(f"结果: {result}")

    # 测试4: 正常ticker（如果本地缓存有数据）
    print("\n【测试4】正常ticker（AAPL）：")
    result = tools.get_company_info("AAPL")
    print(f"结果: {result}")


def test_search_companies_validation():
    """测试 search_companies 的参数验证"""
    print("\n" + "=" * 70)
    print("【测试】search_companies 参数验证")
    print("=" * 70)

    tools = SECEdgarTools()

    # 测试1: 空字符串
    print("\n【测试1】空字符串：")
    result = tools.search_companies("")
    print(f"结果: {result}")

    # 测试2: None
    print("\n【测试2】None参数：")
    result = tools.search_companies(None)  # type: ignore
    print(f"结果: {result}")

    # 测试3: 太短的query
    print("\n【测试3】太短的query（1个字符）：")
    result = tools.search_companies("A")
    print(f"结果: {result}")

    # 测试4: 无效的limit
    print("\n【测试4】无效的limit（0）：")
    result = tools.search_companies("Apple", limit=0)
    print(f"结果: {result}")

    # 测试5: 无效的limit（超过100）
    print("\n【测试5】无效的limit（200）：")
    result = tools.search_companies("Apple", limit=200)
    print(f"结果: {result}")

    # 测试6: 正常query
    print("\n【测试6】正常query（Apple）：")
    result = tools.search_companies("Apple", limit=5)
    print(f"结果: {result}")


def test_get_recent_filings_validation():
    """测试 get_recent_filings 的参数验证"""
    print("\n" + "=" * 70)
    print("【测试】get_recent_filings 参数验证")
    print("=" * 70)

    tools = SECEdgarTools()

    # 测试1: 空identifier
    print("\n【测试1】空identifier：")
    result = tools.get_recent_filings(identifier="")
    print(f"结果: {result}")

    # 测试2: None identifier
    print("\n【测试2】None identifier：")
    result = tools.get_recent_filings(identifier=None)
    print(f"结果: {result}")

    # 测试3: 无效的days（0）
    print("\n【测试3】无效的days（0）：")
    result = tools.get_recent_filings(identifier="AAPL", days=0)
    print(f"结果: {result}")

    # 测试4: 无效的days（超过3650）
    print("\n【测试4】无效的days（4000）：")
    result = tools.get_recent_filings(identifier="AAPL", days=4000)
    print(f"结果: {result}")

    # 测试5: 无效的limit（0）
    print("\n【测试5】无效的limit（0）：")
    result = tools.get_recent_filings(identifier="AAPL", limit=0)
    print(f"结果: {result}")

    # 测试6: 无效的limit（超过100）
    print("\n【测试6】无效的limit（200）：")
    result = tools.get_recent_filings(identifier="AAPL", limit=200)
    print(f"结果: {result}")

    # 测试7: 正常参数
    print("\n【测试7】正常参数（AAPL, 30天）：")
    result = tools.get_recent_filings(identifier="AAPL", days=30, limit=10)
    print(f"结果: {result}")


def test_get_company_facts_validation():
    """测试 get_company_facts 的参数验证"""
    print("\n" + "=" * 70)
    print("【测试】get_company_facts 参数验证")
    print("=" * 70)

    tools = SECEdgarTools()

    # 测试1: 空字符串
    print("\n【测试1】空字符串：")
    result = tools.get_company_facts("")
    print(f"结果: {result}")

    # 测试2: None
    print("\n【测试2】None参数：")
    result = tools.get_company_facts(None)  # type: ignore
    print(f"结果: {result}")

    # 测试3: 过长的identifier
    print("\n【测试3】过长的identifier：")
    result = tools.get_company_facts("A" * 25)
    print(f"结果: {result}")

    # 测试4: 正常ticker
    print("\n【测试4】正常ticker（AAPL）：")
    result = tools.get_company_facts("AAPL")
    print(f"结果: {result}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("SEC EDGAR 工具参数验证测试")
    print("=" * 70)

    test_get_cik_by_ticker_validation()
    test_get_company_info_validation()
    test_search_companies_validation()
    test_get_recent_filings_validation()
    test_get_company_facts_validation()

    print("\n" + "=" * 70)
    print("✓ 所有参数验证测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
