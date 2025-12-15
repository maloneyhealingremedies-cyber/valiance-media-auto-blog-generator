"""
WordPress Sync - CLI handlers for syncing blog content to WordPress

This module provides functions for:
1. Syncing categories to WordPress Categories
2. Syncing posts to WordPress Posts
3. Displaying sync status
4. Bulk sync operations
"""

from datetime import datetime
from typing import Optional
import aiohttp
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SUPABASE_URL, get_supabase_headers, WORDPRESS_DEFAULT_AUTHOR_ID
from tools.wordpress_tools import (
    sync_category_to_wordpress,
    sync_post_to_wordpress,
    get_wordpress_visibility_label,
    clear_sync_cache,
    fetch_all_wordpress_categories,
    fetch_all_wordpress_tags,
    fetch_all_wordpress_posts,
    fetch_wordpress_media,
)


# =============================================================================
# SUPABASE HELPERS
# =============================================================================

async def get_all_categories() -> list:
    """Fetch all categories from Supabase."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_categories?select=*&order=sort_order,name",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []


async def get_category_by_slug(slug: str) -> Optional[dict]:
    """Fetch a single category by slug."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_categories?slug=eq.{slug}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    categories = await resp.json()
                    return categories[0] if categories else None
                return None
    except Exception:
        return None


async def get_category_by_id(category_id: str) -> Optional[dict]:
    """Fetch a single category by ID."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_categories?id=eq.{category_id}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    categories = await resp.json()
                    return categories[0] if categories else None
                return None
    except Exception:
        return None


async def update_category_wordpress_fields(category_id: str, wordpress_category_id: int) -> bool:
    """Update category with WordPress sync info."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.patch(
                f"{SUPABASE_URL}/rest/v1/blog_categories?id=eq.{category_id}",
                headers=headers,
                json={
                    "wordpress_category_id": wordpress_category_id,
                    "wordpress_synced_at": datetime.utcnow().isoformat(),
                }
            ) as resp:
                return resp.status in [200, 204]
    except Exception:
        return False


async def get_all_posts() -> list:
    """Fetch all posts from Supabase with related data."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_posts?select=*,blog_categories(id,slug,name,wordpress_category_id),blog_authors(id,slug,name)&order=updated_at.desc",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return []


async def get_post_by_slug(slug: str) -> Optional[dict]:
    """Fetch a single post by slug with related data."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_posts?slug=eq.{slug}&select=*,blog_categories(id,slug,name,wordpress_category_id),blog_authors(id,slug,name)&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    posts = await resp.json()
                    return posts[0] if posts else None
                return None
    except Exception:
        return None


async def get_post_by_id(post_id: str) -> Optional[dict]:
    """Fetch a single post by ID with related data."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_posts?id=eq.{post_id}&select=*,blog_categories(id,slug,name,wordpress_category_id),blog_authors(id,slug,name)&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    posts = await resp.json()
                    return posts[0] if posts else None
                return None
    except Exception:
        return None


async def get_post_tags(post_id: str) -> list:
    """Fetch tags for a post."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_post_tags?post_id=eq.{post_id}&select=blog_tags(name)",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    return [r['blog_tags']['name'] for r in results if r.get('blog_tags')]
                return []
    except Exception:
        return []


async def update_post_wordpress_fields(
    post_id: str,
    wordpress_post_id: Optional[int] = None,
    error: Optional[str] = None
) -> bool:
    """Update post with WordPress sync info."""
    try:
        update_data = {
            "wordpress_synced_at": datetime.utcnow().isoformat(),
        }
        if wordpress_post_id:
            update_data["wordpress_post_id"] = wordpress_post_id
            update_data["wordpress_sync_error"] = None
        if error:
            update_data["wordpress_sync_error"] = error

        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.patch(
                f"{SUPABASE_URL}/rest/v1/blog_posts?id=eq.{post_id}",
                headers=headers,
                json=update_data
            ) as resp:
                return resp.status in [200, 204]
    except Exception:
        return False


# =============================================================================
# CATEGORY SYNC FUNCTIONS
# =============================================================================

async def sync_all_categories(force: bool = False) -> dict:
    """
    Sync all categories to WordPress.

    Args:
        force: Force re-sync even if already synced (updates existing)

    Returns:
        dict with keys: synced, failed, skipped
    """
    clear_sync_cache()
    categories = await get_all_categories()

    if not categories:
        print("No categories found in database.")
        return {"synced": 0, "failed": 0, "skipped": 0}

    print(f"Found {len(categories)} categories to sync...")
    if force:
        print("Force mode: will re-sync all categories\n")
    else:
        print()

    synced = 0
    failed = 0
    skipped = 0

    for cat in categories:
        cat_id = cat['id']
        name = cat['name']
        slug = cat['slug']
        description = cat.get('description', '')
        existing_id = cat.get('wordpress_category_id')
        seo = cat.get('seo')

        # Skip if already synced and not forcing
        if existing_id and not force:
            print(f"  [SKIP] {name} - already synced")
            skipped += 1
            continue

        # Print status
        if force and existing_id:
            print(f"  Syncing: {name} (force)...", end=" ")
        else:
            print(f"  Syncing: {name}...", end=" ")

        result = await sync_category_to_wordpress(
            category_id=cat_id,
            name=name,
            slug=slug,
            description=description,
            existing_wp_id=existing_id,
            seo=seo,
        )

        if result.get("success"):
            await update_category_wordpress_fields(cat_id, result["wordpress_category_id"])
            seo_warning = result.get("seo_warning")
            if seo_warning:
                print(f"OK (ID: {result['wordpress_category_id']}) [SEO: {seo_warning}]")
            else:
                print(f"OK (ID: {result['wordpress_category_id']})")
            synced += 1
        else:
            print(f"FAILED: {result.get('error', 'Unknown error')}")
            failed += 1

    return {"synced": synced, "failed": failed, "skipped": skipped}


async def sync_category_by_slug(slug: str, force: bool = False) -> bool:
    """
    Sync a single category by slug.

    Args:
        slug: Category slug
        force: Force re-sync even if already synced

    Returns:
        True if successful
    """
    category = await get_category_by_slug(slug)

    if not category:
        print(f"Category not found: {slug}")
        return False

    existing_id = category.get('wordpress_category_id')

    if existing_id and not force:
        print(f"Category '{category['name']}' already synced. Use --force to re-sync.")
        return True

    print(f"Syncing category: {category['name']}...")

    result = await sync_category_to_wordpress(
        category_id=category['id'],
        name=category['name'],
        slug=slug,
        description=category.get('description', ''),
        existing_wp_id=existing_id,
        seo=category.get('seo'),
    )

    if result.get("success"):
        await update_category_wordpress_fields(category['id'], result["wordpress_category_id"])
        seo_warning = result.get("seo_warning")
        if seo_warning:
            print(f"Synced: ID {result['wordpress_category_id']} [SEO: {seo_warning}]")
        else:
            print(f"Synced: ID {result['wordpress_category_id']}")
        return True
    else:
        print(f"Failed: {result.get('error', 'Unknown error')}")
        return False


async def ensure_category_synced(category_id: str) -> Optional[int]:
    """
    Ensure a category is synced to WordPress, syncing if needed.

    Args:
        category_id: Supabase category UUID

    Returns:
        WordPress category ID if successful, None otherwise
    """
    category = await get_category_by_id(category_id)

    if not category:
        return None

    existing_id = category.get('wordpress_category_id')

    if existing_id:
        return existing_id

    # Sync the category
    result = await sync_category_to_wordpress(
        category_id=category_id,
        name=category['name'],
        slug=category['slug'],
        description=category.get('description', ''),
        seo=category.get('seo'),
    )

    if result.get("success"):
        await update_category_wordpress_fields(category_id, result["wordpress_category_id"])
        return result["wordpress_category_id"]

    return None


# =============================================================================
# POST SYNC FUNCTIONS
# =============================================================================

async def sync_post_by_slug(slug: str, force: bool = False) -> bool:
    """
    Sync a single post by slug.

    Args:
        slug: Post slug
        force: Force re-sync even if already synced

    Returns:
        True if successful or skipped, False if failed
    """
    post = await get_post_by_slug(slug)

    if not post:
        print(f"Post not found: {slug}")
        return False

    result = await _sync_single_post(post, force)
    return result in ("synced", "skipped")


async def sync_post_by_id(post_id: str, force: bool = False) -> bool:
    """
    Sync a single post by ID.

    Args:
        post_id: Post UUID
        force: Force re-sync even if already synced

    Returns:
        True if successful or skipped, False if failed
    """
    post = await get_post_by_id(post_id)

    if not post:
        print(f"Post not found: {post_id}")
        return False

    result = await _sync_single_post(post, force)
    return result in ("synced", "skipped")


async def _sync_single_post(post: dict, force: bool = False) -> str:
    """
    Internal function to sync a single post.

    Returns:
        "synced" if successfully synced
        "skipped" if post is up-to-date and not forced
        "failed" if sync failed
    """
    post_id = post['id']
    title = post['title']
    slug = post['slug']
    status = post.get('status', 'draft')
    existing_wp_id = post.get('wordpress_post_id')
    updated_at = post.get('updated_at', '')
    synced_at = post.get('wordpress_synced_at', '')

    # Check if sync is needed
    needs_sync = (
        force or
        not existing_wp_id or
        (updated_at and (not synced_at or updated_at > synced_at))
    )

    if not needs_sync:
        visibility = get_wordpress_visibility_label(status)
        print(f"  [SKIP] {title[:50]} - up-to-date ({visibility})")
        return "skipped"

    # Ensure category is synced first
    category = post.get('blog_categories')
    if not category:
        print(f"  [FAIL] {title[:50]} - no category assigned")
        return "failed"

    wordpress_category_id = category.get('wordpress_category_id')
    if not wordpress_category_id:
        print(f"  Syncing category '{category['name']}' first...")
        wordpress_category_id = await ensure_category_synced(category['id'])
        if not wordpress_category_id:
            print(f"  [FAIL] {title[:50]} - category sync failed")
            return "failed"

    # Get author ID (WordPress uses integer IDs)
    author = post.get('blog_authors', {})
    # WordPress requires user ID, not name - use default
    author_id = WORDPRESS_DEFAULT_AUTHOR_ID

    # Get tags
    tags = await get_post_tags(post_id)

    visibility = get_wordpress_visibility_label(status)
    print(f"  Syncing: {title[:50]}... ({visibility})", end=" ")

    result = await sync_post_to_wordpress(
        post_id=post_id,
        title=title,
        slug=slug,
        excerpt=post.get('excerpt', ''),
        content=post.get('content', []),
        status=status,
        wordpress_category_id=wordpress_category_id,
        author_id=author_id,
        featured_image=post.get('featured_image'),
        featured_image_alt=post.get('featured_image_alt'),
        seo=post.get('seo'),
        scheduled_at=post.get('scheduled_at'),
        tags=tags,
        existing_wordpress_id=existing_wp_id,
    )

    if result.get("success"):
        await update_post_wordpress_fields(post_id, wordpress_post_id=result["wordpress_post_id"])
        print("OK")
        return "synced"
    else:
        error = result.get('error', 'Unknown error')
        await update_post_wordpress_fields(post_id, error=error)
        print(f"FAILED: {error}")
        return "failed"


def _needs_sync(post: dict) -> bool:
    """Check if a post needs syncing."""
    wordpress_post_id = post.get('wordpress_post_id')
    updated_at = post.get('updated_at', '')
    synced_at = post.get('wordpress_synced_at', '')

    # Never synced
    if not wordpress_post_id:
        return True

    # Updated since last sync
    if updated_at and (not synced_at or updated_at > synced_at):
        return True

    return False


async def get_posts_needing_sync() -> list:
    """Get all posts that need syncing to WordPress."""
    posts = await get_all_posts()
    return [p for p in posts if _needs_sync(p)]


async def sync_all_posts(force: bool = False) -> dict:
    """
    Sync all posts to WordPress.

    Args:
        force: Force re-sync even if post appears up-to-date

    Returns:
        dict with keys: synced, failed, skipped
    """
    clear_sync_cache()
    posts = await get_all_posts()

    if not posts:
        print("No posts found in database.")
        return {"synced": 0, "failed": 0, "skipped": 0}

    print(f"Found {len(posts)} post(s) to sync...\n")

    synced = 0
    failed = 0
    skipped = 0

    for post in posts:
        result = await _sync_single_post(post, force=force)
        if result == "synced":
            synced += 1
        elif result == "skipped":
            skipped += 1
        else:
            failed += 1

    return {"synced": synced, "failed": failed, "skipped": skipped}


async def sync_pending_posts() -> dict:
    """
    Sync only posts that need syncing (smart sync).

    Returns:
        dict with keys: synced, failed, skipped
    """
    clear_sync_cache()
    posts = await get_posts_needing_sync()

    if not posts:
        print("No posts need syncing. Use --force to re-sync all.")
        return {"synced": 0, "failed": 0, "skipped": 0}

    print(f"Found {len(posts)} post(s) needing sync...\n")

    synced = 0
    failed = 0

    for post in posts:
        result = await _sync_single_post(post, force=False)
        if result == "synced":
            synced += 1
        else:
            failed += 1

    return {"synced": synced, "failed": failed, "skipped": 0}


async def sync_recent(n: int, force: bool = False) -> dict:
    """
    Sync the N most recently updated posts.

    Args:
        n: Number of posts to sync
        force: Force re-sync even if already synced

    Returns:
        dict with keys: synced, failed, skipped
    """
    clear_sync_cache()
    posts = await get_all_posts()
    posts = posts[:n]  # Already sorted by updated_at desc

    if not posts:
        print("No posts found.")
        return {"synced": 0, "failed": 0, "skipped": 0}

    print(f"Syncing {len(posts)} most recent post(s)...\n")

    synced = 0
    failed = 0
    skipped = 0

    for post in posts:
        result = await _sync_single_post(post, force=force)
        if result == "synced":
            synced += 1
        elif result == "skipped":
            skipped += 1
        else:
            failed += 1

    return {"synced": synced, "failed": failed, "skipped": skipped}


# =============================================================================
# STATUS DISPLAY FUNCTIONS
# =============================================================================

def _format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str[:16] if len(dt_str) >= 16 else dt_str


def _get_sync_status(post: dict) -> tuple:
    """Get sync status emoji and label for a post."""
    wordpress_post_id = post.get('wordpress_post_id')
    wordpress_sync_error = post.get('wordpress_sync_error')
    updated_at = post.get('updated_at', '')
    synced_at = post.get('wordpress_synced_at', '')

    if wordpress_sync_error:
        return ("ERROR", wordpress_sync_error[:30])

    if not wordpress_post_id:
        return ("NOT SYNCED", "")

    if updated_at and synced_at and updated_at > synced_at:
        return ("STALE", "")

    return ("SYNCED", "")


async def show_sync_status() -> None:
    """Print table of post sync status."""
    posts = await get_all_posts()

    if not posts:
        print("No posts found.")
        return

    # Header
    print()
    print(f"{'TITLE':<42} {'STATUS':<10} {'WORDPRESS':<12} {'SYNC STATUS':<14} {'LAST EDIT':<18} {'LAST SYNC':<18}")
    print("-" * 114)

    for post in posts:
        title = post.get('title', '')[:40]
        status = post.get('status', 'draft')
        wp_vis = get_wordpress_visibility_label(status)
        sync_status, sync_note = _get_sync_status(post)
        updated_at = _format_datetime(post.get('updated_at', ''))
        synced_at = _format_datetime(post.get('wordpress_synced_at', ''))

        # Display sync status
        if sync_status == "SYNCED":
            sync_display = "SYNCED"
        elif sync_status == "STALE":
            sync_display = "STALE"
        elif sync_status == "ERROR":
            sync_display = "ERROR"
        else:
            sync_display = "NOT SYNCED"

        print(f"{title:<42} {status:<10} {wp_vis:<12} {sync_display:<14} {updated_at:<18} {synced_at:<18}")

    print()

    # Summary counts
    synced_count = sum(1 for p in posts if p.get('wordpress_post_id') and not _needs_sync(p))
    stale_count = sum(1 for p in posts if p.get('wordpress_post_id') and _needs_sync(p))
    not_synced_count = sum(1 for p in posts if not p.get('wordpress_post_id'))
    error_count = sum(1 for p in posts if p.get('wordpress_sync_error'))

    print(f"Total: {len(posts)} | Synced: {synced_count} | Stale: {stale_count} | Not Synced: {not_synced_count} | Errors: {error_count}")


async def show_category_sync_status() -> None:
    """Print table of category sync status."""
    categories = await get_all_categories()

    if not categories:
        print("No categories found.")
        return

    # Header
    print()
    print(f"{'NAME':<30} {'SLUG':<25} {'SYNC STATUS':<15} {'WP ID':<10} {'LAST SYNC':<18}")
    print("-" * 100)

    for cat in categories:
        name = cat.get('name', '')[:28]
        slug = cat.get('slug', '')[:23]
        wp_id = cat.get('wordpress_category_id')
        synced_at = _format_datetime(cat.get('wordpress_synced_at', ''))

        if wp_id:
            sync_status = "SYNCED"
            wp_id_str = str(wp_id)
        else:
            sync_status = "NOT SYNCED"
            wp_id_str = "—"
            synced_at = "—"

        print(f"{name:<30} {slug:<25} {sync_status:<15} {wp_id_str:<10} {synced_at:<18}")

    print()

    # Summary
    synced_count = sum(1 for c in categories if c.get('wordpress_category_id'))
    not_synced_count = len(categories) - synced_count

    print(f"Total: {len(categories)} | Synced: {synced_count} | Not Synced: {not_synced_count}")


# =============================================================================
# IMPORT FUNCTIONS (CMS -> Supabase)
# =============================================================================

def _decode_html_entities(text: str) -> str:
    """Decode HTML entities in WordPress category names."""
    import html
    if not text:
        return text
    return html.unescape(text)


async def _get_category_by_slug_supabase(slug: str) -> Optional[dict]:
    """Check if a category exists in Supabase by slug."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_categories?slug=eq.{slug}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    categories = await resp.json()
                    return categories[0] if categories else None
                return None
    except Exception:
        return None


async def _insert_category_supabase(category_data: dict) -> tuple[bool, str]:
    """Insert a new category into Supabase.

    Returns:
        Tuple of (success, error_message)
    """
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.post(
                f"{SUPABASE_URL}/rest/v1/blog_categories",
                headers=headers,
                json=category_data
            ) as resp:
                if resp.status in [200, 201]:
                    return True, ""
                else:
                    error_text = await resp.text()
                    return False, f"HTTP {resp.status}: {error_text[:200]}"
    except Exception as e:
        return False, str(e)


async def _update_category_supabase(category_id: str, category_data: dict) -> bool:
    """Update an existing category in Supabase."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.patch(
                f"{SUPABASE_URL}/rest/v1/blog_categories?id=eq.{category_id}",
                headers=headers,
                json=category_data
            ) as resp:
                return resp.status in [200, 204]
    except Exception:
        return False


async def import_categories_from_wordpress(force_pull: bool = False) -> dict:
    """
    Import categories from WordPress into Supabase.

    This is a reverse sync - pulling existing categories from WordPress
    into Supabase. Useful when setting up the generator with an existing blog.

    Args:
        force_pull: If True, overwrite existing Supabase categories with WordPress data.
                   If False (default), skip categories that already exist.

    Returns:
        dict with keys: imported, updated, skipped, errors
    """
    print("Fetching categories from WordPress...")

    wp_categories = await fetch_all_wordpress_categories()

    if not wp_categories:
        print("No categories found in WordPress (or fetch failed).")
        return {"imported": 0, "updated": 0, "skipped": 0, "errors": []}

    print(f"Found {len(wp_categories)} categories in WordPress\n")

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    for wp_cat in wp_categories:
        wp_id = wp_cat.get("id")
        slug = wp_cat.get("slug", "")
        name = _decode_html_entities(wp_cat.get("name", ""))
        description = _decode_html_entities(wp_cat.get("description", ""))

        if not slug:
            errors.append(f"Category {wp_id} has no slug, skipping")
            continue

        # Check if category already exists in Supabase
        existing = await _get_category_by_slug_supabase(slug)

        if existing:
            if force_pull:
                # Update existing category with WordPress data
                update_data = {
                    "name": name,
                    "wordpress_category_id": wp_id,
                    "wordpress_synced_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                # Only update description if WordPress has one
                if description:
                    update_data["description"] = description

                success = await _update_category_supabase(existing["id"], update_data)
                if success:
                    print(f"  [UPDATE] {name} ({slug})")
                    updated += 1
                else:
                    errors.append(f"Failed to update {slug}")
            else:
                print(f"  [SKIP] {name} ({slug}) - already exists")
                skipped += 1
        else:
            # Insert new category
            insert_data = {
                "slug": slug,
                "name": name,
                "description": description or None,
                "wordpress_category_id": wp_id,
                "wordpress_synced_at": datetime.utcnow().isoformat(),
            }

            success, error_msg = await _insert_category_supabase(insert_data)
            if success:
                print(f"  [IMPORT] {name} ({slug})")
                imported += 1
            else:
                print(f"  [FAIL] {name} ({slug}) - {error_msg}")
                errors.append(f"Failed to import {slug}: {error_msg}")

    # Summary
    print()
    print(f"Import complete: {imported} imported, {updated} updated, {skipped} skipped")
    if errors:
        print(f"Errors: {len(errors)}")
        for err in errors[:5]:  # Show first 5 errors
            print(f"  - {err}")

    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


# =============================================================================
# TAG IMPORT (WordPress → Supabase)
# =============================================================================

async def _get_tag_by_slug_supabase(slug: str) -> Optional[dict]:
    """Check if a tag exists in Supabase by slug."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_tags?slug=eq.{slug}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    tags = await resp.json()
                    return tags[0] if tags else None
                return None
    except Exception:
        return None


async def _insert_tag_supabase(tag_data: dict) -> tuple[bool, str]:
    """Insert a new tag into Supabase. Returns (success, error_message)."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.post(
                f"{SUPABASE_URL}/rest/v1/blog_tags",
                headers=headers,
                json=tag_data
            ) as resp:
                if resp.status in [200, 201]:
                    return True, ""
                else:
                    error_text = await resp.text()
                    return False, f"HTTP {resp.status}: {error_text[:200]}"
    except Exception as e:
        return False, str(e)


async def _update_tag_supabase(tag_id: str, update_data: dict) -> bool:
    """Update an existing tag in Supabase."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.patch(
                f"{SUPABASE_URL}/rest/v1/blog_tags?id=eq.{tag_id}",
                headers=headers,
                json=update_data
            ) as resp:
                return resp.status in [200, 204]
    except Exception:
        return False


async def import_tags_from_wordpress(force_pull: bool = False) -> dict:
    """
    Import tags from WordPress into Supabase.

    This is a reverse sync - pulling existing tags from WordPress
    into Supabase. Useful when setting up the generator with an existing blog.

    Args:
        force_pull: If True, overwrite existing Supabase tags with WordPress data.
                   If False (default), skip tags that already exist.

    Returns:
        dict with keys: imported, updated, skipped, errors
    """
    print("Fetching tags from WordPress...")

    wp_tags = await fetch_all_wordpress_tags()

    if not wp_tags:
        print("No tags found in WordPress (or fetch failed).")
        return {"imported": 0, "updated": 0, "skipped": 0, "errors": []}

    print(f"Found {len(wp_tags)} tags in WordPress\n")

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    for wp_tag in wp_tags:
        wp_id = wp_tag.get("id")
        slug = wp_tag.get("slug", "")
        name = _decode_html_entities(wp_tag.get("name", ""))

        if not slug:
            errors.append(f"Tag {wp_id} has no slug, skipping")
            continue

        # Check if tag already exists in Supabase
        existing = await _get_tag_by_slug_supabase(slug)

        if existing:
            if force_pull:
                # Update existing tag with WordPress data
                update_data = {
                    "name": name,
                    "wordpress_tag_id": wp_id,
                    "wordpress_synced_at": datetime.utcnow().isoformat(),
                }

                success = await _update_tag_supabase(existing["id"], update_data)
                if success:
                    print(f"  [UPDATE] {name} ({slug})")
                    updated += 1
                else:
                    errors.append(f"Failed to update {slug}")
            else:
                print(f"  [SKIP] {name} ({slug}) - already exists")
                skipped += 1
        else:
            # Insert new tag
            insert_data = {
                "slug": slug,
                "name": name,
                "wordpress_tag_id": wp_id,
                "wordpress_synced_at": datetime.utcnow().isoformat(),
            }

            success, error_msg = await _insert_tag_supabase(insert_data)
            if success:
                print(f"  [IMPORT] {name} ({slug})")
                imported += 1
            else:
                print(f"  [FAIL] {name} ({slug}) - {error_msg}")
                errors.append(f"Failed to import {slug}: {error_msg}")

    # Summary
    print()
    print(f"Import complete: {imported} imported, {updated} updated, {skipped} skipped")
    if errors:
        print(f"Errors: {len(errors)}")
        for err in errors[:5]:  # Show first 5 errors
            print(f"  - {err}")

    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


# =============================================================================
# POST IMPORT (WordPress → Supabase)
# =============================================================================

def _map_wordpress_status_to_supabase(wp_status: str) -> str:
    """Map WordPress status to Supabase status."""
    mapping = {
        'publish': 'published',
        'draft': 'draft',
        'private': 'archived',
        'future': 'scheduled',
        'pending': 'draft',
        'trash': 'archived',
    }
    return mapping.get(wp_status, 'draft')


def _extract_featured_image_url(wp_post: dict) -> Optional[str]:
    """Extract featured image URL from WordPress post with _embed data."""
    try:
        embedded = wp_post.get("_embedded", {})
        featured_media = embedded.get("wp:featuredmedia", [])
        if featured_media and len(featured_media) > 0:
            media = featured_media[0]
            # Try to get a reasonable size, fall back to source
            sizes = media.get("media_details", {}).get("sizes", {})
            if "large" in sizes:
                return sizes["large"]["source_url"]
            elif "medium_large" in sizes:
                return sizes["medium_large"]["source_url"]
            return media.get("source_url")
    except Exception:
        pass
    return None


def _extract_category_ids(wp_post: dict) -> list:
    """Extract category IDs from WordPress post."""
    return wp_post.get("categories", [])


def _extract_tag_ids(wp_post: dict) -> list:
    """Extract tag IDs from WordPress post."""
    return wp_post.get("tags", [])


async def _get_post_by_slug_supabase(slug: str) -> Optional[dict]:
    """Check if a post exists in Supabase by slug."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_posts?slug=eq.{slug}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    posts = await resp.json()
                    return posts[0] if posts else None
                return None
    except Exception:
        return None


async def _get_category_by_wordpress_id(wp_id: int) -> Optional[dict]:
    """Get Supabase category by WordPress ID."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_categories?wordpress_category_id=eq.{wp_id}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    categories = await resp.json()
                    return categories[0] if categories else None
                return None
    except Exception:
        return None


async def _get_tag_by_wordpress_id(wp_id: int) -> Optional[dict]:
    """Get Supabase tag by WordPress ID."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_tags?wordpress_tag_id=eq.{wp_id}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    tags = await resp.json()
                    return tags[0] if tags else None
                return None
    except Exception:
        return None


async def _get_default_author_id() -> Optional[str]:
    """Get the default author ID from Supabase."""
    from config import DEFAULT_AUTHOR_SLUG
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_authors?slug=eq.{DEFAULT_AUTHOR_SLUG}&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    authors = await resp.json()
                    return authors[0]["id"] if authors else None
                return None
    except Exception:
        return None


async def _insert_post_supabase(post_data: dict) -> tuple[bool, str, Optional[str]]:
    """Insert a new post into Supabase. Returns (success, error_message, post_id)."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            headers["Prefer"] = "return=representation"
            async with session.post(
                f"{SUPABASE_URL}/rest/v1/blog_posts",
                headers=headers,
                json=post_data
            ) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    post_id = result[0]["id"] if result else None
                    return True, "", post_id
                else:
                    error_text = await resp.text()
                    return False, f"HTTP {resp.status}: {error_text[:200]}", None
    except Exception as e:
        return False, str(e), None


async def _update_post_supabase(post_id: str, update_data: dict) -> bool:
    """Update an existing post in Supabase."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.patch(
                f"{SUPABASE_URL}/rest/v1/blog_posts?id=eq.{post_id}",
                headers=headers,
                json=update_data
            ) as resp:
                return resp.status in [200, 204]
    except Exception:
        return False


async def _create_post_tag_relations(post_id: str, tag_ids: list) -> int:
    """Create post-tag relationships. Returns number of relations created."""
    if not tag_ids:
        return 0

    created = 0
    for tag_id in tag_ids:
        try:
            async with aiohttp.ClientSession() as session:
                headers = get_supabase_headers()
                async with session.post(
                    f"{SUPABASE_URL}/rest/v1/blog_post_tags",
                    headers=headers,
                    json={"post_id": post_id, "tag_id": tag_id}
                ) as resp:
                    if resp.status in [200, 201]:
                        created += 1
        except Exception:
            pass
    return created


async def _delete_post_tag_relations(post_id: str) -> bool:
    """Delete all post-tag relationships for a post."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = get_supabase_headers()
            async with session.delete(
                f"{SUPABASE_URL}/rest/v1/blog_post_tags?post_id=eq.{post_id}",
                headers=headers
            ) as resp:
                return resp.status in [200, 204]
    except Exception:
        return False


async def import_posts_from_wordpress(force_pull: bool = False) -> dict:
    """
    Import posts from WordPress into Supabase.

    This is a reverse sync - pulling existing posts from WordPress
    into Supabase. Useful when setting up the generator with an existing blog.

    WordPress HTML content is stored as a single HTML content block in the
    content JSONB field, preserving the original formatting.

    Prerequisites:
    - Import categories first with --wordpress-import-categories
    - Import tags first with --wordpress-import-tags

    Args:
        force_pull: If True, overwrite existing Supabase posts with WordPress data.
                   If False (default), skip posts that already exist.

    Returns:
        dict with keys: imported, updated, skipped, errors
    """
    print("Fetching posts from WordPress...")

    wp_posts = await fetch_all_wordpress_posts()

    if not wp_posts:
        print("No posts found in WordPress (or fetch failed).")
        return {"imported": 0, "updated": 0, "skipped": 0, "errors": []}

    print(f"Found {len(wp_posts)} posts in WordPress\n")

    # Get default author
    default_author_id = await _get_default_author_id()
    if not default_author_id:
        print("Warning: No default author found. Posts will be created without author.")

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    for wp_post in wp_posts:
        wp_id = wp_post.get("id")
        slug = wp_post.get("slug", "")
        title = _decode_html_entities(wp_post.get("title", {}).get("rendered", ""))
        content_html = wp_post.get("content", {}).get("rendered", "")
        excerpt_html = wp_post.get("excerpt", {}).get("rendered", "")
        wp_status = wp_post.get("status", "draft")
        date_str = wp_post.get("date", "")

        if not slug:
            errors.append(f"Post {wp_id} has no slug, skipping")
            continue

        # Clean up excerpt (remove HTML tags for plain text excerpt)
        import re
        excerpt = re.sub(r'<[^>]+>', '', excerpt_html).strip()
        excerpt = _decode_html_entities(excerpt)
        if len(excerpt) > 300:
            excerpt = excerpt[:297] + "..."

        # Store HTML content as a single HTML block
        content_blocks = [{"type": "html", "content": content_html}] if content_html else []

        # Map WordPress status to Supabase status
        status = _map_wordpress_status_to_supabase(wp_status)

        # Get featured image URL
        featured_image = _extract_featured_image_url(wp_post)

        # Resolve category (use first one if multiple)
        wp_category_ids = _extract_category_ids(wp_post)
        category_id = None
        if wp_category_ids:
            cat = await _get_category_by_wordpress_id(wp_category_ids[0])
            if cat:
                category_id = cat["id"]

        # Resolve tags
        wp_tag_ids = _extract_tag_ids(wp_post)
        supabase_tag_ids = []
        for wp_tag_id in wp_tag_ids:
            tag = await _get_tag_by_wordpress_id(wp_tag_id)
            if tag:
                supabase_tag_ids.append(tag["id"])

        # Check if post already exists in Supabase
        existing = await _get_post_by_slug_supabase(slug)

        if existing:
            if force_pull:
                # Update existing post with WordPress data
                update_data = {
                    "title": title,
                    "excerpt": excerpt or "No excerpt available.",
                    "content": content_blocks,
                    "status": status,
                    "featured_image": featured_image,
                    "category_id": category_id,
                    "wordpress_post_id": wp_id,
                    "wordpress_synced_at": datetime.utcnow().isoformat(),
                    "wordpress_sync_error": None,
                }

                success = await _update_post_supabase(existing["id"], update_data)
                if success:
                    # Update tag relations
                    await _delete_post_tag_relations(existing["id"])
                    await _create_post_tag_relations(existing["id"], supabase_tag_ids)
                    print(f"  [UPDATE] {title[:50]}... ({slug})")
                    updated += 1
                else:
                    errors.append(f"Failed to update {slug}")
            else:
                print(f"  [SKIP] {title[:50]}... ({slug}) - already exists")
                skipped += 1
        else:
            # Insert new post
            insert_data = {
                "slug": slug,
                "title": title,
                "excerpt": excerpt or "No excerpt available.",
                "content": content_blocks,
                "status": status,
                "featured_image": featured_image,
                "author_id": default_author_id,
                "category_id": category_id,
                "wordpress_post_id": wp_id,
                "wordpress_synced_at": datetime.utcnow().isoformat(),
            }

            # Parse date if available
            if date_str:
                try:
                    insert_data["created_at"] = date_str
                except Exception:
                    pass

            success, error_msg, new_post_id = await _insert_post_supabase(insert_data)
            if success and new_post_id:
                # Create tag relations
                await _create_post_tag_relations(new_post_id, supabase_tag_ids)
                tag_count = len(supabase_tag_ids)
                tag_info = f" [{tag_count} tags]" if tag_count else ""
                print(f"  [IMPORT] {title[:50]}... ({slug}){tag_info}")
                imported += 1
            else:
                print(f"  [FAIL] {title[:50]}... ({slug}) - {error_msg}")
                errors.append(f"Failed to import {slug}: {error_msg}")

    # Summary
    print()
    print(f"Import complete: {imported} imported, {updated} updated, {skipped} skipped")
    if errors:
        print(f"Errors: {len(errors)}")
        for err in errors[:5]:  # Show first 5 errors
            print(f"  - {err}")

    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


async def import_all_from_wordpress(force_pull: bool = False) -> dict:
    """
    Import all content from WordPress into Supabase.

    Imports in order: categories, tags, posts.

    Args:
        force_pull: If True, overwrite existing Supabase data.

    Returns:
        dict with results for each content type
    """
    results = {}

    print("=" * 60)
    print("IMPORTING CATEGORIES")
    print("=" * 60)
    results["categories"] = await import_categories_from_wordpress(force_pull)
    print()

    print("=" * 60)
    print("IMPORTING TAGS")
    print("=" * 60)
    results["tags"] = await import_tags_from_wordpress(force_pull)
    print()

    print("=" * 60)
    print("IMPORTING POSTS")
    print("=" * 60)
    results["posts"] = await import_posts_from_wordpress(force_pull)
    print()

    # Final summary
    print("=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    total_imported = sum(r.get("imported", 0) for r in results.values())
    total_updated = sum(r.get("updated", 0) for r in results.values())
    total_skipped = sum(r.get("skipped", 0) for r in results.values())
    total_errors = sum(len(r.get("errors", [])) for r in results.values())

    print(f"Total: {total_imported} imported, {total_updated} updated, {total_skipped} skipped, {total_errors} errors")

    return results
