import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.chat_session import ChatSession
from app.models.identity import IdentityProvider
from app.models.org import OrgMember
from app.models.user import User, Identity
from app.schemas.schemas import (
    ChannelAccountOut, AdminUnbindRequest, MergeDuplicateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


# ─── User Search (for team member selector) ─────────────


@router.get("/search")
async def search_tenant_users(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search users in the same tenant by name or email. Available to all authenticated users."""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant")

    stmt = (
        select(User)
        .join(Identity, User.identity_id == Identity.id)
        .where(
            User.tenant_id == current_user.tenant_id,
            User.is_active.is_(True),
            User.id != current_user.id,
            # 仅显示通过平台注册的用户，排除飞书/微信等渠道同步用户
            or_(
                User.registration_source == 'web',
                User.registration_source.is_(None),
            ),
        )
    )

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.display_name.ilike(pattern),
                Identity.email.ilike(pattern),
                Identity.username.ilike(pattern),
            )
        )

    stmt = stmt.order_by(User.display_name).limit(50)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        {
            "id": str(u.id),
            "display_name": u.display_name or "",
            "avatar_url": u.avatar_url,
            "email": u.email or "",
        }
        for u in users
    ]


class UserQuotaUpdate(BaseModel):
    quota_message_limit: int | None = None
    quota_message_period: str | None = None
    quota_max_agents: int | None = None
    quota_agent_ttl_hours: int | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    # username/email/display_name can be None for SSO-created users whose Identity
    # was created without explicit values (e.g., DingTalk/Feishu OAuth flow).
    # The frontend should handle None gracefully.
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    role: str
    is_active: bool
    # Quota fields
    quota_message_limit: int
    quota_message_period: str
    quota_messages_used: int
    quota_max_agents: int
    quota_agent_ttl_hours: int
    # Computed
    agents_count: int = 0
    # Source info
    created_at: str | None = None
    source: str = 'registered'  # 'registered' | 'feishu' | 'dingtalk' | 'wecom' | etc.
    # Channel accounts
    channel_accounts: list[ChannelAccountOut] = []

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[UserOut])
async def list_users(
    tenant_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the specified tenant (admin only)."""
    if current_user.role not in ("platform_admin", "org_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Platform admins can view any tenant; org_admins only their own
    tid = tenant_id if tenant_id and current_user.role == "platform_admin" else str(current_user.tenant_id)

    # Filter users by tenant — platform_admins only shown in their own tenant
    result = await db.execute(
        select(User).options(selectinload(User.identity)).where(
            User.tenant_id == tid
        ).order_by(User.created_at.asc())
    )
    users = result.scalars().all()

    # Batch agent counts per user
    user_ids = [u.id for u in users]
    agent_count_map: dict = {}
    if user_ids:
        acq = await db.execute(
            select(Agent.creator_id, func.count(Agent.id))
            .where(Agent.creator_id.in_(user_ids), Agent.is_expired == False)
            .group_by(Agent.creator_id)
        )
        agent_count_map = {str(r[0]): r[1] for r in acq.all()}

    # Batch channel accounts per user
    channel_accounts_map: dict[str, list[ChannelAccountOut]] = {}
    if user_ids:
        ca_result = await db.execute(
            select(OrgMember, IdentityProvider.provider_type)
            .join(IdentityProvider, OrgMember.provider_id == IdentityProvider.id, isouter=True)
            .where(
                OrgMember.user_id.in_(user_ids),
                OrgMember.status == "active",
            )
        )
        for member, provider_type in ca_result.all():
            uid = str(member.user_id)
            if uid not in channel_accounts_map:
                channel_accounts_map[uid] = []
            channel_accounts_map[uid].append(ChannelAccountOut(
                id=member.id,
                channel_type=provider_type or "unknown",
                external_id=member.external_id,
                open_id=member.open_id,
                unionid=member.unionid,
                name=member.name,
                email=member.email,
                phone=member.phone,
                avatar_url=member.avatar_url,
                is_linked=member.user_id is not None,
            ))

    out = []
    for u in users:
        agents_count = agent_count_map.get(str(u.id), 0)

        user_dict = {
            "id": u.id,
            # Fallback to empty string if username/email/display_name is None to prevent
            # serialization errors for SSO-created users with incomplete Identity records.
            "username": u.username or u.email or f"{u.registration_source or 'user'}_{str(u.id)[:8]}",
            "email": u.email or "",
            "display_name": u.display_name or u.username or "",
            "role": u.role,
            "is_active": u.is_active,
            "quota_message_limit": u.quota_message_limit,
            "quota_message_period": u.quota_message_period,
            "quota_messages_used": u.quota_messages_used,
            "quota_max_agents": u.quota_max_agents,
            "quota_agent_ttl_hours": u.quota_agent_ttl_hours,
            "agents_count": agents_count,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "source": (u.registration_source or 'registered'),
            "channel_accounts": channel_accounts_map.get(str(u.id), []),
        }
        out.append(UserOut(**user_dict))
    return out


@router.patch("/{user_id}/quota", response_model=UserOut)
async def update_user_quota(
    user_id: uuid.UUID,
    data: UserQuotaUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's quota settings (admin only)."""
    if current_user.role not in ("platform_admin", "org_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(User).options(selectinload(User.identity)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot modify users outside your organization")

    if data.quota_message_limit is not None:
        user.quota_message_limit = data.quota_message_limit
    if data.quota_message_period is not None:
        if data.quota_message_period not in ("permanent", "daily", "weekly", "monthly"):
            raise HTTPException(status_code=400, detail="Invalid period. Use: permanent, daily, weekly, monthly")
        user.quota_message_period = data.quota_message_period
    if data.quota_max_agents is not None:
        user.quota_max_agents = data.quota_max_agents
    if data.quota_agent_ttl_hours is not None:
        user.quota_agent_ttl_hours = data.quota_agent_ttl_hours

    await db.commit()
    await db.refresh(user)

    # Count agents
    count_result = await db.execute(
        select(func.count()).select_from(Agent).where(
            Agent.creator_id == user.id,
            Agent.is_expired == False,
        )
    )
    agents_count = count_result.scalar() or 0

    return UserOut(
        id=user.id, username=user.username, email=user.email,
        display_name=user.display_name, role=user.role, is_active=user.is_active,
        quota_message_limit=user.quota_message_limit,
        quota_message_period=user.quota_message_period,
        quota_messages_used=user.quota_messages_used,
        quota_max_agents=user.quota_max_agents,
        quota_agent_ttl_hours=user.quota_agent_ttl_hours,
        agents_count=agents_count,
    )


# ─── Role Management ───────────────────────────────────

class RoleUpdate(BaseModel):
    role: str


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role within the same company.

    Permissions:
    - org_admin: can set roles to org_admin / member within own tenant.
      Cannot assign platform_admin.
    - platform_admin: can set any valid role.

    Safety:
    - If the target is the ONLY remaining org_admin in the company,
      demoting them is blocked to prevent orphaned companies.
    """
    if current_user.role not in ("platform_admin", "org_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate target role value
    allowed_roles = ("org_admin", "member")
    if current_user.role == "platform_admin":
        allowed_roles = ("platform_admin", "org_admin", "member")
    if data.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {', '.join(allowed_roles)}")

    # Find target user
    result = await db.execute(
        select(User).options(selectinload(User.identity)).where(User.id == user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # org_admin can only modify users in the same tenant
    if current_user.role == "org_admin" and target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot modify users outside your organization")

    # No-op shortcut
    if target_user.role == data.role:
        return {"status": "ok", "user_id": str(user_id), "role": data.role}

    # Last-admin protection: if demoting an org_admin, check they are not the only one
    if target_user.role in ("org_admin", "platform_admin") and data.role not in ("org_admin", "platform_admin"):
        admin_count_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.tenant_id == target_user.tenant_id,
                User.role.in_(["org_admin", "platform_admin"]),
            )
        )
        admin_count = admin_count_result.scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the only administrator. Promote another user first."
            )

    target_user.role = data.role
    await db.commit()
    return {"status": "ok", "user_id": str(user_id), "role": data.role}


# ─── Channel Account Binding (Admin) ────────────────────


class _BindByOrgMemberRequest(BaseModel):
    org_member_id: uuid.UUID


def _check_admin(current_user: User):
    if current_user.role not in ("platform_admin", "org_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/unlinked-channel-accounts", response_model=list[ChannelAccountOut])
async def list_unlinked_channel_accounts(
    channel_type: str = "",
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List channel accounts not yet linked to a registered (web) user.

    "Unlinked" means: OrgMember has no user_id, OR its user_id points to a
    channel-source auto-created user (not a web-registered user). Admins can
    then rebind these to a real registered user.

    Two data sources:
    1. OrgMembers unlinked or linked only to channel-source users
    2. Channel-source Users without any OrgMember (wechat/discord/slack/teams duplicates)
    """
    _check_admin(current_user)
    ct = (channel_type or "").strip()
    kw = (q or "").strip()
    CHANNEL_SOURCES = ["feishu", "dingtalk", "wecom", "wechat", "discord", "slack", "microsoft_teams"]

    # --- Source 1: OrgMembers not linked to a web-registered user ---
    org_query = (
        select(OrgMember, IdentityProvider.provider_type, User.display_name)
        .join(IdentityProvider, OrgMember.provider_id == IdentityProvider.id, isouter=True)
        .outerjoin(User, OrgMember.user_id == User.id)
        .where(
            OrgMember.status == "active",
            or_(
                OrgMember.user_id.is_(None),
                User.registration_source.in_(CHANNEL_SOURCES),
            ),
        )
    )
    if current_user.tenant_id:
        org_query = org_query.where(OrgMember.tenant_id == current_user.tenant_id)
    if ct:
        # Match by provider_type OR by channel-specific ID patterns.
        # Catches OrgMembers whose provider_id is missing/invalid (e.g. partial org sync),
        # identified by channel-specific ID formats (feishu: ou_/on_ prefix).
        if ct == "feishu":
            org_query = org_query.where(
                or_(
                    IdentityProvider.provider_type == "feishu",
                    OrgMember.open_id.startswith("ou_"),
                    OrgMember.unionid.startswith("on_"),
                )
            )
        else:
            org_query = org_query.where(IdentityProvider.provider_type == ct)
    if kw:
        pattern = f"%{kw}%"
        org_query = org_query.where(
            or_(OrgMember.name.ilike(pattern), OrgMember.external_id.ilike(pattern),
                OrgMember.email.ilike(pattern), OrgMember.open_id.ilike(pattern))
        )
    org_query = org_query.order_by(OrgMember.name).limit(100)
    org_result = await db.execute(org_query)

    accounts = []
    seen_ids: set[str] = set()
    for member, provider_type, linked_name in org_result.all():
        seen_ids.add(str(member.id))
        accounts.append(ChannelAccountOut(
            id=member.id,
            channel_type=provider_type or "unknown",
            external_id=member.external_id,
            open_id=member.open_id,
            unionid=member.unionid,
            name=member.name,
            email=member.email,
            phone=member.phone,
            avatar_url=member.avatar_url,
            is_linked=False,
            linked_to_user_name=linked_name,
        ))

    # --- Source 2: Channel-source Users without OrgMember (wechat/discord/slack/teams duplicates) ---
    channel_sources = ["wechat", "discord", "slack", "microsoft_teams"]
    if ct:
        # Only query if channel_type matches a non-enterprise source
        if ct not in channel_sources:
            return accounts
        channel_sources = [ct]

    # Find channel-source users in the same tenant that have NO OrgMember
    subq = select(OrgMember.user_id).where(OrgMember.user_id.isnot(None))
    user_query = (
        select(User, Identity.email)
        .join(Identity, User.identity_id == Identity.id, isouter=True)
        .where(
            User.registration_source.in_(channel_sources),
            User.is_active == True,
            User.id.notin_(subq),
        )
    )
    if current_user.tenant_id:
        user_query = user_query.where(User.tenant_id == current_user.tenant_id)
    if kw:
        pattern = f"%{kw}%"
        user_query = user_query.where(
            or_(User.display_name.ilike(pattern), Identity.email.ilike(pattern))
        )
    user_query = user_query.order_by(User.display_name).limit(100)
    user_result = await db.execute(user_query)

    seen_ext_ids: set[str] = set()
    for ch_user, identity_email in user_result.all():
        uid = str(ch_user.id)
        if uid in seen_ids:
            continue
        # Extract external_id from identity email pattern: wechat_{id}@wechat.local
        ext_id = ""
        if identity_email and "@" in identity_email:
            local = identity_email.split("@")[0]
            # Pattern: wechat_o9cq801K8_BI or wechat_o9cq801K8_BI_o9cq80
            parts = local.split("_", 1)
            if len(parts) > 1:
                ext_id = parts[1]
        # Deduplicate by external_id: same channel user creates a new User per message,
        # but all share the same openid. Only show one entry per openid.
        dedup_key = ext_id or uid
        if dedup_key in seen_ext_ids:
            continue
        seen_ext_ids.add(dedup_key)
        accounts.append(ChannelAccountOut(
            id=ch_user.id,
            channel_type=ch_user.registration_source or "unknown",
            external_id=ext_id or None,
            open_id=None,
            unionid=None,
            name=ch_user.display_name,
            email=identity_email,
            phone=None,
            avatar_url=ch_user.avatar_url,
            is_linked=False,
        ))

    return accounts


@router.get("/{user_id}/channel-accounts", response_model=list[ChannelAccountOut])
async def list_channel_accounts(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List channel accounts (OrgMembers) linked to a user."""
    _check_admin(current_user)

    target = await db.get(User, user_id)
    if not target or target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(OrgMember, IdentityProvider.provider_type)
        .join(IdentityProvider, OrgMember.provider_id == IdentityProvider.id, isouter=True)
        .where(
            OrgMember.user_id == user_id,
            OrgMember.status == "active",
        )
    )
    rows = result.all()

    accounts = []
    for member, provider_type in rows:
        accounts.append(ChannelAccountOut(
            id=member.id,
            channel_type=provider_type or "unknown",
            external_id=member.external_id,
            open_id=member.open_id,
            unionid=member.unionid,
            name=member.name,
            email=member.email,
            phone=member.phone,
            avatar_url=member.avatar_url,
            is_linked=member.user_id is not None,
        ))
    return accounts


@router.post("/{user_id}/channel-accounts/bind-by-org-member", response_model=ChannelAccountOut)
async def bind_by_org_member_id(
    user_id: uuid.UUID,
    data: _BindByOrgMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin binds a channel account to a user.

    Two cases:
    1. org_member_id is an OrgMember → set user_id directly
    2. org_member_id is a channel-source User (no OrgMember) → create OrgMember, then bind
    """
    _check_admin(current_user)

    target = await db.get(User, user_id)
    if not target or target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Try OrgMember first
    member = await db.get(OrgMember, data.org_member_id)
    if member:
        if member.user_id and member.user_id != user_id:
            # Allow rebinding if current link is to a channel-source user (not a registered user)
            cur_user = await db.get(User, member.user_id)
            if cur_user and cur_user.registration_source in ("feishu", "dingtalk", "wecom", "wechat", "discord", "slack", "microsoft_teams"):
                pass  # allow rebinding from channel user to registered user
            else:
                raise HTTPException(status_code=409, detail="This channel account is already linked to another user")
        member.user_id = user_id
        await db.flush()
        provider = await db.get(IdentityProvider, member.provider_id)
        provider_type = provider.provider_type if provider else "unknown"
        return ChannelAccountOut(
            id=member.id,
            channel_type=provider_type,
            external_id=member.external_id,
            open_id=member.open_id,
            unionid=member.unionid,
            name=member.name,
            email=member.email,
            phone=member.phone,
            avatar_url=member.avatar_url,
            is_linked=True,
        )

    # Not an OrgMember — check if it's a channel-source User
    ch_user = await db.get(User, data.org_member_id)
    if not ch_user or not ch_user.registration_source or ch_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")

    # Ensure the channel user isn't already linked via an OrgMember
    existing = await db.execute(
        select(OrgMember).where(OrgMember.user_id == ch_user.id, OrgMember.status == "active")
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This channel user already has an OrgMember")

    # Get or create IdentityProvider for this channel type
    provider_type = ch_user.registration_source
    prov_result = await db.execute(
        select(IdentityProvider).where(
            IdentityProvider.provider_type == provider_type,
            IdentityProvider.tenant_id == current_user.tenant_id,
        )
    )
    provider = prov_result.scalar_one_or_none()
    if not provider:
        provider = IdentityProvider(
            provider_type=provider_type,
            name=provider_type.capitalize(),
            tenant_id=current_user.tenant_id,
        )
        db.add(provider)
        await db.flush()

    # Extract external_id from identity email
    ext_id = ""
    identity = await db.get(Identity, ch_user.identity_id) if ch_user.identity_id else None
    if identity and identity.email and "@" in identity.email:
        local = identity.email.split("@")[0]
        parts = local.split("_", 1)
        if len(parts) > 1:
            ext_id = parts[1]

    # Create OrgMember linking this channel user to the target registered user
    new_member = OrgMember(
        external_id=ext_id or None,
        name=ch_user.display_name,
        avatar_url=ch_user.avatar_url,
        user_id=user_id,
        provider_id=provider.id,
        tenant_id=current_user.tenant_id,
        status="active",
    )
    db.add(new_member)
    await db.flush()

    return ChannelAccountOut(
        id=new_member.id,
        channel_type=provider_type,
        external_id=new_member.external_id,
        open_id=None,
        unionid=None,
        name=new_member.name,
        email=identity.email if identity else None,
        phone=None,
        avatar_url=new_member.avatar_url,
        is_linked=True,
    )

@router.post("/{user_id}/channel-accounts/unbind")
async def unbind_channel_account(
    user_id: uuid.UUID,
    data: AdminUnbindRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin unbinds a channel account from a user."""
    _check_admin(current_user)

    target = await db.get(User, user_id)
    if not target or target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    from app.services.sso_service import sso_service

    success = await sso_service.admin_unlink_identity(db, data.org_member_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Channel account not found or not linked to this user")

    return {"status": "ok"}


@router.post("/merge-duplicates")
async def merge_duplicate_users(
    data: MergeDuplicateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Merge duplicate channel users into a target registered user.

    Reassigns ChatSessions from source users to the target user,
    then soft-deletes source users (is_active=False).
    """
    _check_admin(current_user)

    # Validate target user
    target = await db.get(User, data.target_user_id)
    if not target or target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Validate source users
    if not data.source_user_ids:
        raise HTTPException(status_code=400, detail="No source users provided")

    source_users_result = await db.execute(
        select(User).where(User.id.in_(data.source_user_ids))
    )
    source_users = source_users_result.scalars().all()

    if len(source_users) != len(data.source_user_ids):
        raise HTTPException(status_code=400, detail="Some source users not found")

    # Ensure all source users are in the same tenant
    for su in source_users:
        if su.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Cannot merge users from different tenants")

    # Reassign ChatSessions
    reassigned = 0
    for source_id in data.source_user_ids:
        result = await db.execute(
            update(ChatSession)
            .where(ChatSession.user_id == source_id)
            .values(user_id=data.target_user_id)
        )
        reassigned += result.rowcount

    # Reassign OrgMembers from source users to target
    for source_id in data.source_user_ids:
        await db.execute(
            update(OrgMember)
            .where(OrgMember.user_id == source_id)
            .values(user_id=data.target_user_id)
        )

    # Soft-delete source users
    await db.execute(
        update(User)
        .where(User.id.in_(data.source_user_ids))
        .values(is_active=False)
    )

    await db.commit()

    return {
        "status": "ok",
        "merged_count": len(source_users),
        "sessions_reassigned": reassigned,
    }
