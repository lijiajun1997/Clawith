import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    PieChart, Pie, Cell, ResponsiveContainer,
    Tooltip, BarChart, Bar, XAxis, YAxis,
    LineChart, Line, CartesianGrid, AreaChart, Area,
} from 'recharts';
import { agentApi, taskApi, activityApi, fetchJson, enterpriseApi } from '../services/api';
import type { Agent, Task } from '../types';

/* ────── Color Palette ────── */
const STATUS_COLORS: Record<string, string> = {
    running: '#22c55e', idle: '#f59e0b', stopped: '#64748b',
    error: '#ef4444', creating: '#3b82f6',
};
const ACTIVITY_COLORS: Record<string, string> = {
    chat_reply: '#3b82f6', tool_call: '#8b5cf6', file_written: '#f59e0b',
    schedule_run: '#06b6d4', heartbeat: '#22c55e',
};
const TASK_COLORS: Record<string, string> = {
    pending: '#f59e0b', doing: '#3b82f6', done: '#22c55e', paused: '#64748b',
};

/* ────── Helpers ────── */

const timeAgo = (dateStr: string | undefined, t: any) => {
    if (!dateStr) return '-';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return t('dashboard.justNow');
    if (mins < 60) return t('dashboard.minutesAgo', { count: mins });
    const hours = Math.floor(mins / 60);
    if (hours < 24) return t('dashboard.hoursAgo', { count: hours });
    return t('dashboard.daysAgo', { count: Math.floor(hours / 24) });
};

const formatTokens = (n: number) => {
    if (!n) return '0';
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return String(n);
};

const statusLabel = (s: string, t: any) => {
    switch (s) {
        case 'running': return t('dashboard.status.running');
        case 'idle': return t('dashboard.status.idle');
        case 'stopped': return t('dashboard.status.stopped');
        case 'error': return t('dashboard.status.error');
        case 'creating': return t('dashboard.status.creating');
        default: return s;
    }
};

const statusColor = (s: string) => {
    switch (s) {
        case 'running': return 'var(--status-running)';
        case 'idle': return 'var(--status-idle)';
        case 'error': return 'var(--status-error)';
        case 'stopped': return 'var(--status-stopped)';
        default: return 'var(--text-tertiary)';
    }
};

const priorityColor = (p: string) => {
    switch (p) {
        case 'urgent': return 'var(--error)';
        case 'high': return 'var(--warning)';
        case 'medium': return 'var(--accent-primary)';
        default: return 'var(--text-tertiary)';
    }
};

/* ────── Inline SVG Icons ────── */

const Icons = {
    bot: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="5" width="12" height="10" rx="2" />
            <circle cx="7" cy="10" r="1" fill="currentColor" stroke="none" />
            <circle cx="11" cy="10" r="1" fill="currentColor" stroke="none" />
            <path d="M9 2v3M6 2h6" />
        </svg>
    ),
    plus: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M8 3v10M3 8h10" />
        </svg>
    ),
    activity: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 8h3l2-5 3 10 2-5h4" />
        </svg>
    ),
    users: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="6" cy="5" r="2.5" /><path d="M1.5 14v-1a3.5 3.5 0 017 0v1" />
            <circle cx="11.5" cy="5.5" r="2" /><path d="M14.5 14v-.5a3 3 0 00-3-3" />
        </svg>
    ),
    zap: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8.5 1.5L3 9h4.5l-.5 5.5L13 7H8.5l.5-5.5z" />
        </svg>
    ),
    tasks: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="2" width="12" height="12" rx="2" /><path d="M5.5 8l2 2 3.5-3.5" />
        </svg>
    ),
    clock: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="8" cy="8" r="6" /><path d="M8 4.5V8l2.5 1.5" />
        </svg>
    ),
    settings: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="8" cy="8" r="2.5" />
            <path d="M13.3 10a1.2 1.2 0 00.2 1.3l.1.1a1.45 1.45 0 11-2.05 2.05l-.1-.1a1.2 1.2 0 00-1.3-.2 1.2 1.2 0 00-.73 1.1v.3a1.45 1.45 0 11-2.9 0v-.15A1.2 1.2 0 005.7 13.3a1.2 1.2 0 00-1.3.2l-.1.1a1.45 1.45 0 11-2.05-2.05l.1-.1a1.2 1.2 0 00.2-1.3 1.2 1.2 0 00-1.1-.73h-.3a1.45 1.45 0 110-2.9h.15A1.2 1.2 0 002.7 5.7a1.2 1.2 0 00-.2-1.3l-.1-.1A1.45 1.45 0 114.45 2.25l.1.1a1.2 1.2 0 001.3.2h.06a1.2 1.2 0 00.73-1.1v-.3a1.45 1.45 0 012.9 0v.15a1.2 1.2 0 00.73 1.1 1.2 1.2 0 001.3-.2l.1-.1a1.45 1.45 0 112.05 2.05l-.1.1a1.2 1.2 0 00-.2 1.3v.06a1.2 1.2 0 001.1.73h.3a1.45 1.45 0 010 2.9h-.15a1.2 1.2 0 00-1.1.73z" />
        </svg>
    ),
    shield: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 1.5L2.5 4v4c0 3.5 2.35 6.75 5.5 7.5 3.15-.75 5.5-4 5.5-7.5V4L8 1.5z" />
            <path d="M6 8l1.5 1.5L10.5 6" />
        </svg>
    ),
    chart: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="8" width="3" height="6" rx="0.5" />
            <rect x="6.5" y="4" width="3" height="10" rx="0.5" />
            <rect x="11" y="2" width="3" height="12" rx="0.5" />
        </svg>
    ),
    alertTriangle: (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 1L1 14h14L8 1z" /><path d="M8 6v3M8 11.5v.5" />
        </svg>
    ),
    messageSquare: (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 10c0 .55-.45 1-1 1H5l-3 3V3c0-.55.45-1 1-1h10c.55 0 1 .45 1 1v7z" />
        </svg>
    ),
    fileText: (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 1H3v14h10V4l-3-3z" /><path d="M10 1v3h3M5 8h6M5 11h4" />
        </svg>
    ),
    tool: (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.7 12.3l-8-8C7.5 3.1 8 2.1 8 1 6.3 1 4.8 1.8 3.8 3L1.5.7.7 1.5 3 3.8C1.8 4.8 1 6.3 1 8c1.1 0 2.1-.5 3.3-1.3l8 8c.6.6 1.5.6 2.1 0l1.3-1.3c.6-.6.6-1.5 0-2.1z" />
        </svg>
    ),
    schedule: (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="8" cy="8" r="6.5" /><path d="M8 4v4l2.5 1.5" /><path d="M1 2l2-1M15 2l-2-1" />
        </svg>
    ),
    heartbeat: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 8h2l1.5-4 2 8 2-6L11 8h3" />
        </svg>
    ),
};

/* ────── KPI Card ────── */

function KpiCard({ icon, label, value, sub, accent }: {
    icon: React.ReactNode; label: string; value: string | number;
    sub?: string; accent?: string;
}) {
    const accentStyle = accent ? { color: accent } : {};
    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '14px 16px',
            display: 'flex', flexDirection: 'column', gap: '4px',
            transition: 'border-color 0.15s, box-shadow 0.15s',
        }}
            onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-default)';
                (e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-sm)';
            }}
            onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-subtle)';
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
            }}
        >
            <div style={{
                fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600,
                textTransform: 'uppercase', letterSpacing: '0.5px',
                display: 'flex', alignItems: 'center', gap: '6px',
            }}>
                <span style={{ display: 'flex', opacity: 0.7, ...accentStyle }}>{icon}</span>
                {label}
            </div>
            <div style={{
                fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)',
                letterSpacing: '-0.03em', fontFamily: 'var(--font-mono)',
                ...accentStyle,
            }}>
                {value}
            </div>
            {sub && <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{sub}</div>}
        </div>
    );
}

/* ────── Sidebar Chart Card ────── */

function SidebarChart({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
        }}>
            <div style={{
                padding: '10px 14px',
                fontSize: '12px', fontWeight: 600,
                color: 'var(--text-secondary)',
                borderBottom: '1px solid var(--border-subtle)',
            }}>
                {title}
            </div>
            <div style={{ padding: '12px 14px' }}>
                {children}
            </div>
        </div>
    );
}

/* ────── Status Donut (compact) ────── */

function StatusDonut({ agents }: { agents: Agent[] }) {
    const { t } = useTranslation();
    const data = useMemo(() => {
        const counts: Record<string, number> = {};
        agents.forEach(a => { counts[a.status] = (counts[a.status] || 0) + 1; });
        return Object.entries(counts).map(([status, count]) => ({
            name: statusLabel(status, t), value: count, status,
        }));
    }, [agents, t]);

    if (data.length === 0) return null;

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '72px', height: '72px', flexShrink: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie data={data} dataKey="value" cx="50%" cy="50%"
                            innerRadius={20} outerRadius={34} paddingAngle={2} strokeWidth={0}>
                            {data.map((_, i) => (
                                <Cell key={i} fill={STATUS_COLORS[_.status] || '#64748b'} />
                            ))}
                        </Pie>
                    </PieChart>
                </ResponsiveContainer>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {data.map(s => (
                    <div key={s.status} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px' }}>
                        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: STATUS_COLORS[s.status] || '#64748b', flexShrink: 0 }} />
                        <span style={{ color: 'var(--text-secondary)', minWidth: '40px' }}>{s.name}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>{s.value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ────── Token Top5 Bar Chart ────── */

function TokenTopBar({ agents }: { agents: Agent[] }) {
    const data = useMemo(() =>
        [...agents]
            .sort((a, b) => (b.tokens_used_today || 0) - (a.tokens_used_today || 0))
            .slice(0, 5)
            .map(a => ({ name: a.name.length > 8 ? a.name.slice(0, 8) + '..' : a.name, tokens: a.tokens_used_today || 0 })),
        [agents]);

    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    return (
        <div style={{ height: data.length * 28 + 10 }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                    <XAxis type="number" hide />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} width={60} />
                    <Bar dataKey="tokens" radius={[0, 3, 3, 0]} barSize={14}>
                        {data.map((_, i) => (
                            <Cell key={i} fill={['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4'][i]} />
                        ))}
                    </Bar>
                    <Tooltip
                        contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }}
                        formatter={(v: any) => [formatTokens(Number(v)), 'Token']}
                    />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ────── Task Pipeline ────── */

function TaskPipeline({ tasks }: { tasks: Task[] }) {
    const { t } = useTranslation();
    const counts = useMemo(() => {
        const c = { pending: 0, doing: 0, done: 0, paused: 0 };
        tasks.forEach(t => { if (t.status in c) c[t.status as keyof typeof c]++; });
        return c;
    }, [tasks]);
    const total = counts.pending + counts.doing + counts.done + counts.paused;

    const labels: Record<string, string> = {
        pending: t('dashboard.task.pending', '待处理'),
        doing: t('dashboard.task.doing', '进行中'),
        done: t('dashboard.task.done', '已完成'),
        paused: t('dashboard.task.paused', '已暂停'),
    };

    return (
        <div>
            <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden', background: 'var(--bg-tertiary)', marginBottom: '10px' }}>
                {total > 0 && Object.entries(counts).map(([s, c]) => c > 0 ? (
                    <div key={s} style={{ width: `${(c / total) * 100}%`, background: TASK_COLORS[s], transition: 'width 0.4s' }} />
                ) : null)}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                {(['pending', 'doing', 'done', 'paused'] as const).map(s => (
                    <div key={s} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px' }}>
                        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: TASK_COLORS[s], flexShrink: 0 }} />
                        <span style={{ color: 'var(--text-secondary)' }}>{labels[s]}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)', marginLeft: 'auto' }}>{counts[s]}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ────── Activity Type Pie ────── */

function ActivityTypePie({ activities }: { activities: any[] }) {
    const data = useMemo(() => {
        const counts: Record<string, number> = {};
        activities.forEach(a => {
            const type = a.action_type || 'other';
            counts[type] = (counts[type] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([type, count]) => ({ name: type.replace(/_/g, ' '), type, count }))
            .sort((a, b) => b.count - a.count);
    }, [activities]);

    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '72px', height: '72px', flexShrink: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie data={data} dataKey="count" cx="50%" cy="50%"
                            innerRadius={18} outerRadius={34} paddingAngle={2} strokeWidth={0}>
                            {data.map((d, i) => (
                                <Cell key={i} fill={ACTIVITY_COLORS[d.type] || '#64748b'} />
                            ))}
                        </Pie>
                    </PieChart>
                </ResponsiveContainer>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {data.map(d => (
                    <div key={d.type} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px' }}>
                        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: ACTIVITY_COLORS[d.type] || '#64748b', flexShrink: 0 }} />
                        <span style={{ color: 'var(--text-secondary)' }}>{d.name}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)', marginLeft: 'auto' }}>{d.count}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ────── Hourly Activity Trend (24h line chart) ────── */

function ActivityTrendChart({ activities }: { activities: any[] }) {
    const data = useMemo(() => {
        const now = new Date();
        const hours: { hour: string; count: number }[] = [];
        // Build 24 hourly buckets
        for (let i = 23; i >= 0; i--) {
            const h = new Date(now.getTime() - i * 3600000);
            const label = `${h.getHours().toString().padStart(2, '0')}:00`;
            hours.push({ hour: label, count: 0 });
        }
        activities.forEach(act => {
            if (!act.created_at) return;
            const t = new Date(act.created_at);
            const diffH = Math.floor((now.getTime() - t.getTime()) / 3600000);
            if (diffH >= 0 && diffH < 24) {
                hours[23 - diffH].count++;
            }
        });
        return hours;
    }, [activities]);

    const maxCount = Math.max(1, ...data.map(d => d.count));

    return (
        <div style={{ height: '100px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                    <XAxis dataKey="hour" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false}
                        interval={5} />
                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false}
                        domain={[0, maxCount]} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }} />
                    <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={1.5}
                        dot={false} activeDot={{ r: 3 }} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ────── Token Comparison (today vs month per agent) ────── */


/* ────── Conversation Stats (multi-channel line chart) ────── */

const CHANNEL_COLORS: Record<string, string> = {
    feishu: '#3b82f6', web: '#10b981', dingtalk: '#f59e0b', wecom: '#06b6d4', other: '#8b5cf6',
};
const CHANNEL_NAMES: Record<string, string> = {
    feishu: '飞书', web: 'Web', dingtalk: '钉钉', wecom: '企微', other: '其他',
};

function ConversationStatsChart({ activities, range }: { activities: any[]; range: number }) {
    const data = useMemo(() => {
        const now = new Date();
        const days = range;
        const buckets: { _key: string; day: string; feishu: number; web: number; dingtalk: number; wecom: number; other: number }[] = [];
        for (let i = days - 1; i >= 0; i--) {
            const d = new Date(now.getTime() - i * 86400000);
            const key = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
            buckets.push({
                _key: key,
                day: `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')}`,
                feishu: 0, web: 0, dingtalk: 0, wecom: 0, other: 0,
            });
        }
        activities.forEach(act => {
            if (act.action_type !== 'chat_reply' || !act.created_at) return;
            const actDate = new Date(act.created_at);
            const key = `${actDate.getFullYear()}-${(actDate.getMonth() + 1).toString().padStart(2, '0')}-${actDate.getDate().toString().padStart(2, '0')}`;
            const b = buckets.find(bk => bk._key === key);
            if (!b) return;
            const ch = act.detail?.channel || act.detail_json?.channel || 'other';
            const validCh = ['feishu', 'web', 'dingtalk', 'wecom'].includes(ch) ? ch : 'other';
            (b as any)[validCh]++;
        });
        return buckets;
    }, [activities, range]);

    const channels = ['feishu', 'web', 'dingtalk', 'wecom', 'other'];

    return (
        <div style={{ height: '140px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                    <XAxis dataKey="day" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }}
                        formatter={(v: any, name: any) => [v, CHANNEL_NAMES[String(name)] || String(name)]} />
                    {channels.map(ch => (
                        <Line key={ch} type="monotone" dataKey={ch} stroke={CHANNEL_COLORS[ch]} strokeWidth={1.5}
                            dot={false} activeDot={{ r: 3 }} name={ch} />
                    ))}
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ────── Token By Agent (horizontal bar with day/month toggle) ────── */
/* ────── File Delivery Trend (send_channel_file per day) ────── */

function FileDeliveryChart({ activities, dailyStats, range }: { activities: any[]; dailyStats: any[]; range: number }) {
    const data = useMemo(() => {
        const now = new Date();
        const buckets: { _key: string; day: string; deliveries: number }[] = [];
        for (let i = range - 1; i >= 0; i--) {
            const d = new Date(now.getTime() - i * 86400000);
            const key = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
            buckets.push({
                _key: key,
                day: `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')}`,
                deliveries: 0,
            });
        }
        // Prefer server-side aggregated stats
        const deliveryStats = dailyStats.filter(s => s.action_type === 'tool_call' && s.detail_tool === 'send_channel_file');
        if (deliveryStats.length > 0) {
            deliveryStats.forEach(s => {
                const b = buckets.find(bk => bk._key === s.date);
                if (b) b.deliveries += s.count;
            });
        } else {
            // Fallback: count from raw activities
            activities.forEach(a => {
                if (a.action_type !== 'tool_call' || !a.created_at) return;
                if (a.detail?.tool !== 'send_channel_file') return;
                const actDate = new Date(a.created_at);
                const key = `${actDate.getFullYear()}-${(actDate.getMonth() + 1).toString().padStart(2, '0')}-${actDate.getDate().toString().padStart(2, '0')}`;
                const b = buckets.find(bk => bk._key === key);
                if (b) b.deliveries++;
            });
        }
        return buckets;
    }, [activities, dailyStats, range]);

    const total = data.reduce((s, d) => s + d.deliveries, 0);

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>共 {total} 次交付</span>
            </div>
            <div style={{ height: '120px' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
                        <defs>
                            <linearGradient id="deliveryGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                        <XAxis dataKey="day" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} allowDecimals={false} />
                        <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }}
                            formatter={(v: any) => [v, '交付次数']} />
                        <Area type="monotone" dataKey="deliveries" stroke="#10b981" strokeWidth={1.5}
                            fill="url(#deliveryGrad)" dot={{ r: 2, fill: '#10b981' }} activeDot={{ r: 3 }} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

function TokenByAgentChart({ agents, mode }: { agents: Agent[]; mode: 'day' | 'month' }) {
    const data = useMemo(() => {
        const key = mode === 'day' ? 'tokens_used_today' as const : 'tokens_used_month' as const;
        return [...agents].sort((a, b) => (b[key] || 0) - (a[key] || 0))
            .slice(0, 6)
            .map(a => ({
                name: a.name.length > 10 ? a.name.slice(0, 10) + '..' : a.name,
                tokens: a[key] || 0,
            }));
    }, [agents, mode]);

    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    return (
        <div style={{ height: data.length * 28 + 8 }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                    <XAxis type="number" hide />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} width={70} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }}
                        formatter={(v: any) => [formatTokens(Number(v)), 'Token']} />
                    <Bar dataKey="tokens" radius={[0, 3, 3, 0]} barSize={14}>
                        {data.map((_, i) => <Cell key={i} fill={['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899'][i]} />)}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ────── Token Month (today vs rest stacked) ────── */

function TokenMonthChart({ agents }: { agents: Agent[] }) {
    const data = useMemo(() => {
        const totalToday = agents.reduce((s, a) => s + (a.tokens_used_today || 0), 0);
        const totalMonthRest = agents.reduce((s, a) => s + Math.max(0, (a.tokens_used_month || 0) - (a.tokens_used_today || 0)), 0);
        return [
            { name: 'Token', today: totalToday, rest: totalMonthRest },
        ];
    }, [agents]);

    const tokens = agents.reduce((s, a) => s + (a.tokens_used_today || 0), 0);
    const tokensMonth = agents.reduce((s, a) => s + (a.tokens_used_month || 0), 0);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Summary numbers */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-md)', background: 'var(--bg-tertiary)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginBottom: '2px' }}>今日</div>
                    <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#3b82f6' }}>{formatTokens(tokens)}</div>
                </div>
                <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-md)', background: 'var(--bg-tertiary)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginBottom: '2px' }}>本月</div>
                    <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#8b5cf6' }}>{formatTokens(tokensMonth)}</div>
                </div>
            </div>
            {/* Progress bar */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
                    <span>今日占比</span>
                    <span>{tokensMonth > 0 ? ((tokens / tokensMonth) * 100).toFixed(1) : 0}%</span>
                </div>
                <div style={{ height: '6px', borderRadius: '3px', overflow: 'hidden', background: 'var(--bg-tertiary)' }}>
                    <div style={{
                        height: '100%', borderRadius: '3px',
                        width: tokensMonth > 0 ? `${(tokens / tokensMonth) * 100}%` : '0%',
                        background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                        transition: 'width 0.4s',
                    }} />
                </div>
            </div>
        </div>
    );
}

/* ────── Token Consumption (daily area chart) ────── */

function TokenConsumptionChart({ data }: { data: { date: string; tokens: number }[] }) {
    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    return (
        <div style={{ height: '140px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <defs>
                        <linearGradient id="tokenGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false}
                        tickFormatter={(v: string) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false}
                        tickFormatter={(v: number) => formatTokens(v)} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }}
                        formatter={(v: any) => [formatTokens(Number(v)), 'Token']} />
                    <Area type="monotone" dataKey="tokens" stroke="#8b5cf6" strokeWidth={1.5}
                        fill="url(#tokenGrad)" dot={false} activeDot={{ r: 3 }} />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ────── Agent Activity Rank (with day/week/month toggle) ────── */

const RANK_COLORS = ['#fbbf24', '#94a3b8', '#cd7f32']; // gold, silver, bronze

function AgentActivityRankChart({ agents, activities, timeRange }: {
    agents: Agent[]; activities: any[]; timeRange: 'day' | 'week' | 'month';
}) {
    const data = useMemo(() => {
        const now = Date.now();
        const rangeMs = timeRange === 'day' ? 86400000 : timeRange === 'week' ? 604800000 : 2592000000;
        const agentActCount: Record<string, number> = {};
        activities.forEach(a => {
            if (!a.created_at || !a.agent_id) return;
            if ((now - new Date(a.created_at).getTime()) < rangeMs) {
                agentActCount[a.agent_id] = (agentActCount[a.agent_id] || 0) + 1;
            }
        });
        return [...agents]
            .map(a => ({
                id: a.id,
                name: a.name.length > 8 ? a.name.slice(0, 8) + '..' : a.name,
                count: agentActCount[a.id] || 0,
            }))
            .filter(a => a.count > 0)
            .sort((a, b) => b.count - a.count)
            .slice(0, 8);
    }, [agents, activities, timeRange]);

    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {data.map((d, i) => (
                <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                        width: '18px', height: '18px', borderRadius: '50%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '9px', fontWeight: 700, flexShrink: 0,
                        background: i < 3 ? RANK_COLORS[i] : 'var(--bg-tertiary)',
                        color: i < 3 ? '#fff' : 'var(--text-tertiary)',
                    }}>{i + 1}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', width: '70px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
                    <div style={{ flex: 1, height: '6px', borderRadius: '3px', overflow: 'hidden', background: 'var(--bg-tertiary)' }}>
                        <div style={{
                            height: '100%', borderRadius: '3px',
                            width: `${(d.count / (data[0]?.count || 1)) * 100}%`,
                            background: i < 3 ? RANK_COLORS[i] : 'var(--accent-primary)',
                            transition: 'width 0.3s',
                        }} />
                    </div>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', width: '30px', textAlign: 'right' }}>{d.count}</span>
                </div>
            ))}
        </div>
    );
}

/* ────── Tool Call Statistics (per-tool calls + success rate) ────── */

function ToolStatsChart({ activities }: { activities: any[] }) {
    const data = useMemo(() => {
        const toolStats: Record<string, { calls: number; success: number }> = {};
        activities.forEach(a => {
            if (a.action_type !== 'tool_call') return;
            const toolName = a.detail?.tool || 'unknown';
            if (!toolStats[toolName]) toolStats[toolName] = { calls: 0, success: 0 };
            toolStats[toolName].calls++;
            const result = a.detail?.result || '';
            if (!result.startsWith('❌')) toolStats[toolName].success++;
        });
        return Object.entries(toolStats)
            .map(([tool, s]) => ({
                tool: tool.length > 14 ? tool.slice(0, 14) + '..' : tool,
                calls: s.calls,
                success: s.calls > 0 ? Math.round((s.success / s.calls) * 100) : 0,
            }))
            .sort((a, b) => b.calls - a.calls)
            .slice(0, 10);
    }, [activities]);

    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    const maxCalls = data[0]?.calls || 1;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {data.map(d => (
                <div key={d.tool} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-secondary)', width: '80px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flexShrink: 0 }}>{d.tool}</span>
                    <div style={{ flex: 1, height: '6px', borderRadius: '3px', overflow: 'hidden', background: 'var(--bg-tertiary)' }}>
                        <div style={{
                            height: '100%', borderRadius: '3px',
                            width: `${(d.calls / maxCalls) * 100}%`,
                            background: d.success >= 90 ? '#22c55e' : d.success >= 70 ? '#f59e0b' : '#ef4444',
                            opacity: 0.7,
                            transition: 'width 0.3s',
                        }} />
                    </div>
                    <span style={{ fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', width: '24px', textAlign: 'right' }}>{d.calls}</span>
                    <span style={{
                        fontSize: '9px', fontWeight: 600, width: '28px', textAlign: 'right',
                        color: d.success >= 90 ? '#22c55e' : d.success >= 70 ? '#f59e0b' : '#ef4444',
                    }}>{d.success}%</span>
                </div>
            ))}
        </div>
    );
}

/* ────── Model Distribution (agents by LLM model) ────── */

const MODEL_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#64748b'];

function ModelDistributionChart({ agents, models }: { agents: Agent[]; models: any[] }) {
    const data = useMemo(() => {
        const modelMap = new Map(models.map((m: any) => [m.id, m.label || m.name || m.id]));
        const counts: Record<string, { agents: number; tokens: number }> = {};
        agents.forEach(a => {
            const label = modelMap.get(a.primary_model_id) || 'Default';
            if (!counts[label]) counts[label] = { agents: 0, tokens: 0 };
            counts[label].agents++;
            counts[label].tokens += a.tokens_used_month || 0;
        });
        return Object.entries(counts)
            .map(([name, v]) => ({ name, ...v }))
            .sort((a, b) => b.agents - a.agents)
            .slice(0, 6);
    }, [agents, models]);

    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {data.map((d, i) => (
                <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                        width: '8px', height: '8px', borderRadius: '2px', flexShrink: 0,
                        background: MODEL_COLORS[i % MODEL_COLORS.length],
                    }} />
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', width: '60px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
                    <div style={{ flex: 1, height: '6px', borderRadius: '3px', overflow: 'hidden', background: 'var(--bg-tertiary)' }}>
                        <div style={{
                            height: '100%', borderRadius: '3px',
                            width: `${(d.agents / (data[0]?.agents || 1)) * 100}%`,
                            background: MODEL_COLORS[i % MODEL_COLORS.length],
                            opacity: 0.7,
                            transition: 'width 0.3s',
                        }} />
                    </div>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>{d.agents}</span>
                </div>
            ))}
        </div>
    );
}

/* ────── Channel Activity (vertical bar chart) ────── */

const CH_COLORS: Record<string, string> = {
    chat_reply: '#06b6d4', tool_call: '#f59e0b', heartbeat: '#22c55e',
    schedule_run: '#ec4899', error: '#ef4444', other: '#64748b',
};
const CH_LABELS: Record<string, string> = {
    chat_reply: '对话回复', tool_call: '工具调用', heartbeat: '心跳',
    schedule_run: '定时任务', error: '错误', task_created: '任务创建',
    task_updated: '任务更新', file_written: '文件写入', plaza_post: '广场发布',
};

function ChannelActivityChart({ activities }: { activities: any[] }) {
    const data = useMemo(() => {
        const counts: Record<string, number> = {};
        activities.forEach(a => {
            const ch = a.action_type;
            const label = CH_LABELS[ch] || '其他';
            counts[label] = (counts[label] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([name, count]) => ({
                name,
                count,
                type: Object.entries(CH_LABELS).find(([, v]) => v === name)?.[0] || 'other',
            }))
            .sort((a, b) => b.count - a.count);
    }, [activities]);

    if (data.length === 0) return <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '12px' }}>暂无数据</div>;

    return (
        <div style={{ height: '140px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                    <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }} />
                    <Bar dataKey="count" radius={[3, 3, 0, 0]} barSize={24}>
                        {data.map((d, i) => <Cell key={i} fill={CH_COLORS[d.type] || '#64748b'} />)}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ────── Error Trend (14-day line) ────── */

function ErrorTrendChart({ activities }: { activities: any[] }) {
    const data = useMemo(() => {
        const now = new Date();
        const days = 14;
        const buckets: { _key: string; day: string; errors: number }[] = [];
        for (let i = days - 1; i >= 0; i--) {
            const d = new Date(now.getTime() - i * 86400000);
            const key = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
            buckets.push({
                _key: key,
                day: `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')}`,
                errors: 0,
            });
        }
        activities.forEach(a => {
            if (a.action_type !== 'error' || !a.created_at) return;
            const ad = new Date(a.created_at);
            const key = `${ad.getFullYear()}-${(ad.getMonth() + 1).toString().padStart(2, '0')}-${ad.getDate().toString().padStart(2, '0')}`;
            const b = buckets.find(bk => bk._key === key);
            if (b) b.errors++;
        });
        return buckets;
    }, [activities]);

    return (
        <div style={{ height: '100px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
                    <defs>
                        <linearGradient id="errorGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                    <XAxis dataKey="day" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', fontSize: '11px' }} />
                    <Area type="monotone" dataKey="errors" stroke="#ef4444" strokeWidth={1.5}
                        fill="url(#errorGrad)" dot={false} activeDot={{ r: 3 }} />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ────── Range Tab Toggle ────── */

function RangeTabs({ value, onChange, options }: {
    value: string; onChange: (v: string) => void; options: { key: string; label: string }[];
}) {
    return (
        <div style={{ display: 'flex', background: 'var(--bg-tertiary)', borderRadius: '6px', padding: '2px', border: '1px solid var(--border-subtle)' }}>
            {options.map(o => (
                <button key={o.key} onClick={() => onChange(o.key)} style={{
                    padding: '2px 8px', fontSize: '10px', border: 'none', cursor: 'pointer',
                    borderRadius: '4px', transition: 'all 0.15s',
                    background: value === o.key ? 'var(--accent-primary)' : 'transparent',
                    color: value === o.key ? '#fff' : 'var(--text-tertiary)',
                }}>{o.label}</button>
            ))}
        </div>
    );
}

/* ────── Agent Row ────── */

function AgentRow({ agent, tasks, recentActivity }: {
    agent: Agent; tasks: Task[]; recentActivity: any[];
}) {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const pendingTasks = tasks.filter(t => t.status === 'pending' || t.status === 'doing');
    const latestActivity = recentActivity[0];
    const maxTokens = agent.max_tokens_per_day || 0;
    const usedTokens = agent.tokens_used_today || 0;
    const tokenPct = maxTokens > 0 ? Math.min(100, (usedTokens / maxTokens) * 100) : 0;

    return (
        <div onClick={() => navigate(`/agents/${agent.id}`)} style={{
            display: 'grid', gridTemplateColumns: '220px 100px 1fr 130px 90px',
            alignItems: 'center', gap: '16px', padding: '12px 16px',
            borderRadius: 'var(--radius-md)', cursor: 'pointer', transition: 'background 120ms ease',
        }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                <div style={{
                    width: '32px', height: '32px', borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'var(--text-tertiary)', flexShrink: 0,
                }}>{Icons.bot}</div>
                <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
                        {agent.name}
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 400, color: statusColor(agent.status) }}>
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: statusColor(agent.status), display: 'inline-block' }} />
                            {statusLabel(agent.status, t)}
                        </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {agent.role_description || '-'}
                    </div>
                </div>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {(agent as any).creator_username || '-'}
            </div>
            <div style={{ minWidth: 0 }}>
                {latestActivity ? (
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        <span style={{ color: 'var(--text-tertiary)', marginRight: '6px' }}>{timeAgo(latestActivity.created_at, t)}</span>
                        {latestActivity.summary}
                    </div>
                ) : (
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{t('dashboard.noActivity')}</div>
                )}
                {pendingTasks.length > 0 && (
                    <div style={{ display: 'flex', gap: '4px', marginTop: '4px', flexWrap: 'wrap' }}>
                        {pendingTasks.slice(0, 3).map(t => (
                            <span key={t.id} style={{
                                fontSize: '11px', padding: '1px 6px', borderRadius: 'var(--radius-sm)',
                                background: 'var(--bg-tertiary)', color: 'var(--text-secondary)',
                                maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                display: 'inline-flex', alignItems: 'center', gap: '3px',
                            }}>
                                <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: priorityColor(t.priority), flexShrink: 0 }} />
                                {t.title}
                            </span>
                        ))}
                        {pendingTasks.length > 3 && (
                            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', padding: '1px 4px' }}>+{pendingTasks.length - 3}</span>
                        )}
                    </div>
                )}
            </div>
            <div>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '3px' }}>
                    {formatTokens(usedTokens)}
                    {maxTokens > 0 && <span style={{ opacity: 0.6 }}> / {formatTokens(maxTokens)}</span>}
                </div>
                {maxTokens > 0 ? (
                    <div style={{ height: '3px', background: 'var(--bg-tertiary)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{
                            height: '100%', borderRadius: '2px', width: `${tokenPct}%`,
                            background: tokenPct > 80 ? 'var(--error)' : tokenPct > 50 ? 'var(--warning)' : 'var(--text-tertiary)',
                            transition: 'width 0.3s',
                        }} />
                    </div>
                ) : (
                    <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', opacity: 0.5 }}>{t('dashboard.noLimit')}</div>
                )}
            </div>
            <div style={{ textAlign: 'right', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                {timeAgo(agent.last_active_at, t)}
            </div>
        </div>
    );
}

/* ────── Activity Feed ────── */

function getActivityIcon(actionType: string) {
    switch (actionType) {
        case 'chat_reply': return { icon: Icons.messageSquare, color: '#3b82f6' };
        case 'tool_call': return { icon: Icons.tool, color: '#8b5cf6' };
        case 'file_written': return { icon: Icons.fileText, color: '#f59e0b' };
        case 'schedule_run': return { icon: Icons.schedule, color: '#06b6d4' };
        case 'heartbeat': return { icon: Icons.heartbeat, color: '#22c55e' };
        default: return { icon: Icons.activity, color: 'var(--text-tertiary)' };
    }
}

function ActivityFeed({ activities, agents }: { activities: any[]; agents: Agent[] }) {
    const { t } = useTranslation();
    const agentMap = new Map(agents.map(a => [a.id, a]));

    if (activities.length === 0) {
        return <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-tertiary)', fontSize: '13px' }}>{t('dashboard.noActivity')}</div>;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
            {activities.map((act, i) => {
                const agent = agentMap.get(act.agent_id);
                const { icon, color } = getActivityIcon(act.action_type || '');
                return (
                    <div key={act.id || i} style={{
                        display: 'flex', gap: '10px', padding: '8px 12px',
                        fontSize: '13px', alignItems: 'flex-start',
                        borderRadius: 'var(--radius-sm)', transition: 'background 0.12s',
                    }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                    >
                        <div style={{
                            width: '28px', height: '28px', borderRadius: 'var(--radius-md)',
                            background: `${color}15`, display: 'flex',
                            alignItems: 'center', justifyContent: 'center',
                            flexShrink: 0, color,
                        }}>{icon}</div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                                <span style={{
                                    fontSize: '11px', padding: '1px 6px', borderRadius: 'var(--radius-sm)',
                                    background: 'var(--bg-tertiary)', color: 'var(--text-secondary)', fontWeight: 500,
                                }}>{agent?.name || act.agent_id?.slice(0, 6)}</span>
                                <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{act.summary}</span>
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{timeAgo(act.created_at, t)}</div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

/* ────── Section Card ────── */

function SectionCard({ title, icon, extra, children, noPadding }: {
    title: string; icon?: React.ReactNode; extra?: React.ReactNode;
    children: React.ReactNode; noPadding?: boolean;
}) {
    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)', overflow: 'hidden',
        }}>
            <div style={{
                padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
                <h3 style={{
                    margin: 0, fontSize: '13px', fontWeight: 500,
                    display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)',
                }}>
                    {icon && <span style={{ display: 'flex', opacity: 0.6 }}>{icon}</span>}
                    {title}
                </h3>
                {extra}
            </div>
            <div style={noPadding ? undefined : { padding: '12px 16px' }}>{children}</div>
        </div>
    );
}

/* ────── Health Badge ────── */

function HealthBadge({ label, healthy, detail }: { label: string; healthy: boolean; detail?: string }) {
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '8px 10px', borderRadius: 'var(--radius-md)', background: 'var(--bg-tertiary)',
        }}>
            <span style={{
                width: '7px', height: '7px', borderRadius: '50%',
                background: healthy ? 'var(--success)' : 'var(--error)',
                boxShadow: healthy ? '0 0 6px rgba(34,197,94,0.4)' : '0 0 6px rgba(239,68,68,0.4)',
            }} />
            <div>
                <div style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-primary)' }}>{label}</div>
                {detail && <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>{detail}</div>}
            </div>
        </div>
    );
}

/* ────── Quick Action ────── */

function QuickAction({ icon, label, onClick, accent }: {
    icon: React.ReactNode; label: string; onClick: () => void; accent?: boolean;
}) {
    return (
        <button onClick={onClick} style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '8px 12px', borderRadius: 'var(--radius-md)',
            background: accent ? 'var(--accent-subtle)' : 'var(--bg-tertiary)',
            border: `1px solid ${accent ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
            color: accent ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontSize: '11px', fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s', width: '100%',
        }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = accent ? 'var(--accent-subtle)' : 'var(--bg-tertiary)'; }}
        >
            <span style={{ display: 'flex' }}>{icon}</span>{label}
        </button>
    );
}

/* ════════════════════════════════════════════════════════
   Main Dashboard
   ════════════════════════════════════════════════════════ */

export default function Dashboard() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const currentTenant = localStorage.getItem('current_tenant_id') || '';

    const { data: agents = [], isLoading } = useQuery({
        queryKey: ['agents', currentTenant],
        queryFn: () => agentApi.list(currentTenant || undefined),
        refetchInterval: 15000,
    });

    const { data: enterpriseStats } = useQuery({
        queryKey: ['enterprise-stats', currentTenant],
        queryFn: () => fetchJson<any>(`/enterprise/stats${currentTenant ? `?tenant_id=${currentTenant}` : ''}`).catch(() => null),
        refetchInterval: 30000,
    });

    // Chart range toggles
    const [activityRange, setActivityRange] = useState<'day' | 'week' | 'month'>('week');
    const [tokenRange, setTokenRange] = useState<'week' | 'month' | 'year'>('month');
    const [convRange, setConvRange] = useState(14);
    const [tokenByAgentMode, setTokenByAgentMode] = useState<'day' | 'month'>('day');
    const [deliveryRange, setDeliveryRange] = useState(30);

    // Daily token usage time-series
    const tokenDays = tokenRange === 'week' ? 7 : tokenRange === 'month' ? 30 : 365;
    const { data: tokenTimeSeries = [] } = useQuery({
        queryKey: ['daily-token-usage', currentTenant, tokenDays],
        queryFn: () => enterpriseApi.dailyTokenUsage(tokenDays),
        refetchInterval: 60000,
    });

    // LLM models for distribution chart
    const { data: llmModels = [] } = useQuery({
        queryKey: ['llm-models'],
        queryFn: () => enterpriseApi.llmModels().catch(() => []),
        staleTime: 300000,
    });

    const [allTasks, setAllTasks] = useState<Task[]>([]);
    const [allActivities, setAllActivities] = useState<any[]>([]);
    const [agentActivities, setAgentActivities] = useState<Record<string, any[]>>({});
    const [allDailyStats, setAllDailyStats] = useState<any[]>([]);

    useEffect(() => {
        if (agents.length === 0) return;
        const fetchData = async () => {
            try {
                const taskResults = await Promise.allSettled(agents.map(a => taskApi.list(a.id)));
                const tasks: Task[] = [];
                taskResults.forEach(r => { if (r.status === 'fulfilled') tasks.push(...r.value); });
                setAllTasks(tasks);
            } catch (e) { console.error('Failed to fetch tasks:', e); }
            try {
                const actResults = await Promise.allSettled(agents.map(a => activityApi.list(a.id, 2000, 90)));
                const activities: any[] = [];
                const perAgent: Record<string, any[]> = {};
                actResults.forEach((r, i) => {
                    if (r.status === 'fulfilled') {
                        perAgent[agents[i].id] = r.value;
                        activities.push(...r.value.map((v: any) => ({ ...v, agent_id: agents[i].id })));
                    }
                });
                activities.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                setAllActivities(activities);
                setAgentActivities(perAgent);
            } catch (e) { console.error('Failed to fetch activities:', e); }
            // Fetch daily aggregated stats (90 days to cover all chart ranges)
            try {
                const statsResults = await Promise.allSettled(
                    agents.map(a => activityApi.dailyStats(a.id, 90)),
                );
                const merged: any[] = [];
                statsResults.forEach((r, i) => {
                    if (r.status === 'fulfilled') {
                        merged.push(...r.value.map((v: any) => ({ ...v, agent_id: agents[i].id })));
                    }
                });
                setAllDailyStats(merged);
            } catch (e) { console.error('Failed to fetch daily stats:', e); }
        };
        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, [agents.map(a => a.id).join(',')]);

    const tasksByAgent = useMemo(() => {
        const map = new Map<string, Task[]>();
        allTasks.forEach(t => { if (!map.has(t.agent_id)) map.set(t.agent_id, []); map.get(t.agent_id)!.push(t); });
        return map;
    }, [allTasks]);

    // Metrics
    const totalAgents = agents.length;
    const activeAgents = agents.filter(a => a.status === 'running' || a.status === 'idle').length;
    const errorAgents = agents.filter(a => a.status === 'error').length;
    const pendingTasks = allTasks.filter(t => t.status === 'pending' || t.status === 'doing').length;
    const completedToday = allTasks.filter(t => {
        if (t.status !== 'done' || !t.completed_at) return false;
        return new Date(t.completed_at).toDateString() === new Date().toDateString();
    }).length;
    const totalTokensToday = agents.reduce((s, a) => s + (a.tokens_used_today || 0), 0);
    const totalTokensMonth = agents.reduce((s, a) => s + (a.tokens_used_month || 0), 0);
    const recentlyActive = agents.filter(a => a.last_active_at && Date.now() - new Date(a.last_active_at).getTime() < 3600000).length;
    const heartbeatAgents = agents.filter(a => a.heartbeat_enabled).length;
    const isAdmin = user?.role === 'platform_admin' || user?.role === 'org_admin';

    const hour = new Date().getHours();
    const greeting = hour < 6 ? '🌙 ' + t('dashboard.greeting.lateNight') : hour < 12 ? '☀️ ' + t('dashboard.greeting.morning') : hour < 18 ? '🌤️ ' + t('dashboard.greeting.afternoon') : '🌙 ' + t('dashboard.greeting.evening');

    return (
        <div>
            {/* ── Header ── */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div>
                    <h1 style={{ fontSize: '20px', fontWeight: 600, margin: 0, marginBottom: '2px', letterSpacing: '-0.02em' }}>{greeting}</h1>
                    <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', margin: 0 }}>
                        {t('dashboard.totalAgents', { count: agents.length })}
                        {enterpriseStats && (
                            <span> · {t('dashboard.stats.activeUsers', '活跃用户')}: <strong style={{ color: 'var(--text-secondary)' }}>{enterpriseStats.total_active_users ?? '-'}</strong></span>
                        )}
                        {enterpriseStats?.pending_approvals > 0 && (
                            <span style={{ color: 'var(--warning)', marginLeft: '8px' }}>· {enterpriseStats.pending_approvals} {t('dashboard.pendingApprovals', '待审批')}</span>
                        )}
                    </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button className="btn btn-ghost" onClick={() => navigate('/plaza')} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                        {Icons.chart} {t('dashboard.action.plaza', '广场')}
                    </button>
                    {isAdmin && (
                        <button className="btn btn-ghost" onClick={() => navigate('/enterprise')} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                            {Icons.settings} {t('dashboard.action.enterprise', '企业管理')}
                        </button>
                    )}
                    <button className="btn btn-primary" onClick={() => navigate('/agents/new')} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {Icons.plus} {t('nav.newAgent')}
                    </button>
                </div>
            </div>

            {isLoading ? (
                <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-tertiary)', fontSize: '13px' }}>{t('common.loading')}</div>
            ) : agents.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '80px' }}>
                    <div style={{ color: 'var(--text-tertiary)', marginBottom: '4px', fontSize: '32px' }}>{Icons.bot}</div>
                    <div style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '14px' }}>{t('dashboard.noAgents')}</div>
                    <button className="btn btn-primary" onClick={() => navigate('/agents/new')}>{Icons.plus} {t('nav.newAgent')}</button>
                </div>
            ) : (
                <>
                    {/* ── KPI Row ── */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '16px' }}>
                        <KpiCard icon={Icons.bot} label={t('dashboard.stats.agents', '数字员工')} value={totalAgents} sub={t('dashboard.stats.online', { count: activeAgents })} accent={activeAgents > 0 ? 'var(--success)' : undefined} />
                        <KpiCard icon={Icons.tasks} label={t('dashboard.stats.activeTasks', '进行中任务')} value={pendingTasks} sub={t('dashboard.stats.completedToday', { count: completedToday })} />
                        <KpiCard icon={Icons.zap} label={t('dashboard.stats.todayTokens', '今日 Token')} value={formatTokens(totalTokensToday)} sub={`${t('dashboard.stats.monthTokens', '本月')}: ${formatTokens(totalTokensMonth)}`} />
                        <KpiCard icon={Icons.heartbeat} label={t('dashboard.stats.heartbeat', '心跳监控')} value={heartbeatAgents} sub={`${heartbeatAgents} / ${totalAgents} ${t('dashboard.stats.enabled', '已启用')}`} accent={heartbeatAgents > 0 ? 'var(--success)' : undefined} />
                    </div>

                    {/* ── Two-Column Layout: Main + Sidebar ── */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: '16px', alignItems: 'start' }}>

                        {/* ═══ LEFT: Agent List + Activity ═══ */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', minWidth: 0 }}>
                            {/* Agent List */}
                            <SectionCard
                                title={t('dashboard.agentList', '数字员工列表')}
                                icon={Icons.bot}
                                extra={<span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{activeAgents} / {totalAgents} {t('dashboard.active', '活跃')}</span>}
                                noPadding
                            >
                                <div style={{
                                    display: 'grid', gridTemplateColumns: '220px 100px 1fr 130px 90px',
                                    padding: '10px 16px', fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 500,
                                    textTransform: 'uppercase' as const, letterSpacing: '0.05em',
                                    borderBottom: '1px solid var(--border-subtle)',
                                }}>
                                    <span>{t('dashboard.table.agent')}</span>
                                    <span>{t('dashboard.table.owner')}</span>
                                    <span>{t('dashboard.table.latestActivity')}</span>
                                    <span>Token</span>
                                    <span style={{ textAlign: 'right' }}>{t('dashboard.table.active')}</span>
                                </div>
                                <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
                                    {agents.sort((a, b) => {
                                        const aa = a.status === 'running' || a.status === 'idle' ? 1 : 0;
                                        const bb = b.status === 'running' || b.status === 'idle' ? 1 : 0;
                                        if (aa !== bb) return bb - aa;
                                        return (b.last_active_at ? new Date(b.last_active_at).getTime() : 0) - (a.last_active_at ? new Date(a.last_active_at).getTime() : 0);
                                    }).map(agent => (
                                        <AgentRow key={agent.id} agent={agent}
                                            tasks={tasksByAgent.get(agent.id) || []}
                                            recentActivity={agentActivities[agent.id] || []}
                                        />
                                    ))}
                                </div>
                            </SectionCard>

                            {/* Activity Feed */}
                            <SectionCard
                                title={t('dashboard.globalActivity', '全局活动')}
                                icon={Icons.activity}
                                extra={<span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{t('dashboard.recentCount', { count: 20 })}</span>}
                            >
                                <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
                                    <ActivityFeed activities={allActivities} agents={agents} />
                                </div>
                            </SectionCard>

                            {/* Error Banner */}
                            {errorAgents > 0 && (
                                <div style={{
                                    padding: '12px 16px', background: 'var(--error-subtle)',
                                    border: '1px solid rgba(239,68,68,0.2)', borderRadius: 'var(--radius-lg)',
                                    display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: 'var(--error)',
                                }}>
                                    <span style={{ display: 'flex' }}>{Icons.alertTriangle}</span>
                                    <span>{t('dashboard.errorAlert', '{{count}} 个数字员工处于异常状态', { count: errorAgents })}</span>
                                    <button className="btn btn-ghost" style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--error)', padding: '4px 8px', height: 'auto' }} onClick={() => navigate('/agents')}>
                                        {t('dashboard.viewDetails', '查看详情')} →
                                    </button>
                                </div>
                            )}

                            {/* ── Analytics Charts ── */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                {/* 24h Activity Trend */}
                                <SectionCard title={t('dashboard.hourlyTrend', '24h 活跃趋势')} icon={Icons.activity}>
                                    <ActivityTrendChart activities={allActivities} />
                                </SectionCard>

                                {/* Conversation Stats */}
                                <SectionCard title={t('dashboard.conversationStats', '用户对话统计')} icon={Icons.messageSquare}
                                    extra={<RangeTabs value={String(convRange)} onChange={v => setConvRange(Number(v))} options={[
                                        { key: '7', label: '7d' }, { key: '14', label: '14d' }, { key: '30', label: '30d' },
                                    ]} />}>
                                    <ConversationStatsChart activities={allActivities} range={convRange} />
                                </SectionCard>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                {/* Token Consumption */}
                                <SectionCard title={t('dashboard.tokenConsumption', '每日 Token 消耗')} icon={Icons.zap}
                                    extra={<RangeTabs value={tokenRange} onChange={v => setTokenRange(v as any)} options={[
                                        { key: 'week', label: t('dashboard.rangeWeek', '周') },
                                        { key: 'month', label: t('dashboard.rangeMonth', '月') },
                                        { key: 'year', label: t('dashboard.rangeYear', '年') },
                                    ]} />}>
                                    <TokenConsumptionChart data={tokenTimeSeries} />
                                </SectionCard>

                                {/* Agent Activity Rank */}
                                <SectionCard title={t('dashboard.agentActivity', '数字员工活跃度')} icon={Icons.users}
                                    extra={<RangeTabs value={activityRange} onChange={v => setActivityRange(v as any)} options={[
                                        { key: 'day', label: t('dashboard.rangeDay', '日') },
                                        { key: 'week', label: t('dashboard.rangeWeek', '周') },
                                        { key: 'month', label: t('dashboard.rangeMonth', '月') },
                                    ]} />}>
                                    <AgentActivityRankChart agents={agents} activities={allActivities} timeRange={activityRange} />
                                </SectionCard>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                {/* Token per Agent */}
                                <SectionCard title={t('dashboard.tokenByAgent', 'Token 消耗分布')} icon={Icons.zap}
                                    extra={<RangeTabs value={tokenByAgentMode} onChange={v => setTokenByAgentMode(v as any)} options={[
                                        { key: 'day', label: t('dashboard.rangeDay', '日') },
                                        { key: 'month', label: t('dashboard.rangeMonth', '月') },
                                    ]} />}>
                                    <TokenByAgentChart agents={agents} mode={tokenByAgentMode} />
                                </SectionCard>

                                {/* Token Today vs Month */}
                                <SectionCard title={t('dashboard.tokenMonthTrend', '月度 Token 分布')} icon={Icons.zap}>
                                    <TokenMonthChart agents={agents} />
                                </SectionCard>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                {/* Model Distribution */}
                                <SectionCard title={t('dashboard.modelDistribution', '模型分布')} icon={Icons.bot}>
                                    <ModelDistributionChart agents={agents} models={llmModels} />
                                </SectionCard>

                                {/* Tool Call Statistics */}
                                <SectionCard title={t('dashboard.toolStats', '工具调用统计')} icon={Icons.tool}>
                                    <ToolStatsChart activities={allActivities} />
                                </SectionCard>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                {/* File Delivery Trend */}
                                <SectionCard title={t('dashboard.fileDelivery', '文件交付趋势')} icon={Icons.fileText}
                                    extra={<RangeTabs value={String(deliveryRange)} onChange={v => setDeliveryRange(Number(v))} options={[
                                        { key: '7', label: '7d' }, { key: '14', label: '14d' }, { key: '30', label: '30d' },
                                    ]} />}>
                                    <FileDeliveryChart activities={allActivities} dailyStats={allDailyStats} range={deliveryRange} />
                                </SectionCard>

                                {/* Task Pipeline */}
                                <SectionCard title={t('dashboard.taskPipeline', '任务状态分布')} icon={Icons.tasks}>
                                    <TaskPipeline tasks={allTasks} />
                                </SectionCard>
                            </div>
                        </div>

                        {/* ═══ RIGHT: Sidebar Charts ═══ */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', position: 'sticky', top: '16px' }}>

                            {/* Status Distribution */}
                            <SidebarChart title={t('dashboard.agentStatus', '状态分布')}>
                                <StatusDonut agents={agents} />
                            </SidebarChart>

                            {/* Token Top 5 */}
                            <SidebarChart title={t('dashboard.tokenRank', 'Token 排行')}>
                                <TokenTopBar agents={agents} />
                            </SidebarChart>

                            {/* Task Pipeline */}
                            <SidebarChart title={t('dashboard.taskPipeline', '任务流水线')}>
                                <TaskPipeline tasks={allTasks} />
                            </SidebarChart>

                            {/* Activity Types */}
                            <SidebarChart title={t('dashboard.activityTypes', '活动类型')}>
                                <ActivityTypePie activities={allActivities} />
                            </SidebarChart>

                            {/* System Health */}
                            <SidebarChart title={t('dashboard.systemHealth', '系统健康')}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                    <HealthBadge label={t('dashboard.health.agents', '数字员工')} healthy={errorAgents === 0}
                                        detail={errorAgents === 0 ? t('dashboard.health.allGood', '全部正常') : t('dashboard.health.hasErrors', { count: errorAgents })} />
                                    <HealthBadge label={t('dashboard.health.tasks', '任务队列')} healthy={pendingTasks < 50}
                                        detail={pendingTasks < 50 ? t('dashboard.health.queueOk', '正常') : t('dashboard.health.queueHigh', '较多')} />
                                    <HealthBadge label={t('dashboard.health.heartbeat', '心跳')} healthy={heartbeatAgents > 0}
                                        detail={heartbeatAgents > 0 ? `${heartbeatAgents} ${t('dashboard.health.monitoring', '监控中')}` : t('dashboard.health.noMonitor', '未启用')} />
                                </div>
                            </SidebarChart>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
