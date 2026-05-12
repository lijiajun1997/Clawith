import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { skillApi, fileApi, type AgentSkillItem } from '../services/api';
import { SkillDetailDrawer } from './SkillDetailDrawer';

interface SkillMarketplaceProps {
    agentId: string;
    open: boolean;
    onClose: () => void;
    installedFolderNames: Set<string>;
    onImported: () => void;
}

export const SkillMarketplace: React.FC<SkillMarketplaceProps> = ({
    agentId,
    open,
    onClose,
    installedFolderNames,
    onImported,
}) => {
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [importingSkillId, setImportingSkillId] = useState<string | null>(null);
    const [previewSkill, setPreviewSkill] = useState<AgentSkillItem | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    const { data: globalSkills = [], isLoading } = useQuery({
        queryKey: ['global-skills-for-market'],
        queryFn: () => skillApi.list(),
        enabled: open,
    });

    const filtered = useMemo(() => {
        if (!search.trim()) return globalSkills;
        const q = search.toLowerCase();
        return globalSkills.filter((s: any) =>
            s.name.toLowerCase().includes(q) ||
            (s.description || '').toLowerCase().includes(q) ||
            s.folder_name.toLowerCase().includes(q)
        );
    }, [globalSkills, search]);

    const handleInstall = useCallback(async (skill: any) => {
        setImportingSkillId(skill.id);
        try {
            await fileApi.importSkill(agentId, skill.id);
            queryClient.invalidateQueries({ queryKey: ['agent-skills', agentId] });
            queryClient.invalidateQueries({ queryKey: ['files', agentId, 'skills'] });
            onImported();
        } catch (err: any) {
            alert(`Install failed: ${err?.message || err}`);
        } finally {
            setImportingSkillId(null);
        }
    }, [agentId, queryClient, onImported]);

    const handlePreview = useCallback((skill: any) => {
        const item: AgentSkillItem = {
            folder_name: skill.folder_name,
            name: skill.name,
            description: skill.description || '',
            icon: skill.icon || '--',
            category: skill.category || 'general',
            is_global: true,
            file_count: 0,
            skill_md_content: '',
        };
        setPreviewSkill(item);
        setDrawerOpen(true);

        skillApi.get(skill.id).then((detail: any) => {
            const skillMd = detail.files?.find((f: any) => f.path === 'SKILL.md');
            if (skillMd) {
                setPreviewSkill(prev => prev ? { ...prev, skill_md_content: skillMd.content, file_count: detail.files?.length || 0 } : prev);
            }
        }).catch(() => {});
    }, []);

    if (!open) return null;

    return (
        <>
            <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={onClose}>
                <div
                    style={{
                        background: 'var(--bg-primary)', borderRadius: '12px',
                        width: '1200px', maxWidth: '95vw', maxHeight: '85vh',
                        display: 'flex', flexDirection: 'column',
                        border: '1px solid var(--border-default)',
                        boxShadow: '0 16px 48px rgba(0,0,0,0.2)',
                    }}
                    onClick={e => e.stopPropagation()}
                >
                    {/* Header */}
                    <div style={{ padding: '20px 28px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <h3 style={{ margin: 0, fontSize: '18px' }}>Skill Marketplace</h3>
                            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer', color: 'var(--text-secondary)', padding: '4px 8px' }}>x</button>
                        </div>
                        <input
                            className="input"
                            placeholder="Search skills..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            autoFocus
                            style={{ width: '100%', fontSize: '13px' }}
                        />
                    </div>

                    {/* Grid */}
                    <div style={{ flex: 1, overflowY: 'auto', padding: '16px 28px' }}>
                        {isLoading ? (
                            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)', fontSize: '13px' }}>Loading...</div>
                        ) : filtered.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
                                {search ? 'No skills match your search.' : 'No skills available.'}
                            </div>
                        ) : (
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                                {filtered.map((skill: any) => {
                                    const installed = installedFolderNames.has(skill.folder_name);
                                    return (
                                        <div
                                            key={skill.id}
                                            style={{
                                                padding: '14px', borderRadius: '10px',
                                                border: '1px solid var(--border-subtle)',
                                                background: 'var(--bg-primary)',
                                                display: 'flex', flexDirection: 'column', gap: '8px',
                                                cursor: 'pointer',
                                                minWidth: 0, overflow: 'hidden',
                                                transition: 'border-color 0.15s, box-shadow 0.15s',
                                            }}
                                            onClick={() => handlePreview(skill)}
                                            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.08)'; }}
                                            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.boxShadow = 'none'; }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                                                <span style={{ fontSize: '22px', lineHeight: 1, flexShrink: 0 }}>{skill.icon || '--'}</span>
                                                <div style={{ fontWeight: 600, fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>
                                                    {skill.name}
                                                </div>
                                            </div>
                                            <div style={{
                                                fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4,
                                                display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                                                overflow: 'hidden', flex: 1, wordBreak: 'break-word',
                                            }}>
                                                {skill.description || 'No description.'}
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                                {installed ? (
                                                    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(16,185,129,0.1)', color: '#10b981', fontWeight: 600 }}>Installed</span>
                                                ) : (
                                                    <button
                                                        className="btn btn-secondary"
                                                        style={{ fontSize: '11px', padding: '2px 10px' }}
                                                        disabled={importingSkillId === skill.id}
                                                        onClick={e => { e.stopPropagation(); handleInstall(skill); }}
                                                    >
                                                        {importingSkillId === skill.id ? '...' : 'Install'}
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <SkillDetailDrawer skill={previewSkill} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
        </>
    );
};
