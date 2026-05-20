---
name: Word Advanced
description: Word 文档工具完整指南 — 50+ 操作列表、参数说明、修订模式、示例、边界处理与 Python fallback。使用 word_advanced 工具前必读。
---

# Word Advanced Toolkit 使用指南

## 快速开始

工具名：`word_advanced`
必填参数：`action`
文件路径参数：`filename`

**首次使用或遇到参数错误时，先读此文档再调用工具。**

> **修订模式**：所有编辑操作（增删改、格式化）自动启用 Track Changes，文档在 Word 中打开时会显示修订痕迹。只读操作不受影响。

---

## 操作一览

### 文档管理

| action | 必填参数 | 说明 |
|--------|----------|------|
| `create_document` | `filename` | 新建文档，可选 `title`, `author` |
| `get_document_info` | `filename` | 获取文档属性（标题、作者、段落数等） |
| `get_document_text` | `filename` | 提取全部文本 |
| `get_document_outline` | `filename` | 获取文档结构（段落 + 表格索引） |
| `list_documents` | `directory` | 列出目录下所有 .docx 文件 |
| `copy_document` | `filename`, `output_filename` | 复制文档 |
| `get_document_xml` | `filename` | 查看原始 XML（调试用） |

### 内容操作（修订模式）

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `add_paragraph` | `filename`, `text` | `style`, `font_name`, `font_size`, `bold`, `italic`, `color` | 添加段落 |
| `add_heading` | `filename`, `text`, `level` | `font_name`, `font_size`, `bold`, `italic`, `border_bottom` | 添加标题（level 1-9） |
| `add_table` | `filename`, `rows`, `cols` | `data` | 添加表格 |
| `add_picture` | `filename`, `image_path` | `width` | 插入图片 |
| `add_page_break` | `filename` | — | 分页符 |
| `add_table_of_contents` | `filename` | `title`, `max_level` | 目录 |
| `delete_paragraph` | `filename`, `paragraph_index` | — | 删除段落 |
| `search_and_replace` | `filename`, `search_text`, `replace_text` | — | 全局查找替换 |

### 定位插入（修订模式）

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `insert_header_near_text` | `filename`, `header_title` | `target_text`, `position`, `header_style`, `target_paragraph_index` | 在指定位置插入标题 |
| `insert_paragraph_near_text` | `filename`, `line_text` | `target_text`, `position`, `line_style`, `target_paragraph_index` | 在指定位置插入段落 |
| `insert_list_near_text` | `filename`, `list_items` | `target_text`, `position`, `bullet_type`, `target_paragraph_index` | 插入列表（bullet/number） |

### 块替换（修订模式）

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `replace_paragraph_block_below_header` | `filename`, `header_text`, `new_paragraphs` | `new_paragraph_style` | 替换标题下所有内容 |
| `replace_block_between_manual_anchors` | `filename`, `start_anchor_text`, `new_paragraphs` | `end_anchor_text`, `new_paragraph_style` | 替换两锚点间内容 |

### 格式操作（修订模式）

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `format_text` | `filename`, `paragraph_index`, `start_pos`, `end_pos` | `bold`, `italic`, `underline`, `color`, `font_size`, `font_name` | 格式化文本范围 |
| `create_custom_style` | `filename`, `style_name` | `font_name`, `font_size`, `bold`, `base_style` | 创建自定义样式 |
| `format_table` | `filename`, `table_index` | `has_header_row`, `border_style`, `shading` | 表格整体格式化 |

### 表格样式（修订模式）

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `set_cell_shading` | `filename`, `table_index`, `row_index`, `col_index`, `fill_color` | — | 单元格底色 |
| `apply_alternating_rows` | `filename`, `table_index` | `color1`, `color2` | 交替行颜色 |
| `highlight_header` | `filename`, `table_index` | `header_color`, `text_color` | 表头高亮 |
| `merge_cells` | `filename`, `table_index`, `start_row`, `start_col`, `end_row`, `end_col` | — | 合并单元格（矩形） |
| `merge_cells_horizontal` | `filename`, `table_index`, `row_index`, `start_col`, `end_col` | — | 水平合并 |
| `merge_cells_vertical` | `filename`, `table_index`, `col_index`, `start_row`, `end_row` | — | 垂直合并 |
| `set_cell_alignment` | `filename`, `table_index`, `row_index`, `col_index` | `horizontal`, `vertical` | 单元格对齐 |
| `set_table_alignment` | `filename`, `table_index` | `horizontal`, `vertical` | 全表对齐 |
| `set_column_width` | `filename`, `table_index`, `col_index`, `width` | `width_type` | 单列宽 |
| `set_column_widths` | `filename`, `table_index`, `widths` | `width_type` | 多列宽 |
| `set_table_width` | `filename`, `table_index`, `width` | `width_type` | 表格总宽 |
| `auto_fit_columns` | `filename`, `table_index` | — | 自动列宽 |
| `format_cell_text` | `filename`, `table_index`, `row_index`, `col_index` | `text_content`, `bold`, `italic`, `underline`, `color`, `font_size`, `font_name` | 单元格文字格式 |
| `set_cell_padding` | `filename`, `table_index`, `row_index`, `col_index` | `top`, `bottom`, `left`, `right`, `unit` | 单元格内边距 |

### 脚注（修订模式）

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `add_footnote` | `filename`, `paragraph_index`, `footnote_text` | — | 添加脚注 |
| `add_footnote_after_text` | `filename`, `search_text`, `footnote_text` | `output_filename` | 文本后加脚注 |
| `add_footnote_before_text` | `filename`, `search_text`, `footnote_text` | `output_filename` | 文本前加脚注 |
| `add_footnote_enhanced` | `filename`, `paragraph_index`, `footnote_text` | `output_filename` | 增强版脚注 |
| `add_endnote` | `filename`, `paragraph_index`, `footnote_text` | — | 尾注 |
| `customize_footnote_style` | `filename` | `numbering_format`, `start_number`, `font_name`, `font_size` | 脚注样式 |
| `delete_footnote` | `filename` | `footnote_id`, `search_text` | 删除脚注 |
| `validate_footnotes` | `filename` | — | 验证脚注完整性 |

### 保护

| action | 必填参数 | 说明 |
|--------|----------|------|
| `protect_document` | `filename`, `password` | 加密保护 |
| `unprotect_document` | `filename`, `password` | 解除保护 |

### 查找与转换

| action | 必填参数 | 可选参数 | 说明 |
|--------|----------|----------|------|
| `get_paragraph_text` | `filename`, `paragraph_index` | — | 读取单段文本 |
| `find_text` | `filename`, `search_text` | `match_case`, `whole_word` | 查找文本位置 |
| `convert_to_pdf` | `filename` | `output_filename` | 转为 PDF |

### 批注

| action | 必填参数 | 说明 |
|--------|----------|------|
| `get_all_comments` | `filename` | 读取所有批注 |
| `get_comments_by_author` | `filename`, `author` | 按作者筛选批注 |
| `get_comments_for_paragraph` | `filename`, `paragraph_index` | 按段落筛选批注 |

---

## 参数详解

| 参数 | 类型 | 说明 |
|------|------|------|
| `action` | string | 操作名称（见上表） |
| `filename` | string | 文档路径，相对 workspace |
| `paragraph_index` | int | 段落索引（从 0 开始） |
| `table_index` | int | 表格索引（从 0 开始） |
| `target_text` | string | 目标定位文本 |
| `position` | string | `before` 或 `after` |
| `level` | int | 标题级别 1-9 |
| `text` | string | 段落/标题文本内容 |
| `data` | array | 表格数据（二维数组） |
| `font_name` | string | 字体名 |
| `font_size` | int | 字号（磅） |
| `bold` | boolean | 加粗 |
| `italic` | boolean | 斜体 |
| `color` | string | 颜色（十六进制 RGB，如 `FF0000`） |
| `width_type` | string | `points`/`percentage`/`auto` |

---

## 典型工作流

### 创建审计报告
```
1. word_advanced(action="create_document", filename="workspace/audit_report.docx", title="审计报告", author="AI")
2. word_advanced(action="add_heading", filename="workspace/audit_report.docx", text="一、审计概述", level=1)
3. word_advanced(action="add_paragraph", filename="workspace/audit_report.docx", text="本报告...")
4. word_advanced(action="add_table", filename="workspace/audit_report.docx", rows=3, cols=3, data=[...])
5. word_advanced(action="highlight_header", filename="workspace/audit_report.docx", table_index=0)
```

### 编辑已有文档
```
1. word_advanced(action="get_document_outline", filename="workspace/report.docx")
2. word_advanced(action="find_text", filename="workspace/report.docx", search_text="旧内容")
3. word_advanced(action="search_and_replace", filename="workspace/report.docx", search_text="旧内容", replace_text="新内容")
```

---

## 何时使用 Python 代码替代

以下场景 `word_advanced` 无法覆盖，请使用 `run_code`（Python + python-docx）：

- **页眉页脚**：自定义页眉/页脚内容
- **分栏布局**
- **复杂页面设置**：纸张方向、边距、分节符
- **书签与超链接**
- **内容控件/表单域**
- **邮件合并**
- **嵌入对象**（OLE）
- **自定义编号列表**（多级编号）
- **页面水印**
- **样式继承/链式样式**

示例代码：
```python
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.section import WD_ORIENT

doc = Document("workspace/report.docx")

# 页面设置：横向 A4
section = doc.sections[0]
section.orientation = WD_ORIENT.LANDSCAPE
section.page_width = Cm(29.7)
section.page_height = Cm(21.0)

# 添加页眉
header = section.header
header_para = header.paragraphs[0]
header_para.text = "机密文件 - 内部使用"

# 添加书签
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
para = doc.add_paragraph("书签目标位置")
bm = OxmlElement('w:bookmarkStart')
bm.set(qn('w:id'), '1')
bm.set(qn('w:name'), 'my_bookmark')
para._element.insert(0, bm)

doc.save("workspace/report.docx")
```
