import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fileApi, skillApi, type AgentSkillItem } from '../services/api';
import { SkillDetailDrawer } from './SkillDetailDrawer';
import SkillIcon from './SkillIcon';
import FileBrowser from './FileBrowser';
import type { FileBrowserApi } from './FileBrowser';

// 预定义分类
const SKILL_CATEGORIES = ['全部', '办公', '审计', '咨询', '其他'];

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

interface SkillCardGridProps {
    agentId: string;
    /** FileBrowser adapter for advanced mode */
    fileBrowserApi: FileBrowserApi;
    /** Called to open the skill marketplace */
    onOpenMarketplace: () => void;
    /** Called to open URL import */
    onOpenUrlImport?: () => void;
    /** Called to open ClawHub browse */
    onOpenClawhub?: () => void;
    /** Called to open ZIP import */
    onOpenZipImport?: () => void;
}

export const SkillCardGrid: React.FC<SkillCardGridProps> = ({
    agentId,
    fileBrowserApi,
    onOpenMarketplace,
    onOpenUrlImport,
    onOpenClawhub,
    onOpenZipImport,
}) => {
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('全部');
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [selectedSkill, setSelectedSkill] = useState<AgentSkillItem | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [deletingFolder, setDeletingFolder] = useState<string | null>(null);

    const { data: skills = [], isLoading } = useQuery({
        queryKey: ['agent-skills', agentId],
        queryFn: () => fileApi.agentSkills.list(agentId),
    });

    const filtered = useMemo(() => {
        let result = skills;
        if (categoryFilter !== '全部') {
            result = result.filter(s => s.category === categoryFilter);
        }
        if (search.trim()) {
            const q = search.toLowerCase();
            result = result.filter(s =>
                s.name.toLowerCase().includes(q) ||
                s.description.toLowerCase().includes(q) ||
                s.folder_name.toLowerCase().includes(q)
            );
        }
        return result;
    }, [skills, search, categoryFilter]);

    const openDetail = useCallback((skill: AgentSkillItem) => {
        setSelectedSkill(skill);
        setDrawerOpen(true);
    }, []);

    const closeDetail = useCallback(() => {
        setDrawerOpen(false);
    }, []);

    const handleDelete = useCallback(async (folderName: string) => {
        if (!confirm(`确定移除技能 "${folderName}"？将删除该技能文件夹下的所有文件。`)) return;
        setDeletingFolder(folderName);
        try {
            await fileBrowserApi.delete(`skills/${folderName}`);
            queryClient.invalidateQueries({ queryKey: ['agent-skills', agentId] });
            queryClient.invalidateQueries({ queryKey: ['files', agentId, 'skills'] });
            if (selectedSkill?.folder_name === folderName) {
                setDrawerOpen(false);
            }
        } catch (err: any) {
            alert(`移除失败: ${err?.message || err}`);
        } finally {
            setDeletingFolder(null);
        }
    }, [agentId, fileBrowserApi, queryClient, selectedSkill]);

    const handleEditFiles = useCallback((_folderName: string) => {
        setShowAdvanced(true);
    }, []);

    const invalidateSkills = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: ['agent-skills', agentId] });
        queryClient.invalidateQueries({ queryKey: ['files', agentId, 'skills'] });
    }, [agentId, queryClient]);

    return (
        <div>
            {/* Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '6px' }}>
                    {onOpenUrlImport && (
                        <button className="btn btn-ghost" style={{ fontSize: '12px', padding: '3px 8px' }} onClick={onOpenUrlImport}>
                            Import from URL
                        </button>
                    )}
                    {onOpenClawhub && (
                        <button className="btn btn-ghost" style={{ fontSize: '12px', padding: '3px 8px' }} onClick={onOpenClawhub}>
                            Browse ClawHub
                        </button>
                    )}
                    {onOpenZipImport && (
                        <button className="btn btn-ghost" style={{ fontSize: '12px', padding: '3px 8px' }} onClick={onOpenZipImport}>
                            Import ZIP
                        </button>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input
                        className="input"
                        placeholder="搜索技能..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{ fontSize: '12px', width: '180px' }}
                    />
                    <button
                        className="btn btn-primary"
                        style={{ fontSize: '13px', whiteSpace: 'nowrap' }}
                        onClick={onOpenMarketplace}
                    >
                        技能市场
                    </button>
                    <button
                        className="btn btn-ghost"
                        style={{ fontSize: '12px', padding: '4px 10px' }}
                        onClick={() => setShowAdvanced(v => !v)}
                    >
                        {showAdvanced ? 'Card View' : 'Advanced'}
                    </button>
                </div>
            </div>

            {/* Category filter */}
            <div style={{ display: 'flex', gap: '4px', marginBottom: '12px', flexWrap: 'wrap' }}>
                {SKILL_CATEGORIES.map(cat => (
                    <button
                        key={cat}
                        onClick={() => setCategoryFilter(cat)}
                        style={{
                            padding: '3px 10px', borderRadius: '14px', fontSize: '11px', border: 'none', cursor: 'pointer',
                            background: categoryFilter === cat ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                            color: categoryFilter === cat ? '#fff' : 'var(--text-secondary)',
                            transition: 'all 0.15s',
                        }}
                    >
                        {cat}
                    </button>
                ))}
            </div>

            {/* Advanced mode: FileBrowser */}
            {showAdvanced && (
                <div style={{ marginBottom: '16px' }}>
                    <FileBrowser
                        api={fileBrowserApi}
                        rootPath="skills"
                        features={{ newFile: true, edit: true, delete: true, newFolder: true, upload: true, directoryNavigation: true }}
                        title="Skill Files (Advanced)"
                        onRefresh={invalidateSkills}
                    />
                </div>
            )}

            {/* Card grid */}
            {!showAdvanced && (
                <>
                    {isLoading ? (
                        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
                            加载技能中...
                        </div>
                    ) : filtered.length === 0 ? (
                        <div style={{
                            textAlign: 'center', padding: '60px 20px',
                            background: 'var(--bg-secondary)', borderRadius: '12px',
                            border: '1px dashed var(--border-subtle)',
                        }}>
                            <SkillIcon icon="" size={48} style={{ margin: '0 auto 12px' }} />
                            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                                {skills.length === 0
                                    ? '暂无已安装的技能。点击"技能市场"开始安装。'
                                    : '没有匹配的技能。'}
                            </div>
                            {skills.length === 0 && (
                                <button className="btn btn-primary" style={{ fontSize: '13px' }} onClick={onOpenMarketplace}>
                                    安装技能
                                </button>
                            )}
                        </div>
                    ) : (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(4, 1fr)',
                            gap: '12px',
                        }}>
                            {filtered.map(skill => (
                                <SkillCard
                                    key={skill.folder_name}
                                    skill={skill}
                                    isDeleting={deletingFolder === skill.folder_name}
                                    onView={() => openDetail(skill)}
                                    onEdit={() => handleEditFiles(skill.folder_name)}
                                    onDelete={() => handleDelete(skill.folder_name)}
                                />
                            ))}

                            {/* Add skill card */}
                            <div
                                onClick={onOpenMarketplace}
                                style={{
                                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                    padding: '24px 16px', borderRadius: '10px',
                                    border: '1px dashed var(--border-subtle)',
                                    cursor: 'pointer', minHeight: '160px',
                                    transition: 'border-color 0.15s, background 0.15s',
                                    background: 'var(--bg-secondary)',
                                }}
                                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.background = 'var(--accent-subtle)'; }}
                                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.background = 'var(--bg-secondary)'; }}
                            >
                                <span style={{ fontSize: '24px', color: 'var(--text-tertiary)', marginBottom: '8px' }}>+</span>
                                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>安装技能</span>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Detail drawer */}
            <SkillDetailDrawer
                skill={selectedSkill}
                open={drawerOpen}
                onClose={closeDetail}
                onEditFiles={handleEditFiles}
                onDelete={handleDelete}
            />
        </div>
    );
};

// ─── Individual Skill Card ──────────────────────────────

interface SkillCardProps {
    skill: AgentSkillItem;
    isDeleting: boolean;
    onView: () => void;
    onEdit: () => void;
    onDelete: () => void;
}

const SkillCard: React.FC<SkillCardProps> = ({ skill, isDeleting, onView, onEdit, onDelete }) => {
    return (
        <div
            style={{
                padding: '16px',
                borderRadius: '10px',
                border: '1px solid var(--border-subtle)',
                background: 'var(--bg-primary)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                transition: 'border-color 0.15s, box-shadow 0.15s',
                cursor: 'pointer',
                minHeight: '160px',
                minWidth: 0,
                overflow: 'hidden',
            }}
            onClick={onView}
            onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--accent-primary)';
                e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
                e.currentTarget.style.boxShadow = 'none';
            }}
        >
            {/* Icon + Name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <SkillIcon icon={skill.icon} size={32} />
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {skill.name}
                    </div>
                    {skill.category && (
                        <span style={{
                            fontSize: '10px', padding: '1px 6px', borderRadius: '4px',
                            background: 'var(--accent-subtle)', color: 'var(--accent-text)',
                            display: 'inline-block', marginTop: '2px',
                        }}>
                            {skill.category}
                        </span>
                    )}
                </div>
            </div>

            {/* Description */}
            <div style={{
                fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4,
                display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                overflow: 'hidden', flex: 1,
            }}>
                {skill.description || '暂无描述'}
            </div>

            {/* Footer */}
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                fontSize: '11px', color: 'var(--text-tertiary)',
            }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span>{skill.file_count} 个文件</span>
                    {skill.updated_at && (
                        <span>{formatRelativeTime(skill.updated_at)}</span>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '4px' }} onClick={e => e.stopPropagation()}>
                    <button
                        className="btn btn-ghost"
                        style={{ fontSize: '11px', padding: '2px 6px' }}
                        onClick={onEdit}
                        title="编辑文件"
                    >
                        编辑
                    </button>
                    <button
                        className="btn btn-ghost"
                        style={{ fontSize: '11px', padding: '2px 6px', color: 'var(--error, #ef4444)' }}
                        onClick={onDelete}
                        disabled={isDeleting}
                        title="移除技能"
                    >
                        {isDeleting ? '...' : '移除'}
                    </button>
                </div>
            </div>
        </div>
    );
};
