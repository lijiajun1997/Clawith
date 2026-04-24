/**
 * RecentFilesPanel - 最近文件面板
 * 参考ChatGPT Canvas和AgentBayLivePanel的交互方式
 * 在右侧显示最近生成的文件列表，支持展开/收起
 */

import { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { IconChevronLeft, IconChevronRight, IconFile, IconDownload, IconEye } from '@tabler/icons-react';
import { formatFileSize } from '../utils/formatFileSize';

interface FileInfo {
    name: string;
    path: string;
    is_dir: boolean;
    size: number;
    modified_at: string;
    url: string | null;
}

interface RecentFilesResponse {
    files: FileInfo[];
    total: number;
    limit: number;
    offset: number;
}

interface RecentFilesPanelProps {
    agentId: string | undefined;
    onPreviewFile?: (file: FileInfo) => void;
}

export default function RecentFilesPanel({ agentId, onPreviewFile }: RecentFilesPanelProps) {
    const { t } = useTranslation();
    const [visible, setVisible] = useState(true); // 默认展开
    const [page, setPage] = useState(0);
    const [panelWidth, setPanelWidth] = useState(320);
    const pageSize = 10;

    const { data: recentFilesData, isLoading } = useQuery({
        queryKey: ['recent-files', agentId, page, pageSize],
        queryFn: () => fetchRecentFiles(agentId!, page * pageSize, pageSize),
        enabled: !!agentId,
        refetchInterval: visible ? 5000 : false,
    });

    const files = recentFilesData?.files || [];
    const total = recentFilesData?.total || 0;
    const totalPages = Math.ceil(total / pageSize);

    // 自动展开：当有文件时自动展开
    useEffect(() => {
        if (total > 0 && !visible) {
            setVisible(true);
        }
    }, [total]);

    const handleFileClick = (file: FileInfo) => {
        if (onPreviewFile) {
            onPreviewFile(file);
        } else if (file.url) {
            window.open(file.url, '_blank');
        }
    };

    const formatTime = (timestamp: string) => {
        const date = new Date(parseFloat(timestamp) * 1000);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return t('recentFiles.justNow', '刚刚');
        if (diffMins < 60) return t('recentFiles.minsAgo', '{{mins}}分钟前', { mins: diffMins });
        if (diffHours < 24) return t('recentFiles.hoursAgo', '{{hours}}小时前', { hours: diffHours });
        if (diffDays < 7) return t('recentFiles.daysAgo', '{{days}}天前', { days: diffDays });

        return date.toLocaleDateString();
    };

    const getFileIcon = (fileName: string) => {
        const ext = fileName.toLowerCase().split('.').pop();
        const iconMap: Record<string, string> = {
            'pdf': '📕',
            'docx': '📘',
            'doc': '📘',
            'xlsx': '📗',
            'xls': '📗',
            'pptx': '📙',
            'ppt': '📙',
            'txt': '📄',
            'md': '📝',
            'png': '🖼️',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'gif': '🖼️',
            'svg': '🖼️',
            'zip': '📦',
            'mp4': '🎬',
            'mp3': '🎵',
        };
        return iconMap[ext || ''] || '📄';
    };

    // 收起状态：显示展开按钮
    if (!visible) {
        // 只有当有文件时才显示展开按钮
        if (total === 0) return null;
        return (
            <button
                className="live-panel-toggle"
                onClick={() => setVisible(true)}
                title="打开最近文件"
                style={{
                    position: 'absolute',
                    right: 0,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-default)',
                    borderRadius: '6px 0 0 6px',
                    padding: '8px',
                    cursor: 'pointer',
                    boxShadow: '-2px 0 8px rgba(0,0,0,0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    zIndex: 10,
                }}
            >
                <IconChevronLeft size={16} />
                <IconFile size={16} />
                {total > 0 && (
                    <span
                        style={{
                            background: 'var(--accent-primary)',
                            color: 'white',
                            fontSize: '10px',
                            fontWeight: 600,
                            padding: '2px 6px',
                            borderRadius: '10px',
                        }}
                    >
                        {total > 99 ? '99+' : total}
                    </span>
                )}
            </button>
        );
    }

    // 展开状态
    return (
        <div
            className="live-panel recent-files-panel"
            style={{
                width: `${panelWidth}px`,
                flexShrink: 0,
                position: 'relative',
            }}
        >
            {/* Header */}
            <div className="live-panel-header">
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    flex: 1,
                }}>
                    <IconFile size={16} />
                    <span style={{
                        fontSize: '13px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                    }}>
                        {t('recentFiles.title', '最近文件')}
                    </span>
                    {total > 0 && (
                        <span
                            style={{
                                background: 'var(--accent-primary)',
                                color: 'white',
                                fontSize: '10px',
                                fontWeight: 600,
                                padding: '2px 6px',
                                borderRadius: '10px',
                            }}
                        >
                            {total}
                        </span>
                    )}
                </div>
                <button
                    className="live-panel-collapse"
                    onClick={() => setVisible(false)}
                    title="收起"
                >
                    <IconChevronRight size={14} />
                </button>
            </div>

            {/* Content */}
            <div className="live-panel-content" style={{
                overflowY: 'auto',
                flex: 1,
            }}>
                {isLoading ? (
                    <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                        <div style={{ fontSize: '12px' }}>{t('common.loading', '加载中...')}</div>
                    </div>
                ) : files.length === 0 ? (
                    <div
                        style={{
                            padding: '30px 20px',
                            textAlign: 'center',
                            color: 'var(--text-tertiary)',
                        }}
                    >
                        <IconFile size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
                        <div style={{ fontSize: '12px', lineHeight: '1.5' }}>
                            {t('recentFiles.empty', 'Agent生成的文件\\n会显示在这里')}
                        </div>
                    </div>
                ) : (
                    <div style={{ padding: '8px' }}>
                        {files.map((file, index) => (
                            <div
                                key={file.path}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    padding: '8px',
                                    margin: '4px 0',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    transition: 'all 180ms cubic-bezier(0.4, 0, 0.2, 1)',
                                    border: '1px solid transparent',
                                }}
                                onClick={() => handleFileClick(file)}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'var(--bg-hover)';
                                    e.currentTarget.style.borderColor = 'var(--border-subtle)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'transparent';
                                    e.currentTarget.style.borderColor = 'transparent';
                                }}
                                title={`${file.name}\n${formatFileSize(file.size)}\n${formatTime(file.modified_at)}`}
                            >
                                {/* File Icon */}
                                <div
                                    style={{
                                        width: '32px',
                                        height: '32px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        flexShrink: 0,
                                        borderRadius: '6px',
                                        background: 'var(--bg-tertiary)',
                                        border: '1px solid var(--border-subtle)',
                                        fontSize: '18px',
                                    }}
                                >
                                    {getFileIcon(file.name)}
                                </div>

                                {/* File Info */}
                                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                    <div
                                        style={{
                                            fontSize: '13px',
                                            fontWeight: 500,
                                            color: 'var(--text-primary)',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                        }}
                                    >
                                        {file.name}
                                    </div>
                                    <div
                                        style={{
                                            fontSize: '11px',
                                            color: 'var(--text-tertiary)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '6px',
                                        }}
                                    >
                                        <span>{formatFileSize(file.size)}</span>
                                        <span>•</span>
                                        <span>{formatTime(file.modified_at)}</span>
                                    </div>
                                </div>

                                {/* Quick Actions */}
                                <div
                                    style={{
                                        display: 'flex',
                                        gap: '4px',
                                    }}
                                >
                                    {file.url && (
                                        <>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    if (file.url) {
                                                        window.open(file.url, '_blank');
                                                    }
                                                }}
                                                style={{
                                                    background: 'var(--bg-tertiary)',
                                                    border: '1px solid var(--border-subtle)',
                                                    borderRadius: '4px',
                                                    padding: '4px',
                                                    cursor: 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                }}
                                                title={t('recentFiles.download', '下载')}
                                            >
                                                <IconDownload size={14} />
                                            </button>
                                            {onPreviewFile && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onPreviewFile(file);
                                                    }}
                                                    style={{
                                                        background: 'var(--bg-tertiary)',
                                                        border: '1px solid var(--border-subtle)',
                                                        borderRadius: '4px',
                                                        padding: '4px',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                    }}
                                                    title={t('recentFiles.preview', '预览')}
                                                >
                                                    <IconEye size={14} />
                                                </button>
                                            )}
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div
                    style={{
                        padding: '12px',
                        borderTop: '1px solid var(--border-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '8px',
                    }}
                >
                    <button
                        onClick={() => setPage(Math.max(0, page - 1))}
                        disabled={page === 0}
                        style={{
                            background: page === 0 ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '6px 12px',
                            fontSize: '12px',
                            fontWeight: 500,
                            color: page === 0 ? 'var(--text-tertiary)' : 'white',
                            cursor: page === 0 ? 'not-allowed' : 'pointer',
                            transition: 'all 180ms',
                        }}
                    >
                        <IconChevronLeft size={14} style={{ marginRight: '4px' }} />
                        {t('recentFiles.previous', '上一页')}
                    </button>
                    <span
                        style={{
                            fontSize: '12px',
                            color: 'var(--text-secondary)',
                            fontWeight: 500,
                        }}
                    >
                        {page + 1} / {totalPages}
                    </span>
                    <button
                        onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                        disabled={page >= totalPages - 1}
                        style={{
                            background: page >= totalPages - 1 ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '6px 12px',
                            fontSize: '12px',
                            fontWeight: 500,
                            color: page >= totalPages - 1 ? 'var(--text-tertiary)' : 'white',
                            cursor: page >= totalPages - 1 ? 'not-allowed' : 'pointer',
                            transition: 'all 180ms',
                        }}
                    >
                        {t('recentFiles.next', '下一页')}
                        <IconChevronRight size={14} style={{ marginLeft: '4px' }} />
                    </button>
                </div>
            )}
        </div>
    );
}

// API fetch function
async function fetchRecentFiles(agentId: string, offset: number, limit: number): Promise<RecentFilesResponse> {
    const token = localStorage.getItem('token');
    const url = `/api/agents/${agentId}/files/recent?offset=${offset}&limit=${limit}&exclude_code=true`;

    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch recent files: ${response.statusText}`);
    }

    return response.json();
}
