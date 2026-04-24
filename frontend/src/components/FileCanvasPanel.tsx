/**
 * File Canvas Panel - OpenAI Canvas 风格的文件生成面板
 * 实时显示 AI 正在生成/编辑的文件，支持预览和操作
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { IconFile, IconFileText, IconCode, IconCheck, IconX, IconEye, IconDownload, IconChevronRight, IconCopy } from '@tabler/icons-react';

interface GeneratingFile {
    name: string;
    status: 'generating' | 'done' | 'error';
    progress?: number;
    content?: string;
    path?: string;
}

interface FileCanvasPanelProps {
    files: Map<string, GeneratingFile>;
    visible: boolean;
    onToggle: () => void;
    onPreviewFile?: (file: GeneratingFile) => void;
    agentId?: string;
}

export default function FileCanvasPanel({ files, visible, onToggle, onPreviewFile, agentId }: FileCanvasPanelProps) {
    const { t } = useTranslation();
    const [expandedFile, setExpandedFile] = useState<string | null>(null);

    const fileList = Array.from(files.entries());
    const hasActiveFiles = fileList.some(([_, f]) => f.status === 'generating');
    const completedCount = fileList.filter(([_, f]) => f.status === 'done').length;

    const getFileIcon = (fileName: string) => {
        const ext = fileName.toLowerCase().split('.').pop();
        if (['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'go', 'rs'].includes(ext || '')) {
            return <IconCode size={16} />;
        }
        if (['md', 'txt', 'json', 'yaml', 'yml'].includes(ext || '')) {
            return <IconFileText size={16} />;
        }
        return <IconFile size={16} />;
    };

    const getFileLanguage = (fileName: string): string => {
        const ext = fileName.toLowerCase().split('.').pop();
        const map: Record<string, string> = {
            py: 'python', js: 'javascript', ts: 'typescript',
            jsx: 'jsx', tsx: 'tsx', json: 'json', md: 'markdown',
            html: 'html', css: 'css', java: 'java', cpp: 'cpp',
            c: 'c', go: 'go', rs: 'rust', yaml: 'yaml', yml: 'yaml',
            txt: 'plaintext',
        };
        return map[ext || ''] || 'plaintext';
    };

    // 收起状态 — 只显示标签按钮
    if (!visible || fileList.length === 0) {
        if (fileList.length === 0) return null;
        return (
            <button
                onClick={onToggle}
                style={{
                    position: 'fixed',
                    right: 0,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    zIndex: 50,
                    width: '40px',
                    height: '80px',
                    background: hasActiveFiles
                        ? 'linear-gradient(135deg, var(--accent-primary), #8b5cf6)'
                        : 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    borderRight: 'none',
                    borderRadius: '12px 0 0 12px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    cursor: 'pointer',
                    transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
                    boxShadow: hasActiveFiles
                        ? '0 4px 16px rgba(99, 102, 241, 0.3)'
                        : '0 2px 8px rgba(0,0,0,0.1)',
                }}
                title={t('fileCanvas.toggle', '展开文件面板')}
            >
                <IconChevronRight size={18} style={{ color: hasActiveFiles ? 'white' : 'var(--text-secondary)' }} />
                {hasActiveFiles && (
                    <span style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        color: 'white',
                        animation: 'pulse 2s ease-in-out infinite',
                    }}>
                        {t('fileCanvas.generating', '生成中')}
                    </span>
                )}
                {completedCount > 0 && (
                    <span style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        color: hasActiveFiles ? 'rgba(255,255,255,0.8)' : 'var(--text-tertiary)',
                    }}>
                        {completedCount} {t('fileCanvas.files', '个文件')}
                    </span>
                )}
            </button>
        );
    }

    return (
        <div
            style={{
                width: '380px',
                flexShrink: 0,
                background: 'var(--bg-secondary)',
                borderLeft: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                boxShadow: '-4px 0 24px rgba(15, 23, 42, 0.08)',
            }}
        >
            {/* Header */}
            <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid var(--border-subtle)',
                background: 'var(--bg-tertiary)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
            }}>
                <div style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '8px',
                    background: hasActiveFiles
                        ? 'linear-gradient(135deg, var(--accent-primary), #8b5cf6)'
                        : 'var(--accent-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: hasActiveFiles ? 'white' : 'var(--accent-primary)',
                    fontSize: '14px',
                    fontWeight: 600,
                }}>
                    {fileList.length}
                </div>
                <div style={{ flex: 1 }}>
                    <div style={{
                        fontSize: '13px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                    }}>
                        {t('fileCanvas.title', '文件工作台')}
                    </div>
                    {hasActiveFiles && (
                        <div style={{
                            fontSize: '11px',
                            color: 'var(--accent-primary)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                        }}>
                            <span style={{
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                background: 'var(--accent-primary)',
                                animation: 'pulse 2s ease-in-out infinite',
                            }} />
                            {t('fileCanvas.generatingFiles', '正在生成文件...')}
                        </div>
                    )}
                </div>
                <button
                    onClick={onToggle}
                    style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '6px',
                        border: 'none',
                        background: 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-tertiary)',
                        transition: 'all 150ms ease',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-hover)';
                        e.currentTarget.style.color = 'var(--text-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-tertiary)';
                    }}
                    title={t('fileCanvas.collapse', '收起面板')}
                >
                    <IconChevronRight size={16} />
                </button>
            </div>

            {/* File List */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
            }}>
                {fileList.map(([key, file]) => (
                    <div
                        key={key}
                        style={{
                            background: 'var(--bg-primary)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '12px',
                            overflow: 'hidden',
                            transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
                            boxShadow: file.status === 'generating'
                                ? '0 0 0 2px var(--accent-subtle), 0 4px 12px rgba(99, 102, 241, 0.15)'
                                : 'var(--shadow-sm)',
                        }}
                    >
                        {/* File Header */}
                        <div
                            style={{
                                padding: '12px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px',
                                cursor: 'pointer',
                                borderBottom: expandedFile === key ? '1px solid var(--border-subtle)' : 'none',
                            }}
                            onClick={() => setExpandedFile(expandedFile === key ? null : key)}
                        >
                            <div style={{
                                width: '36px',
                                height: '36px',
                                borderRadius: '8px',
                                background: file.status === 'generating'
                                    ? 'var(--accent-subtle)'
                                    : file.status === 'done'
                                        ? 'var(--success-subtle)'
                                        : 'var(--error-subtle)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: file.status === 'generating'
                                    ? 'var(--accent-primary)'
                                    : file.status === 'done'
                                        ? 'var(--success)'
                                        : 'var(--error)',
                            }}>
                                {file.status === 'generating' ? (
                                    <span style={{ animation: 'spin 1s linear infinite', display: 'flex' }}>
                                        {getFileIcon(file.name)}
                                    </span>
                                ) : file.status === 'done' ? (
                                    <IconCheck size={16} />
                                ) : (
                                    <IconX size={16} />
                                )}
                            </div>

                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{
                                    fontSize: '13px',
                                    fontWeight: 600,
                                    color: 'var(--text-primary)',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                }}>
                                    {file.name}
                                </div>
                                <div style={{
                                    fontSize: '11px',
                                    color: 'var(--text-tertiary)',
                                    marginTop: '2px',
                                }}>
                                    {file.status === 'generating' && t('fileCanvas.statusGenerating', '生成中...')}
                                    {file.status === 'done' && t('fileCanvas.statusDone', '已完成')}
                                    {file.status === 'error' && t('fileCanvas.statusError', '生成失败')}
                                </div>
                            </div>

                            {/* Status Badge */}
                            <div style={{
                                padding: '4px 8px',
                                borderRadius: '8px',
                                fontSize: '10px',
                                fontWeight: 600,
                                background: file.status === 'generating'
                                    ? 'var(--accent-subtle)'
                                    : file.status === 'done'
                                        ? 'var(--success-subtle)'
                                        : 'var(--error-subtle)',
                                color: file.status === 'generating'
                                    ? 'var(--accent-primary)'
                                    : file.status === 'done'
                                        ? 'var(--success)'
                                        : 'var(--error)',
                            }}>
                                {file.status === 'generating' && '...'}
                                {file.status === 'done' && '✓'}
                                {file.status === 'error' && '!'}
                            </div>
                        </div>

                        {/* Expanded Content Preview */}
                        {expandedFile === key && file.content && (
                            <div style={{ padding: '12px' }}>
                                <div style={{
                                    background: 'var(--bg-tertiary)',
                                    border: '1px solid var(--border-subtle)',
                                    borderRadius: '8px',
                                    padding: '12px',
                                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                                    fontSize: '11px',
                                    lineHeight: '1.6',
                                    maxHeight: '200px',
                                    overflowY: 'auto',
                                    color: 'var(--text-secondary)',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-all',
                                }}>
                                    {file.content.length > 1500
                                        ? file.content.substring(0, 1500) + '\n...'
                                        : file.content
                                    }
                                </div>

                                {/* Action Buttons */}
                                <div style={{
                                    display: 'flex',
                                    gap: '8px',
                                    marginTop: '12px',
                                }}>
                                    {onPreviewFile && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onPreviewFile(file);
                                            }}
                                            style={{
                                                flex: 1,
                                                padding: '8px 12px',
                                                borderRadius: '8px',
                                                border: '1px solid var(--border-default)',
                                                background: 'var(--bg-primary)',
                                                color: 'var(--text-primary)',
                                                fontSize: '12px',
                                                fontWeight: 500,
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                gap: '6px',
                                                transition: 'all 150ms ease',
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.background = 'var(--bg-hover)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.background = 'var(--bg-primary)';
                                            }}
                                        >
                                            <IconEye size={14} />
                                            {t('fileCanvas.preview', '预览')}
                                        </button>
                                    )}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            navigator.clipboard.writeText(file.content || '');
                                        }}
                                        style={{
                                            flex: 1,
                                            padding: '8px 12px',
                                            borderRadius: '8px',
                                            border: '1px solid var(--border-default)',
                                            background: 'var(--bg-primary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '12px',
                                            fontWeight: 500,
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            gap: '6px',
                                            transition: 'all 150ms ease',
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.background = 'var(--bg-hover)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.background = 'var(--bg-primary)';
                                        }}
                                    >
                                        <IconCopy size={14} />
                                        {t('fileCanvas.copy', '复制')}
                                    </button>
                                    {file.path && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                // 触发文件下载
                                                const token = localStorage.getItem('token');
                                                fetch(`/api/agents/${agentId}/files/download?path=${encodeURIComponent(file.path!)}`, {
                                                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                                                })
                                                    .then(res => res.blob())
                                                    .then(blob => {
                                                        const url = URL.createObjectURL(blob);
                                                        const a = document.createElement('a');
                                                        a.href = url;
                                                        a.download = file.name;
                                                        a.click();
                                                        URL.revokeObjectURL(url);
                                                    });
                                            }}
                                            style={{
                                                flex: 1,
                                                padding: '8px 12px',
                                                borderRadius: '8px',
                                                border: 'none',
                                                background: 'var(--accent-primary)',
                                                color: 'white',
                                                fontSize: '12px',
                                                fontWeight: 500,
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                gap: '6px',
                                                transition: 'all 150ms ease',
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.background = 'var(--accent-hover)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.background = 'var(--accent-primary)';
                                            }}
                                        >
                                            <IconDownload size={14} />
                                            {t('fileCanvas.download', '下载')}
                                        </button>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* CSS Animations */}
            <style>{`
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}
