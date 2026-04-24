/**
 * FileCanvasPanel — ChatGPT Canvas 风格文件预览面板
 *
 * 数据源：从 chatMessages 的 tool_call 中提取文件列表（刷新不丢失）
 * 预览策略：
 *   代码 → 语法高亮 + 行号
 *   Markdown → MarkdownRenderer / 可编辑 textarea + 保存
 *   PDF/DOCX/XLSX/PPTX → DocumentViewer (JIT)
 *   图片 → <img>
 *   其他 → 纯文本
 *
 * 面板宽度可拖拽调整。
 */

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
    IconFile, IconFileText, IconCode, IconPhoto, IconCheck,
    IconCopy, IconDownload, IconChevronRight, IconChevronLeft,
    IconEdit, IconDeviceFloppy, IconX,
} from '@tabler/icons-react';
import MarkdownRenderer from './MarkdownRenderer';
import DocumentViewer, { isSupportedDocumentFormat } from './DocumentViewer';

/* ── Types ── */
export interface CanvasFile {
    name: string;
    status: 'generating' | 'done' | 'error';
    content?: string;
    path?: string;
}

interface FileCanvasPanelProps {
    files: Map<string, CanvasFile>;
    visible: boolean;
    onToggle: () => void;
    agentId?: string;
}

/* ── Constants ── */
const MIN_WIDTH = 320;
const MAX_WIDTH_VW = 0.65;

function calcInitialWidth(): number {
    const el = document.querySelector('.agent-chat-area') as HTMLElement | null;
    if (el) return Math.max(MIN_WIDTH, Math.floor(el.clientWidth * 0.45));
    return Math.max(MIN_WIDTH, Math.floor((window.innerWidth - 60) * 0.45));
}

/* ── File type helpers ── */
type FileType = 'code' | 'markdown' | 'image' | 'document' | 'text';

function getFileType(name: string): FileType {
    const ext = name.toLowerCase().split('.').pop() || '';
    if (['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php',
        'swift', 'kt', 'sh', 'bat', 'css', 'scss', 'html', 'sql', 'toml', 'dockerfile'].includes(ext)) return 'code';
    if (['md', 'mdx', 'rst'].includes(ext)) return 'markdown';
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'ico'].includes(ext)) return 'image';
    if (isSupportedDocumentFormat(name)) return 'document';
    return 'text';
}

function getFileIcon(name: string, size = 16) {
    switch (getFileType(name)) {
        case 'code': return <IconCode size={size} />;
        case 'markdown': return <IconFileText size={size} />;
        case 'image': return <IconPhoto size={size} />;
        default: return <IconFile size={size} />;
    }
}

function getLanguageLabel(name: string): string {
    const ext = name.toLowerCase().split('.').pop() || '';
    const map: Record<string, string> = {
        py: 'Python', js: 'JavaScript', ts: 'TypeScript', jsx: 'JSX', tsx: 'TSX',
        java: 'Java', cpp: 'C++', c: 'C', go: 'Go', rs: 'Rust', rb: 'Ruby',
        php: 'PHP', sh: 'Shell', css: 'CSS', html: 'HTML', sql: 'SQL',
        json: 'JSON', yaml: 'YAML', yml: 'YAML', md: 'Markdown', txt: 'Text',
    };
    return map[ext] || ext.toUpperCase() || 'Text';
}

/* ── Lightweight syntax highlighting ── */
const KW = new Set([
    'import', 'from', 'export', 'default', 'class', 'def', 'function', 'const', 'let', 'var',
    'if', 'else', 'elif', 'for', 'while', 'return', 'try', 'catch', 'finally', 'throw',
    'new', 'this', 'super', 'extends', 'async', 'await', 'yield', 'with', 'as', 'in', 'of',
    'True', 'False', 'None', 'null', 'undefined', 'true', 'false',
    'public', 'private', 'protected', 'static', 'final', 'abstract', 'pass', 'raise', 'del',
]);

function hl(line: string): string {
    let s = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    s = s.replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"[^"]*"|'[^']*'|`[^`]*`)/g, '<span style="color:#a5d6a7">$1</span>');
    s = s.replace(/(\/\/.*?$|#.*?$)/gm, '<span style="color:#90a4ae;font-style:italic">$1</span>');
    s = s.replace(/\b(\d+\.?\d*)\b/g, '<span style="color:#ffcc80">$1</span>');
    s = s.replace(new RegExp(`\\b(${[...KW].slice(0, 30).join('|')})\\b`, 'g'), '<span style="color:#ce93d8">$1</span>');
    return s;
}

/* ── Sub-components ── */

function Skeleton() {
    return (
        <div style={{ padding: '16px' }}>
            {[40, 65, 80, 55, 70, 45, 60, 75, 50, 85].map((w, i) => (
                <div key={i} style={{
                    height: '14px', width: `${w}%`,
                    background: 'linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-hover) 50%, var(--bg-tertiary) 75%)',
                    backgroundSize: '200% 100%', borderRadius: '4px',
                    marginBottom: '8px', marginLeft: i === 0 ? '0' : '40px',
                    animation: 'fcpShimmer 1.5s ease-in-out infinite', animationDelay: `${i * 80}ms`,
                }} />
            ))}
        </div>
    );
}

function CodePreview({ content, fileName }: { content: string; fileName: string }) {
    const lines = content.split('\n');
    const numW = String(lines.length).length;
    return (
        <div style={{ fontFamily: "'JetBrains Mono','Fira Code',monospace", fontSize: '12px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            <div style={{ padding: '6px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: '11px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                {getFileIcon(fileName, 13)} {getLanguageLabel(fileName)}
                <span style={{ marginLeft: 'auto' }}>{lines.length} lines</span>
            </div>
            <div style={{ overflowX: 'auto' }}>
                {lines.map((line, i) => (
                    <div key={i} style={{ display: 'flex', minHeight: '20px' }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                        <span style={{ width: `${numW * 8 + 20}px`, flexShrink: 0, textAlign: 'right', paddingRight: '12px', color: 'var(--text-tertiary)', opacity: 0.5, userSelect: 'none', fontSize: '11px' }}>{i + 1}</span>
                        <span style={{ flex: 1, whiteSpace: 'pre', paddingRight: '16px' }} dangerouslySetInnerHTML={{ __html: hl(line) || ' ' }} />
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ── Main Component ── */
export default function FileCanvasPanel({ files, visible, onToggle, agentId }: FileCanvasPanelProps) {
    const { t } = useTranslation();

    // ── Panel width + drag ──
    const [panelWidth, setPanelWidth] = useState(() => calcInitialWidth());
    const isDragging = useRef(false);
    const userResized = useRef(false);
    const dragStartX = useRef(0);
    const dragStartWidth = useRef(0);

    useEffect(() => {
        const onResize = () => { if (!isDragging.current && !userResized.current) setPanelWidth(calcInitialWidth()); };
        window.addEventListener('resize', onResize);
        return () => window.removeEventListener('resize', onResize);
    }, []);

    useEffect(() => {
        const onMove = (e: MouseEvent) => {
            if (!isDragging.current) return;
            const delta = dragStartX.current - e.clientX;
            const maxW = window.innerWidth * MAX_WIDTH_VW;
            setPanelWidth(Math.min(maxW, Math.max(MIN_WIDTH, dragStartWidth.current + delta)));
        };
        const onUp = () => {
            if (!isDragging.current) return;
            isDragging.current = false;
            userResized.current = true;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        return () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    }, []);

    const startDrag = useCallback((e: React.MouseEvent) => {
        isDragging.current = true;
        dragStartX.current = e.clientX;
        dragStartWidth.current = panelWidth;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }, [panelWidth]);

    // ── Tabs ──
    const fileList = useMemo(() => Array.from(files.entries()), [files]);
    const [activeTab, setActiveTab] = useState<string | null>(null);
    const hasActive = fileList.some(([_, f]) => f.status === 'generating');

    // Auto-select latest file
    useEffect(() => {
        if (fileList.length > 0 && (!activeTab || !files.has(activeTab))) {
            setActiveTab(fileList[fileList.length - 1][0]);
        }
    }, [fileList.length, files]);

    const activeFile = activeTab ? files.get(activeTab) : null;

    // ── Fetch full content from API ──
    const [fetchedContent, setFetchedContent] = useState<Record<string, string>>({});
    useEffect(() => {
        if (!activeFile || !activeFile.path || !agentId) return;
        if (activeFile.status !== 'done') return;
        if (fetchedContent[activeTab!]) return; // already fetched
        const token = localStorage.getItem('token');
        fetch(`/api/agents/${agentId}/files/content?path=${encodeURIComponent(activeFile.path)}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        }).then(r => r.ok ? r.json() : null).then(d => {
            if (d?.content) setFetchedContent(prev => ({ ...prev, [activeTab!]: d.content }));
        }).catch(() => {});
    }, [activeTab, activeFile?.status, activeFile?.path]);

    const displayContent = activeTab ? fetchedContent[activeTab] : undefined;

    // ── MD editing ──
    const [editing, setEditing] = useState(false);
    const [editContent, setEditContent] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => { setEditing(false); }, [activeTab]);

    const startEdit = useCallback(() => {
        setEditContent(displayContent || '');
        setEditing(true);
    }, [displayContent]);

    const saveEdit = useCallback(async () => {
        if (!activeFile?.path || !agentId) return;
        setSaving(true);
        try {
            const token = localStorage.getItem('token');
            await fetch(`/api/agents/${agentId}/files/content?path=${encodeURIComponent(activeFile.path!)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                body: JSON.stringify({ content: editContent }),
            });
            setFetchedContent(prev => ({ ...prev, [activeTab!]: editContent }));
            setEditing(false);
        } finally { setSaving(false); }
    }, [activeFile, agentId, editContent, activeTab]);

    // ── Copy / Download ──
    const [copied, setCopied] = useState(false);
    const handleCopy = useCallback(() => {
        if (!displayContent) return;
        navigator.clipboard.writeText(displayContent);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }, [displayContent]);

    const handleDownload = useCallback(() => {
        if (!activeFile?.path || !agentId) return;
        const token = localStorage.getItem('token');
        fetch(`/api/agents/${agentId}/files/download?path=${encodeURIComponent(activeFile.path!)}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        }).then(r => r.blob()).then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = activeFile.name; a.click();
            URL.revokeObjectURL(url);
        });
    }, [activeFile, agentId]);

    // ── Collapsed ──
    if (!visible || fileList.length === 0) {
        if (fileList.length === 0) return null;
        return (
            <button onClick={onToggle} style={{
                position: 'relative', width: '44px', flexShrink: 0,
                background: hasActive ? 'linear-gradient(180deg, var(--accent-primary), #8b5cf6)' : 'var(--bg-tertiary)',
                border: 'none', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '6px',
                cursor: 'pointer', transition: 'all 200ms ease',
                boxShadow: hasActive ? '-2px 0 12px rgba(99,102,241,0.2)' : 'none',
            }} title={t('fileCanvas.expand', '展开文件预览')}>
                <IconChevronLeft size={18} style={{ color: hasActive ? '#fff' : 'var(--text-tertiary)' }} />
                <span style={{ fontSize: '18px', fontWeight: 700, color: hasActive ? '#fff' : 'var(--accent-primary)' }}>{fileList.length}</span>
                {hasActive && <span style={{ fontSize: '9px', fontWeight: 600, color: 'rgba(255,255,255,0.8)', animation: 'fcpPulse 2s ease-in-out infinite' }}>{t('fileCanvas.generating', '生成中')}</span>}
            </button>
        );
    }

    // ── Expanded ──
    const isMd = activeFile && getFileType(activeFile.name) === 'markdown';

    return (
        <div style={{
            width: `${panelWidth}px`, minWidth: `${MIN_WIDTH}px`, maxWidth: `${window.innerWidth * MAX_WIDTH_VW}px`,
            flexShrink: 0, background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border-subtle)',
            display: 'flex', flexDirection: 'column', height: '100%',
            boxShadow: '-4px 0 24px rgba(15,23,42,0.06)', animation: 'fcpSlideIn 250ms ease',
            position: 'relative',
        }}>
            {/* Resize handle */}
            <div onMouseDown={startDrag} style={{
                position: 'absolute', left: 0, top: 0, bottom: 0, width: '5px', cursor: 'col-resize',
                zIndex: 10, transition: 'background 150ms ease',
            }} onMouseEnter={e => (e.currentTarget.style.background = 'var(--accent-primary)')}
               onMouseLeave={e => (e.currentTarget.style.background = 'transparent')} />

            {/* ── Tab Bar ── */}
            <div style={{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'stretch', height: '42px' }}>
                <div style={{ flex: 1, display: 'flex', overflowX: 'auto', scrollbarWidth: 'none' }}>
                    {fileList.map(([key, file]) => {
                        const active = key === activeTab;
                        return (
                            <button key={key} onClick={() => setActiveTab(key)} style={{
                                display: 'flex', alignItems: 'center', gap: '6px', padding: '0 14px',
                                border: 'none', borderBottom: active ? '2px solid var(--accent-primary)' : '2px solid transparent',
                                background: active ? 'var(--accent-subtle)' : 'transparent',
                                color: active ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                                fontSize: '12px', fontWeight: active ? 600 : 400, cursor: 'pointer',
                                whiteSpace: 'nowrap', transition: 'all 150ms ease', flexShrink: 0,
                            }} onMouseEnter={e => { if (!active) { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'var(--bg-hover)'; } }}
                              onMouseLeave={e => { if (!active) { e.currentTarget.style.color = 'var(--text-tertiary)'; e.currentTarget.style.background = 'transparent'; } }}>
                                {file.status === 'generating' ? (
                                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-primary)', animation: 'fcpPulse 1.5s ease-in-out infinite' }} />
                                ) : (
                                    <span style={{ display: 'flex', opacity: 0.7, alignItems: 'center' }}>{getFileIcon(file.name, 13)}</span>
                                )}
                                <span style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{file.name}</span>
                            </button>
                        );
                    })}
                </div>
                <button onClick={onToggle} style={{
                    width: 36, flexShrink: 0, border: 'none', borderLeft: '1px solid var(--border-subtle)',
                    background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'var(--text-tertiary)', transition: 'all 150ms ease',
                }} onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-hover)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-tertiary)'; }}>
                    <IconChevronRight size={16} />
                </button>
            </div>

            {/* ── Content ── */}
            <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-primary)' }}>
                {!activeFile ? (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                        <IconFile size={32} style={{ marginBottom: 8, opacity: 0.4 }} />
                        <div style={{ fontSize: 13 }}>{t('fileCanvas.noContent', '暂无内容')}</div>
                    </div>
                ) : activeFile.status === 'generating' ? <Skeleton /> :
                 activeFile.status === 'error' ? (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--error)' }}>
                        <IconX size={32} style={{ marginBottom: 8, opacity: 0.6 }} />
                        <div style={{ fontSize: 13 }}>{t('fileCanvas.generationFailed', '文件生成失败')}</div>
                    </div>
                 ) : displayContent ? (
                    editing && isMd ? (
                        <textarea value={editContent} onChange={e => setEditContent(e.target.value)} style={{
                            width: '100%', height: '100%', border: 'none', outline: 'none', resize: 'none',
                            padding: '16px', fontFamily: "'JetBrains Mono',monospace", fontSize: '13px', lineHeight: 1.7,
                            color: 'var(--text-primary)', background: 'var(--bg-primary)',
                        }} />
                    ) : getFileType(activeFile.name) === 'code' ? (
                        <CodePreview content={displayContent} fileName={activeFile.name} />
                    ) : getFileType(activeFile.name) === 'markdown' ? (
                        <MarkdownRenderer content={displayContent} style={{ padding: '20px' }} />
                    ) : getFileType(activeFile.name) === 'image' ? (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, gap: 12, minHeight: 200 }}>
                            {activeFile.path && agentId ? (
                                <img src={`/api/agents/${agentId}/files/download?path=${encodeURIComponent(activeFile.path)}${localStorage.getItem('token') ? `&token=${localStorage.getItem('token')}` : ''}`}
                                    alt={activeFile.name} style={{ maxWidth: '100%', maxHeight: 400, objectFit: 'contain', borderRadius: 8, border: '1px solid var(--border-subtle)' }} />
                            ) : <IconPhoto size={40} style={{ color: 'var(--text-tertiary)' }} />}
                            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{activeFile.name}</span>
                        </div>
                    ) : getFileType(activeFile.name) === 'document' && activeFile.path && agentId ? (
                        <DocumentViewer
                            file={`/api/agents/${agentId}/files/download?path=${encodeURIComponent(activeFile.path)}${localStorage.getItem('token') ? `&token=${localStorage.getItem('token')}` : ''}`}
                            filename={activeFile.name} height="100%" theme="light"
                        />
                    ) : (
                        <pre style={{ padding: 16, fontFamily: "'JetBrains Mono',monospace", fontSize: 12, lineHeight: 1.7, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
                            {displayContent}
                        </pre>
                    )
                 ) : (
                    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                        <IconFile size={32} style={{ marginBottom: 8, opacity: 0.4 }} />
                        <div style={{ fontSize: 13 }}>{t('fileCanvas.noContent', '暂无内容')}</div>
                    </div>
                 )}
            </div>

            {/* ── Footer ── */}
            <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                {activeFile && (
                    <span style={{ fontSize: 11, fontWeight: 500, padding: '3px 8px', borderRadius: 6,
                        background: activeFile.status === 'done' ? 'var(--success-subtle)' : 'var(--accent-subtle)',
                        color: activeFile.status === 'done' ? 'var(--success)' : 'var(--accent-primary)' }}>
                        {activeFile.status === 'done' ? `✓ ${getLanguageLabel(activeFile.name)}` : t('fileCanvas.generating', '生成中...')}
                    </span>
                )}
                <div style={{ flex: 1 }} />

                {/* Edit / Save for MD */}
                {isMd && !editing && activeFile?.path && (
                    <button onClick={startEdit} style={footerBtnStyle}>
                        <IconEdit size={13} /> {t('fileCanvas.edit', '编辑')}
                    </button>
                )}
                {editing && (
                    <>
                        <button onClick={() => setEditing(false)} style={footerBtnStyle}>
                            <IconX size={13} /> {t('common.cancel', '取消')}
                        </button>
                        <button onClick={saveEdit} disabled={saving} style={{ ...footerBtnStyle, background: 'var(--accent-primary)', color: '#fff', border: 'none' }}>
                            <IconDeviceFloppy size={13} /> {saving ? t('common.saving', '保存中...') : t('common.save', '保存')}
                        </button>
                    </>
                )}

                {!editing && (
                    <>
                        <button onClick={handleCopy} disabled={!displayContent} style={{ ...footerBtnStyle, opacity: displayContent ? 1 : 0.4 }}>
                            <IconCopy size={13} /> {copied ? t('fileCanvas.copied', '已复制') : t('fileCanvas.copy', '复制')}
                        </button>
                        <button onClick={handleDownload} disabled={!activeFile?.path} style={{ ...footerBtnStyle, opacity: activeFile?.path ? 1 : 0.4 }}>
                            <IconDownload size={13} /> {t('fileCanvas.download', '下载')}
                        </button>
                    </>
                )}
            </div>

            <style>{`
                @keyframes fcpSlideIn { from { opacity:0; transform:translateX(20px) } to { opacity:1; transform:translateX(0) } }
                @keyframes fcpPulse { 0%,100% { opacity:1 } 50% { opacity:0.4 } }
                @keyframes fcpShimmer { 0% { background-position:200% 0 } 100% { background-position:-200% 0 } }
            `}</style>
        </div>
    );
}

const footerBtnStyle: React.CSSProperties = {
    padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border-default)',
    background: 'transparent', color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, transition: 'all 150ms ease',
};
