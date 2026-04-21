# SEC EDGAR 工具参数验证功能说明

## 概述

在 `sec_tools.py` 服务层添加了完整的参数验证功能，所有无效输入都会返回中文的友好错误提示和使用示例。

## 参数验证规则

### 1. get_cik_by_ticker(ticker: str)

**参数验证规则：**
- ticker 不能为空或 None
- ticker 长度必须在 1-10 个字符之间
- ticker 只能包含字母（不能包含数字或特殊字符）

**错误提示示例：**
```python
# 空字符串
{
    "success": False,
    "error": "股票代码不能为空",
    "suggestion": "请提供有效的股票代码，例如：AAPL、BABA、PDD",
    "example": "get_cik_by_ticker('AAPL')"
}

# 无效格式
{
    "success": False,
    "error": "无效的股票代码格式：'AAPL123'",
    "suggestion": "股票代码应为1-10个字母，例如：AAPL、MSFT、GOOGL",
    "example": "get_cik_by_ticker('AAPL')"
}
```

---

### 2. get_company_info(identifier: str)

**参数验证规则：**
- identifier 不能为空或 None
- identifier 长度必须在 1-20 个字符之间
- 支持 ticker（如 "AAPL"）或 CIK（如 "0000320193"）格式

**错误提示示例：**
```python
# 空字符串
{
    "success": False,
    "error": "公司标识符不能为空",
    "suggestion": "请提供股票代码（如AAPL）或CIK号码（如0000320193）",
    "example": "get_company_info('AAPL') 或 get_company_info('0000320193')"
}

# 无效长度
{
    "success": False,
    "error": "无效的公司标识符长度：'AAAAAAAAAAAAAAAAAAAAAAAAA'",
    "suggestion": "股票代码应为1-10个字母，CIK应为10位数字",
    "example": "get_company_info('AAPL') 或 get_company_info('0000320193')"
}
```

---

### 3. search_companies(query: str, limit: int = 10)

**参数验证规则：**
- query 不能为空或 None
- query 长度必须至少 2 个字符
- limit 必须在 1-100 之间

**错误提示示例：**
```python
# 空字符串
{
    "success": False,
    "error": "搜索关键词不能为空",
    "suggestion": "请提供至少2个字符的公司名称关键词",
    "example": "search_companies('Apple') 或 search_companies('Technology')"
}

# 太短的query
{
    "success": False,
    "error": "搜索关键词太短：'A'",
    "suggestion": "请提供至少2个字符的公司名称关键词",
    "example": "search_companies('Apple') 或 search_companies('Tesla')"
}

# 无效的limit
{
    "success": False,
    "error": "无效的返回数量限制：0",
    "suggestion": "返回数量应在1-100之间",
    "example": "search_companies('Apple', limit=10)"
}
```

---

### 4. get_recent_filings(identifier, form_type=None, days=30, limit=40)

**参数验证规则：**
- identifier 不能为空或 None
- days 必须在 1-3650 之间（约10年）
- limit 必须在 1-100 之间
- form_type 如果提供，必须是非空字符串

**错误提示示例：**
```python
# 空identifier
{
    "success": False,
    "error": "公司标识符不能为空",
    "suggestion": "请提供股票代码（如AAPL）或CIK号码（如0000320193）",
    "example": "get_recent_filings('AAPL') 或 get_recent_filings('0000320193', form_type='10-K')"
}

# 无效的days
{
    "success": False,
    "error": "无效的天数参数：0",
    "suggestion": "天数应在1-3650之间（约10年）",
    "example": "get_recent_filings('AAPL', days=90)"
}

# 无效的limit
{
    "success": False,
    "error": "无效的返回数量限制：200",
    "suggestion": "返回数量应在1-100之间",
    "example": "get_recent_filings('AAPL', limit=20)"
}

# 无效的form_type
{
    "success": False,
    "error": "无效的表格类型参数",
    "suggestion": "有效的表格类型包括：10-K, 10-Q, 8-K, 10-K/A, 10-Q/A, 8-K/A, DEF 14A, S-1, 4, 3",
    "example": "get_recent_filings('AAPL', form_type='10-K')"
}
```

---

### 5. get_company_facts(identifier: str)

**参数验证规则：**
- identifier 不能为空或 None
- identifier 长度必须在 1-20 个字符之间
- 支持 ticker（如 "AAPL"）或 CIK（如 "0000320193"）格式

**错误提示示例：**
```python
# 空字符串
{
    "success": False,
    "error": "公司标识符不能为空",
    "suggestion": "请提供股票代码（如AAPL）或CIK号码（如0000320193）",
    "example": "get_company_facts('AAPL') 或 get_company_facts('0000320193')"
}

# 无效长度
{
    "success": False,
    "error": "无效的公司标识符长度：'AAAAAAAAAAAAAAAAAAAAAAAAA'",
    "suggestion": "股票代码应为1-10个字母，CIK应为10位数字",
    "example": "get_company_facts('AAPL') 或 get_company_facts('0000320193')"
}
```

---

## 测试

运行参数验证测试：

```bash
cd backend
python app/services/sec_edgar_server/test_validation_simple.py
```

测试覆盖以下场景：
- ✓ 空字符串验证
- ✓ None 参数验证
- ✓ 格式验证（长度、字符类型）
- ✓ 数值范围验证（days、limit）
- ✓ 正常输入验证

## 设计原则

1. **服务层验证**：所有参数验证都在 `sec_tools.py` 服务层完成，不在 `agent_tools.py` 中验证
2. **中文提示**：所有错误提示和使用示例都使用中文
3. **友好建议**：每个错误都包含具体的建议和正确的使用示例
4. **快速失败**：在执行任何网络请求之前先验证参数，避免不必要的API调用
5. **一致性**：所有函数的验证规则和错误格式保持一致

## 修改的文件

- `backend/app/services/sec_edgar_server/sec_tools.py` - 主要修改文件
  - get_cik_by_ticker()
  - get_company_info()
  - search_companies()
  - get_recent_filings()
  - get_company_facts()

## 相关文件

- `backend/app/services/sec_edgar_server/test_validation_simple.py` - 参数验证测试脚本
- `backend/app/services/sec_edgar_server/sync_tickers.py` - SEC数据同步脚本
