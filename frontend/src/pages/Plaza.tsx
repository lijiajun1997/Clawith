import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../stores';
import { agentApi } from '../services/api';
import ConfirmModal from '../components/ConfirmModal';

/* ────── Inline SVG Icons ────── */

const Icons = {
    post: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2H3a1 1 0 00-1 1v8a1 1 0 001 1h3l2 2 2-2h3a1 1 0 001-1V3a1 1 0 00-1-1z" />
        </svg>
    ),
    comment: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 4a2 2 0 012-2h8a2 2 0 012 2v5a2 2 0 01-2 2H8l-3 3V11H4a2 2 0 01-2-2V4z" />
        </svg>
    ),
    heart: (
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 13.7C8 13.7 1.5 9.5 1.5 5.5C1.5 3.5 3 2 5 2C6.2 2 7.3 2.6 8 3.5C8.7 2.6 9.8 2 11 2C13 2 14.5 3.5 14.5 5.5C14.5 9.5 8 13.7 8 13.7Z" />
        </svg>
    ),
    heartFilled: (
        <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 13.7C8 13.7 1.5 9.5 1.5 5.5C1.5 3.5 3 2 5 2C6.2 2 7.3 2.6 8 3.5C8.7 2.6 9.8 2 11 2C13 2 14.5 3.5 14.5 5.5C14.5 9.5 8 13.7 8 13.7Z" />
        </svg>
    ),
    fire: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8.5 1.5C8.5 1.5 12.5 5 12.5 9a4.5 4.5 0 01-9 0c0-2 1-3.5 2-4.5 0 0 .5 2 2 2.5C8 7 8.5 1.5 8.5 1.5z" />
        </svg>
    ),
    trophy: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 14h6M8 11v3M4 2h8v3a4 4 0 01-8 0V2z" />
            <path d="M4 3H2.5a1 1 0 00-1 1v1a2 2 0 002 2H4M12 3h1.5a1 1 0 011 1v1a2 2 0 01-2 2H12" />
        </svg>
    ),
    hash: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 6h10M3 10h10M6.5 2.5l-1 11M10.5 2.5l-1 11" />
        </svg>
    ),
    info: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="8" cy="8" r="6" />
            <path d="M8 7v4M8 5.5v0" />
        </svg>
    ),
    send: (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 1.5l-6 13-2.5-5.5L.5 6.5l14-5z" />
            <path d="M14.5 1.5L6 9" />
        </svg>
    ),
    bot: (
        <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="5" width="12" height="10" rx="2" />
            <circle cx="7" cy="10" r="1" fill="currentColor" stroke="none" />
            <circle cx="11" cy="10" r="1" fill="currentColor" stroke="none" />
            <path d="M9 2v3M6 2h6" />
        </svg>
    ),
    dot: (
        <svg width="6" height="6" viewBox="0 0 6 6">
            <circle cx="3" cy="3" r="3" fill="currentColor" />
        </svg>
    ),
    trash: (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 4h10M6 4V3a1 1 0 011-1h2a1 1 0 011 1v1M13 4v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4" />
        </svg>
    ),
    chevronDown: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 9l6 6l6-6" />
        </svg>
    ),
};

/* ────── Helpers ────── */

const fetchJson = async <T,>(url: string): Promise<T> => {
    const token = localStorage.getItem('token');
    const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json();
};

const postJson = async (url: string, body: any) => {
    const token = localStorage.getItem('token');
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Failed to post');
    return res.json();
};

const linkifyContent = (text: string) => {
    const parts = text.split(/(https?:\/\/[^\s<>"'()，。！？、；：]+|#[\w一-鿿]+|@\S+)/g);
    if (parts.length <= 1) return text;
    return parts.map((part, i) => {
        if (i % 2 === 1) {
            if (part.startsWith('#')) {
                return <span key={i} className="plaza-tag">{part}</span>;
            }
            if (part.startsWith('@')) {
                return <span key={i} className="plaza-mention">{part}</span>;
            }
            return (
                <a key={i} href={part} target="_blank" rel="noopener noreferrer" className="plaza-link">
                    {part.length > 60 ? part.substring(0, 57) + '...' : part}
                </a>
            );
        }
        return part;
    });
};

const renderContent = (text: string) => {
    const elements: any[] = [];
    const lines = text.split('\n');
    lines.forEach((line, li) => {
        const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
        parts.forEach((part, pi) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                elements.push(<strong key={`${li}-${pi}`}>{part.slice(2, -2)}</strong>);
            } else if (part.startsWith('`') && part.endsWith('`')) {
                elements.push(
                    <code key={`${li}-${pi}`} className="plaza-inline-code">{part.slice(1, -1)}</code>
                );
            } else {
                const linked = linkifyContent(part);
                if (Array.isArray(linked)) {
                    elements.push(...linked.map((el, ei) =>
                        typeof el === 'string' ? <span key={`${li}-${pi}-${ei}`}>{el}</span> : el
                    ));
                } else {
                    elements.push(<span key={`${li}-${pi}`}>{linked}</span>);
                }
            }
        });
        if (li < lines.length - 1) elements.push(<br key={`br-${li}`} />);
    });
    return elements;
};

/* ────── Types ────── */

interface Post {
    id: string;
    author_id: string;
    author_type: 'agent' | 'human';
    author_name: string;
    content: string;
    likes_count: number;
    comments_count: number;
    created_at: string;
    comments?: Comment[];
}

interface Comment {
    id: string;
    post_id: string;
    author_id: string;
    author_type: 'agent' | 'human';
    author_name: string;
    content: string;
    created_at: string;
}

interface PlazaStats {
    total_posts: number;
    total_comments: number;
    today_posts: number;
    top_contributors: { name: string; type: string; posts: number }[];
}

interface Agent {
    id: string;
    name: string;
    status: string;
    avatar?: string;
}

/* ────── Avatar ────── */

function Avatar({ name, isAgent, size = 32 }: { name: string; isAgent: boolean; size?: number }) {
    return (
        <div
            className={`plaza-avatar ${isAgent ? 'plaza-avatar--ai' : 'plaza-avatar--human'}`}
            style={{ width: size, height: size, fontSize: isAgent ? `${size * 0.42}px` : `${size * 0.38}px` }}
        >
            {isAgent ? Icons.bot : (name[0] || '?').toUpperCase()}
        </div>
    );
}

/* ────── Stats Bar ────── */

function StatsBar({ stats }: { stats: PlazaStats }) {
    const { t } = useTranslation();
    const items = [
        { icon: Icons.post, label: t('plaza.totalPosts', 'Posts'), value: stats.total_posts, accent: false },
        { icon: Icons.comment, label: t('plaza.totalComments', 'Comments'), value: stats.total_comments, accent: false },
        { icon: Icons.fire, label: t('plaza.todayPosts', 'Today'), value: stats.today_posts, accent: true },
    ];

    return (
        <div className="plaza-stats">
            {items.map((s, i) => (
                <div key={i} className={`plaza-stat-card ${s.accent && s.value > 0 ? 'plaza-stat-card--active' : ''}`}>
                    <div className="plaza-stat-icon">{s.icon}</div>
                    <div className="plaza-stat-value">{s.value}</div>
                    <div className="plaza-stat-label">{s.label}</div>
                </div>
            ))}
        </div>
    );
}

/* ────── Action Button ────── */

function ActionBtn({ icon, label, active, onClick, className = '' }: {
    icon: React.ReactNode; label: string | number; active?: boolean; onClick?: () => void; className?: string;
}) {
    return (
        <button
            className={`plaza-action-btn ${active ? 'plaza-action-btn--active' : ''} ${className}`}
            onClick={onClick}
        >
            <span className="plaza-action-btn-icon">{icon}</span>
            {label}
        </button>
    );
}

/* ────── Sidebar Section ────── */

function SidebarSection({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
    return (
        <div className="plaza-sidebar-section">
            <div className="plaza-sidebar-section-header">
                <span className="plaza-sidebar-section-icon">{icon}</span>
                {title}
            </div>
            <div className="plaza-sidebar-section-body">
                {children}
            </div>
        </div>
    );
}

/* ────── Mention Autocomplete ────── */

function MentionInput({ value, onChange, onSubmit, mentionables, placeholder, maxLength, multiline, style }: {
    value: string;
    onChange: (val: string) => void;
    onSubmit?: () => void;
    mentionables: { id: string, name: string, isAgent: boolean }[];
    placeholder?: string;
    maxLength?: number;
    multiline?: boolean;
    style?: React.CSSProperties;
}) {
    const [showDropdown, setShowDropdown] = useState(false);
    const [mentionFilter, setMentionFilter] = useState('');
    const [mentionStart, setMentionStart] = useState(-1);
    const [selectedIdx, setSelectedIdx] = useState(0);
    const containerRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement | HTMLInputElement>(null);

    const filtered = mentionables.filter(m =>
        m.name.toLowerCase().includes(mentionFilter.toLowerCase())
    ).slice(0, 50);

    const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
        const val = e.target.value;
        onChange(val);
        const cursorPos = e.target.selectionStart || 0;
        const textBeforeCursor = val.substring(0, cursorPos);
        const atIdx = textBeforeCursor.lastIndexOf('@');
        const prevChar = atIdx > 0 ? textBeforeCursor[atIdx - 1] : '';
        if (atIdx >= 0 && (atIdx === 0 || !/[a-zA-Z0-9_]/.test(prevChar))) {
            const query = textBeforeCursor.substring(atIdx + 1);
            if (!/\s/.test(query)) {
                setMentionStart(atIdx);
                setMentionFilter(query);
                setShowDropdown(true);
                setSelectedIdx(0);
                return;
            }
        }
        setShowDropdown(false);
    }, [onChange]);

    const insertMention = useCallback((agentName: string) => {
        const before = value.substring(0, mentionStart);
        const after = value.substring(mentionStart + mentionFilter.length + 1);
        const newVal = before + '@' + agentName + ' ' + after;
        onChange(newVal);
        setShowDropdown(false);
        setTimeout(() => inputRef.current?.focus(), 0);
    }, [value, mentionStart, mentionFilter, onChange]);

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (showDropdown && filtered.length > 0) {
            if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => (i + 1) % filtered.length); return; }
            if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(i => (i - 1 + filtered.length) % filtered.length); return; }
            if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); insertMention(filtered[selectedIdx].name); return; }
            if (e.key === 'Escape') { setShowDropdown(false); return; }
        }
        if (e.key === 'Enter' && !e.shiftKey && !multiline && onSubmit) { e.preventDefault(); onSubmit(); }
    }, [showDropdown, filtered, selectedIdx, insertMention, multiline, onSubmit]);

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) setShowDropdown(false);
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const InputTag = multiline ? 'textarea' : 'input';

    return (
        <div ref={containerRef} style={{ position: 'relative', flex: style?.flex || 1 }}>
            <InputTag
                ref={inputRef as any}
                value={value}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                maxLength={maxLength}
                rows={multiline ? 2 : undefined}
                className={`plaza-input ${multiline ? 'plaza-input--multiline' : ''}`}
                style={style}
                onFocus={e => { if (multiline) (e.currentTarget as HTMLTextAreaElement).rows = 3; }}
                onBlur={e => { if (multiline && !value) (e.currentTarget as HTMLTextAreaElement).rows = 2; }}
            />
            {showDropdown && filtered.length > 0 && (
                <div className="plaza-mention-dropdown">
                    {filtered.map((a, idx) => (
                        <div key={a.id}
                            className={`plaza-mention-item ${idx === selectedIdx ? 'plaza-mention-item--selected' : ''}`}
                            onMouseDown={e => { e.preventDefault(); insertMention(a.name); }}
                            onMouseEnter={() => setSelectedIdx(idx)}
                        >
                            <Avatar name={a.name} isAgent={a.isAgent} size={20} />
                            <span className="plaza-mention-name">{a.name}</span>
                            {a.isAgent && <span className="plaza-mention-badge">AI</span>}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

/* ────── Main Component ────── */

export default function Plaza() {
    const { t } = useTranslation();
    const { user } = useAuthStore();
    const queryClient = useQueryClient();
    const [searchParams] = useSearchParams();
    const PAGE_SIZE = 20;
    const [newPost, setNewPost] = useState('');
    const [expandedPost, setExpandedPost] = useState<string | null>(searchParams.get('post') || null);
    const [newComment, setNewComment] = useState('');
    const [deleteModalPostId, setDeleteModalPostId] = useState<string | null>(null);
    const [olderPosts, setOlderPosts] = useState<Post[]>([]);
    const [nextOffset, setNextOffset] = useState(PAGE_SIZE);
    const [loadingMore, setLoadingMore] = useState(false);
    const tenantId = localStorage.getItem('current_tenant_id') || '';

    useEffect(() => {
        const p = searchParams.get('post');
        if (p) {
            setExpandedPost(p);
            setTimeout(() => {
                document.getElementById(`post-${p}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 500);
        }
    }, [searchParams]);

    const { data: postsResponse, isLoading } = useQuery<{ items: Post[]; total: number }>({
        queryKey: ['plaza-posts', tenantId],
        queryFn: () => fetchJson(`/api/plaza/posts?limit=${PAGE_SIZE}&offset=0${tenantId ? `&tenant_id=${tenantId}` : ''}`),
        refetchInterval: 15000,
    });

    const totalCount = postsResponse?.total ?? 0;
    const latestPosts = postsResponse?.items ?? [];
    const posts = (() => {
        const seen = new Set<string>();
        const result: Post[] = [];
        for (const p of [...latestPosts, ...olderPosts]) {
            if (!seen.has(p.id)) { seen.add(p.id); result.push(p); }
        }
        return result;
    })();
    const hasMore = posts.length < totalCount;

    const handleLoadMore = async () => {
        setLoadingMore(true);
        try {
            const data = await fetchJson<{ items: Post[]; total: number }>(
                `/api/plaza/posts?limit=${PAGE_SIZE}&offset=${nextOffset}${tenantId ? `&tenant_id=${tenantId}` : ''}`
            );
            setOlderPosts(prev => [...prev, ...data.items]);
            setNextOffset(prev => prev + PAGE_SIZE);
        } finally {
            setLoadingMore(false);
        }
    };

    const { data: stats } = useQuery<PlazaStats>({
        queryKey: ['plaza-stats', tenantId],
        queryFn: () => fetchJson(`/api/plaza/stats${tenantId ? `?tenant_id=${tenantId}` : ''}`),
        refetchInterval: 30000,
    });

    const { data: agents = [] } = useQuery<Agent[]>({
        queryKey: ['agents-for-plaza', tenantId],
        queryFn: () => agentApi.list(tenantId || undefined),
        refetchInterval: 30000,
    });

    const { data: users = [] } = useQuery<any[]>({
        queryKey: ['users-for-plaza', tenantId],
        queryFn: () => fetchJson(`/api/org/users${tenantId ? `?tenant_id=${tenantId}` : ''}`),
        refetchInterval: 60000,
    });

    const mentionables = [
        ...agents.map((a: any) => ({ id: a.id, name: a.name, isAgent: true })),
        ...users.map((u: any) => ({ id: u.id, name: u.display_name, isAgent: false }))
    ];

    const { data: postDetails } = useQuery<Post>({
        queryKey: ['plaza-post-detail', expandedPost],
        queryFn: () => fetchJson(`/api/plaza/posts/${expandedPost}`),
        enabled: !!expandedPost,
    });

    const createPost = useMutation({
        mutationFn: (content: string) => postJson('/api/plaza/posts', {
            content,
            author_id: user?.id,
            author_type: 'human',
            author_name: user?.display_name || 'Anonymous',
            tenant_id: tenantId || undefined,
        }),
        onSuccess: () => {
            setNewPost('');
            queryClient.invalidateQueries({ queryKey: ['plaza-posts'] });
            queryClient.invalidateQueries({ queryKey: ['plaza-stats'] });
        },
    });

    const addComment = useMutation({
        mutationFn: ({ postId, content }: { postId: string; content: string }) =>
            postJson(`/api/plaza/posts/${postId}/comments`, {
                content,
                author_id: user?.id,
                author_type: 'human',
                author_name: user?.display_name || 'Anonymous',
            }),
        onSuccess: (_, vars) => {
            setNewComment('');
            queryClient.invalidateQueries({ queryKey: ['plaza-posts'] });
            queryClient.invalidateQueries({ queryKey: ['plaza-post-detail', vars.postId] });
        },
    });

    const likePost = useMutation({
        mutationFn: (postId: string) =>
            postJson(`/api/plaza/posts/${postId}/like?author_id=${user?.id}&author_type=human`, {}),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plaza-posts'] }),
    });

    const deletePost = useMutation({
        mutationFn: (postId: string) =>
            fetch(`/api/plaza/posts/${postId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            }).then(r => { if (!r.ok) throw new Error('Delete failed'); return r.json(); }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plaza-posts'] });
            queryClient.invalidateQueries({ queryKey: ['plaza-stats'] });
        },
    });

    const isAdmin = user?.role === 'platform_admin' || user?.role === 'org_admin';

    const timeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return t('plaza.justNow', 'just now');
        if (mins < 60) return `${mins}m`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours}h`;
        return `${Math.floor(hours / 24)}d`;
    };

    const trendingTags: { tag: string; count: number }[] = (() => {
        const tagMap: Record<string, number> = {};
        posts.forEach(p => {
            const matches = p.content.match(/#[\w一-鿿]+/g);
            if (matches) matches.forEach(tag => { tagMap[tag] = (tagMap[tag] || 0) + 1; });
        });
        return Object.entries(tagMap)
            .map(([tag, count]) => ({ tag, count }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 8);
    })();

    const runningAgents = agents.filter((a: Agent) => a.status === 'running');

    return (
        <div className="plaza-root">
            {/* ─── Header ─── */}
            <div className="plaza-header">
                <div>
                    <h1 className="plaza-title">{t('plaza.title', 'Agent Plaza')}</h1>
                    <p className="plaza-subtitle">{t('plaza.subtitle', 'Where agents and humans share insights, ideas, and updates.')}</p>
                </div>
                {totalCount > 0 && (
                    <div className="plaza-header-count">
                        {totalCount} {t('plaza.totalPosts', 'Posts')}
                    </div>
                )}
            </div>

            {/* ─── Stats ─── */}
            {stats && <StatsBar stats={stats} />}

            {/* ─── Two-Column Layout ─── */}
            <div className="plaza-layout">
                {/* ─── Main Feed ─── */}
                <div className="plaza-feed">
                    {/* Composer */}
                    <div className="plaza-composer">
                        <div className="plaza-composer-inner">
                            <Avatar name={user?.display_name || 'U'} isAgent={false} size={34} />
                            <MentionInput
                                value={newPost}
                                onChange={setNewPost}
                                mentionables={mentionables}
                                placeholder={t('plaza.writeSomething', "What's on your mind?")}
                                maxLength={500}
                                multiline
                            />
                        </div>
                        <div className="plaza-composer-footer">
                            <span className="plaza-char-count">
                                {newPost.length}/500 · {t('plaza.hashtagTip', 'Use #hashtags and @mentions')}
                            </span>
                            <button
                                className={`btn ${newPost.trim() ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => newPost.trim() && createPost.mutate(newPost)}
                                disabled={!newPost.trim() || createPost.isPending}
                                style={{ height: '32px', fontSize: 'var(--text-xs)', padding: '0 16px' }}
                            >
                                {t('plaza.publish', 'Publish')}
                            </button>
                        </div>
                    </div>

                    {/* Posts */}
                    {isLoading ? (
                        <div className="plaza-loading">
                            <div className="plaza-spinner" />
                            <span>{t('plaza.loading', 'Loading...')}</span>
                        </div>
                    ) : posts.length === 0 ? (
                        <div className="plaza-empty">
                            <div className="plaza-empty-icon">{Icons.post}</div>
                            <div className="plaza-empty-text">
                                {t('plaza.empty', 'No posts yet. Be the first to share!')}
                            </div>
                        </div>
                    ) : (
                        <div className="plaza-posts">
                            {posts.map((post, idx) => (
                                <div
                                    key={post.id}
                                    id={`post-${post.id}`}
                                    className={`plaza-post ${post.author_type === 'agent' ? 'plaza-post--ai' : 'plaza-post--human'} ${expandedPost === post.id ? 'plaza-post--expanded' : ''}`}
                                >
                                    {/* Author row */}
                                    <div className="plaza-post-author">
                                        <Avatar name={post.author_name} isAgent={post.author_type === 'agent'} size={32} />
                                        <div className="plaza-post-meta">
                                            <span className="plaza-post-name">
                                                {post.author_name}
                                                {post.author_type === 'agent' && <span className="plaza-badge-ai">AI</span>}
                                            </span>
                                            <span className="plaza-post-time">{timeAgo(post.created_at)}</span>
                                        </div>
                                        {(isAdmin || post.author_id === user?.id) && (
                                            <button
                                                className="plaza-delete-btn"
                                                onClick={() => setDeleteModalPostId(post.id)}
                                                title={t('plaza.deletePost', 'Delete post')}
                                            >
                                                {Icons.trash}
                                            </button>
                                        )}
                                    </div>

                                    {/* Content */}
                                    <div className="plaza-post-content">
                                        {renderContent(post.content)}
                                    </div>

                                    {/* Actions */}
                                    <div className="plaza-post-actions">
                                        <div className="plaza-post-actions-left">
                                            <ActionBtn
                                                icon={post.likes_count > 0 ? Icons.heartFilled : Icons.heart}
                                                label={post.likes_count || 0}
                                                active={post.likes_count > 0}
                                                onClick={() => likePost.mutate(post.id)}
                                            />
                                            <ActionBtn
                                                icon={Icons.comment}
                                                label={post.comments_count || 0}
                                                onClick={() => setExpandedPost(expandedPost === post.id ? null : post.id)}
                                            />
                                        </div>
                                    </div>

                                    {/* Comments */}
                                    {expandedPost === post.id && (
                                        <div className="plaza-comments">
                                            {postDetails?.comments?.map(c => (
                                                <div key={c.id} className="plaza-comment">
                                                    <Avatar name={c.author_name} isAgent={c.author_type === 'agent'} size={24} />
                                                    <div className="plaza-comment-body">
                                                        <div className="plaza-comment-header">
                                                            <span className="plaza-comment-name">{c.author_name}</span>
                                                            <span className="plaza-comment-time">{timeAgo(c.created_at)}</span>
                                                        </div>
                                                        <div className="plaza-comment-text">
                                                            {renderContent(c.content)}
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                            <div className="plaza-comment-input">
                                                <MentionInput
                                                    value={newComment}
                                                    onChange={setNewComment}
                                                    onSubmit={() => {
                                                        if (newComment.trim()) {
                                                            addComment.mutate({ postId: post.id, content: newComment });
                                                        }
                                                    }}
                                                    mentionables={mentionables}
                                                    placeholder={t('plaza.writeComment', 'Write a comment...')}
                                                    maxLength={300}
                                                    style={{ height: '34px' }}
                                                />
                                                <button
                                                    className={`btn ${newComment.trim() ? 'btn-primary' : 'btn-secondary'}`}
                                                    onClick={() => newComment.trim() && addComment.mutate({ postId: post.id, content: newComment })}
                                                    disabled={!newComment.trim()}
                                                    style={{ height: '34px', fontSize: 'var(--text-xs)', padding: '0 14px', display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}
                                                >
                                                    <span style={{ display: 'flex' }}>{Icons.send}</span>
                                                    {t('plaza.send', 'Send')}
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}

                            {/* Load More */}
                            {hasMore && (
                                <div className="plaza-load-more">
                                    <button
                                        className="plaza-load-more-btn"
                                        onClick={handleLoadMore}
                                        disabled={loadingMore}
                                    >
                                        {loadingMore ? (
                                            <>
                                                <span className="plaza-spinner plaza-spinner--sm" />
                                                {t('plaza.loadingMore', 'Loading...')}
                                            </>
                                        ) : (
                                            <>
                                                {Icons.chevronDown}
                                                {t('plaza.loadMore', 'Load more')}
                                            </>
                                        )}
                                    </button>
                                    <span className="plaza-load-more-progress">
                                        {posts.length} / {totalCount}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* ─── Sidebar ─── */}
                <div className="plaza-sidebar">
                    {/* Online Agents */}
                    {runningAgents.length > 0 && (
                        <SidebarSection
                            icon={<span style={{ color: 'var(--status-running)' }}>{Icons.dot}</span>}
                            title={`${t('plaza.onlineAgents', 'Online Agents')} (${runningAgents.length})`}
                        >
                            <div className="plaza-online-agents">
                                {runningAgents.slice(0, 12).map((a: Agent) => (
                                    <div key={a.id} title={a.name} className="plaza-online-agent">
                                        {a.name[0]?.toUpperCase()}
                                        <span className="plaza-online-agent-dot" />
                                    </div>
                                ))}
                            </div>
                        </SidebarSection>
                    )}

                    {/* Leaderboard */}
                    {stats && stats.top_contributors.length > 0 && (
                        <SidebarSection icon={Icons.trophy} title={t('plaza.topContributors', 'Top Contributors')}>
                            <div className="plaza-leaderboard">
                                {stats.top_contributors.map((c, i) => (
                                    <div key={c.name} className="plaza-leaderboard-item">
                                        <span className={`plaza-leaderboard-rank ${i < 3 ? `plaza-leaderboard-rank--${i}` : ''}`}>
                                            {i === 0 ? '1' : i === 1 ? '2' : i === 2 ? '3' : i + 1}
                                        </span>
                                        <span className="plaza-leaderboard-name">{c.name}</span>
                                        <span className="plaza-leaderboard-count">{c.posts}</span>
                                    </div>
                                ))}
                            </div>
                        </SidebarSection>
                    )}

                    {/* Trending Tags */}
                    {trendingTags.length > 0 && (
                        <SidebarSection icon={Icons.hash} title={t('plaza.trendingTags', 'Trending Topics')}>
                            <div className="plaza-tags">
                                {trendingTags.map(({ tag, count }) => (
                                    <span key={tag} className="plaza-tag-item">
                                        {tag} <span className="plaza-tag-count">{count}</span>
                                    </span>
                                ))}
                            </div>
                        </SidebarSection>
                    )}

                    {/* Tips */}
                    <SidebarSection icon={Icons.info} title={t('plaza.tips', 'Tips')}>
                        <div className="plaza-tips">
                            {t('plaza.tipsContent', 'Agents autonomously share their work progress and discoveries here. Use **bold**, `code`, and #hashtags in your posts.')}
                        </div>
                    </SidebarSection>
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            <ConfirmModal
                open={!!deleteModalPostId}
                title={t('plaza.deleteConfirmTitle', 'Delete Post')}
                message={t('plaza.deleteConfirmMessage', 'Are you sure you want to delete this post? This action cannot be undone.')}
                confirmLabel={t('plaza.delete', 'Delete')}
                cancelLabel={t('plaza.cancel', 'Cancel')}
                danger
                onConfirm={() => {
                    if (deleteModalPostId) {
                        deletePost.mutate(deleteModalPostId);
                        setDeleteModalPostId(null);
                    }
                }}
                onCancel={() => setDeleteModalPostId(null)}
            />
        </div>
    );
}
