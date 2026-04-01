import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { IconRobot, IconBrain, IconWorld, IconAlertCircle, IconTarget, IconSchool } from '@tabler/icons-react';
import { useAuthStore } from '../stores';
import { authApi, tenantApi, fetchJson } from '../services/api';
import type { TokenResponse } from '../types';

export default function Login() {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const invitationCode = searchParams.get('code');
    const setAuth = useAuthStore((s) => s.setAuth);
    const [isRegister, setIsRegister] = useState(!!invitationCode);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [tenant, setTenant] = useState<any>(null);
    const [resolving, setResolving] = useState(true);
    const [ssoProviders, setSsoProviders] = useState<any[]>([]);
    const [ssoLoading, setSsoLoading] = useState(false);
    const [ssoError, setSsoError] = useState('');
    const [tenantSelection, setTenantSelection] = useState<any[] | null>(null);

    const [form, setForm] = useState({
        login_identifier: '',
        password: '',
        tenant_id: '',
    });

    // Login page always uses dark theme (hero panel is dark)
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', 'dark');

        // Resolve tenant by domain (for SSO detection only, not for login form)
        const domain = window.location.host;
        if (domain.startsWith('localhost') || domain.startsWith('127.0.0.1')) {
            setResolving(false);
            return;
        }

        tenantApi.resolveByDomain(domain)
            .then(res => {
                if (res) {
                    setTenant(res);
                }
            })
            .catch(() => { })
            .finally(() => setResolving(false));
    }, []);

    useEffect(() => {
        let cancelled = false;
        if (!tenant?.sso_enabled || isRegister) {
            setSsoProviders([]);
            setSsoError('');
            return;
        }
        if (!tenant?.id) return;

        setSsoLoading(true);
        setSsoError('');

        fetchJson<{ session_id: string }>(`/sso/session?tenant_id=${tenant.id}`, { method: 'POST' })
            .then(res => fetchJson<any[]>(`/sso/config?sid=${res.session_id}`))
            .then(providers => {
                if (cancelled) return;
                setSsoProviders(providers || []);
            })
            .catch(() => {
                if (cancelled) return;
                setSsoError(t('auth.ssoLoadFailed', 'Failed to load SSO providers.'));
                setSsoProviders([]);
            })
            .finally(() => {
                if (cancelled) return;
                setSsoLoading(false);
            });

        return () => { cancelled = true; };
    }, [tenant?.id, tenant?.sso_enabled, isRegister, t]);

    const toggleLang = () => {
        i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh');
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccessMessage('');
        setLoading(true);

        try {
            if (isRegister) {
                const regRes = await authApi.register({
                    username: form.login_identifier.split('@')[0],
                    email: form.login_identifier,
                    password: form.password,
                    display_name: form.login_identifier.split('@')[0],
                    ...(invitationCode ? { invitation_code: invitationCode } : {})
                });
                // Save authentication state for company selection (user not active yet)
                if (regRes.access_token && regRes.user) {
                    setAuth(regRes.user, regRes.access_token);
                }
                // Redirect based on whether company setup is needed
                if (regRes.needs_company_setup === false) {
                    navigate('/verify-email', { state: { fromRegister: true, email: regRes.email } });
                } else {
                    navigate('/setup-company', { state: { fromRegister: true, email: regRes.email } });
                }
                return;
            } else {
                const res = await authApi.login({
                    login_identifier: form.login_identifier,
                    password: form.password,
                    ...(tenant?.id ? { tenant_id: tenant.id } : {}),
                });

                // Check if multi-tenant selection is needed
                if ('requires_tenant_selection' in res && res.requires_tenant_selection) {
                    setTenantSelection(res.tenants);
                    setLoading(false);
                    return;
                }

                const tokenRes = res as TokenResponse;
                setAuth(tokenRes.user, tokenRes.access_token);

                if (tokenRes.user && !tokenRes.user.tenant_id) {
                    navigate('/setup-company');
                } else {
                    navigate('/');
                }
            }
        } catch (err: any) {
            // Handle structured verification error
            if (err.detail?.needs_verification) {
                navigate('/verify-email', { 
                    state: { 
                        fromRegister: false, 
                        email: err.detail.email || form.login_identifier 
                    } 
                });
                return;
            }

            const msg = err.message || '';
            if (msg && msg !== 'Failed to fetch' && !msg.includes('NetworkError') && !msg.includes('ERR_CONNECTION')) {
                if (msg.includes('company has been disabled')) {
                    setError(t('auth.companyDisabled'));
                } else if (msg.includes('Invalid credentials')) {
                    setError(t('auth.invalidCredentials'));
                } else if (msg.includes('Account is disabled')) {
                    setError(t('auth.accountDisabled'));
                } else if (msg.includes('does not belong to this organization')) {
                    setError(t('auth.notInOrganization', 'This account does not belong to this organization.'));
                } else if (msg.includes('500') || msg.includes('Internal Server Error')) {
                    setError(t('auth.serverStarting'));
                } else if (msg.includes('Email already registered') || msg.includes('该邮箱已注册')) {
                    setError(t('auth.emailAlreadyRegistered', '该邮箱已注册，请直接登录'));
                } else {
                    setError(msg);
                }
            } else {
                setError(t('auth.serverUnreachable'));
            }
        } finally {
            setLoading(false);
        }
    };

    const handleTenantSelect = async (tenantId: string) => {
        setForm(f => ({ ...f, tenant_id: tenantId }));
        setTenantSelection(null);
        setError('');
        setLoading(true);

        try {
            const res = await authApi.login({
                login_identifier: form.login_identifier,
                password: form.password,
                tenant_id: tenantId,
            });

            // Should not get multi-tenant response when tenant_id is provided
            if ('requires_tenant_selection' in res && res.requires_tenant_selection) {
                setTenantSelection(res.tenants);
                setLoading(false);
                return;
            }

            const tokenRes = res as TokenResponse;
            setAuth(tokenRes.user, tokenRes.access_token);
            if (tokenRes.user && !tokenRes.user.tenant_id) {
                navigate('/setup-company');
            } else {
                navigate('/');
            }
        } catch (err: any) {
            const msg = err.message || '';
            setError(msg || t('auth.loginFailed', 'Login failed'));
        } finally {
            setLoading(false);
        }
    };

    const ssoMeta: Record<string, { label: string; icon: string }> = {
        feishu: { label: 'Feishu', icon: '/feishu.png' },
        dingtalk: { label: 'DingTalk', icon: '/dingtalk.png' },
        wecom: { label: 'WeCom', icon: '/wecom.png' },
    };

    return (
        <div className="login-page">
            {/* ── Left: Branding Panel ── */}
            <div className="login-hero">
                <div className="login-hero-bg" />
                <div className="login-hero-decor" />
                <div className="login-hero-shapes">
                    {/* Globe decoration - world element */}
                    <div className="login-hero-chart login-hero-chart--globe">
                        <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                            {/* Outer glow */}
                            <circle cx="60" cy="60" r="55" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
                            {/* Globe outline */}
                            <circle cx="60" cy="60" r="45" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.35)" strokeWidth="1.5"/>
                            {/* Longitude lines */}
                            <ellipse cx="60" cy="60" rx="20" ry="45" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1"/>
                            <ellipse cx="60" cy="60" rx="35" ry="45" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="0.8"/>
                            {/* Latitude lines */}
                            <line x1="15" y1="60" x2="105" y2="60" stroke="rgba(255,255,255,0.15)" strokeWidth="0.8"/>
                            <line x1="20" y1="45" x2="100" y2="45" stroke="rgba(255,255,255,0.1)" strokeWidth="0.6"/>
                            <line x1="20" y1="75" x2="100" y2="75" stroke="rgba(255,255,255,0.1)" strokeWidth="0.6"/>
                            {/* Equator highlight */}
                            <ellipse cx="60" cy="60" rx="45" ry="15" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="0.8"/>
                            {/* Data points on globe */}
                            <circle cx="45" cy="40" r="2.5" fill="rgba(255,255,255,0.6)"/>
                            <circle cx="75" cy="50" r="3" fill="rgba(255,255,255,0.7)"/>
                            <circle cx="55" cy="75" r="2.5" fill="rgba(255,255,255,0.6)"/>
                            <circle cx="80" cy="35" r="2" fill="rgba(255,255,255,0.5)"/>
                        </svg>
                    </div>

                    {/* Stock chart decoration - rising trend with area fill */}
                    <div className="login-hero-chart login-hero-chart--stock">
                        <svg viewBox="0 0 200 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                            {/* Grid lines */}
                            <line x1="0" y1="25" x2="200" y2="25" stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
                            <line x1="0" y1="50" x2="200" y2="50" stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
                            <line x1="0" y1="75" x2="200" y2="75" stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
                            {/* Rising stock line */}
                            <path d="M0 85 L25 70 L50 75 L75 55 L100 60 L125 40 L150 45 L175 25 L200 15"
                                stroke="rgba(255,255,255,0.5)" strokeWidth="2" fill="none"
                                strokeLinecap="round" strokeLinejoin="round"/>
                            {/* Area fill */}
                            <path d="M0 85 L25 70 L50 75 L75 55 L100 60 L125 40 L150 45 L175 25 L200 15 L200 100 L0 100 Z"
                                fill="url(#stockGradient)" opacity="0.2"/>
                            <defs>
                                <linearGradient id="stockGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                    <stop offset="0%" stopColor="rgba(255,255,255,0.4)"/>
                                    <stop offset="100%" stopColor="rgba(255,255,255,0)"/>
                                </linearGradient>
                            </defs>
                            {/* Data points */}
                            <circle cx="75" cy="55" r="3" fill="rgba(255,255,255,0.7)"/>
                            <circle cx="125" cy="40" r="3" fill="rgba(255,255,255,0.7)"/>
                            <circle cx="175" cy="25" r="4" fill="rgba(255,255,255,0.9)"/>
                        </svg>
                    </div>

                    {/* Bar chart decoration */}
                    <div className="login-hero-chart login-hero-chart--bar">
                        <svg viewBox="0 0 160 80" fill="none" xmlns="http://www.w3.org/2000/svg">
                            {/* Bars */}
                            <rect x="10" y="50" width="20" height="30" rx="2" fill="rgba(255,255,255,0.25)"/>
                            <rect x="40" y="35" width="20" height="45" rx="2" fill="rgba(255,255,255,0.3)"/>
                            <rect x="70" y="25" width="20" height="55" rx="2" fill="rgba(255,255,255,0.35)"/>
                            <rect x="100" y="15" width="20" height="65" rx="2" fill="rgba(255,255,255,0.4)"/>
                            <rect x="130" y="5" width="20" height="75" rx="2" fill="rgba(255,255,255,0.5)"/>
                        </svg>
                    </div>

                    {/* Pie chart decoration */}
                    <div className="login-hero-chart login-hero-chart--pie">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1"/>
                            {/* Pie segments */}
                            <path d="M50 50 L50 10 A40 40 0 0 1 85 65 Z" fill="rgba(255,255,255,0.2)"/>
                            <path d="M50 50 L85 65 A40 40 0 0 1 20 75 Z" fill="rgba(255,255,255,0.15)"/>
                            <path d="M50 50 L20 75 A40 40 0 0 1 50 10 Z" fill="rgba(255,255,255,0.25)"/>
                        </svg>
                    </div>

                    {/* Decorative circles */}
                    <div className="login-hero-orb login-hero-orb--1"></div>
                    <div className="login-hero-orb login-hero-orb--2"></div>
                    <div className="login-hero-orb login-hero-orb--3"></div>

                    {/* Trend line decoration */}
                    <div className="login-hero-chart login-hero-chart--trend">
                        <svg viewBox="0 0 180 72" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M0 58 L36 48 L72 52 L108 35 L144 40 L180 28"
                                stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" fill="none"
                                strokeLinecap="round" strokeLinejoin="round"/>
                            <circle cx="36" cy="48" r="2.5" fill="rgba(255,255,255,0.25)"/>
                            <circle cx="108" cy="35" r="2.5" fill="rgba(255,255,255,0.25)"/>
                        </svg>
                    </div>

                    {/* Currency symbols */}
                    <div className="login-hero-symbol login-hero-symbol--dollar">$</div>
                    <div className="login-hero-symbol login-hero-symbol--yen">¥</div>
                    <div className="login-hero-symbol login-hero-symbol--euro">€</div>
                    <div className="login-hero-symbol login-hero-symbol--pound">£</div>
                    <div className="login-hero-symbol login-hero-symbol--dollar2">$</div>

                    {/* Percentage indicator */}
                    <div className="login-hero-symbol login-hero-symbol--percent">%</div>
                </div>
                <div className="login-hero-grid" />
                <div className="login-hero-content">
                    <div className="login-hero-badge">
                        <span className="login-hero-badge-dot" />
                        {t('login.hero.badge')}
                    </div>
                    <h1 className="login-hero-title">
                        {t('login.hero.title')}
                    </h1>
                    <p className="login-hero-subtitle">{t('login.hero.subtitle')}</p>
                    <p className="login-hero-desc" dangerouslySetInnerHTML={{ __html: t('login.hero.description') }} />
                    <div className="login-hero-features">
                        <div className="login-hero-feature">
                            <span className="login-hero-feature-icon"><IconRobot size={24} stroke={1.5} /></span>
                            <div>
                                <div className="login-hero-feature-title">{t('login.hero.features.multiAgent.title')}</div>
                                <div className="login-hero-feature-desc">{t('login.hero.features.multiAgent.description')}</div>
                            </div>
                        </div>
                        <div className="login-hero-feature">
                            <span className="login-hero-feature-icon"><IconTarget size={24} stroke={1.5} /></span>
                            <div>
                                <div className="login-hero-feature-title">{t('login.hero.features.serviceDelivery.title')}</div>
                                <div className="login-hero-feature-desc">{t('login.hero.features.serviceDelivery.description')}</div>
                            </div>
                        </div>
                        <div className="login-hero-feature">
                            <span className="login-hero-feature-icon"><IconBrain size={24} stroke={1.5} /></span>
                            <div>
                                <div className="login-hero-feature-title">{t('login.hero.features.persistentMemory.title')}</div>
                                <div className="login-hero-feature-desc">{t('login.hero.features.persistentMemory.description')}</div>
                            </div>
                        </div>
                        <div className="login-hero-feature">
                            <span className="login-hero-feature-icon"><IconSchool size={24} stroke={1.5} /></span>
                            <div>
                                <div className="login-hero-feature-title">{t('login.hero.features.learning.title')}</div>
                                <div className="login-hero-feature-desc">{t('login.hero.features.learning.description')}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Right: Form Panel ── */}
            <div className="login-form-panel">
                {/* Language Switcher */}
                <div style={{
                    position: 'absolute', top: '16px', right: '16px',
                    cursor: 'pointer', fontSize: '13px', color: '#64748b',
                    display: 'flex', alignItems: 'center', gap: '4px',
                    padding: '6px 12px', borderRadius: '8px',
                    background: '#f1f5f9', border: '1px solid #e2e8f0',
                    zIndex: 101,
                }} onClick={toggleLang}>
                    <IconWorld size={16} stroke={1.5} />
                </div>

                <div className="login-form-wrapper">
                    <div className="login-form-header">
                        <div className="login-form-logo"><img src="/logo-black.png" className="login-logo-img" alt="" style={{ width: 28, height: 28, marginRight: 8, verticalAlign: 'middle' }} />ProudCopilot</div>
                        <h2 className="login-form-title">
                            {isRegister ? t('auth.register') : t('auth.login')}
                        </h2>
                        <p className="login-form-subtitle">
                            {isRegister ? t('auth.subtitleRegister') : t('auth.subtitleLogin')}
                        </p>
                    </div>

                    {error && (
                        <div className="login-error">
                            <IconAlertCircle size={16} stroke={1.5} /> {error}
                        </div>
                    )}

                    {successMessage && (
                        <div className="login-success" style={{
                            background: 'rgba(34, 197, 94, 0.1)',
                            color: '#16a34a',
                            padding: '12px 16px',
                            borderRadius: '8px',
                            marginBottom: '16px',
                            fontSize: '14px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            border: '1px solid rgba(34, 197, 94, 0.2)',
                        }}>
                            <span>✓</span> {successMessage}
                        </div>
                    )}

                    {tenant && tenant.sso_enabled && !isRegister && (
                        <div style={{ marginBottom: '24px' }}>
                            <div style={{
                                padding: '16px', borderRadius: '12px', background: 'rgba(59,130,246,0.08)',
                                border: '1px solid rgba(59,130,246,0.15)', marginBottom: '16px',
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--accent-primary)', marginBottom: '4px' }}>
                                    {tenant.name}
                                </div>
                                <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                                    {t('auth.ssoNotice', 'Enterprise SSO is enabled for this domain.')}
                                </div>
                            </div>

                            {ssoLoading && (
                                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '12px' }}>
                                    {t('auth.ssoLoading', 'Loading SSO providers...')}
                                </div>
                            )}

                            {!ssoLoading && ssoProviders.length > 0 && (
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
                                    {ssoProviders.map(p => {
                                        const meta = ssoMeta[p.provider_type] || { label: p.name || p.provider_type, icon: '' };
                                        return (
                                            <button
                                                key={p.provider_type}
                                                className="login-submit"
                                                style={{
                                                    background: 'var(--bg-secondary)',
                                                    color: 'var(--text-primary)',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    gap: '10px',
                                                    border: '1px solid var(--border-subtle)',
                                                }}
                                                onClick={() => window.location.href = p.url}
                                            >
                                                {meta.icon ? (
                                                    <img src={meta.icon} alt={meta.label} width={18} height={18} style={{ borderRadius: '4px' }} />
                                                ) : (
                                                    <span style={{ width: 18, height: 18, borderRadius: 4, background: 'var(--bg-tertiary)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10 }}>
                                                        {(meta.label || '').slice(0, 1).toUpperCase()}
                                                    </span>
                                                )}
                                                {meta.label || p.name || p.provider_type}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}

                            {!ssoLoading && ssoProviders.length === 0 && (
                                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '12px' }}>
                                    {ssoError || t('auth.ssoNoProviders', 'No SSO providers configured.')}
                                </div>
                            )}

                            <div style={{
                                display: 'flex', alignItems: 'center', gap: '12px',
                                margin: '20px 0', color: 'var(--text-tertiary)', fontSize: '11px'
                            }}>
                                <div style={{ flex: 1, height: '1px', background: 'var(--border-subtle)' }} />
                                {t('auth.or', 'or')}
                                <div style={{ flex: 1, height: '1px', background: 'var(--border-subtle)' }} />
                            </div>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="login-form">
                        <div className="login-field">
                            <label>{t('auth.email')}</label>
                            <input
                                type="email"
                                value={form.login_identifier}
                                onChange={(e) => setForm({ ...form, login_identifier: e.target.value })}
                                required
                                autoFocus
                                placeholder={t('auth.emailPlaceholder')}
                            />
                        </div>

                        <div className="login-field">
                            <label>{t('auth.password')}</label>
                            <input
                                type="password"
                                value={form.password}
                                onChange={(e) => setForm({ ...form, password: e.target.value })}
                                required
                                placeholder={t('auth.passwordPlaceholder')}
                            />
                        </div>

                        {!isRegister && (
                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '-4px', marginBottom: '8px' }}>
                                <Link
                                    to="/forgot-password"
                                    style={{ fontSize: '13px', color: 'var(--accent-primary)', textDecoration: 'none' }}
                                >
                                    {t('auth.forgotPassword', 'Forgot password?')}
                                </Link>
                            </div>
                        )}

                        <button className="login-submit" type="submit" disabled={loading}>
                            {loading ? (
                                <span className="login-spinner" />
                            ) : (
                                <>
                                    {isRegister ? t('auth.register') : t('auth.login')}
                                    <span style={{ marginLeft: '6px' }}>→</span>
                                </>
                            )}
                        </button>
                    </form>

                    {/* Multi-tenant selection modal */}
                    {tenantSelection && (
                        <div style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: 'rgba(0,0,0,0.5)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            zIndex: 1000,
                        }}>
                            <div style={{
                                background: 'var(--bg-primary)',
                                borderRadius: '16px',
                                padding: '32px',
                                maxWidth: '400px',
                                width: '90%',
                            }}>
                                <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px', color: 'var(--text-primary)' }}>
                                    {t('auth.selectOrganization', '选择公司')}
                                </h3>
                                <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                                    {t('auth.multiTenantPrompt', '该邮箱对应多个公司，请选择要登录的公司：')}
                                </p>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    {tenantSelection.map((tenant: any) => (
                                        <button
                                            key={tenant.tenant_id}
                                            onClick={() => handleTenantSelect(tenant.tenant_id)}
                                            style={{
                                                padding: '12px 16px',
                                                borderRadius: '8px',
                                                border: '1px solid var(--border-subtle)',
                                                background: 'var(--bg-secondary)',
                                                color: 'var(--text-primary)',
                                                fontSize: '14px',
                                                cursor: 'pointer',
                                                textAlign: 'left',
                                            }}
                                        >
                                            {tenant.tenant_name} {tenant.tenant_slug && `(${tenant.tenant_slug})`}
                                        </button>
                                    ))}
                                    {/* Create or Join Organization */}
                                    <button
                                        onClick={async () => {
                                            // Log in with the first tenant to get a valid token, then redirect to company setup
                                            try {
                                                setLoading(true);
                                                const firstTenant = tenantSelection[0];
                                                const res = await authApi.login({
                                                    login_identifier: form.login_identifier,
                                                    password: form.password,
                                                    tenant_id: firstTenant.tenant_id,
                                                });
                                                const tokenRes = res as TokenResponse;
                                                setAuth(tokenRes.user, tokenRes.access_token);
                                                setTenantSelection(null);
                                                navigate('/setup-company?from=tenant-selection');
                                            } catch (err: any) {
                                                setError(err.message || 'Failed');
                                                setTenantSelection(null);
                                            } finally {
                                                setLoading(false);
                                            }
                                        }}
                                        style={{
                                            padding: '12px 16px',
                                            borderRadius: '8px',
                                            border: '1px dashed var(--border-subtle)',
                                            background: 'transparent',
                                            color: 'var(--text-secondary)',
                                            fontSize: '14px',
                                            cursor: 'pointer',
                                            textAlign: 'left',
                                        }}
                                    >
                                        {t('auth.createOrJoinOrganization', 'Create or Join Organization')}
                                    </button>
                                </div>
                                <button
                                    onClick={() => setTenantSelection(null)}
                                    style={{
                                        marginTop: '20px',
                                        padding: '10px 16px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: 'var(--bg-tertiary)',
                                        color: 'var(--text-primary)',
                                        fontSize: '14px',
                                        cursor: 'pointer',
                                        width: '100%',
                                    }}
                                >
                                    {t('common.cancel', 'Cancel')}
                                </button>
                            </div>
                        </div>
                    )}

                    <div className="login-switch">
                        {isRegister ? t('auth.hasAccount') : t('auth.noAccount')}{' '}
                        <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(!isRegister); setError(''); }}>
                            {isRegister ? t('auth.goLogin') : t('auth.goRegister')}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    );
}
