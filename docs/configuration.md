# Configuration Reference

All configuration is done through environment variables. Copy `.env.example` to `.env` and customize.

## Required Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `DEFAULT_AUTHOR_SLUG` | Author slug for generated posts |

## Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `MAX_TURNS` | `15` | Max agentic loop iterations |
| `DEFAULT_STATUS` | `draft` | Default post status (`draft`, `published`, `scheduled`) |
| `BLOGS_PER_RUN` | `1` | Number of blogs to generate per autonomous run |

## Niche & Content

| Variable | Default | Description |
|----------|---------|-------------|
| `NICHE_PROMPT_PATH` | `prompts/niche/golf.md` | Path to niche-specific prompt |
| `ALLOW_NEW_CATEGORIES` | `true` | Allow AI to create new categories |
| `DEFAULT_CATEGORY_SLUG` | - | Fallback category if none specified |

## Image Generation

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_IMAGE_GENERATION` | `false` | Enable AI image generation |
| `GEMINI_API_KEY` | - | Google AI API key (required if enabled) |
| `GEMINI_MODEL` | `gemini-2.0-flash-exp-image-generation` | Gemini model for images |
| `IMAGE_CONTEXT` | - | Site theme context (e.g., "golf course, outdoor, sunny") |
| `IMAGE_ASPECT_RATIO` | `21:9` | Image aspect ratio |
| `IMAGE_WIDTH` | `1600` | Image width in pixels |
| `IMAGE_QUALITY` | `85` | WebP quality (1-100) |
| `SUPABASE_STORAGE_BUCKET` | `blog-images` | Storage bucket name |

### Image Context Examples

The `IMAGE_CONTEXT` helps generate consistent, on-brand images:

```env
# Golf blog
IMAGE_CONTEXT=golf course, outdoor sports, sunny day, green grass

# Tech blog
IMAGE_CONTEXT=modern office, technology, clean workspace, minimal design

# Food blog
IMAGE_CONTEXT=kitchen, food photography, warm lighting, fresh ingredients

# Fitness blog
IMAGE_CONTEXT=gym, fitness equipment, active lifestyle, energetic
```

## Link Building

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_LINK_BUILDING` | `true` | Enable internal link suggestions and tracking |
| `INTERNAL_LINK_PATTERN` | `/blog/{slug}` | URL pattern for internal links |
| `LINK_VALIDATION_TIMEOUT` | `5000` | URL validation timeout in ms |
| `LINK_SUGGESTIONS_LIMIT` | `8` | Max link suggestions to return |

### URL Pattern Examples

The `INTERNAL_LINK_PATTERN` supports `{slug}` and `{category}` placeholders:

```env
# Simple blog URL
INTERNAL_LINK_PATTERN=/blog/{slug}

# With category prefix
INTERNAL_LINK_PATTERN=/blog/{category}/{slug}

# Shopify style
INTERNAL_LINK_PATTERN=/blogs/news/{slug}
```

## Shopify Sync

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_SHOPIFY_SYNC` | `false` | Enable sync to Shopify |
| `SHOPIFY_STORE` | - | Store name (before .myshopify.com) |
| `SHOPIFY_CLIENT_ID` | - | OAuth Client ID from Dev Dashboard |
| `SHOPIFY_CLIENT_SECRET` | - | OAuth Client Secret |
| `SHOPIFY_API_VERSION` | `2025-01` | Shopify API version |
| `SHOPIFY_DEFAULT_AUTHOR` | - | Default author name for articles |
| `SHOPIFY_SYNC_ON_PUBLISH` | `true` | Auto-sync when posts are created |

## WordPress Sync

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_WORDPRESS_SYNC` | `false` | Enable sync to WordPress |
| `WORDPRESS_URL` | - | WordPress site URL (no trailing slash) |
| `WORDPRESS_USERNAME` | - | WordPress username for API auth |
| `WORDPRESS_APP_PASSWORD` | - | Application Password from WP admin |
| `WORDPRESS_DEFAULT_AUTHOR_ID` | `1` | WordPress user ID for posts |
| `WORDPRESS_SYNC_ON_PUBLISH` | `true` | Auto-sync when posts are created |
| `WORDPRESS_SEO_PLUGIN` | `none` | SEO plugin for meta fields |

### SEO Plugin Options

The `WORDPRESS_SEO_PLUGIN` setting determines which meta fields are populated:

| Value | Plugin | Category SEO |
|-------|--------|--------------|
| `yoast` | Yoast SEO | Requires snippet* |
| `rankmath` | RankMath | Works automatically |
| `aioseo` | All in One SEO | Works automatically |
| `seopress` | SEOPress | Works automatically |
| `flavor` | The SEO Framework | Works automatically |
| `none` | Don't populate SEO meta | N/A |

*Yoast stores category SEO differently. See [Getting Started with WordPress](setup/wordpress/getting-started-with-wordpress.md) for the required PHP snippet.

## Example Configurations

### Minimal Setup

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyxxxxx
DEFAULT_AUTHOR_SLUG=staff-writer
```

### With Image Generation

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyxxxxx
DEFAULT_AUTHOR_SLUG=staff-writer

ENABLE_IMAGE_GENERATION=true
GEMINI_API_KEY=xxxxx
IMAGE_CONTEXT=modern office, technology, clean design
SUPABASE_STORAGE_BUCKET=blog-images
```

### With Shopify Sync

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyxxxxx
DEFAULT_AUTHOR_SLUG=staff-writer

ENABLE_SHOPIFY_SYNC=true
SHOPIFY_STORE=my-store
SHOPIFY_CLIENT_ID=xxxxx
SHOPIFY_CLIENT_SECRET=xxxxx
SHOPIFY_DEFAULT_AUTHOR=Staff Writer
SHOPIFY_SYNC_ON_PUBLISH=true
```

### With WordPress Sync

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyxxxxx
DEFAULT_AUTHOR_SLUG=staff-writer

ENABLE_WORDPRESS_SYNC=true
WORDPRESS_URL=https://myblog.com
WORDPRESS_USERNAME=admin
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
WORDPRESS_DEFAULT_AUTHOR_ID=1
WORDPRESS_SYNC_ON_PUBLISH=true
WORDPRESS_SEO_PLUGIN=yoast
```

### Production Setup

```env
# Core
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyxxxxx
DEFAULT_AUTHOR_SLUG=expert-writer

# Content
CLAUDE_MODEL=claude-sonnet-4-5-20250929
MAX_TURNS=15
DEFAULT_STATUS=published
BLOGS_PER_RUN=3
NICHE_PROMPT_PATH=prompts/niche/cooking.md
ALLOW_NEW_CATEGORIES=false
DEFAULT_CATEGORY_SLUG=recipes

# Images
ENABLE_IMAGE_GENERATION=true
GEMINI_API_KEY=xxxxx
GEMINI_MODEL=gemini-2.0-flash-exp-image-generation
IMAGE_CONTEXT=kitchen, food photography, warm lighting
IMAGE_ASPECT_RATIO=16:9
IMAGE_WIDTH=1920
IMAGE_QUALITY=90
SUPABASE_STORAGE_BUCKET=blog-images

# Link Building
ENABLE_LINK_BUILDING=true
INTERNAL_LINK_PATTERN=/recipes/{slug}

# Shopify
ENABLE_SHOPIFY_SYNC=true
SHOPIFY_STORE=my-food-blog
SHOPIFY_CLIENT_ID=xxxxx
SHOPIFY_CLIENT_SECRET=xxxxx
SHOPIFY_API_VERSION=2025-01
SHOPIFY_DEFAULT_AUTHOR=Chef Expert
SHOPIFY_SYNC_ON_PUBLISH=true
```

## Cost Estimation

Using Claude Sonnet 4.5 with prompt caching:

- ~70K tokens per blog post
- ~$0.15-0.25 per post
- 10 posts: ~$1.50-2.50

Prompt caching reduces costs by ~50% after the first turn.

## Automation

### Cron Job

```bash
# Generate 3 posts daily at 9am
0 9 * * * cd /path/to/blog-generator && python generator.py -a -c 3 >> /var/log/blog.log 2>&1
```

### GitHub Actions

Key secrets to configure:
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY` (if using images)
- `SHOPIFY_CLIENT_ID` (if using Shopify)
- `SHOPIFY_CLIENT_SECRET` (if using Shopify)
- `WORDPRESS_USERNAME` (if using WordPress)
- `WORDPRESS_APP_PASSWORD` (if using WordPress)
