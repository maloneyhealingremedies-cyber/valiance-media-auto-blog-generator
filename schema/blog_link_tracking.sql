-- =============================================================================
-- Blog Link Tracking Schema
-- =============================================================================
-- Adds link tracking to the blog system. Run after blog_tables.sql.
--
-- Tables: blog_post_links
-- Views: v_broken_links, v_post_link_stats, v_internal_backlinks, v_external_domains
-- =============================================================================

-- =============================================================================
-- 1. BLOG POST LINKS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.blog_post_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source post
    post_id UUID NOT NULL,

    -- Link details
    url TEXT NOT NULL,
    anchor_text TEXT,
    link_type TEXT NOT NULL,                -- 'internal' or 'external'

    -- Internal link target (NULL if external or target deleted)
    linked_post_id UUID,

    -- External link domain (e.g., 'pga.com')
    domain TEXT,

    -- Link attributes
    opens_new_tab BOOLEAN DEFAULT false,
    is_nofollow BOOLEAN DEFAULT false,

    -- Validation tracking
    is_valid BOOLEAN DEFAULT true,
    last_validated_at TIMESTAMPTZ,
    last_status_code INTEGER,
    redirect_url TEXT,
    validation_error TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Constraints
    CONSTRAINT blog_post_links_post_id_fkey
        FOREIGN KEY (post_id) REFERENCES public.blog_posts(id) ON DELETE CASCADE,
    CONSTRAINT blog_post_links_linked_post_id_fkey
        FOREIGN KEY (linked_post_id) REFERENCES public.blog_posts(id) ON DELETE SET NULL,
    CONSTRAINT blog_post_links_type_check
        CHECK (link_type IN ('internal', 'external')),
    CONSTRAINT blog_post_links_external_has_domain
        CHECK (link_type = 'internal' OR domain IS NOT NULL)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_post_links_post_id ON public.blog_post_links(post_id);
CREATE INDEX IF NOT EXISTS idx_post_links_linked_post ON public.blog_post_links(linked_post_id) WHERE linked_post_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_post_links_domain ON public.blog_post_links(domain) WHERE link_type = 'external';
CREATE INDEX IF NOT EXISTS idx_post_links_invalid ON public.blog_post_links(is_valid, post_id) WHERE is_valid = false;
CREATE INDEX IF NOT EXISTS idx_post_links_stale_validation ON public.blog_post_links(last_validated_at) WHERE last_validated_at IS NOT NULL;

-- Enable RLS
ALTER TABLE public.blog_post_links ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Public read access for links of published posts"
    ON public.blog_post_links FOR SELECT
    USING (EXISTS (SELECT 1 FROM public.blog_posts WHERE id = post_id AND status = 'published'));

CREATE POLICY "Service role full access for post links"
    ON public.blog_post_links FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_blog_post_links_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_blog_post_links_updated_at ON public.blog_post_links;
CREATE TRIGGER trigger_blog_post_links_updated_at
    BEFORE UPDATE ON public.blog_post_links
    FOR EACH ROW
    EXECUTE FUNCTION update_blog_post_links_updated_at();

-- Mark internal links invalid when target post is deleted
CREATE OR REPLACE FUNCTION mark_orphaned_internal_links()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.blog_post_links
    SET is_valid = false, validation_error = 'Target post was deleted', updated_at = now()
    WHERE linked_post_id = OLD.id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_mark_orphaned_links ON public.blog_posts;
CREATE TRIGGER trigger_mark_orphaned_links
    BEFORE DELETE ON public.blog_posts
    FOR EACH ROW
    EXECUTE FUNCTION mark_orphaned_internal_links();


-- =============================================================================
-- 2. HELPER VIEWS
-- =============================================================================

-- Broken links with post context
CREATE OR REPLACE VIEW public.v_broken_links AS
SELECT
    l.id AS link_id, l.url, l.anchor_text, l.link_type, l.domain,
    l.last_status_code, l.validation_error, l.last_validated_at, l.redirect_url,
    p.id AS post_id, p.slug AS post_slug, p.title AS post_title, p.status AS post_status
FROM public.blog_post_links l
JOIN public.blog_posts p ON l.post_id = p.id
WHERE l.is_valid = false
ORDER BY l.last_validated_at DESC NULLS LAST;

-- Link counts per post
CREATE OR REPLACE VIEW public.v_post_link_stats AS
SELECT
    p.id AS post_id, p.slug, p.title, p.status, p.created_at AS post_created_at,
    COALESCE(COUNT(l.id), 0) AS total_links,
    COALESCE(COUNT(l.id) FILTER (WHERE l.link_type = 'internal'), 0) AS internal_links,
    COALESCE(COUNT(l.id) FILTER (WHERE l.link_type = 'external'), 0) AS external_links,
    COALESCE(COUNT(l.id) FILTER (WHERE l.is_valid = false), 0) AS broken_links
FROM public.blog_posts p
LEFT JOIN public.blog_post_links l ON p.id = l.post_id
GROUP BY p.id, p.slug, p.title, p.status, p.created_at
ORDER BY p.created_at DESC;

-- Internal backlinks (which posts link to which)
CREATE OR REPLACE VIEW public.v_internal_backlinks AS
SELECT
    l.linked_post_id AS target_post_id, target.slug AS target_slug, target.title AS target_title,
    l.post_id AS source_post_id, source.slug AS source_slug, source.title AS source_title,
    source.status AS source_status, l.anchor_text, l.url, l.created_at AS link_created_at
FROM public.blog_post_links l
JOIN public.blog_posts source ON l.post_id = source.id
JOIN public.blog_posts target ON l.linked_post_id = target.id
WHERE l.link_type = 'internal'
ORDER BY l.created_at DESC;

-- External domains ranked by usage
CREATE OR REPLACE VIEW public.v_external_domains AS
SELECT
    domain,
    COUNT(*) AS total_links,
    COUNT(DISTINCT post_id) AS posts_using,
    COUNT(*) FILTER (WHERE is_valid = false) AS broken_links,
    MAX(last_validated_at) AS last_checked
FROM public.blog_post_links
WHERE link_type = 'external'
GROUP BY domain
ORDER BY total_links DESC;


-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'blog_post_links';
-- SELECT indexname FROM pg_indexes WHERE tablename = 'blog_post_links';
-- SELECT policyname FROM pg_policies WHERE tablename = 'blog_post_links';
