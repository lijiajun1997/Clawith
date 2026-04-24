/**
 * File Canvas Panel - ChatGPT Canvas 风格的文件预览面板
 * 支持代码高亮、Markdown渲染、图片预览
 * 支持文件生成实时追踪（write_file / edit_file / python 等）
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
    IconFile, IconFileText, IconCode, IconPhoto, IconCheck, IconX,
    IconCopy, IconDownload, IconChevronRight, IconChevronLeft,
} from '@tabler/icons-react';

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

/* ── Helpers ── */
type FileType = 'code' | 'markdown' | 'image' | 'text';

function getFileType(name: string): FileType {
    const ext = name.toLowerCase().split('.').pop() || '';
    if (['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php', 'swift', 'kt', 'sh', 'bat', 'css', 'scss', 'html', 'sql', 'json', 'yaml', 'yml', 'toml', 'xml', 'dockerfile'].includes(ext)) return 'code';
    if (['md', 'mdx', 'rst'].includes(ext)) return 'markdown';
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'ico'].includes(ext)) return 'image';
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
        json: 'JSON', yaml: 'YAML', md: 'Markdown', txt: 'Text',
    };
    return map[ext] || ext.toUpperCase() || 'Text';
}

/* ── Token colors for lightweight syntax highlighting ── */
const KEYWORDS = new Set([
    'import', 'from', 'export', 'default', 'class', 'def', 'function', 'const', 'let', 'var',
    'if', 'else', 'elif', 'for', 'while', 'return', 'try', 'catch', 'finally', 'throw',
    'new', 'this', 'super', 'extends', 'implements', 'interface', 'type', 'enum',
    'async', 'await', 'yield', 'with', 'as', 'in', 'of', 'not', 'and', 'or',
    'True', 'False', 'None', 'null', 'undefined', 'true', 'false',
    'public', 'private', 'protected', 'static', 'final', 'abstract',
]);

function highlightLine(line: string): string {
    // Simple token-based highlighting — good enough for preview
    return line
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        // strings
        .replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"[^"]*"|'[^']*'|`[^`]*`)/g, '<span style="color:#a5d6a7">$1</span>')
        // comments
        .replace(/(\/\/.*$|#.*$)/gm, '<span style="color:#90a4ae;font-style:italic">$1</span>')
        // numbers
        .replace(/\b(\d+\.?\d*)\b/g, '<span style="color:#ffcc80">$1</span>')
        // keywords
        .replace(new RegExp(`\\b(${[...KEYWORDS].join('|')})\\b`, 'g'), '<span style="color:#ce93d8">$1</span>');
}

/* ── Sub-components ── */

function GeneratingSkeleton() {
    return (
        <div style={{ padding: '16px' }}>
            {[40, 65, 80, 55, 70, 45, 60, 75, 50, 85, 35, 60].map((w, i) => (
                <div key={i} style={{
                    height: '14px',
                    width: `${w}%`,
                    background: 'linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-hover) 50%, var(--bg-tertiary) 75%)',
                    backgroundSize: '200% 100%',
                    borderRadius: '4px',
                    marginBottom: '8px',
                    marginLeft: i === 0 ? '0' : '40px',
                    animation: 'shimmer 1.5s ease-in-out infinite',
                    animationDelay: `${i * 80}ms`,
                }} />
            ))}
        </div>
    );
}

function CodePreview({ content, fileName }: { content: string; fileName: string }) {
    const lines = content.split('\n');
    const lineNumWidth = String(lines.length).length;
    return (
        <div style={{
            fontFamily: "'JetBrains Mono','Fira Code','Cascadia Code',monospace",
            fontSize: '12px',
            lineHeight: '1.7',
            color: 'var(--text-secondary)',
            background: 'var(--bg-primary)',
        }}>
            {/* Language badge */}
            <div style={{
                padding: '6px 16px',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: '11px',
                color: 'var(--text-tertiary)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
            }}>
                {getFileIcon(fileName, 13)}
                {getLanguageLabel(fileName)}
                <span style={{ marginLeft: 'auto' }}>{lines.length} lines</span>
            </div>
            <div style={{ overflowX: 'auto' }}>
                {lines.map((line, i) => (
                    <div key={i} style={{
                        display: 'flex',
                        minHeight: '20px',
                        transition: 'background 80ms ease',
                    }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                        <span style={{
                            width: `${lineNumWidth * 8 + 20}px`,
                            flexShrink: 0,
                            textAlign: 'right',
                            paddingRight: '12px',
                            color: 'var(--text-tertiary)',
                            opacity: 0.5,
                            userSelect: 'none',
                            fontSize: '11px',
                        }}>{i + 1}</span>
                        <span
                            style={{ flex: 1, whiteSpace: 'pre', paddingRight: '16px' }}
                            dangerouslySetInnerHTML={{ __html: highlightLine(line) || ' ' }}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}

function MarkdownPreview({ content }: { content: string }) {
    // Lightweight markdown rendering for preview
    const html = content
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/^### (.+)$/gm, '<h3 style="font-size:15px;font-weight:700;margin:16px 0 8px;color:var(--text-primary)">$1</h3>')
        .replace(/^## (.+)$/gm, '<h2 style="font-size:17px;font-weight:700;margin:20px 0 10px;color:var(--text-primary)">$1</h2>')
        .replace(/^# (.+)$/gm, '<h1 style="font-size:20px;font-weight:700;margin:20px 0 12px;color:var(--text-primary)">$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code style="background:var(--bg-tertiary);padding:2px 6px;border-radius:4px;font-size:12px;font-family:monospace">$1</code>')
        .replace(/^- (.+)$/gm, '<li style="margin-left:16px;margin-bottom:4px">$1</li>')
        .replace(/\n/g, '<br/>');
    return (
        <div style={{
            padding: '20px',
            fontSize: '13px',
            lineHeight: '1.7',
            color: 'var(--text-secondary)',
        }}
            dangerouslySetInnerHTML={{ __html: html }}
        />
    );
}

function ImagePreview({ fileName, agentId, filePath }: { fileName: string; agentId?: string; filePath?: string }) {
    const token = localStorage.getItem('token');
    const src = filePath && agentId
        ? `/api/agents/${agentId}/files/download?path=${encodeURIComponent(filePath)}${token ? `&token=${token}` : ''}`
        : undefined;
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            gap: '12px',
            minHeight: '200px',
        }}>
            {src ? (
                <img
                    src={src}
                    alt={fileName}
                    style={{
                        maxWidth: '100%',
                        maxHeight: '400px',
                        objectFit: 'contain',
                        borderRadius: '8px',
                        border: '1px solid var(--border-subtle)',
                    }}
                />
            ) : (
                <div style={{
                    width: '120px', height: '120px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '12px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'var(--text-tertiary)',
                }}>
                    <IconPhoto size={40} />
                </div>
            )}
            <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{fileName}</span>
        </div>
    );
}

/* ── Main Component ── */
export default function FileCanvasPanel({ files, visible, onToggle, agentId }: FileCanvasPanelProps) {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const panelRef = useRef<HTMLDivElement>(null);
    const tabScrollRef = useRef<HTMLDivElement>(null);

    const fileList = Array.from(files.entries());
    const hasActiveFiles = fileList.some(([_, f]) => f.status === 'generating');

    // Auto-select latest file
    useEffect(() => {
        if (fileList.length > 0 && (!activeTab || !files.has(activeTab))) {
            setActiveTab(fileList[fileList.length - 1][0]);
        }
    }, [fileList.length]);

    const activeFile = activeTab ? files.get(activeTab) : null;

    // Fetch full file content from API when status is 'done' but no content yet
    const [fetchedContent, setFetchedContent] = useState<Record<string, string>>({});
    useEffect(() => {
        if (!activeFile || !activeFile.path || !agentId) return;
        if (activeFile.status !== 'done') return;
        if (activeFile.content || fetchedContent[activeTab!]) return;

        const token = localStorage.getItem('token');
        fetch(`/api/agents/${agentId}/files/content?path=${encodeURIComponent(activeFile.path)}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (data?.content) {
                    setFetchedContent(prev => ({ ...prev, [activeTab!]: data.content }));
                }
            })
            .catch(() => {});
    }, [activeTab, activeFile?.status, activeFile?.path]);

    const displayContent = activeFile?.content || (activeTab ? fetchedContent[activeTab] : undefined);

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
        })
            .then(res => res.blob())
            .then(blob => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = activeFile.name;
                a.click();
                URL.revokeObjectURL(url);
            });
    }, [activeFile, agentId]);

    // ── Collapsed state ──
    if (!visible || fileList.length === 0) {
        if (fileList.length === 0) return null;
        return (
            <button
                onClick={onToggle}
                style={{
                    position: 'relative',
                    width: '44px',
                    flexShrink: 0,
                    background: hasActiveFiles
                        ? 'linear-gradient(180deg, var(--accent-primary), #8b5cf6)'
                        : 'var(--bg-tertiary)',
                    border: 'none',
                    borderRight: 'none',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                    transition: 'all 200ms ease',
                    boxShadow: hasActiveFiles ? '-2px 0 12px rgba(99,102,241,0.2)' : 'none',
                }}
                title={t('fileCanvas.expand', '展开文件预览')}
            >
                <IconChevronLeft size={18} style={{ color: hasActiveFiles ? '#fff' : 'var(--text-tertiary)' }} />
                <span style={{
                    fontSize: '18px', fontWeight: 700,
                    color: hasActiveFiles ? '#fff' : 'var(--accent-primary)',
                }}>{fileList.length}</span>
                {hasActiveFiles && (
                    <span style={{
                        fontSize: '9px', fontWeight: 600, color: 'rgba(255,255,255,0.8)',
                        animation: 'fcpPulse 2s ease-in-out infinite',
                    }}>
                        {t('fileCanvas.generating', '生成中')}
                    </span>
                )}
            </button>
        );
    }

    // ── Expanded state ──
    return (
        <div
            ref={panelRef}
            style={{
                width: '50%',
                minWidth: '380px',
                maxWidth: '60%',
                flexShrink: 0,
                background: 'var(--bg-secondary)',
                borderLeft: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                boxShadow: '-4px 0 24px rgba(15,23,42,0.06)',
                animation: 'fcpSlideIn 250ms ease',
            }}
        >
            {/* ── Tab Bar ── */}
            <div style={{
                background: 'var(--bg-tertiary)',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'stretch',
                height: '42px',
            }}>
                <div
                    ref={tabScrollRef}
                    style={{
                        flex: 1,
                        display: 'flex',
                        overflowX: 'auto',
                        scrollbarWidth: 'none',
                    }}
                >
                    {fileList.map(([key, file]) => {
                        const isActive = key === activeTab;
                        return (
                            <button
                                key={key}
                                onClick={() => setActiveTab(key)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    padding: '0 14px',
                                    border: 'none',
                                    borderBottom: isActive ? '2px solid var(--accent-primary)' : '2px solid transparent',
                                    background: isActive ? 'var(--accent-subtle)' : 'transparent',
                                    color: isActive ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                                    fontSize: '12px',
                                    fontWeight: isActive ? 600 : 400,
                                    cursor: 'pointer',
                                    whiteSpace: 'nowrap',
                                    transition: 'all 150ms ease',
                                    position: 'relative',
                                    flexShrink: 0,
                                }}
                                onMouseEnter={e => {
                                    if (!isActive) {
                                        e.currentTarget.style.color = 'var(--text-primary)';
                                        e.currentTarget.style.background = 'var(--bg-hover)';
                                    }
                                }}
                                onMouseLeave={e => {
                                    if (!isActive) {
                                        e.currentTarget.style.color = 'var(--text-tertiary)';
                                        e.currentTarget.style.background = 'transparent';
                                    }
                                }}
                            >
                                {file.status === 'generating' ? (
                                    <span style={{
                                        width: '6px', height: '6px', borderRadius: '50%',
                                        background: 'var(--accent-primary)',
                                        animation: 'fcpPulse 1.5s ease-in-out infinite',
                                    }} />
                                ) : (
                                    <span style={{ display: 'flex', opacity: 0.7, alignItems: 'center' }}>
                                        {getFileIcon(file.name, 13)}
                                    </span>
                                )}
                                <span style={{
                                    maxWidth: '120px',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                }}>
                                    {file.name}
                                </span>
                            </button>
                        );
                    })}
                </div>

                {/* Close button */}
                <button
                    onClick={onToggle}
                    style={{
                        width: '36px',
                        flexShrink: 0,
                        border: 'none',
                        borderLeft: '1px solid var(--border-subtle)',
                        background: 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-tertiary)',
                        transition: 'all 150ms ease',
                    }}
                    onMouseEnter={e => {
                        e.currentTarget.style.background = 'var(--bg-hover)';
                        e.currentTarget.style.color = 'var(--text-primary)';
                    }}
                    onMouseLeave={e => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-tertiary)';
                    }}
                >
                    <IconChevronRight size={16} />
                </button>
            </div>

            {/* ── Content Area ── */}
            <div style={{
                flex: 1,
                overflow: 'auto',
                background: 'var(--bg-primary)',
                position: 'relative',
            }}>
                {activeFile?.status === 'generating' ? (
                    <GeneratingSkeleton />
                ) : activeFile?.status === 'error' ? (
                    <div style={{
                        padding: '40px 20px',
                        textAlign: 'center',
                        color: 'var(--error)',
                    }}>
                        <IconX size={32} style={{ marginBottom: '8px', opacity: 0.6 }} />
                        <div style={{ fontSize: '13px' }}>{t('fileCanvas.generationFailed', '文件生成失败')}</div>
                    </div>
                ) : displayContent ? (
                    getFileType(activeFile!.name) === 'code' ? (
                        <CodePreview content={displayContent} fileName={activeFile!.name} />
                    ) : getFileType(activeFile!.name) === 'markdown' ? (
                        <MarkdownPreview content={displayContent} />
                    ) : getFileType(activeFile!.name) === 'image' ? (
                        <ImagePreview fileName={activeFile!.name} agentId={agentId} filePath={activeFile!.path} />
                    ) : (
                        <pre style={{
                            padding: '16px',
                            fontFamily: "'JetBrains Mono',monospace",
                            fontSize: '12px',
                            lineHeight: '1.7',
                            color: 'var(--text-secondary)',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            margin: 0,
                        }}>
                            {displayContent}
                        </pre>
                    )
                ) : (
                    <div style={{
                        padding: '40px 20px',
                        textAlign: 'center',
                        color: 'var(--text-tertiary)',
                    }}>
                        <IconFile size={32} style={{ marginBottom: '8px', opacity: 0.4 }} />
                        <div style={{ fontSize: '13px' }}>{t('fileCanvas.noContent', '暂无内容')}</div>
                    </div>
                )}
            </div>

            {/* ── Footer ── */}
            <div style={{
                padding: '8px 12px',
                borderTop: '1px solid var(--border-subtle)',
                background: 'var(--bg-tertiary)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flexShrink: 0,
            }}>
                {/* Status */}
                {activeFile && (
                    <div style={{
                        fontSize: '11px',
                        fontWeight: 500,
                        padding: '3px 8px',
                        borderRadius: '6px',
                        background: activeFile.status === 'done' ? 'var(--success-subtle)' : activeFile.status === 'generating' ? 'var(--accent-subtle)' : 'var(--error-subtle)',
                        color: activeFile.status === 'done' ? 'var(--success)' : activeFile.status === 'generating' ? 'var(--accent-primary)' : 'var(--error)',
                    }}>
                        {activeFile.status === 'done' && `✓ ${getLanguageLabel(activeFile.name)}`}
                        {activeFile.status === 'generating' && t('fileCanvas.generating', '生成中...')}
                        {activeFile.status === 'error' && t('fileCanvas.error', '失败')}
                    </div>
                )}

                <div style={{ flex: 1 }} />

                {/* Actions */}
                <button onClick={handleCopy} disabled={!displayContent} style={{
                    padding: '5px 10px', borderRadius: '6px',
                    border: '1px solid var(--border-default)',
                    background: copied ? 'var(--success-subtle)' : 'transparent',
                    color: copied ? 'var(--success)' : 'var(--text-secondary)',
                    fontSize: '11px', fontWeight: 500, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: '4px',
                    transition: 'all 150ms ease',
                    opacity: displayContent ? 1 : 0.4,
                }}>
                    <IconCopy size={13} />
                    {copied ? t('fileCanvas.copied', '已复制') : t('fileCanvas.copy', '复制')}
                </button>

                <button onClick={handleDownload} disabled={!activeFile?.path} style={{
                    padding: '5px 10px', borderRadius: '6px',
                    border: '1px solid var(--border-default)',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    fontSize: '11px', fontWeight: 500, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: '4px',
                    transition: 'all 150ms ease',
                    opacity: activeFile?.path ? 1 : 0.4,
                }}>
                    <IconDownload size={13} />
                    {t('fileCanvas.download', '下载')}
                </button>
            </div>

            {/* Animations */}
            <style>{`
                @keyframes fcpSlideIn {
                    from { opacity: 0; transform: translateX(20px); }
                    to   { opacity: 1; transform: translateX(0); }
                }
                @keyframes fcpPulse {
                    0%, 100% { opacity: 1; }
                    50%      { opacity: 0.4; }
                }
                @keyframes shimmer {
                    0%   { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
            `}</style>
        </div>
    );
}
