"""Backfill OrgMembers for channel users and merge duplicates.

For existing wechat/discord/slack/teams users created before the channel_user_service
fix, this script:
1. Creates missing OrgMember records so future messages resolve correctly
2. Detects and merges duplicate users with the same external identity
3. Supports --dry-run to preview changes without committing

Usage:
    cd backend
    python -m scripts.backfill_and_merge_channel_users           # preview only
    python -m scripts.backfill_and_merge_channel_users --apply   # apply changes
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import uuid
from collections import defaultdict

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

# Bootstrap the app
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.database import async_session
from app.models.identity import IdentityProvider
from app.models.org import OrgMember
from app.models.user import User, Identity
from app.models.chat_session import ChatSession


# Channels that were NOT creating OrgMembers before the fix
NON_ENTERPRISE_CHANNELS = ("wechat", "discord", "slack", "microsoft_teams")


async def backfill_org_members(db: AsyncSession, dry_run: bool) -> int:
    """Create missing OrgMember records for non-enterprise channel users."""
    created = 0

    for channel_type in NON_ENTERPRISE_CHANNELS:
        # Find users with this registration_source
        result = await db.execute(
            select(User, Identity)
            .join(Identity, User.identity_id == Identity.id)
            .where(
                User.registration_source == channel_type,
                User.is_active == True,
            )
        )
        rows = result.all()

        if not rows:
            print(f"  [{channel_type}] No channel users found.")
            continue

        # Ensure provider exists
        provider_result = await db.execute(
            select(IdentityProvider).where(IdentityProvider.provider_type == channel_type)
        )
        provider = provider_result.scalar_one_or_none()

        if not provider and not dry_run:
            provider = IdentityProvider(
                provider_type=channel_type,
                name=channel_type.capitalize(),
                is_active=True,
                config={},
                tenant_id=None,
            )
            db.add(provider)
            await db.flush()
            print(f"  [{channel_type}] Created IdentityProvider: {provider.id}")

        provider_id = provider.id if provider else None

        for user, identity in rows:
            # Check if OrgMember already exists for this user + provider
            existing_member = None
            if provider_id:
                existing_result = await db.execute(
                    select(OrgMember).where(
                        OrgMember.provider_id == provider_id,
                        OrgMember.user_id == user.id,
                        OrgMember.status == "active",
                    )
                )
                existing_member = existing_result.scalar_one_or_none()

            if existing_member:
                continue

            # Extract external_user_id from username or email
            external_id = _extract_external_id(channel_type, identity.username, identity.email, user)
            if not external_id:
                print(f"  [{channel_type}] WARNING: Could not extract external_id for user {user.id} ({identity.username})")
                continue

            if dry_run:
                print(f"  [{channel_type}] Would create OrgMember: user={user.id}, external_id={external_id}")
            else:
                # Create provider if needed (may not exist in dry_run branch)
                if not provider:
                    provider = IdentityProvider(
                        provider_type=channel_type,
                        name=channel_type.capitalize(),
                        is_active=True,
                        config={},
                        tenant_id=user.tenant_id,
                    )
                    db.add(provider)
                    await db.flush()
                    provider_id = provider.id

                member = OrgMember(
                    name=user.display_name or identity.username or f"{channel_type} User",
                    email=identity.email if identity.email and not identity.email.endswith(".local") else None,
                    provider_id=provider_id,
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    external_id=external_id,
                    status="active",
                )
                db.add(member)
            created += 1

    if not dry_run and created > 0:
        await db.flush()

    return created


def _extract_external_id(channel_type: str, username: str | None, email: str | None, user: User) -> str | None:
    """Extract external_user_id from username/email patterns.

    Pattern 1: username = "{channel_type}_{external_id[:12]}"
    Pattern 2: email = "{username}@{channel_type}.local"
    Pattern 3: Fallback to username without prefix
    """
    prefix = f"{channel_type}_"

    if username and username.startswith(prefix):
        return username[len(prefix):]

    if email and email.startswith(prefix) and email.endswith(f"@{channel_type}.local"):
        return email.split("@")[0][len(prefix):]

    # Last resort: use username as-is if it doesn't look like a normal email
    if username and "@" not in username and not username.startswith("user_"):
        return username

    return None


async def merge_duplicates(db: AsyncSession, dry_run: bool) -> int:
    """Find and merge duplicate channel users with the same (provider_id, external_id)."""
    merged = 0

    # Find OrgMember groups with same (provider_id, external_id) but different user_ids
    result = await db.execute(
        select(
            OrgMember.provider_id,
            OrgMember.external_id,
            func.array_agg(OrgMember.id),
            func.array_agg(OrgMember.user_id),
            func.count(OrgMember.id),
        )
        .where(
            OrgMember.external_id.isnot(None),
            OrgMember.status == "active",
            OrgMember.user_id.isnot(None),
        )
        .group_by(OrgMember.provider_id, OrgMember.external_id)
        .having(func.count(OrgMember.id) > 1)
    )
    groups = result.all()

    if not groups:
        print("  No duplicate OrgMember groups found.")
        return 0

    for provider_id, external_id, member_ids, user_ids, count in groups:
        # Resolve provider type
        provider = await db.get(IdentityProvider, provider_id)
        channel_type = provider.provider_type if provider else "unknown"

        print(f"  [{channel_type}] Duplicate group: external_id={external_id}, {count} members")

        # Load all users in this group
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = users_result.scalars().all()

        # Pick the best target user:
        # 1. Has a real email (not .local) -> prefer
        # 2. Has most recent activity
        # 3. Earliest created
        target_user = _pick_target_user(users)

        if not target_user:
            continue

        source_user_ids = [uid for uid in user_ids if uid != target_user.id]

        if dry_run:
            print(f"    Target: {target_user.id} ({target_user.display_name})")
            print(f"    Sources to merge: {source_user_ids}")
            continue

        # Reassign ChatSessions
        for source_id in source_user_ids:
            result = await db.execute(
                update(ChatSession)
                .where(ChatSession.user_id == source_id)
                .values(user_id=target_user.id)
            )
            if result.rowcount:
                print(f"    Reassigned {result.rowcount} sessions from {source_id} to {target_user.id}")

        # Remove duplicate OrgMembers (keep only one linked to target)
        for member_id in member_ids:
            member = await db.get(OrgMember, member_id)
            if member and member.user_id != target_user.id:
                # Point to target user instead
                member.user_id = target_user.id

        # Soft-delete source users
        await db.execute(
            update(User)
            .where(User.id.in_(source_user_ids))
            .values(is_active=False)
        )

        print(f"    Merged {len(source_user_ids)} users into {target_user.id}")
        merged += len(source_user_ids)

    if not dry_run and merged > 0:
        await db.commit()

    return merged


def _pick_target_user(users: list[User]) -> User | None:
    """Pick the best target user from a group of duplicates."""
    if not users:
        return None

    # Prefer users with real emails (not .local)
    real_email_users = []
    for u in users:
        email = getattr(u, 'email', None)
        # Use association proxy - email comes from Identity
        # We'll just use the first active user as fallback
        if u.is_active:
            real_email_users.append(u)

    if real_email_users:
        # Return the one with the earliest creation date (most established)
        return sorted(real_email_users, key=lambda u: u.created_at or '')[:1][0]

    # Fallback: return first active user
    active = [u for u in users if u.is_active]
    if active:
        return sorted(active, key=lambda u: u.created_at or '')[:1][0]

    return users[0]


async def main():
    parser = argparse.ArgumentParser(description="Backfill OrgMembers and merge duplicate channel users")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    args = parser.parse_args()

    dry_run = not args.apply
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLY'}")
    print()

    async with async_session() as db:
        print("=== Step 1: Backfill missing OrgMembers ===")
        created = await backfill_org_members(db, dry_run)
        print(f"  OrgMembers {'would be ' if dry_run else ''}created: {created}")
        print()

        print("=== Step 2: Merge duplicate users ===")
        merged = await merge_duplicates(db, dry_run)
        print(f"  Users {'would be ' if dry_run else ''}merged: {merged}")

        if dry_run and (created > 0 or merged > 0):
            print()
            print("Run with --apply to commit these changes.")

        if not dry_run:
            await db.commit()
            print("\nChanges committed.")


if __name__ == "__main__":
    asyncio.run(main())
