---
name: Web Research & AI Model
description: web_search + call_model 工具指南 — 参数、并发模式、文件引用、Grok搜索、Flash批量、YAML输出
---

# Web Research & AI Model 调用指南

## 核心原则

1. **文件引用优先**：待分析内容用 `{{file:path}}` 引用，不要粘贴长文本到 prompt
2. **共性指令提取**：重复使用的 prompt 规则先 `write_file` 保存，再用 `{{file:}}` 引用
3. **call.prompt 完全替换顶层 prompt（不拼接）**：并发中每个 call 如需共用规则，必须显式 `{{file:}}` 引用
4. **并发结果只有 500 字符预览**：务必 `read_file(md_file_path)` 读完整结果

---

## 一、web_search

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索关键词 |
| `max_results` | int | 否 | 结果数量，默认 5 |
| `search_engine` | string | 否 | duckduckgo / tavily / google / bing / zhipu / exa |

专用引擎工具（替代方案）：`duckduckgo_search`、`tavily_search`、`exa_search`、`google_search`、`jina_search`

```
web_search(query="2025年中国GDP增速", max_results=5)
```

---

## 二、call_model 参数

### 单次模式

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model_name` | string | 是 | 模型名（从工具配置的 models 列表选） |
| `prompt` | string | 是 | 指令，建议 `{{file:path}}` 引用 |
| `images` | array | 否 | 图片（本地路径/URL/base64） |
| `session_id` | string | 否 | 传入则续接历史上下文 |

返回：`content`（完整结果）、`session_id`、`md_file_path`

### 并发模式（传入 `calls` 数组即触发）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model_name` | string | 是 | 默认模型，可被 call 覆盖 |
| `prompt` | string | 否 | 共享 prompt，call 无 prompt 时继承 |
| `calls` | array | 是 | 并发数组，最多 20 项 |

**call 项**：`label`（标识）、`prompt`（替换顶层）、`model_name`（覆盖）、`images`（覆盖）、`temperature`（默认 0.7）

**合并规则**：`call.prompt || 顶层prompt`，`call.model_name || 顶层model_name`，`call.images || 顶层images`

---

## 三、并发场景与模式

### 模式 A：同 prompt 不同模型（顶层 prompt 直接生效）

```
call_model(
  model_name="grok-4.1",
  prompt="分析这篇研报：{{file:workspace/report.md}}",
  calls=[
    {"label": "grok", "model_name": "grok-4.1"},
    {"label": "gemini", "model_name": "gemini-3-pro"},
  ]
)
```

### 模式 B：同指令不同目标（共性指令提取为文件）

```
write_file(path="workspace/prompts/biz_analysis.md", content="分析业务模式：主营业务、盈利模式、核心竞争力。300字中文。")

call_model(
  model_name="gemini-3-pro",
  calls=[
    {"label": "公司A", "prompt": "{{file:workspace/prompts/biz_analysis.md}}\n\n{{file:workspace/company_a.md}}"},
    {"label": "公司B", "prompt": "{{file:workspace/prompts/biz_analysis.md}}\n\n{{file:workspace/company_b.md}}"},
  ]
)
```

### 模式 C：同目标不同维度（共性规则 + 目标文件 + 差异维度）

```
write_file(path="workspace/prompts/analysis_rules.md", content="专业分析师视角，客观、数据驱动，引用具体数字。")

call_model(
  model_name="grok-4.1",
  calls=[
    {"label": "财务", "prompt": "{{file:workspace/prompts/analysis_rules.md}}\n维度：财务指标\n{{file:workspace/target.md}}"},
    {"label": "竞争", "prompt": "{{file:workspace/prompts/analysis_rules.md}}\n维度：竞争格局\n{{file:workspace/target.md}}"},
    {"label": "风险", "prompt": "{{file:workspace/prompts/analysis_rules.md}}\n维度：风险评估\n{{file:workspace/target.md}}"},
  ]
)
```

---

## 四、Grok 联网搜索

Grok（如 grok-4.1）内置联网能力，适合复杂查询。

**强制规则：每次 Grok 搜索必须要求返回来源 URL。**

```
write_file(path="workspace/prompts/grok_search_rules.md", content="""搜索规则：
1. 每条信息标注来源 URL，格式：[来源](URL)
2. 未确认来源标注「⚠️未验证」
3. 优先官方公告、权威媒体
4. 不编造 URL，只返回实际访问过的页面""")

call_model(
  model_name="grok-4.1",
  prompt="{{file:workspace/prompts/grok_search_rules.md}}\n\n搜索「XX公司 2025年营收」"
)
```

### Grok 并发多维度调研

搜索规则文件写入一次，多个搜索维度引用同一规则：

```
call_model(
  model_name="grok-4.1",
  calls=[
    {"label": "概况", "prompt": "{{file:workspace/prompts/grok_search_rules.md}}\n\n搜索「XX公司」基本信息"},
    {"label": "财务", "prompt": "{{file:workspace/prompts/grok_search_rules.md}}\n\n搜索「XX公司」财务数据"},
    {"label": "风险", "prompt": "{{file:workspace/prompts/grok_search_rules.md}}\n\n搜索「XX公司 风险 处罚」"},
  ]
)
```

### 深度搜索流程

```
1. Grok 并发搜索 → 各维度摘要 + URL 列表
2. 选 2-3 个关键 URL → web_search/fetch 抓取原文 → write_file 保存
3. call_model 引用原始文件深度分析
```

---

## 五、Flash 模型批量处理

批量、低成本任务用 flash 模型（如 gemini-3-flash）：分类、抽取、翻译、摘要、格式转换。

```
write_file(path="workspace/prompts/summarize.md", content="200字中文摘要，保留关键数据。")

call_model(
  model_name="gemini-3-flash",
  calls=[
    {"label": "文件1", "prompt": "{{file:workspace/prompts/summarize.md}}\n\n{{file:workspace/doc_01.md}}"},
    {"label": "文件2", "prompt": "{{file:workspace/prompts/summarize.md}}\n\n{{file:workspace/doc_02.md}}"},
    {"label": "文件3", "prompt": "{{file:workspace/prompts/summarize.md}}\n\n{{file:workspace/doc_03.md}}"},
  ]
)
```

---

## 六、结构化输出：YAML > JSON

要求模型返回结构化数据时，指定 YAML 格式（对 LLM 更友好，引号逗号要求宽松，多行文本原生支持）。

输出格式模板同样提取为文件复用：

```
write_file(path="workspace/prompts/yaml_format.md", content="""提取关键信息，严格按 YAML 输出，不要其他文字：
```yaml
公司名称: ""
成立年份: null
主营业务:
  - ""
关键财务指标:
  营收: null
  净利润: null
```""")

call_model(
  model_name="gemini-3-pro",
  prompt="{{file:workspace/prompts/yaml_format.md}}\n\n{{file:workspace/target.md}}"
)
```

---

## 注意事项

- `model_name` 必须是工具配置中已有模型
- 文件引用：`{{file:path}}`，路径相对 workspace，推荐 MD 文本格式
- 图片支持本地路径、HTTP URL、base64
- 并发最多 20 项，受 `max_concurrency` 限制（默认 5）
- 单次返回完整 `content` + `md_file_path`；并发只返回 500 字符预览 + `md_file_path`
