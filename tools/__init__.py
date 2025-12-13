"""
Blog Generator Tools

These tools allow Claude to interact with the Supabase database
to create and manage blog content autonomously.
"""

from .query_tools import (
    get_blog_context,
    get_sample_post,
    check_slug_exists,
    get_posts_without_images,
    QUERY_TOOLS,
)

from .write_tools import (
    create_blog_post,
    create_category,
    create_tag,
    link_tags_to_post,
    update_post_status,
    update_post_image,
    WRITE_TOOLS,
)

from .idea_tools import (
    get_and_claim_blog_idea,
    complete_blog_idea,
    fail_blog_idea,
    skip_blog_idea,
    get_idea_queue_status,
    IDEA_TOOLS,
)

from .link_tools import (
    get_internal_link_suggestions,
    validate_urls,
    save_post_links,
    get_posts_needing_links,
    get_post_for_linking,
    apply_link_insertions,
    remove_internal_links_from_post,
    cleanup_internal_links,
    LINK_TOOLS,
    BACKFILL_LINK_TOOLS,
)

__all__ = [
    # Query tools
    "get_blog_context",
    "get_sample_post",
    "check_slug_exists",
    "get_posts_without_images",
    "QUERY_TOOLS",
    # Write tools
    "create_blog_post",
    "create_category",
    "create_tag",
    "link_tags_to_post",
    "update_post_status",
    "update_post_image",
    "WRITE_TOOLS",
    # Idea tools
    "get_and_claim_blog_idea",
    "complete_blog_idea",
    "fail_blog_idea",
    "skip_blog_idea",
    "get_idea_queue_status",
    "IDEA_TOOLS",
    # Link tools
    "get_internal_link_suggestions",
    "validate_urls",
    "save_post_links",
    "get_posts_needing_links",
    "get_post_for_linking",
    "apply_link_insertions",
    "cleanup_internal_links",
    "LINK_TOOLS",
    "BACKFILL_LINK_TOOLS",
]
