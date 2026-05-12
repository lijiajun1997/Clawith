import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fileApi, type AgentSkillItem } from '../services/api';
import { SkillDetailDrawer } from './SkillDetailDrawer';
import FileBrowser from './FileBrowser';
import type { FileBrowserApi } from './FileBrowser';

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
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [selectedSkill, setSelectedSkill] = useState<AgentSkillItem | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [deletingFolder, setDeletingFolder] = useState<string | null>(null);

    const { data: skills = [], isLoading } = useQuery({
        queryKey: ['agent-skills', agentId],
        queryFn: () => fileApi.agentSkills.list(agentId),
    });

    const filtered = useMemo(() => {
        if (!search.trim()) return skills;
        const q = search.toLowerCase();
        return skills.filter(s =>
            s.name.toLowerCase().includes(q) ||
            s.description.toLowerCase().includes(q) ||
            s.folder_name.toLowerCase().includes(q)
        );
    }, [skills, search]);

    const openDetail = useCallback((skill: AgentSkillItem) => {
        setSelectedSkill(skill);
        setDrawerOpen(true);
    }, []);

    const closeDetail = useCallback(() => {
        setDrawerOpen(false);
    }, []);

    const handleDelete = useCallback(async (folderName: string) => {
        if (!confirm(`Remove skill "${folderName}"? This will delete all files in the skill folder.`)) return;
        setDeletingFolder(folderName);
        try {
            await fileBrowserApi.delete(`skills/${folderName}`);
            queryClient.invalidateQueries({ queryKey: ['agent-skills', agentId] });
            queryClient.invalidateQueries({ queryKey: ['files', agentId, 'skills'] });
            if (selectedSkill?.folder_name === folderName) {
                setDrawerOpen(false);
            }
        } catch (err: any) {
            alert(`Failed to remove: ${err?.message || err}`);
        } finally {
            setDeletingFolder(null);
        }
    }, [agentId, fileBrowserApi, queryClient, selectedSkill]);

    const handleEditFiles = useCallback((folderName: string) => {
        setShowAdvanced(true);
        // FileBrowser will open at skills/ path; user can navigate into the folder
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
                        placeholder="Search skills..."
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
                            Loading skills...
                        </div>
                    ) : filtered.length === 0 ? (
                        <div style={{
                            textAlign: 'center', padding: '60px 20px',
                            background: 'var(--bg-secondary)', borderRadius: '12px',
                            border: '1px dashed var(--border-subtle)',
                        }}>
                            <div style={{ fontSize: '36px', marginBottom: '12px' }}>--</div>
                            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                                {skills.length === 0
                                    ? 'No skills installed yet. Click "Install Skill" to get started.'
                                    : 'No skills match your search.'}
                            </div>
                            {skills.length === 0 && (
                                <button className="btn btn-primary" style={{ fontSize: '13px' }} onClick={onOpenMarketplace}>
                                    Install Skill
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
                                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Install Skill</span>
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
                <span style={{ fontSize: '28px', lineHeight: 1, flexShrink: 0 }}>{skill.icon}</span>
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
                {skill.description || 'No description available.'}
            </div>

            {/* Footer */}
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                fontSize: '11px', color: 'var(--text-tertiary)',
            }}>
                <span>{skill.file_count} file{skill.file_count !== 1 ? 's' : ''}</span>
                <div style={{ display: 'flex', gap: '4px' }} onClick={e => e.stopPropagation()}>
                    <button
                        className="btn btn-ghost"
                        style={{ fontSize: '11px', padding: '2px 6px' }}
                        onClick={onEdit}
                        title="Edit files"
                    >
                        Edit
                    </button>
                    <button
                        className="btn btn-ghost"
                        style={{ fontSize: '11px', padding: '2px 6px', color: 'var(--error, #ef4444)' }}
                        onClick={onDelete}
                        disabled={isDeleting}
                        title="Remove skill"
                    >
                        {isDeleting ? '...' : 'Remove'}
                    </button>
                </div>
            </div>
        </div>
    );
};
