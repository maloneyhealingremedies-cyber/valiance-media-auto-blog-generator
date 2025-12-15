# How to Automate

Run the blog generator on a schedule using GitHub Actions.

## Quick Start

1. Fork this repository
2. Add secrets and variables to your fork
3. Enable the workflow
4. Posts generate automatically on schedule

The workflow file already exists at `.github/workflows/generate-blogs.yml`.

---

## Step 1: Fork the Repository

1. Click **Fork** in the top right of this repo
2. Choose your account/organization
3. Clone your fork locally to customize prompts

---

## Step 2: Add Repository Secrets

Go to your fork's **Settings** → **Secrets and variables** → **Actions** → **Secrets** tab → **New repository secret**

| Secret | Required | Description |
|--------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key |
| `GEMINI_API_KEY` | If using images | Google AI API key |
| `SHOPIFY_CLIENT_ID` | If using Shopify | Shopify OAuth client ID |
| `SHOPIFY_CLIENT_SECRET` | If using Shopify | Shopify OAuth client secret |
| `WORDPRESS_USERNAME` | If using WordPress | WordPress username |
| `WORDPRESS_APP_PASSWORD` | If using WordPress | WordPress Application Password |

---

## Step 3: Add Repository Variables

Go to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab → **New repository variable**

### Required Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `DEFAULT_AUTHOR_SLUG` | `staff-writer` | Author slug for posts |
| `DEFAULT_STATUS` | `published` | Post status (`draft` or `published`) |

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BLOGS_PER_RUN` | `1` | Number of posts to generate per scheduled run |
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `MAX_TURNS` | `15` | Max agent loop iterations |
| `NICHE_PROMPT_PATH` | `prompts/niche/golf.md` | Path to your niche prompt file |

### Category Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOW_NEW_CATEGORIES` | `false` | Allow AI to create new categories |
| `DEFAULT_CATEGORY_SLUG` | `general` | Fallback category slug |

### Image Generation

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_IMAGE_GENERATION` | `false` | Enable Gemini image generation |
| `GEMINI_MODEL` | `gemini-3-pro-image` | Gemini model for images |
| `IMAGE_ASPECT_RATIO` | `21:9` | Image aspect ratio |
| `IMAGE_WIDTH` | `1600` | Image width in pixels |
| `IMAGE_QUALITY` | `85` | WebP quality (1-100) |
| `SUPABASE_STORAGE_BUCKET` | `blog-images` | Storage bucket name |
| `IMAGE_CONTEXT` | | Theme for images (e.g., "golf course, sunny day") |
| `IMAGE_STYLE_PREFIX` | | Custom style prefix for prompts |

### Link Building

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_LINK_BUILDING` | `true` | Enable internal link building |
| `INTERNAL_LINK_PATTERN` | `/blog/{slug}` | URL pattern for internal links |
| `LINK_VALIDATION_TIMEOUT` | `5000` | URL validation timeout (ms) |
| `LINK_SUGGESTIONS_LIMIT` | `8` | Max link suggestions per post |

### Shopify Sync

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_SHOPIFY_SYNC` | `false` | Enable Shopify sync |
| `SHOPIFY_STORE` | | Your store name (before .myshopify.com) |
| `SHOPIFY_API_VERSION` | `2025-01` | Shopify API version |
| `SHOPIFY_DEFAULT_AUTHOR` | | Author name for Shopify articles |
| `SHOPIFY_SYNC_ON_PUBLISH` | `true` | Auto-sync on publish |

### WordPress Sync

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_WORDPRESS_SYNC` | `false` | Enable WordPress sync |
| `WORDPRESS_URL` | | Your WordPress site URL |
| `WORDPRESS_DEFAULT_AUTHOR_ID` | `1` | WordPress user ID for posts |
| `WORDPRESS_SYNC_ON_PUBLISH` | `true` | Auto-sync on publish |
| `WORDPRESS_SEO_PLUGIN` | `none` | SEO plugin: yoast, rankmath, aioseo, seopress, flavor, none |

---

## Step 4: Enable the Workflow

1. Go to your fork's **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. The workflow runs daily at 9 PM UTC by default

---

## Manual Trigger

Run the workflow manually anytime:

1. Go to **Actions** → **Generate Blog Posts**
2. Click **Run workflow**
3. Optionally enter the number of posts (overrides `BLOGS_PER_RUN`)
4. Click **Run workflow**

---

## Change the Schedule

Edit `.github/workflows/generate-blogs.yml` to change the cron schedule:

```yaml
schedule:
  # Current: Daily at 9 PM UTC
  - cron: '0 21 * * *'

  # Every day at 9 AM UTC
  # - cron: '0 9 * * *'

  # Every Monday and Thursday at 2 PM UTC
  # - cron: '0 14 * * 1,4'

  # Every 6 hours
  # - cron: '0 */6 * * *'
```

Use [crontab.guru](https://crontab.guru/) to build cron expressions.

---

## Customizing Your Fork

### 1. Create Your Niche Prompt

```bash
cp prompts/niche/golf.md prompts/niche/your-niche.md
```

Edit the file with your niche's tone, topics, and guidelines.

### 2. Update the Variable

Add `NICHE_PROMPT_PATH` to your repository variables:

| Variable | Value |
|----------|-------|
| `NICHE_PROMPT_PATH` | `prompts/niche/your-niche.md` |

### 3. Seed Your Queue

Add ideas to your Supabase `blog_ideas` table:

```sql
INSERT INTO blog_ideas (topic, description, priority) VALUES
  ('Topic 1', 'Description', 90),
  ('Topic 2', 'Description', 85),
  ('Topic 3', 'Description', 80);
```

---

## Monitoring

### Check Workflow Runs

Go to **Actions** tab to see run history, logs, and any failures.

### Check Queue Status

The workflow automatically shows queue status before generating. Check the logs to see pending ideas.

---

## Cost Estimation

Running daily with 1 post (default):
- ~$0.30/post × 30 days = ~$9/month (without images)
- ~$0.45/post × 30 days = ~$13.50/month (with images)
- GitHub Actions: Free for public repos, 2000 mins/month for private

---

## Troubleshooting

**Workflow not running on schedule**
→ GitHub disables scheduled workflows after 60 days of repo inactivity. Push a commit or run manually to re-enable.

**"Secret not found" errors**
→ Check secret names match exactly (case-sensitive). Secrets go in Secrets tab, variables go in Variables tab.

**BLOGS_PER_RUN not working**
→ Make sure `BLOGS_PER_RUN` is set in the Variables tab (not Secrets). The workflow uses this to determine how many posts to generate on scheduled runs.

**Posts not appearing**
→ Check `DEFAULT_STATUS` variable is set to `published`, or posts will be drafts.

**Queue empty**
→ Add more ideas to `blog_ideas` table in Supabase.

**Images not generating**
→ Check `ENABLE_IMAGE_GENERATION=true` and `GEMINI_API_KEY` is set as a secret.

**Links not being added**
→ Check `ENABLE_LINK_BUILDING=true` and you have enough published posts (minimum 3).

**Timeout errors**
→ The workflow has a 30-minute timeout. If posts are complex, reduce the count or increase `MAX_TURNS`.
