import React, { useCallback } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import type { AgentSkillItem } from '../services/api';

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
                        <span style={{ fontSize: '32px', lineHeight: 1, flexShrink: 0 }}>{skill.icon}</span>
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
                                        Global
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
                        x
                    </button>
                </div>

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
                            No SKILL.md content available.
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
                            Edit Files
                        </button>
                    )}
                    {onDelete && (
                        <button
                            className="btn btn-secondary"
                            style={{ fontSize: '13px', color: 'var(--error, #ef4444)' }}
                            onClick={handleDelete}
                        >
                            Remove
                        </button>
                    )}
                </div>
            </div>
        </>
    );
};
