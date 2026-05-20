---
name: Excel Advanced
description: Excel 读写工具完整指南 — 操作列表、参数说明、示例、边界处理与 Python fallback。使用 excel_advanced 工具前必读。
---

# Excel Advanced Toolkit 使用指南

## 快速开始

工具名：`excel_advanced`
必填参数：`action`
文件路径参数：`file_path`（或 `filename`）

**首次使用或遇到参数错误时，先读此文档再调用工具。**

---

## 操作一览

### 文件操作

| action | 必填参数 | 说明 |
|--------|----------|------|
| `create` | — | 创建空白工作簿，默认文件名 `new_workbook.xlsx` |
| `read_workbook` | `file_path` | 读取整个工作簿所有 Sheet 数据 |
| `list_sheets` | `file_path` | 列出所有 Sheet 名称 |

### Sheet 管理

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `add_sheet` | `file_path` | `sheet_name` | 添加新 Sheet（同名自动追加 `_2`, `_3`…） |
| `delete_sheet` | `file_path`, `sheet_name` | — | 删除指定 Sheet（不能删最后一个） |
| `rename_sheet` | `file_path`, `old_name`, `new_name` | — | 重命名 Sheet |

### 读取数据

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `read_cell` | `file_path`, `cell` | `sheet_name` | 读取单个单元格，如 `A1` |
| `read_range` | `file_path` | `range`, `sheet_name` | 读取范围，如 `A1:C10`；不传 `range` 则读取整个 Sheet |

### 写入数据

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `write_cell` | `file_path`, `cell`, `value` | `sheet_name` | 写入单个单元格 |
| `write_range` | `file_path`, `data` | `range`, `sheet_name`, `start_row`, `start_col` | 写入二维数组 |
| `set_formula` | `file_path`, `cell`, `formula` | `sheet_name` | 设置公式，如 `SUM(A1:A10)` |

### 批注

| action | 必填参数 | 说明 |
|--------|----------|------|
| `read_comments` | `file_path` | 读取所有批注（旧版 Notes + 新版 Threaded Comments） |

---

## 参数详解

| 参数 | 类型 | 说明 |
|------|------|------|
| `action` | string | 操作名称（见上表） |
| `file_path` | string | Excel 文件路径，相对 workspace，如 `reports/data.xlsx` |
| `sheet_name` | string | Sheet 名称，缺省时使用当前活动 Sheet |
| `cell` | string | 单元格地址，如 `A1`, `B5`, `AA10` |
| `range` | string | 范围地址，如 `A1:C10` |
| `value` | any | 要写入的值（数字、文本、布尔） |
| `data` | array[array] | 二维数组，如 `[["Name","Age"],["Alice",30]]` |
| `formula` | string | 公式（无需前导 `=`，系统自动补） |
| `old_name` | string | 旧 Sheet 名（rename_sheet 用） |
| `new_name` | string | 新 Sheet 名（rename_sheet 用） |

---

## 典型工作流

### 创建报表并写入数据
```
1. excel_advanced(action="create", file_path="workspace/report.xlsx")
2. excel_advanced(action="write_range", file_path="workspace/report.xlsx", data=[["科目","金额"],["收入","1000000"]])
3. excel_advanced(action="set_formula", file_path="workspace/report.xlsx", cell="B3", formula="SUM(B2:B2)")
```

### 读取已有文件
```
1. excel_advanced(action="list_sheets", file_path="workspace/data.xlsx")
2. excel_advanced(action="read_range", file_path="workspace/data.xlsx", range="A1:F20", sheet_name="Sheet1")
```

---

## 边界情况处理

| 场景 | 工具行为 |
|------|----------|
| 合并单元格写入 | 自动解除合并后写入 |
| Sheet 已存在（add_sheet） | 自动追加序号 `_2`, `_3`… |
| 文件不存在（读取操作） | 返回错误 + 目录文件列表提示 |
| 文件路径无 workspace/ 前缀 | 自动搜索 agent 目录 |
| 写入到不存在的文件 | 自动创建新工作簿 |

---

## 何时使用 Python 代码替代

以下场景 `excel_advanced` 无法覆盖，请使用 `run_code`（Python + openpyxl）：

- **条件格式**：数据条、色阶、图标集
- **图表**：柱状图、折线图、饼图
- **数据透视表**
- **单元格样式**：边框、背景色、字体颜色、对齐方式
- **列宽/行高**自动调整
- **合并单元格**（主动合并）
- **冻结窗格、筛选**
- **打印设置**：页眉页脚、打印区域
- **图片插入**
- **VBA 宏操作**

示例代码：
```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = openpyxl.load_workbook("workspace/report.xlsx")
ws = wb.active

# 设置标题样式
ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
ws["A1"].fill = PatternFill(start_color="4472C4", fill_type="solid")

# 合并单元格
ws.merge_cells("A1:D1")

# 自动列宽
for col in ws.columns:
    max_len = max(len(str(c.value or "")) for c in col)
    ws.column_dimensions[col[0].column_letter].width = max_len + 2

wb.save("workspace/report.xlsx")
```
