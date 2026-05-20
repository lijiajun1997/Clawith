import React, { useState, useMemo } from 'react';
import { TABLER_ICON_MAP, AVAILABLE_TABLER_ICONS } from './SkillIcon';

// 将 IconName 转为可读名称: IconFileCheck -> File Check
function formatIconName(name: string): string {
    return name.replace('Icon', '').replace(/([A-Z])/g, ' $1').trim();
}

interface IconPickerProps {
    value: string;
    onChange: (icon: string) => void;
    open: boolean;
    onClose: () => void;
}

const IconPicker: React.FC<IconPickerProps> = ({ value, onChange, open, onClose }) => {
    const [search, setSearch] = useState('');

    const filteredIcons = useMemo(() => {
        if (!search.trim()) return AVAILABLE_TABLER_ICONS;
        const q = search.toLowerCase();
        return AVAILABLE_TABLER_ICONS.filter(name =>
            name.toLowerCase().includes(q) ||
            formatIconName(name).toLowerCase().includes(q)
        );
    }, [search]);

    if (!open) return null;

    return (
        <div style={{ position: 'fixed', inset: 0, zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)' }} onClick={onClose} />
            <div style={{
                position: 'relative', background: 'var(--bg-primary)', borderRadius: '12px',
                width: '520px', maxWidth: '95vw', maxHeight: '80vh',
                border: '1px solid var(--border-default)', boxShadow: '0 16px 48px rgba(0,0,0,0.2)',
                display: 'flex', flexDirection: 'column',
            }}>
                {/* Header */}
                <div style={{ padding: '16px 20px 12px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <h4 style={{ margin: 0, fontSize: '15px' }}>选择图标</h4>
                        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', color: 'var(--text-secondary)' }}>✕</button>
                    </div>
                    <input
                        className="input"
                        placeholder="搜索图标..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{ width: '100%', fontSize: '12px' }}
                        autoFocus
                    />
                </div>

                {/* Grid */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '6px' }}>
                        {filteredIcons.map(name => {
                            const Comp = TABLER_ICON_MAP[name];
                            if (!Comp) return null;
                            const isSelected = value === name;
                            return (
                                <div
                                    key={name}
                                    onClick={() => { onChange(name); onClose(); }}
                                    title={formatIconName(name)}
                                    style={{
                                        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                        padding: '8px', borderRadius: '8px', cursor: 'pointer',
                                        border: isSelected ? '2px solid var(--accent-primary)' : '1px solid transparent',
                                        background: isSelected ? 'var(--accent-subtle)' : 'transparent',
                                        transition: 'background 0.1s',
                                    }}
                                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-secondary)'; }}
                                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                                >
                                    <Comp size={22} stroke={1.5} style={{ color: 'var(--text-primary)' }} />
                                    <span style={{ fontSize: '9px', color: 'var(--text-tertiary)', marginTop: '2px', textAlign: 'center', lineHeight: 1.2 }}>
                                        {formatIconName(name)}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default IconPicker;
