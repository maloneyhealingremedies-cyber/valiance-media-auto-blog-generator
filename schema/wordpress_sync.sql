-- =============================================================================
-- WordPress Sync Schema Additions
-- =============================================================================
-- Run this migration to add WordPress sync tracking columns to your existing tables.
-- This enables one-way synchronization from Supabase to WordPress REST API.

-- Add WordPress tracking to blog_categories
-- Maps Supabase categories to WordPress Categories
ALTER TABLE public.blog_categories
ADD COLUMN IF NOT EXISTS wordpress_category_id INTEGER;

ALTER TABLE public.blog_categories
ADD COLUMN IF NOT EXISTS wordpress_synced_at TIMESTAMPTZ;

COMMENT ON COLUMN public.blog_categories.wordpress_category_id IS 'WordPress Category ID';
COMMENT ON COLUMN public.blog_categories.wordpress_synced_at IS 'Timestamp of last successful sync to WordPress';

-- Add WordPress tracking to blog_posts
-- Maps Supabase posts to WordPress Posts
ALTER TABLE public.blog_posts
ADD COLUMN IF NOT EXISTS wordpress_post_id INTEGER;

ALTER TABLE public.blog_posts
ADD COLUMN IF NOT EXISTS wordpress_synced_at TIMESTAMPTZ;

ALTER TABLE public.blog_posts
ADD COLUMN IF NOT EXISTS wordpress_sync_error TEXT;

COMMENT ON COLUMN public.blog_posts.wordpress_post_id IS 'WordPress Post ID';
COMMENT ON COLUMN public.blog_posts.wordpress_synced_at IS 'Timestamp of last successful sync to WordPress';
COMMENT ON COLUMN public.blog_posts.wordpress_sync_error IS 'Error message from last failed sync attempt';

-- Index for finding posts that need syncing
-- A post needs sync if:
-- 1. wordpress_post_id IS NULL (never synced), OR
-- 2. updated_at > wordpress_synced_at (updated since last sync)
CREATE INDEX IF NOT EXISTS idx_blog_posts_wordpress_sync
ON public.blog_posts(wordpress_synced_at, updated_at);

-- Index for finding unsynced categories
CREATE INDEX IF NOT EXISTS idx_blog_categories_wordpress_sync
ON public.blog_categories(wordpress_category_id)
WHERE wordpress_category_id IS NULL;

-- =============================================================================
-- Helper Views (Optional)
-- =============================================================================

-- View to easily see posts needing WordPress sync
CREATE OR REPLACE VIEW public.v_posts_needing_wordpress_sync AS
SELECT
    id,
    slug,
    title,
    status,
    updated_at,
    wordpress_synced_at,
    wordpress_post_id,
    CASE
        WHEN wordpress_post_id IS NULL THEN 'never_synced'
        WHEN updated_at > wordpress_synced_at THEN 'stale'
        ELSE 'synced'
    END as sync_status
FROM public.blog_posts
WHERE wordpress_post_id IS NULL
   OR updated_at > COALESCE(wordpress_synced_at, '1970-01-01'::timestamptz)
ORDER BY updated_at DESC;

-- View to see category WordPress sync status
CREATE OR REPLACE VIEW public.v_categories_wordpress_status AS
SELECT
    id,
    slug,
    name,
    wordpress_category_id,
    wordpress_synced_at,
    CASE
        WHEN wordpress_category_id IS NULL THEN 'not_synced'
        ELSE 'synced'
    END as sync_status
FROM public.blog_categories
ORDER BY sort_order, name;

-- =============================================================================
-- Tag Sync Tracking
-- =============================================================================

-- Add WordPress tracking to blog_tags
ALTER TABLE public.blog_tags
ADD COLUMN IF NOT EXISTS wordpress_tag_id INTEGER;

ALTER TABLE public.blog_tags
ADD COLUMN IF NOT EXISTS wordpress_synced_at TIMESTAMPTZ;

COMMENT ON COLUMN public.blog_tags.wordpress_tag_id IS 'WordPress Tag ID';
COMMENT ON COLUMN public.blog_tags.wordpress_synced_at IS 'Timestamp of last successful sync to WordPress';

-- Index for finding unsynced tags
CREATE INDEX IF NOT EXISTS idx_blog_tags_wordpress_sync
ON public.blog_tags(wordpress_tag_id)
WHERE wordpress_tag_id IS NULL;

-- View to see tag WordPress sync status
CREATE OR REPLACE VIEW public.v_tags_wordpress_status AS
SELECT
    id,
    slug,
    name,
    wordpress_tag_id,
    wordpress_synced_at,
    CASE
        WHEN wordpress_tag_id IS NULL THEN 'not_synced'
        ELSE 'synced'
    END as sync_status
FROM public.blog_tags
ORDER BY name;
