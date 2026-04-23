/**
 * DocumentViewer - 基于 jit-viewer 的多格式文档预览组件
 * 支持 PDF、DOCX、XLSX、PPTX、TXT、Markdown 等多种格式
 */

import { useEffect, useRef } from 'react';
import { createViewer, type ViewerInstance } from 'jit-viewer';
import 'jit-viewer/style.css';

interface DocumentViewerProps {
    file: string | File | Blob;
    filename: string;
    width?: string | number;
    height?: string | number;
    theme?: 'light' | 'dark';
    onError?: (error: Error) => void;
}

export default function DocumentViewer({
    file,
    filename,
    width = '100%',
    height = '600px',
    theme = 'light',
    onError
}: DocumentViewerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const viewerRef = useRef<ViewerInstance | null>(null);

    useEffect(() => {
        if (!containerRef.current) {
            return;
        }

        // 创建预览实例
        const viewer = createViewer({
            target: containerRef.current,
            file: file,
            filename: filename,
            theme: theme,
            toolbar: true,
            width: width,
            height: height,
            onReady: () => console.log('Document viewer ready'),
            onLoad: () => console.log('Document loaded'),
            onError: (error) => {
                console.error('Document viewer error:', error);
                onError?.(error);
            }
        });

        viewerRef.current = viewer;

        // 挂载预览器
        viewer.mount().catch((error) => {
            console.error('Failed to mount viewer:', error);
            onError?.(error);
        });

        // 清理函数
        return () => {
            viewer.destroy();
            viewerRef.current = null;
        };
    }, [file, filename, theme, width, height, onError]);

    return (
        <div
            ref={containerRef}
            style={{
                width: typeof width === 'number' ? `${width}px` : width,
                height: typeof height === 'number' ? `${height}px` : height,
            }}
        />
    );
}

/**
 * 判断文件是否支持使用 jit-viewer 预览
 */
export function isSupportedDocumentFormat(filename: string): boolean {
    const supportedExtensions = [
        // PDF
        '.pdf',
        // Office 文档
        '.docx', '.doc',
        '.xlsx', '.xls',
        '.pptx', '.ppt',
        // 文本文件
        '.txt', '.md', '.markdown',
        // OFD (电子版式文件)
        '.ofd',
        // CSV
        '.csv',
    ];

    const lowerName = filename.toLowerCase();
    return supportedExtensions.some(ext => lowerName.endsWith(ext));
}

/**
 * 获取文件类型
 */
export function getDocumentType(filename: string): string {
    const lowerName = filename.toLowerCase();

    if (lowerName.endsWith('.pdf')) return 'pdf';
    if (lowerName.endsWith('.docx') || lowerName.endsWith('.doc')) return 'word';
    if (lowerName.endsWith('.xlsx') || lowerName.endsWith('.xls')) return 'excel';
    if (lowerName.endsWith('.pptx') || lowerName.endsWith('.ppt')) return 'powerpoint';
    if (lowerName.endsWith('.txt')) return 'text';
    if (lowerName.endsWith('.md') || lowerName.endsWith('.markdown')) return 'markdown';
    if (lowerName.endsWith('.ofd')) return 'ofd';
    if (lowerName.endsWith('.csv')) return 'csv';

    return 'unknown';
}
