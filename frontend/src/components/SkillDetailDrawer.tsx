import React, { useCallback } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import SkillIcon from './SkillIcon';
import type { AgentSkillItem } from '../services/api';

// 相对时间格式化
function formatRelativeTime(dateStr: string | undefined | null): string {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return '刚刚';
        if (diffMin < 60) return `${diffMin}分钟前`;
        const diffHour = Math.floor(diffMin / 60);
        if (diffHour < 24) return `${diffHour}小时前`;
        const diffDay = Math.floor(diffHour / 24);
        if (diffDay < 30) return `${diffDay}天前`;
        const diffMonth = Math.floor(diffDay / 30);
        if (diffMonth < 12) return `${diffMonth}个月前`;
        return `${Math.floor(diffMonth / 12)}年前`;
    } catch {
        return '';
    }
}

interface SkillDetailDrawerProps {
    skill: AgentSkillItem | null;
    open: boolean;
    onClose: () => void;
    onEditFiles?: (folderName: string) => void;
    onDelete?: (folderName: string) => void;
}

export const SkillDetailDrawer: React.FC<SkillDetailDrawerProps> = ({
    skill,
    open,
    onClose,
    onEditFiles,
    onDelete,
}) => {
    const handleEditFiles = useCallback(() => {
        if (skill && onEditFiles) onEditFiles(skill.folder_name);
    }, [skill, onEditFiles]);

    const handleDelete = useCallback(() => {
        if (skill && onDelete) onDelete(skill.folder_name);
    }, [skill, onDelete]);

    if (!open || !skill) return null;

    return (
        <>
            {/* Backdrop */}
            <div
                style={{
                    position: 'fixed', inset: 0, zIndex: 9998,
                    background: 'rgba(0,0,0,0.3)',
                    transition: 'opacity 0.2s',
                }}
                onClick={onClose}
            />
            {/* Drawer */}
            <div
                style={{
                    position: 'fixed', top: 0, right: 0, bottom: 0,
                    width: '480px', maxWidth: '90vw', zIndex: 9999,
                    background: 'var(--bg-primary)',
                    borderLeft: '1px solid var(--border-default)',
                    boxShadow: '-8px 0 32px rgba(0,0,0,0.15)',
                    display: 'flex', flexDirection: 'column',
                    transform: open ? 'translateX(0)' : 'translateX(100%)',
                    transition: 'transform 0.25s ease',
                    overflow: 'hidden',
                }}
            >
                {/* Header */}
                <div style={{
                    padding: '20px 24px 16px',
                    borderBottom: '1px solid var(--border-subtle)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                        <SkillIcon icon={skill.icon} size={40} />
                        <div style={{ minWidth: 0 }}>
                            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {skill.name}
                            </h3>
                            <div style={{ display: 'flex', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                                {skill.category && (
                                    <span style={{
                                        fontSize: '11px', padding: '2px 8px', borderRadius: '4px',
                                        background: 'var(--accent-subtle)', color: 'var(--accent-text)',
                                    }}>
                                        {skill.category}
                                    </span>
                                )}
                                {skill.is_global && (
                                    <span style={{
                                        fontSize: '11px', padding: '2px 8px', borderRadius: '4px',
                                        background: 'var(--bg-secondary)', color: 'var(--text-secondary)',
                                    }}>
                                        全局
                                    </span>
                                )}
                                {skill.version && skill.version !== '1.0.0' && (
                                    <span style={{
                                        fontSize: '11px', padding: '2px 6px', borderRadius: '4px',
                                        background: 'var(--bg-secondary)', color: 'var(--text-tertiary)',
                                    }}>
                                        v{skill.version}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none', border: 'none', fontSize: '20px',
                            cursor: 'pointer', color: 'var(--text-secondary)', padding: '4px',
                            lineHeight: 1, flexShrink: 0,
                        }}
                    >
                        ✕
                    </button>
                </div>

                {/* Metadata panel */}
                {(skill.author || skill.updated_at) && (
                    <div style={{
                        padding: '12px 24px',
                        borderBottom: '1px solid var(--border-subtle)',
                        display: 'flex', gap: '16px', fontSize: '12px', color: 'var(--text-secondary)',
                    }}>
                        {skill.author && (
                            <div>
                                <span style={{ color: 'var(--text-tertiary)' }}>作者: </span>
                                {skill.author}
                            </div>
                        )}
                        {skill.updated_at && (
                            <div>
                                <span style={{ color: 'var(--text-tertiary)' }}>更新: </span>
                                {formatRelativeTime(skill.updated_at)}
                            </div>
                        )}
                    </div>
                )}

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>
                    {skill.skill_md_content ? (
                        <MarkdownRenderer content={skill.skill_md_content} />
                    ) : skill.description ? (
                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                            {skill.description}
                        </p>
                    ) : (
                        <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                            暂无 SKILL.md 内容
                        </p>
                    )}
                </div>

                {/* Footer actions */}
                <div style={{
                    padding: '12px 24px',
                    borderTop: '1px solid var(--border-subtle)',
                    display: 'flex', gap: '8px', justifyContent: 'flex-end',
                }}>
                    {onEditFiles && (
                        <button className="btn btn-secondary" style={{ fontSize: '13px' }} onClick={handleEditFiles}>
                            编辑文件
                        </button>
                    )}
                    {onDelete && (
                        <button
                            className="btn btn-secondary"
                            style={{ fontSize: '13px', color: 'var(--error, #ef4444)' }}
                            onClick={handleDelete}
                        >
                            移除
                        </button>
                    )}
                </div>
            </div>
        </>
    );
};
