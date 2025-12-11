# Autonomous Blog Generator

An AI-powered blog generation system that uses Claude to autonomously create high-quality content. The system connects to Supabase, processes topics from a queue, and outputs structured blog posts with SEO metadata and tag relationships.

## Important: Customization Required

**This is not a plug-and-play solution.** This generator uses a **content block system** where posts are stored as JSON arrays of structured blocks, not HTML. Your frontend must be built to render these blocks.

Before using this generator, you will need to:

1. **Set up your database schema** - Create `blog_posts`, `blog_categories`, `blog_tags`, and `blog_authors` tables in Supabase (see [Database Setup](#database-setup))
2. **Adapt the content blocks** - Modify the block types in `prompts/system_prompt.md` to match your frontend's rendering capabilities
3. **Update the write tools** - Adjust `tools/write_tools.py` to match your exact database schema
4. **Build a frontend renderer** - Create components that render each content block type (React, Vue, vanilla JS, etc.)

This project serves as a **reference implementation** and starting point. Fork it and make it your own.

## Features

- **Content Block System**: Generates posts as structured JSON blocks (customizable block types)
- **Autonomous Mode**: Process blog ideas from a queue without manual intervention
- **Context Awareness**: Reads existing categories, tags, and authors to maintain consistency
- **SEO Optimized**: Generates titles, excerpts, slugs, and keyword metadata
- **Draft by Default**: Posts created as drafts for human review before publishing
- **Queue Management**: Priority-based processing with status tracking

## How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  IDEA QUEUE     │     │     CLAUDE      │     │    SUPABASE     │
│  (blog_ideas)   │ ──► │   (AI Agent)    │ ──► │   (blog_posts)  │
│                 │ ◄── │                 │ ◄── │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘

Autonomous Flow:
1. Claude gets next idea from queue (by priority)
2. Claims the idea (marks as in_progress)
3. Reads existing categories, tags, authors from your database
4. Writes complete blog post with structured content blocks
5. Saves to Supabase as draft
6. Links relevant tags
7. Marks idea as completed
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:
```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyxxxxx
DEFAULT_AUTHOR_SLUG=your-author-slug
```

### 3. Set Up Your Database

You'll need these tables in Supabase:

- `blog_posts` - Stores the generated posts
- `blog_categories` - Content categories
- `blog_tags` - Tags for posts
- `blog_authors` - Author profiles
- `blog_ideas` - The generation queue (see `schema/blog_ideas.sql`)

Run the SQL in `schema/blog_ideas.sql` to create the ideas queue table.

### 4. Customize for Your Schema

1. **Edit `tools/write_tools.py`** - Update the `create_blog_post` function to match your `blog_posts` table columns
2. **Edit `tools/query_tools.py`** - Update queries to match your table structures
3. **Edit `prompts/system_prompt.md`** - Define your content block types and their schemas

### 5. Add Ideas to the Queue

```sql
INSERT INTO blog_ideas (topic, description, priority, target_category_slug) VALUES
  ('Your Topic Here', 'Detailed guidance for the AI', 90, 'your-category'),
  ('Another Topic', 'More details', 85, 'another-category');
```

### 6. Run the Generator

```bash
# Process ideas from the queue (autonomous mode)
python generator.py --autonomous

# Process multiple ideas
python generator.py --autonomous --count 5

# Or generate a specific topic (manual mode)
python generator.py "Your topic here"
```

## Content Block System

Posts are stored as JSON arrays of content blocks. **You must build a frontend that renders these blocks.**

### Example Post Structure

```json
{
  "title": "How to Get Started",
  "slug": "how-to-get-started",
  "excerpt": "A beginner's guide...",
  "content_blocks": [
    {
      "id": "intro-1",
      "type": "paragraph",
      "data": {
        "text": "Welcome to this guide..."
      }
    },
    {
      "id": "heading-1",
      "type": "heading",
      "data": {
        "level": 2,
        "text": "Getting Started"
      }
    },
    {
      "id": "tip-1",
      "type": "callout",
      "data": {
        "style": "tip",
        "title": "Pro Tip",
        "text": "Start with the basics."
      }
    }
  ]
}
```

### Default Block Types

The included system prompt defines these block types (customize as needed):

| Type | Description |
|------|-------------|
| `paragraph` | Basic text (supports `<strong>`, `<em>`, `<a>`) |
| `heading` | Section titles (levels 2, 3, 4) |
| `list` | Ordered or unordered lists |
| `callout` | Tip/warning/info boxes |
| `quote` | Blockquotes with attribution |
| `table` | Data tables |
| `stats` | Statistics showcase |
| `proscons` | Pros/cons comparisons |
| `accordion` | Collapsible FAQ sections |
| `checklist` | Interactive checklists |
| `image` | Images with captions |
| `gallery` | Image grids |
| `video` | YouTube/Vimeo embeds |
| `button` | Call-to-action buttons |
| `tableOfContents` | Auto-generated TOC |
| `divider` | Section separators |
| `code` | Code snippets |
| `embed` | Social media embeds |

### Adapting Block Types

To use different block types:

1. Edit `prompts/system_prompt.md` to define your block schemas
2. Build corresponding React/Vue/etc. components to render each type
3. The AI will generate content using whatever block types you define

**Example: Simplified blocks for a basic blog**

If you only need paragraphs, headings, and lists, simplify the system prompt:

```markdown
## Content Blocks

Generate content using these block types only:

### paragraph
{ "id": "string", "type": "paragraph", "data": { "text": "string" } }

### heading
{ "id": "string", "type": "heading", "data": { "level": 2|3|4, "text": "string" } }

### list
{ "id": "string", "type": "list", "data": { "style": "ordered|unordered", "items": ["string"] } }
```

## Usage Modes

### Autonomous Mode (Recommended)

Process ideas from the queue:

```bash
python generator.py --autonomous              # Process one idea
python generator.py --autonomous --count 5    # Process up to 5
python generator.py --status                  # Check queue status
```

### Manual Mode

Generate a single post:

```bash
python generator.py "Your topic here"
python generator.py "Another topic" --verbose
```

### Batch Mode

Generate from a file:

```bash
python generator.py --batch topics.txt
```

### Interactive Mode

```bash
python generator.py --interactive
```

## Database Setup

### Required Tables

Your Supabase database needs these tables (adapt to your schema):

**blog_posts**
```sql
CREATE TABLE blog_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  excerpt TEXT,
  content_blocks JSONB NOT NULL DEFAULT '[]',
  featured_image TEXT,
  category_id UUID REFERENCES blog_categories(id),
  author_id UUID REFERENCES blog_authors(id),
  status TEXT DEFAULT 'draft',
  seo_title TEXT,
  seo_description TEXT,
  seo_keywords TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ
);
```

**blog_ideas** (for the queue)

See `schema/blog_ideas.sql` for the complete schema.

### Managing the Queue

```sql
-- Add an idea
INSERT INTO blog_ideas (topic, description, priority)
VALUES ('My Topic', 'Description here', 80);

-- View pending ideas
SELECT topic, priority FROM blog_ideas
WHERE status = 'pending'
ORDER BY priority DESC;

-- Retry a failed idea
UPDATE blog_ideas
SET status = 'pending', error_message = NULL
WHERE id = 'uuid-here';
```

## Project Structure

```
├── generator.py              # Main entry point
├── config.py                 # Configuration loader
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── tools/
│   ├── __init__.py
│   ├── query_tools.py        # Read from Supabase (customize for your schema)
│   ├── write_tools.py        # Write to Supabase (customize for your schema)
│   └── idea_tools.py         # Queue management
├── prompts/
│   └── system_prompt.md      # Claude instructions (customize block types here)
└── schema/
    └── blog_ideas.sql        # Queue table schema
```

## Automation

### Cron Job

```bash
0 9 * * * cd /path/to/blog-generator && python generator.py --autonomous --count 3 >> /var/log/blog-gen.log 2>&1
```

### GitHub Actions

```yaml
name: Generate Blog Posts

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9am UTC
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Process blog queue
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DEFAULT_AUTHOR_SLUG: your-author-slug
        run: python generator.py --autonomous --count 3 --verbose
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Your Anthropic API key |
| `SUPABASE_URL` | Yes | - | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | - | Supabase service role key |
| `DEFAULT_AUTHOR_SLUG` | Yes | - | Author slug for generated posts |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |
| `MAX_TURNS` | No | `15` | Max agentic loop iterations |
| `DEFAULT_STATUS` | No | `draft` | Default post status |

## Cost Estimation

Using Claude Sonnet:
- ~20-50K tokens per blog post
- ~$0.06-0.15 per post
- 10 posts: ~$0.60-1.50

## Troubleshooting

### "anthropic package not installed"
```bash
pip install anthropic
```

### "Missing required environment variables"
Ensure `.env` exists with all required values.

### Posts not appearing on website
Posts are created as `draft` by default. Update the status to `published` in your database.

### Queue stuck on "in_progress"
Reset stuck ideas:
```sql
UPDATE blog_ideas SET status = 'pending' WHERE status = 'in_progress';
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with [Claude](https://www.anthropic.com/claude) by Anthropic and [Supabase](https://supabase.com/).
