"""
WordPress Tools - Core functions for syncing blog content to WordPress

This module provides:
1. Application Password authentication (Base64 basic auth)
2. WordPress REST API integration
3. Category and Post sync functions
4. Featured image upload with smart deduplication
5. SEO meta field support for multiple plugins
"""

import base64
import re
from typing import Optional, Any
from datetime import datetime
import aiohttp
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    WORDPRESS_URL,
    WORDPRESS_USERNAME,
    WORDPRESS_APP_PASSWORD,
    WORDPRESS_DEFAULT_AUTHOR_ID,
    WORDPRESS_SEO_PLUGIN,
)

# Import HTML renderer from shopify_tools (reuse existing implementation)
from tools.shopify_tools import render_blocks_to_html


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_wordpress_auth_header() -> Optional[str]:
    """
    Generate Base64 Basic Auth header for WordPress Application Passwords.

    Returns:
        Authorization header value, or None if credentials not configured
    """
    if not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return None

    # Application passwords can have spaces, remove them for encoding
    password = WORDPRESS_APP_PASSWORD.replace(" ", "")
    credentials = f"{WORDPRESS_USERNAME}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def get_wordpress_headers() -> Optional[dict]:
    """
    Get headers for WordPress REST API calls.

    Returns:
        Headers dict, or None if credentials not configured
    """
    auth_header = get_wordpress_auth_header()
    if not auth_header:
        return None

    return {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }


# =============================================================================
# STATUS MAPPING
# =============================================================================

def get_wordpress_status(supabase_status: str) -> str:
    """
    Map Supabase post status to WordPress post status.

    Args:
        supabase_status: Post status from Supabase

    Returns:
        WordPress status string
    """
    mapping = {
        'draft': 'draft',
        'published': 'publish',
        'scheduled': 'future',
        'archived': 'private',
    }
    return mapping.get(supabase_status, 'draft')


def get_wordpress_visibility_label(status: str) -> str:
    """Get human-readable WordPress visibility for a given status."""
    mapping = {
        'draft': 'Draft',
        'published': 'Published',
        'scheduled': 'Scheduled',
        'archived': 'Private',
    }
    return mapping.get(status, 'Draft')


# =============================================================================
# REST API HELPERS
# =============================================================================

def get_wordpress_api_url(endpoint: str) -> str:
    """Get the full WordPress REST API URL for an endpoint."""
    base = WORDPRESS_URL.rstrip('/')
    return f"{base}/wp-json/wp/v2/{endpoint.lstrip('/')}"


async def execute_wordpress_request(
    endpoint: str,
    method: str = "GET",
    data: dict = None,
    params: dict = None,
) -> dict:
    """
    Execute a REST API request against WordPress.

    Args:
        endpoint: API endpoint (e.g., "posts", "categories/123")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body for POST/PUT
        params: Query parameters for GET

    Returns:
        Response data or error dict
    """
    if not WORDPRESS_URL or not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return {"error": "WordPress credentials not configured"}

    headers = get_wordpress_headers()
    if not headers:
        return {"error": "Failed to generate WordPress auth headers"}

    url = get_wordpress_api_url(endpoint)

    try:
        async with aiohttp.ClientSession() as session:
            kwargs = {
                "headers": headers,
                "timeout": aiohttp.ClientTimeout(total=60),
            }

            if data and method in ("POST", "PUT", "PATCH"):
                kwargs["json"] = data
            if params:
                kwargs["params"] = params

            async with session.request(method, url, **kwargs) as resp:
                # Handle different response types
                if resp.status == 204:  # No content (successful DELETE)
                    return {"success": True}

                try:
                    result = await resp.json()
                except:
                    text = await resp.text()
                    return {"error": f"Invalid JSON response: {text[:200]}"}

                # Check for WordPress error response
                if resp.status >= 400:
                    error_msg = result.get("message", str(result))
                    error_code = result.get("code", "unknown")
                    return {"error": f"{error_code}: {error_msg}"}

                return result

    except aiohttp.ClientError as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


# =============================================================================
# LOOKUP FUNCTIONS (Duplicate Prevention)
# =============================================================================

# In-memory cache to prevent race conditions during a single sync session
_category_cache: dict[str, int] = {}  # slug -> id
_post_cache: dict[str, int] = {}  # slug -> id
_tag_cache: dict[str, int] = {}  # name -> id


def clear_sync_cache():
    """Clear the in-memory sync cache. Call at start of sync operations."""
    global _category_cache, _post_cache, _tag_cache
    _category_cache = {}
    _post_cache = {}
    _tag_cache = {}


async def fetch_all_wordpress_categories() -> list:
    """
    Fetch all categories from WordPress.

    Returns a list of category dicts with: id, name, slug, description
    Handles pagination automatically.

    Returns:
        List of WordPress category dicts, or empty list on error
    """
    if not WORDPRESS_URL or not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return []

    all_categories = []
    page = 1
    per_page = 100

    while True:
        result = await execute_wordpress_request(
            "categories",
            params={"per_page": per_page, "page": page}
        )

        # Check for error response
        if isinstance(result, dict) and "error" in result:
            if page == 1:
                print(f"Error fetching categories: {result['error']}")
            break

        # Result should be a list
        if not isinstance(result, list):
            break

        if not result:
            break

        all_categories.extend(result)

        # Check if we got fewer than requested (last page)
        if len(result) < per_page:
            break

        page += 1

    return all_categories


async def fetch_all_wordpress_tags() -> list:
    """
    Fetch all tags from WordPress.

    Returns a list of tag dicts with: id, name, slug, description
    Handles pagination automatically.

    Returns:
        List of WordPress tag dicts, or empty list on error
    """
    if not WORDPRESS_URL or not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return []

    all_tags = []
    page = 1
    per_page = 100

    while True:
        result = await execute_wordpress_request(
            "tags",
            params={"per_page": per_page, "page": page}
        )

        # Check for error response
        if isinstance(result, dict) and "error" in result:
            if page == 1:
                print(f"Error fetching tags: {result['error']}")
            break

        # Result should be a list
        if not isinstance(result, list):
            break

        if not result:
            break

        all_tags.extend(result)

        # Check if we got fewer than requested (last page)
        if len(result) < per_page:
            break

        page += 1

    return all_tags


async def fetch_all_wordpress_posts(include_content: bool = True) -> list:
    """
    Fetch all posts from WordPress.

    Returns a list of post dicts with full details including:
    id, title, slug, content, excerpt, status, date, categories, tags, featured_media

    Handles pagination automatically.

    Args:
        include_content: If True, include full content. If False, only metadata.

    Returns:
        List of WordPress post dicts, or empty list on error
    """
    if not WORDPRESS_URL or not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return []

    all_posts = []
    page = 1
    per_page = 100

    while True:
        params = {
            "per_page": per_page,
            "page": page,
            "status": "any",  # Include all statuses
            "_embed": "true",  # Include embedded data (author, featured media, etc.)
        }

        result = await execute_wordpress_request("posts", params=params)

        # Check for error response
        if isinstance(result, dict) and "error" in result:
            if page == 1:
                print(f"Error fetching posts: {result['error']}")
            break

        # Result should be a list
        if not isinstance(result, list):
            break

        if not result:
            break

        all_posts.extend(result)

        # Check if we got fewer than requested (last page)
        if len(result) < per_page:
            break

        page += 1

    return all_posts


async def fetch_wordpress_media(media_id: int) -> Optional[str]:
    """
    Fetch media URL from WordPress by ID.

    Args:
        media_id: WordPress media attachment ID

    Returns:
        URL of the media file, or None if not found
    """
    if not media_id:
        return None

    result = await execute_wordpress_request(f"media/{media_id}")

    if isinstance(result, dict) and "source_url" in result:
        return result.get("source_url")

    return None


async def find_category_by_slug(slug: str) -> Optional[int]:
    """
    Find an existing WordPress category by slug.

    Args:
        slug: Category slug to search for

    Returns:
        WordPress category ID if found, None otherwise
    """
    # Check in-memory cache first
    if slug in _category_cache:
        return _category_cache[slug]

    result = await execute_wordpress_request(
        "categories",
        params={"slug": slug, "per_page": 1}
    )

    if isinstance(result, list) and len(result) > 0:
        cat_id = result[0].get("id")
        _category_cache[slug] = cat_id
        return cat_id

    return None


async def find_post_by_slug(slug: str) -> Optional[int]:
    """
    Find an existing WordPress post by slug.

    Args:
        slug: Post slug to search for

    Returns:
        WordPress post ID if found, None otherwise
    """
    # Check in-memory cache first
    if slug in _post_cache:
        return _post_cache[slug]

    # Search all statuses
    result = await execute_wordpress_request(
        "posts",
        params={"slug": slug, "per_page": 1, "status": "any"}
    )

    if isinstance(result, list) and len(result) > 0:
        post_id = result[0].get("id")
        _post_cache[slug] = post_id
        return post_id

    return None


async def find_tag_by_name(name: str) -> Optional[int]:
    """
    Find an existing WordPress tag by name.

    Args:
        name: Tag name to search for

    Returns:
        WordPress tag ID if found, None otherwise
    """
    # Check in-memory cache first
    if name in _tag_cache:
        return _tag_cache[name]

    # Search by slug (derived from name)
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    result = await execute_wordpress_request(
        "tags",
        params={"slug": slug, "per_page": 1}
    )

    if isinstance(result, list) and len(result) > 0:
        tag_id = result[0].get("id")
        _tag_cache[name] = tag_id
        return tag_id

    return None


async def find_or_create_tag(name: str) -> Optional[int]:
    """
    Find an existing WordPress tag or create a new one.

    Args:
        name: Tag name

    Returns:
        WordPress tag ID, or None if creation failed
    """
    # First try to find existing
    existing_id = await find_tag_by_name(name)
    if existing_id:
        return existing_id

    # Create new tag
    result = await execute_wordpress_request(
        "tags",
        method="POST",
        data={"name": name}
    )

    if "error" in result:
        # Check if it's a duplicate error (race condition)
        if "term_exists" in str(result.get("error", "")):
            # Try to find it again
            return await find_tag_by_name(name)
        print(f"Warning: Failed to create tag '{name}': {result['error']}")
        return None

    tag_id = result.get("id")
    if tag_id:
        _tag_cache[name] = tag_id
    return tag_id


async def resolve_tags(tag_names: list) -> list[int]:
    """
    Resolve a list of tag names to WordPress tag IDs.
    Creates tags that don't exist.

    Args:
        tag_names: List of tag name strings

    Returns:
        List of WordPress tag IDs
    """
    tag_ids = []
    for name in tag_names:
        tag_id = await find_or_create_tag(name)
        if tag_id:
            tag_ids.append(tag_id)
    return tag_ids


# =============================================================================
# FEATURED IMAGE HANDLING
# =============================================================================

async def find_attachment_by_filename(filename: str) -> Optional[dict]:
    """
    Find an existing media attachment by filename.

    Args:
        filename: Filename to search for (e.g., "my-post-featured.jpg")

    Returns:
        Attachment dict with id and meta, or None if not found
    """
    # WordPress media search by slug (filename without extension)
    slug = filename.rsplit('.', 1)[0] if '.' in filename else filename

    result = await execute_wordpress_request(
        "media",
        params={"slug": slug, "per_page": 1}
    )

    if isinstance(result, list) and len(result) > 0:
        attachment = result[0]
        return {
            "id": attachment.get("id"),
            "meta": attachment.get("meta", {}),
            "source_url": attachment.get("source_url"),
        }

    return None


async def delete_attachment(attachment_id: int) -> bool:
    """
    Delete a media attachment from WordPress.

    Args:
        attachment_id: WordPress attachment ID

    Returns:
        True if successful
    """
    result = await execute_wordpress_request(
        f"media/{attachment_id}",
        method="DELETE",
        params={"force": "true"}
    )
    return "error" not in result


async def upload_image_to_wordpress(
    image_url: str,
    filename: str,
    alt_text: str = "",
) -> Optional[int]:
    """
    Download an image from URL and upload to WordPress Media Library.

    Args:
        image_url: Source URL to download from
        filename: Target filename in WordPress
        alt_text: Alt text for the image

    Returns:
        WordPress attachment ID, or None if upload failed
    """
    if not WORDPRESS_URL or not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return None

    try:
        # Download image from source URL
        async with aiohttp.ClientSession() as session:
            async with session.get(
                image_url,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    print(f"Failed to download image: HTTP {resp.status}")
                    return None

                image_data = await resp.read()
                content_type = resp.headers.get("Content-Type", "image/jpeg")

        # Upload to WordPress
        auth_header = get_wordpress_auth_header()
        upload_url = get_wordpress_api_url("media")

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": auth_header,
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": content_type,
            }

            async with session.post(
                upload_url,
                headers=headers,
                data=image_data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status not in (200, 201):
                    error_text = await resp.text()
                    print(f"Failed to upload image: {error_text[:200]}")
                    return None

                result = await resp.json()
                attachment_id = result.get("id")

                # Update alt text and source meta if we got an ID
                if attachment_id and (alt_text or image_url):
                    meta_update = {}
                    if alt_text:
                        meta_update["alt_text"] = alt_text
                    # Store source URL for deduplication
                    meta_update["_supabase_source_url"] = image_url

                    await execute_wordpress_request(
                        f"media/{attachment_id}",
                        method="POST",
                        data=meta_update
                    )

                return attachment_id

    except Exception as e:
        print(f"Error uploading image: {e}")
        return None


async def sync_featured_image(
    supabase_url: str,
    post_slug: str,
    alt_text: str = "",
) -> Optional[int]:
    """
    Sync a featured image to WordPress with smart deduplication.

    If the image already exists and hasn't changed, returns existing ID.
    If the image changed (different URL), deletes old and uploads new.
    If image doesn't exist, uploads new.

    Args:
        supabase_url: Source image URL from Supabase
        post_slug: Post slug for generating filename
        alt_text: Alt text for the image

    Returns:
        WordPress attachment ID, or None if sync failed
    """
    if not supabase_url:
        return None

    # Generate deterministic filename
    # Extract extension from URL if possible
    ext = "jpg"
    if "." in supabase_url.split("/")[-1]:
        url_ext = supabase_url.split(".")[-1].split("?")[0].lower()
        if url_ext in ("jpg", "jpeg", "png", "gif", "webp"):
            ext = url_ext
    filename = f"{post_slug}-featured.{ext}"

    # Check for existing attachment
    existing = await find_attachment_by_filename(filename)

    if existing:
        # Check if source URL changed
        stored_url = existing.get("meta", {}).get("_supabase_source_url", "")

        if stored_url == supabase_url:
            # Same image, reuse existing attachment
            return existing["id"]
        else:
            # Image changed, delete old attachment
            await delete_attachment(existing["id"])

    # Upload new image
    attachment_id = await upload_image_to_wordpress(supabase_url, filename, alt_text)
    return attachment_id


# =============================================================================
# SEO META FIELDS
# =============================================================================

def build_seo_meta(seo_data, plugin: str = None) -> dict:
    """
    Build WordPress meta fields for SEO based on the configured plugin.

    Args:
        seo_data: Dict or JSON string with keys like 'title', 'description', 'keywords'
        plugin: SEO plugin name (or uses WORDPRESS_SEO_PLUGIN config)

    Returns:
        Dict of meta fields to include in post data
    """
    if not seo_data:
        return {}

    # Handle JSON string input (Supabase JSONB sometimes comes as string)
    if isinstance(seo_data, str):
        try:
            import json
            seo_data = json.loads(seo_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    if not isinstance(seo_data, dict):
        return {}

    plugin = plugin or WORDPRESS_SEO_PLUGIN
    if plugin == "none" or not plugin:
        return {}

    meta = {}
    title = seo_data.get("title", "")
    description = seo_data.get("description", "")
    keywords = seo_data.get("keywords", [])

    # Convert keywords list to string if needed
    if isinstance(keywords, list):
        keywords = ", ".join(keywords)

    if plugin == "yoast":
        # Yoast SEO
        if title:
            meta["_yoast_wpseo_title"] = title
        if description:
            meta["_yoast_wpseo_metadesc"] = description
        if keywords:
            meta["_yoast_wpseo_focuskw"] = keywords.split(",")[0].strip() if keywords else ""

    elif plugin == "rankmath":
        # RankMath SEO
        if title:
            meta["rank_math_title"] = title
        if description:
            meta["rank_math_description"] = description
        if keywords:
            meta["rank_math_focus_keyword"] = keywords

    elif plugin == "aioseo":
        # All in One SEO
        if title:
            meta["_aioseo_title"] = title
        if description:
            meta["_aioseo_description"] = description
        if keywords:
            meta["_aioseo_keywords"] = keywords

    elif plugin == "seopress":
        # SEOPress
        if title:
            meta["_seopress_titles_title"] = title
        if description:
            meta["_seopress_titles_desc"] = description

    elif plugin == "flavor":
        # The SEO Framework (also known as flavor/genesis)
        if title:
            meta["_genesis_title"] = title
        if description:
            meta["_genesis_description"] = description

    return meta


# =============================================================================
# YOAST CATEGORY SEO (Custom Endpoint)
# =============================================================================

async def update_yoast_term_seo(
    term_id: int,
    seo_data: dict,
    taxonomy: str = "category",
) -> dict:
    """
    Update Yoast SEO meta for a category/term via custom REST endpoint.

    Yoast stores taxonomy SEO in the 'wpseo_taxonomy_meta' option rather than
    as individual term meta. This requires a custom endpoint to be installed
    on the WordPress site (see docs/setup/wordpress/yoast-category-seo-endpoint.php).

    Args:
        term_id: WordPress term/category ID
        seo_data: Dict or JSON string with 'title', 'description', 'keywords'
        taxonomy: Taxonomy name (default: 'category')

    Returns:
        dict with keys: success, error (if failed)
    """
    if not seo_data:
        return {"success": True, "skipped": True}

    # Handle JSON string input
    if isinstance(seo_data, str):
        try:
            import json
            seo_data = json.loads(seo_data)
        except (json.JSONDecodeError, TypeError):
            return {"success": True, "skipped": True}

    if not isinstance(seo_data, dict):
        return {"success": True, "skipped": True}

    title = seo_data.get("title", "")
    description = seo_data.get("description", "")
    keywords = seo_data.get("keywords", [])

    # Convert keywords list to string (use first keyword as focus keyword)
    focus_keyword = ""
    if isinstance(keywords, list) and keywords:
        focus_keyword = keywords[0]
    elif isinstance(keywords, str) and keywords:
        focus_keyword = keywords.split(",")[0].strip()

    # Skip if no SEO data to update
    if not title and not description and not focus_keyword:
        return {"success": True, "skipped": True}

    # Build request data
    request_data = {
        "term_id": term_id,
        "taxonomy": taxonomy,
    }
    if title:
        request_data["title"] = title
    if description:
        request_data["description"] = description
    if focus_keyword:
        request_data["focus_keyword"] = focus_keyword

    # Call the custom endpoint
    # Note: This uses a different base URL than the standard WP REST API
    if not WORDPRESS_URL or not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return {"success": False, "error": "WordPress credentials not configured"}

    headers = get_wordpress_headers()
    if not headers:
        return {"success": False, "error": "Failed to generate auth headers"}

    url = f"{WORDPRESS_URL.rstrip('/')}/wp-json/blog-generator/v1/yoast-term-seo"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 404:
                    # Custom endpoint not installed
                    return {
                        "success": False,
                        "error": "Yoast endpoint not installed. See docs/setup/wordpress/yoast-category-seo-endpoint.php"
                    }

                try:
                    result = await resp.json()
                except:
                    text = await resp.text()
                    return {"success": False, "error": f"Invalid response: {text[:100]}"}

                if resp.status >= 400:
                    error_msg = result.get("message", str(result))
                    return {"success": False, "error": error_msg}

                return {"success": True, "updated": result.get("updated", False)}

    except aiohttp.ClientError as e:
        return {"success": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


# =============================================================================
# CATEGORY SYNC
# =============================================================================

async def sync_category_to_wordpress(
    category_id: str,
    name: str,
    slug: str,
    description: str = "",
    existing_wp_id: Optional[int] = None,
    seo: Optional[dict] = None,
) -> dict:
    """
    Sync a Supabase category to a WordPress Category.

    Args:
        category_id: Supabase category UUID
        name: Category name
        slug: Category slug
        description: Category description
        existing_wp_id: Existing WordPress category ID if updating
        seo: SEO data dict with 'title', 'description', 'keywords'

    Returns:
        dict with keys: success, wordpress_category_id, error
    """
    # If no existing ID provided, check if category already exists in WordPress
    if not existing_wp_id:
        existing_wp_id = await find_category_by_slug(slug)

    # Build category data
    category_data = {
        "name": name,
        "slug": slug,
    }

    if description:
        category_data["description"] = description

    # Build SEO meta for the category
    # Most SEO plugins use the same meta keys for terms as they do for posts
    # The meta will be applied if the SEO plugin registers its meta for REST API
    seo_meta = build_seo_meta(seo)
    if seo_meta:
        category_data["meta"] = seo_meta
        # Note: WordPress may silently ignore meta if the plugin hasn't registered
        # the meta keys with show_in_rest=true for terms

    if existing_wp_id:
        # Update existing category
        result = await execute_wordpress_request(
            f"categories/{existing_wp_id}",
            method="POST",
            data=category_data
        )

        if "error" in result:
            # Check if it's a "not found" error - category may have been deleted
            if "rest_term_invalid" in str(result.get("error", "")):
                # Fall back to checking by slug
                existing_wp_id = await find_category_by_slug(slug)
                if not existing_wp_id:
                    # Category truly doesn't exist, create it
                    existing_wp_id = None
            else:
                return {"success": False, "error": result["error"]}

        if existing_wp_id and "id" in result:
            _category_cache[slug] = result["id"]
            wp_cat_id = result["id"]

            # Handle Yoast SEO separately (uses custom endpoint)
            seo_warning = await _handle_yoast_category_seo(wp_cat_id, seo)

            response = {
                "success": True,
                "wordpress_category_id": wp_cat_id,
            }
            if seo_warning:
                response["seo_warning"] = seo_warning
            return response

    if not existing_wp_id:
        # Create new category
        result = await execute_wordpress_request(
            "categories",
            method="POST",
            data=category_data
        )

        if "error" in result:
            # Check if it's a duplicate error
            if "term_exists" in str(result.get("error", "")):
                # Try to find it
                found_id = await find_category_by_slug(slug)
                if found_id:
                    # Handle Yoast SEO for found category
                    seo_warning = await _handle_yoast_category_seo(found_id, seo)
                    response = {
                        "success": True,
                        "wordpress_category_id": found_id,
                    }
                    if seo_warning:
                        response["seo_warning"] = seo_warning
                    return response
            return {"success": False, "error": result["error"]}

        cat_id = result.get("id")
        if cat_id:
            _category_cache[slug] = cat_id

            # Handle Yoast SEO separately (uses custom endpoint)
            seo_warning = await _handle_yoast_category_seo(cat_id, seo)

            response = {
                "success": True,
                "wordpress_category_id": cat_id,
            }
            if seo_warning:
                response["seo_warning"] = seo_warning
            return response

    return {"success": False, "error": "Unknown error during category sync"}


async def _handle_yoast_category_seo(wp_category_id: int, seo_data) -> Optional[str]:
    """
    Handle Yoast SEO update for a category after sync.

    Returns:
        Warning message if Yoast SEO update failed, None otherwise
    """
    if WORDPRESS_SEO_PLUGIN != "yoast":
        return None

    if not seo_data:
        return None

    yoast_result = await update_yoast_term_seo(wp_category_id, seo_data)

    if not yoast_result.get("success") and not yoast_result.get("skipped"):
        return yoast_result.get("error", "Yoast SEO update failed")

    return None


# =============================================================================
# POST SYNC
# =============================================================================

async def sync_post_to_wordpress(
    post_id: str,
    title: str,
    slug: str,
    excerpt: str,
    content: list,
    status: str,
    wordpress_category_id: int,
    author_id: Optional[str] = None,
    featured_image: Optional[str] = None,
    featured_image_alt: Optional[str] = None,
    seo: Optional[dict] = None,
    scheduled_at: Optional[str] = None,
    tags: Optional[list] = None,
    existing_wordpress_id: Optional[int] = None,
) -> dict:
    """
    Sync a blog post to WordPress.

    Args:
        post_id: Supabase post UUID
        title: Post title
        slug: Post slug
        excerpt: Post excerpt
        content: JSON content blocks array
        status: Post status (draft/published/scheduled/archived)
        wordpress_category_id: WordPress category ID
        author_id: WordPress author user ID (or uses default)
        featured_image: Featured image URL from Supabase
        featured_image_alt: Featured image alt text
        seo: SEO data dict
        scheduled_at: ISO 8601 datetime for scheduled posts
        tags: List of tag names
        existing_wordpress_id: Existing WordPress post ID if updating

    Returns:
        dict with keys: success, wordpress_post_id, error
    """
    # Render content blocks to HTML
    body_html = render_blocks_to_html(content)

    # Map status
    wp_status = get_wordpress_status(status)

    # Build post data
    post_data = {
        "title": title,
        "slug": slug,
        "content": body_html,
        "excerpt": excerpt,
        "status": wp_status,
        "categories": [wordpress_category_id],
    }

    # Set author
    wp_author_id = author_id or WORDPRESS_DEFAULT_AUTHOR_ID
    if wp_author_id:
        try:
            post_data["author"] = int(wp_author_id)
        except ValueError:
            pass  # Skip invalid author ID

    # Handle scheduled posts
    if status == "scheduled" and scheduled_at:
        post_data["date"] = scheduled_at
        post_data["date_gmt"] = scheduled_at

    # Resolve and add tags
    if tags:
        tag_ids = await resolve_tags(tags)
        if tag_ids:
            post_data["tags"] = tag_ids

    # Build SEO meta fields
    seo_meta = build_seo_meta(seo)
    if seo_meta:
        post_data["meta"] = seo_meta

    # If no existing ID provided, check if post already exists in WordPress
    if not existing_wordpress_id:
        existing_wordpress_id = await find_post_by_slug(slug)

    # Handle featured image (upload to WP Media Library)
    featured_media_id = None
    if featured_image:
        featured_media_id = await sync_featured_image(
            featured_image,
            slug,
            featured_image_alt or f"Featured image for {title}"
        )

    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    if existing_wordpress_id:
        # Update existing post
        result = await execute_wordpress_request(
            f"posts/{existing_wordpress_id}",
            method="POST",
            data=post_data
        )

        if "error" in result:
            # Check if it's a "not found" error - post may have been deleted
            error_str = str(result.get("error", ""))
            if "rest_post_invalid_id" in error_str or "Invalid post ID" in error_str:
                # Fall back to checking by slug
                existing_wordpress_id = await find_post_by_slug(slug)
                if not existing_wordpress_id:
                    # Post truly doesn't exist, create it
                    existing_wordpress_id = None
            else:
                return {"success": False, "error": result["error"]}

        if existing_wordpress_id and "id" in result:
            _post_cache[slug] = result["id"]
            return {
                "success": True,
                "wordpress_post_id": result["id"],
            }

    if not existing_wordpress_id:
        # Create new post
        result = await execute_wordpress_request(
            "posts",
            method="POST",
            data=post_data
        )

        if "error" in result:
            return {"success": False, "error": result["error"]}

        wp_post_id = result.get("id")
        if wp_post_id:
            _post_cache[slug] = wp_post_id
            return {
                "success": True,
                "wordpress_post_id": wp_post_id,
            }

    return {"success": False, "error": "Unknown error during post sync"}
