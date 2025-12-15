# Getting Started with WordPress

Sync your blog content to WordPress via the REST API.

## Prerequisites

### 1. Set Up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** in your dashboard
3. Run the schema files in order:

```
schema/blog_tables.sql      → Core tables (posts, categories, authors, tags)
schema/blog_ideas.sql       → Generation queue
schema/wordpress_sync.sql   → WordPress tracking columns
```

### 2. Create an Author

```sql
INSERT INTO blog_authors (slug, name, bio) VALUES
  ('staff-writer', 'Staff Writer', 'Expert content from our team.');
```

### 3. Configure Base Environment

```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:
```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyxxxxx
DEFAULT_AUTHOR_SLUG=staff-writer
```

---

## WordPress Setup

### 4. Enable Application Passwords

Application Passwords are built into WordPress 5.6+. No plugin required.

1. Log in to your WordPress admin
2. Go to **Users** → **Profile** (or click your username)
3. Scroll down to **Application Passwords**
4. Enter a name (e.g., "Blog Generator")
5. Click **Add New Application Password**
6. **Copy the password immediately** — it won't be shown again

The password looks like: `xxxx xxxx xxxx xxxx xxxx xxxx` (with spaces)

### 5. Find Your WordPress User ID

Your user ID is needed for the `WORDPRESS_DEFAULT_AUTHOR_ID` setting.

**Option A: From Users List**
1. Go to **Users** → **All Users**
2. Hover over the username you want to use
3. Look at the URL in your browser's status bar: `user_id=X`

**Option B: From Your Profile**
1. Go to **Users** → **Profile** (or click your username top-right)
2. Check the URL: `wp-admin/user-edit.php?user_id=1`
3. The number after `user_id=` is your ID

**Note:** The admin user is typically ID `1` (the default). If you only have one admin account, you can skip this step.

### 6. Add WordPress Config to .env

```env
ENABLE_WORDPRESS_SYNC=true
WORDPRESS_URL=https://yoursite.com
WORDPRESS_USERNAME=your-username
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
WORDPRESS_DEFAULT_AUTHOR_ID=1
WORDPRESS_SYNC_ON_PUBLISH=true
WORDPRESS_SEO_PLUGIN=none
```

### 7. Configure SEO Plugin (Optional)

If you use an SEO plugin, set `WORDPRESS_SEO_PLUGIN` to populate the correct meta fields:

| Plugin | Config Value |
|--------|--------------|
| Yoast SEO | `yoast` |
| RankMath | `rankmath` |
| All in One SEO | `aioseo` |
| SEOPress | `seopress` |
| The SEO Framework | `flavor` |
| No SEO plugin | `none` |

Example:
```env
WORDPRESS_SEO_PLUGIN=yoast
```

#### Yoast SEO: Category Meta Setup

Yoast SEO stores category/taxonomy SEO differently than other plugins. To enable category SEO sync with Yoast, you need to add a small code snippet to your WordPress site:

1. Open the file `yoast-category-seo-endpoint.php` from this folder
2. Add it to your WordPress site using one of these methods:

**Option A: Code Snippets Plugin (Recommended)**
1. Install the "Code Snippets" plugin from WordPress.org
2. Go to **Snippets** → **Add New**
3. Copy the code from `yoast-category-seo-endpoint.php` starting from `add_action...`
4. **Important:** Do NOT include the `<?php` tag - Code Snippets adds this automatically
5. Save and activate the snippet

**Option B: Must-Use Plugin**
```
wp-content/mu-plugins/yoast-category-seo-endpoint.php
```

**Option C: Child Theme functions.php**
Add the code to your child theme's `functions.php` file.

**Test the endpoint:**
Visit `https://yoursite.com/wp-json/blog-generator/v1/yoast-term-seo` - you should see a JSON response about missing parameters, not a 404.

Once installed, category SEO (title, meta description, focus keyword) will sync automatically.

> **Note:** Post SEO works without this snippet. This is only needed for category/taxonomy SEO with Yoast.

### 8. Sync Your Content

```bash
pip install -r requirements.txt

# Sync categories first (creates WordPress Categories)
python generator.py --wordpress-sync-categories

# Sync all posts (creates WordPress Posts)
python generator.py --wordpress-sync-all
```

### Alternative: Import Existing Content from WordPress

If you already have content in WordPress and want to import it into Supabase:

```bash
# Import everything at once (categories, tags, posts)
python generator.py --wordpress-import-all

# Or import individually:
python generator.py --wordpress-import-categories
python generator.py --wordpress-import-tags
python generator.py --wordpress-import-posts
```

**With `--force-pull`**: Overwrites existing Supabase data with WordPress data:
```bash
python generator.py --wordpress-import-all --force-pull
```

This is useful when:
- Setting up the generator with an existing WordPress blog
- You want Supabase to mirror your existing WordPress content
- You made changes in WordPress and want to pull them into Supabase

**What gets imported:**
- **Categories**: WordPress categories → `blog_categories` table
- **Tags**: WordPress tags → `blog_tags` table
- **Posts**: WordPress posts → `blog_posts` table (with HTML content preserved)

**Note:** Post content is stored as HTML. To convert to structured content blocks, you would need to manually edit posts in your frontend.

---

## Done!

Your content is now in WordPress. New posts will auto-sync when created (if `WORDPRESS_SYNC_ON_PUBLISH=true`).

---

## Quick Reference

### Check Status
```bash
python generator.py --wordpress-status
python generator.py --wordpress-status-categories
```

### Sync Commands
```bash
# Sync everything
python generator.py --wordpress-sync-categories
python generator.py --wordpress-sync-all

# Sync specific items
python generator.py --wordpress-sync "post-slug"
python generator.py --wordpress-sync-id "uuid"
python generator.py --wordpress-sync-category "category-slug"

# Sync recent posts
python generator.py --wordpress-sync-recent 5

# Force re-sync
python generator.py --wordpress-sync-all --force
```

### How Status Maps

| Supabase | WordPress |
|----------|-----------|
| `draft` | Draft |
| `archived` | Private |
| `published` | Published |
| `scheduled` | Scheduled |

---

## Featured Images

Featured images are automatically uploaded to your WordPress Media Library:

- Images are downloaded from Supabase storage and re-uploaded to WordPress
- Filenames are deterministic: `{post-slug}-featured.jpg`
- Smart deduplication: if the image hasn't changed, the existing attachment is reused
- If you regenerate an image with `--refresh-image`, WordPress gets the new version

---

## Using Both Shopify and WordPress

You can sync to both platforms simultaneously:

```env
ENABLE_SHOPIFY_SYNC=true
ENABLE_WORDPRESS_SYNC=true
```

Both integrations are independent — Supabase remains the source of truth.

```
                    ┌─────────────────┐
                    │    SHOPIFY      │
                    │   (Articles)    │
                    └─────────────────┘
                           ▲
┌─────────────────┐        │
│    SUPABASE     │ ───────┤
│  (blog_posts)   │        │
└─────────────────┘        ▼
                    ┌─────────────────┐
                    │   WORDPRESS     │
                    │    (Posts)      │
                    └─────────────────┘
```

---

## Troubleshooting

**"WordPress credentials not configured"**
→ Check your `.env` has all WordPress variables set

**"rest_cannot_create" or "rest_forbidden"**
→ Your Application Password doesn't have sufficient permissions. Make sure the WordPress user is an Administrator or Editor.

**Posts not appearing on frontend**
→ Check `--wordpress-status`. Drafts sync but aren't visible to visitors.

**"Invalid JSON response"**
→ Your `WORDPRESS_URL` may be incorrect, or the REST API is disabled. Test by visiting `https://yoursite.com/wp-json/wp/v2/posts`

**Images not uploading**
→ Check that your WordPress user has upload permissions and the Media Library is accessible

**SEO fields not populating**
→ Make sure `WORDPRESS_SEO_PLUGIN` matches your installed plugin. The plugin must be active.

**Category SEO not syncing with Yoast**
→ Yoast requires a custom endpoint. See "Yoast SEO: Category Meta Setup" above. Post SEO works without this - it's only needed for categories.

---

## WordPress REST API Requirements

The integration uses these REST API endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wp-json/wp/v2/categories` | GET, POST | Category lookup and creation |
| `/wp-json/wp/v2/posts` | GET, POST | Post lookup, creation, and updates |
| `/wp-json/wp/v2/tags` | GET, POST | Tag lookup and creation |
| `/wp-json/wp/v2/media` | GET, POST, DELETE | Featured image upload |

Ensure your WordPress site:
- Has the REST API enabled (default in WP 5.0+)
- Allows authenticated requests from your server's IP
- Has permalinks set to something other than "Plain"

---

## Next Steps

- See [database-setup.md](../database-setup.md) for queue management
- See [configuration.md](../configuration.md) for all environment variables
- See [how-to-use.md](how-to-use.md) for all CLI commands
