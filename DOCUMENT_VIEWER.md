# 文档预览功能集成说明

## 功能概述

集成了 [jit-viewer](https://github.com/jitOffice/jit-viewer-sdk) 文档预览SDK，实现了在Workspace中直接预览多种格式的文档文件。

## 支持的文件格式

### Office 文档
- **Word**: `.docx`, `.doc`
- **Excel**: `.xlsx`, `.xls`
- **PowerPoint**: `.pptx`, `.ppt`

### PDF 文档
- **PDF**: `.pdf`

### 文本文件
- **纯文本**: `.txt`
- **Markdown**: `.md`, `.markdown`

### 其他格式
- **OFD**: `.ofd` (电子版式文件)
- **CSV**: `.csv`

## 功能特性

### ✅ 核心功能
- 📄 **多格式预览** - 支持上述所有格式
- 🎨 **主题切换** - 支持浅色/深色主题
- 🔧 **内置工具栏** - 缩放、旋转、分页、打印、下载
- 📱 **响应式设计** - 自适应不同屏幕尺寸
- 🚀 **性能优化** - 按需加载，快速渲染

### 🎯 使用场景
1. **Workspace 文件预览**
   - 点击任意支持的文档文件
   - 自动使用文档预览器显示
   - 无需下载即可查看内容

2. **企业知识库**
   - 预览企业文档
   - 快速查阅资料
   - 支持在线标注（待实现）

## 技术实现

### 组件结构
```
frontend/src/components/
├── DocumentViewer.tsx      # 文档预览器组件（新增）
└── FileBrowser.tsx         # 文件浏览器（已修改）
```

### 关键代码

#### DocumentViewer 组件
```tsx
import { createViewer } from 'jit-viewer';
import 'jit-viewer/style.css';

// 创建预览实例
const viewer = createViewer({
  target: containerRef.current,
  file: fileUrl,
  filename: 'document.pdf',
  theme: 'light',
  toolbar: true,
  width: '100%',
  height: '600px'
});

await viewer.mount();
```

#### 文件类型检测
```tsx
import { isSupportedDocumentFormat } from './DocumentViewer';

// 判断文件是否支持预览
if (isSupportedDocumentFormat(filename)) {
  return <DocumentViewer file={fileUrl} filename={filename} />;
}
```

## API 配置

### 文件URL格式
文档预览器需要完整的文件URL：

```tsx
// 前端 API 服务
const fileUrl = `/api/agents/${agentId}/files/download?path=${filePath}&token=${token}`;

// 使用 DocumentViewer
<DocumentViewer
  file={fileUrl}
  filename="document.pdf"
  height="600px"
/>
```

### 认证处理
jit-viewer 通过 URL 参数传递认证令牌：
```tsx
const token = localStorage.getItem('token');
const url = `${apiUrl}?token=${token}`;
```

## 性能优化

### 懒加载
- 文档预览器仅在用户点击文件时加载
- 避免初始页面加载时的性能开销

### 资源清理
```tsx
useEffect(() => {
  // 创建预览器
  const viewer = createViewer({...});
  viewer.mount();

  return () => {
    // 组件卸载时销毁实例
    viewer.destroy();
  };
}, []);
```

## 扩展功能（待实现）

### 🚀 计划中的功能
1. **批量预览** - 支持多个文档并排查看
2. **全屏模式** - 沉浸式阅读体验
3. **目录导航** - 快速跳转到指定页面
4. **搜索功能** - 在文档中搜索关键词
5. **标注功能** - 添加批注和评论
6. **版本对比** - 对比不同版本的文档

### 🔧 配置选项
```tsx
interface DocumentViewerConfig {
  theme?: 'light' | 'dark';
  toolbar?: boolean | ToolbarConfig;
  locale?: 'zh-CN' | 'en';
  width?: string | number;
  height?: string | number;
}
```

## 问题排查

### 常见问题

#### 1. 预览失败
**问题**: 文档无法加载或显示错误
**解决**:
- 检查文件URL是否正确
- 确认token是否有效
- 查看浏览器控制台错误信息

#### 2. 样式冲突
**问题**: 预览器样式与项目样式冲突
**解决**:
- jit-viewer 使用 CSS 隔离
- 检查是否有全局样式覆盖

#### 3. 文件过大
**问题**: 大文件加载缓慢
**解决**:
- 添加加载进度提示
- 实现分块加载
- 服务端压缩优化

## 相关资源

- [jit-viewer 官方文档](https://github.com/jitOffice/jit-viewer-sdk)
- [API 参考文档](https://jit-office.github.io/jit-viewer-sdk/)
- [在线演示](https://jit-office.github.io/jit-viewer-sdk/demo/)

## 更新日志

### Version 1.0.0 (2026-04-23)
- ✨ 首次集成 jit-viewer
- ✅ 支持 PDF、Office、文本文件预览
- ✅ 集成到 Workspace 文件浏览器
- ✅ 支持主题切换
- ✅ 内置工具栏功能

## 许可证

 jit-viewer 使用其原始许可证。
