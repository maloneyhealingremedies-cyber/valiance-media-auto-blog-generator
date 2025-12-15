-- =============================================================================
-- Example Data - Run After Schema Setup
-- =============================================================================
-- This file contains example seed data to help you understand the data structure.
-- Run this in your Supabase SQL Editor AFTER running blog_tables.sql
--
-- All inserts use ON CONFLICT DO NOTHING so it's safe to run multiple times.
--
-- IMPORTANT: Replace the example values with your own data for production use.
-- =============================================================================


-- =============================================================================
-- 1. BLOG AUTHORS
-- =============================================================================
-- Authors write blog posts. You need at least one author before creating posts.

INSERT INTO public.blog_authors (slug, name, image, bio, show_bio) VALUES
  (
    'content-team',
    'Content Team',
    NULL,  -- Optional: URL to author avatar image
    'Our team of expert writers creating helpful content for our readers.',
    true   -- Set to false to hide bio on posts
  ),
  (
    'jane-smith',
    'Jane Smith',
    'https://example.com/avatars/jane-smith.jpg',
    'Jane is a senior writer specializing in technology and digital trends.',
    true
  )
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 2. BLOG CATEGORIES
-- =============================================================================
-- Categories organize posts into main topics. Each post belongs to one category.
-- The SEO field is JSONB and can include: title, description, keywords

INSERT INTO public.blog_categories (slug, name, description, sort_order, seo) VALUES
  (
    'tutorials',
    'Tutorials',
    'Step-by-step guides and how-to articles',
    1,
    '{"title": "Tutorials & How-To Guides", "description": "Learn with our comprehensive tutorials", "keywords": ["tutorial", "guide", "how-to"]}'::jsonb
  ),
  (
    'news',
    'News',
    'Latest updates and announcements',
    2,
    '{"title": "News & Updates", "description": "Stay informed with the latest news"}'::jsonb
  ),
  (
    'tips-and-tricks',
    'Tips & Tricks',
    'Quick tips to improve your workflow',
    3,
    '{}'::jsonb  -- SEO fields are optional
  )
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 3. BLOG TAGS
-- =============================================================================
-- Tags provide additional classification. Posts can have multiple tags.

INSERT INTO public.blog_tags (slug, name) VALUES
  ('beginner', 'Beginner'),
  ('intermediate', 'Intermediate'),
  ('advanced', 'Advanced'),
  ('quick-read', 'Quick Read'),
  ('in-depth', 'In-Depth'),
  ('productivity', 'Productivity'),
  ('best-practices', 'Best Practices')
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 4. BLOG POSTS
-- =============================================================================
-- Posts contain the actual content. The 'content' field is a JSONB array of blocks.
--
-- Content Block Types:
--   - paragraph: { "type": "paragraph", "content": "Text here..." }
--   - heading:   { "type": "heading", "level": 2, "content": "Heading text" }
--   - list:      { "type": "list", "style": "unordered", "items": ["Item 1", "Item 2"] }
--   - image:     { "type": "image", "src": "url", "alt": "description", "caption": "optional" }
--   - quote:     { "type": "quote", "content": "Quote text", "attribution": "Author" }
--   - code:      { "type": "code", "language": "javascript", "content": "code here" }
--
-- Status options: 'draft', 'published', 'scheduled', 'archived'

-- First, we need to get the author and category IDs
-- This example uses a DO block to handle the foreign key relationships

DO $$
DECLARE
  v_author_id UUID;
  v_category_id UUID;
  v_post_id UUID;
  v_tag_id UUID;
BEGIN
  -- Get the author ID
  SELECT id INTO v_author_id FROM public.blog_authors WHERE slug = 'content-team' LIMIT 1;

  -- Get the category ID
  SELECT id INTO v_category_id FROM public.blog_categories WHERE slug = 'tutorials' LIMIT 1;

  -- Only insert if we have both author and category
  IF v_author_id IS NOT NULL AND v_category_id IS NOT NULL THEN
    -- Insert example post (skip if slug already exists)
    INSERT INTO public.blog_posts (
      slug,
      title,
      excerpt,
      content,
      author_id,
      category_id,
      featured_image,
      featured_image_alt,
      reading_time,
      featured,
      status,
      seo
    ) VALUES (
      'getting-started-guide',
      'Getting Started: A Complete Beginner''s Guide',
      'Everything you need to know to get started. This comprehensive guide covers the basics and sets you up for success.',
      '[
        {
          "type": "paragraph",
          "content": "Welcome to our getting started guide! In this article, we''ll walk you through everything you need to know to begin your journey."
        },
        {
          "type": "heading",
          "level": 2,
          "content": "Prerequisites"
        },
        {
          "type": "paragraph",
          "content": "Before we dive in, make sure you have the following ready:"
        },
        {
          "type": "list",
          "style": "unordered",
          "items": [
            "A computer with internet access",
            "Basic familiarity with your operating system",
            "About 30 minutes of free time"
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "content": "Step 1: Setting Up Your Environment"
        },
        {
          "type": "paragraph",
          "content": "The first step is to set up your working environment. This ensures everything runs smoothly as you follow along."
        },
        {
          "type": "quote",
          "content": "The journey of a thousand miles begins with a single step.",
          "attribution": "Lao Tzu"
        },
        {
          "type": "heading",
          "level": 2,
          "content": "Conclusion"
        },
        {
          "type": "paragraph",
          "content": "Congratulations! You''ve completed the basics. From here, you can explore more advanced topics in our other tutorials."
        }
      ]'::jsonb,
      v_author_id,
      v_category_id,
      'https://example.com/images/getting-started-hero.jpg',
      'Illustration showing a person starting their learning journey',
      5,      -- reading_time in minutes
      true,   -- featured on homepage
      'published',
      '{"title": "Getting Started Guide - Complete Tutorial", "description": "A comprehensive beginner''s guide to help you get started quickly and easily.", "keywords": ["getting started", "beginner", "tutorial", "guide"]}'::jsonb
    )
    ON CONFLICT (slug) DO NOTHING
    RETURNING id INTO v_post_id;

    -- If post was inserted, add tags
    IF v_post_id IS NOT NULL THEN
      -- Add 'beginner' tag
      SELECT id INTO v_tag_id FROM public.blog_tags WHERE slug = 'beginner' LIMIT 1;
      IF v_tag_id IS NOT NULL THEN
        INSERT INTO public.blog_post_tags (post_id, tag_id) VALUES (v_post_id, v_tag_id)
        ON CONFLICT DO NOTHING;
      END IF;

      -- Add 'in-depth' tag
      SELECT id INTO v_tag_id FROM public.blog_tags WHERE slug = 'in-depth' LIMIT 1;
      IF v_tag_id IS NOT NULL THEN
        INSERT INTO public.blog_post_tags (post_id, tag_id) VALUES (v_post_id, v_tag_id)
        ON CONFLICT DO NOTHING;
      END IF;
    END IF;
  END IF;
END $$;


-- =============================================================================
-- 5. BLOG IDEAS
-- =============================================================================
-- Ideas queue up topics for future blog posts. The generator picks from this queue.
--
-- Priority: 0-100 (higher = process first)
-- Status: 'pending', 'in_progress', 'completed', 'failed', 'skipped'
-- Source: 'manual', 'ai_suggested', 'trending', 'user_request', 'content_gap'

INSERT INTO public.blog_ideas (
  topic,
  description,
  notes,
  target_category_slug,
  suggested_tags,
  target_word_count,
  priority,
  source,
  created_by
) VALUES
  (
    '10 Productivity Tips for Remote Workers',
    'Cover practical tips for staying productive while working from home. Include morning routines, workspace setup, and time management techniques.',
    'Focus on actionable advice. Include at least 3 tips that don''t require buying anything.',
    'tips-and-tricks',
    ARRAY['productivity', 'beginner', 'quick-read'],
    1200,
    85,    -- High priority
    'manual',
    'admin'
  ),
  (
    'Understanding API Rate Limits: A Developer''s Guide',
    'Explain what rate limits are, why they exist, and best practices for handling them in your applications.',
    NULL,  -- Notes are optional
    'tutorials',
    ARRAY['intermediate', 'best-practices'],
    1500,
    70,
    'manual',
    'admin'
  ),
  (
    'Weekly News Roundup Template',
    'Template for weekly news roundup posts. Summarize the top 5 stories of the week.',
    'Keep each story summary to 2-3 sentences. Link to original sources.',
    'news',
    ARRAY['quick-read'],
    800,
    50,    -- Medium priority
    'manual',
    'admin'
  )
ON CONFLICT DO NOTHING;


-- =============================================================================
-- 6. BLOG POST LINKS (Optional)
-- =============================================================================
-- Links are typically auto-generated when posts are created/updated.
-- This example shows the structure for reference.

DO $$
DECLARE
  v_post_id UUID;
BEGIN
  -- Get the example post ID
  SELECT id INTO v_post_id FROM public.blog_posts WHERE slug = 'getting-started-guide' LIMIT 1;

  IF v_post_id IS NOT NULL THEN
    -- Example internal link (linking to another post on the same blog)
    -- In practice, linked_post_id would reference an actual post
    INSERT INTO public.blog_post_links (
      post_id,
      url,
      anchor_text,
      link_type,
      linked_post_id,  -- NULL if target post doesn't exist yet
      domain,
      opens_new_tab,
      is_nofollow,
      is_valid
    ) VALUES (
      v_post_id,
      '/blog/advanced-techniques',  -- Relative URL for internal links
      'advanced techniques guide',
      'internal',
      NULL,  -- Would be the UUID of the linked post
      NULL,  -- Domain is NULL for internal links
      false, -- Internal links typically stay in same tab
      false,
      true
    )
    ON CONFLICT DO NOTHING;

    -- Example external link
    INSERT INTO public.blog_post_links (
      post_id,
      url,
      anchor_text,
      link_type,
      linked_post_id,
      domain,
      opens_new_tab,
      is_nofollow,
      is_valid,
      last_validated_at,
      last_status_code
    ) VALUES (
      v_post_id,
      'https://docs.example.com/reference',
      'official documentation',
      'external',
      NULL,  -- Always NULL for external links
      'docs.example.com',
      true,  -- External links typically open in new tab
      false, -- Set to true for sponsored/untrusted links
      true,
      NOW(),
      200    -- HTTP status code from last validation
    )
    ON CONFLICT DO NOTHING;
  END IF;
END $$;


-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================
-- Run these to verify the example data was inserted correctly:

-- SELECT slug, name FROM blog_authors;
-- SELECT slug, name, sort_order FROM blog_categories ORDER BY sort_order;
-- SELECT slug, name FROM blog_tags;
-- SELECT slug, title, status, featured FROM blog_posts;
-- SELECT topic, priority, status FROM blog_ideas ORDER BY priority DESC;
-- SELECT url, link_type, anchor_text FROM blog_post_links;

-- View post with all related data:
-- SELECT * FROM blog_posts_with_details WHERE slug = 'getting-started-guide';
