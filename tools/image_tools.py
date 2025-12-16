"""
Image Generation Tools - Generate featured images using Nano Banana (Gemini)

These tools allow Claude to generate high-quality featured images for blog posts
using Google's Gemini image generation models.
"""

import base64
import io
import json
from typing import Any
import aiohttp
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    ENABLE_IMAGE_GENERATION,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    IMAGE_ASPECT_RATIO,
    IMAGE_QUALITY,
    IMAGE_WIDTH,
    IMAGE_STYLE_PREFIX,
    IMAGE_CONTEXT,
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    SUPABASE_STORAGE_BUCKET,
)

# Aspect ratio to height calculation
ASPECT_RATIOS = {
    "1:1": 1.0,
    "2:3": 2/3,
    "3:2": 3/2,
    "3:4": 3/4,
    "4:3": 4/3,
    "4:5": 4/5,
    "5:4": 5/4,
    "9:16": 9/16,
    "16:9": 16/9,
    "21:9": 21/9,
}


def calculate_dimensions(width: int, aspect_ratio: str) -> tuple[int, int]:
    """Calculate height from width and aspect ratio."""
    ratio = ASPECT_RATIOS.get(aspect_ratio, 21/9)
    height = int(width / ratio)
    return width, height


async def generate_featured_image(args: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a featured image using Nano Banana (Gemini) and upload to Supabase.

    Args:
        prompt: Description of the image to generate (will be enhanced with style prefix)
        category_slug: The blog category slug - used as the folder name
        post_slug: The blog post slug - used as the filename

    Returns:
        The public URL of the uploaded image in format: bucket/{category_slug}/{post_slug}.webp
    """
    # Check if image generation is enabled - soft skip if disabled
    if not ENABLE_IMAGE_GENERATION:
        return {
            "content": [{
                "type": "text",
                "text": "SKIPPED: Image generation disabled. Continue without featured image."
            }]
        }

    if not GEMINI_API_KEY:
        return {
            "content": [{
                "type": "text",
                "text": "SKIPPED: GEMINI_API_KEY not configured. Continue without featured image."
            }]
        }

    prompt = args.get("prompt")
    if not prompt:
        return {
            "content": [{"type": "text", "text": "Missing required parameter: prompt"}],
            "is_error": True
        }

    category_slug = args.get("category_slug", "")
    post_slug = args.get("post_slug", "")
    
    if not category_slug:
        return {
            "content": [{"type": "text", "text": "Missing required parameter: category_slug (the category folder name)"}],
            "is_error": True
        }
    
    if not post_slug:
        return {
            "content": [{"type": "text", "text": "Missing required parameter: post_slug (the image filename)"}],
            "is_error": True
        }

    try:
        # Step 1: Generate image with Gemini API
        # Build prompt: style prefix + context (if set) + user prompt
        context_part = f"Setting: {IMAGE_CONTEXT}. " if IMAGE_CONTEXT else ""
        full_prompt = f"{IMAGE_STYLE_PREFIX}{context_part}{prompt}"

        # Set timeout for API calls (60s for image generation, 30s for upload)
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Call Gemini API
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY,
            }

            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                }
            }

            async with session.post(gemini_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    # Graceful degradation - don't block blog creation
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"SKIPPED: Gemini API error ({resp.status}). Continue without featured image."
                        }]
                    }

                result = await resp.json()

            # Extract base64 image from response
            image_data = None
            mime_type = "image/png"

            try:
                for part in result["candidates"][0]["content"]["parts"]:
                    if "inlineData" in part:
                        image_data = part["inlineData"]["data"]
                        mime_type = part["inlineData"].get("mimeType", "image/png")
                        break
            except (KeyError, IndexError):
                # Graceful degradation
                return {
                    "content": [{
                        "type": "text",
                        "text": "SKIPPED: Could not extract image from response. Continue without featured image."
                    }]
                }

            if not image_data:
                return {
                    "content": [{
                        "type": "text",
                        "text": "SKIPPED: No image in response (model may have refused). Continue without featured image."
                    }]
                }

            # Step 2: Process image with Pillow
            try:
                from PIL import Image, ImageFilter

                # Decode base64 image
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))

                # Calculate target dimensions
                target_width, target_height = calculate_dimensions(IMAGE_WIDTH, IMAGE_ASPECT_RATIO)

                # Resize image maintaining aspect ratio, then crop to exact dimensions
                # First, scale to cover the target area
                img_ratio = image.width / image.height
                target_ratio = target_width / target_height

                if img_ratio > target_ratio:
                    # Image is wider, scale by height
                    new_height = target_height
                    new_width = int(target_height * img_ratio)
                else:
                    # Image is taller, scale by width
                    new_width = target_width
                    new_height = int(target_width / img_ratio)

                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Center crop to exact dimensions
                left = (new_width - target_width) // 2
                top = (new_height - target_height) // 2
                right = left + target_width
                bottom = top + target_height
                image = image.crop((left, top, right, bottom))

                # Apply light sharpening to restore detail lost during resize
                # UnsharpMask(radius, percent, threshold) - subtle settings for natural look
                image = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))

                # Convert to RGB if necessary (for WebP)
                if image.mode in ('RGBA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')

                # Adaptive quality WebP encoding
                # Start with configured quality, reduce only if file is too large
                # This prioritizes quality while keeping files reasonable
                MAX_FILE_SIZE_KB = 500  # Target max size in KB
                MIN_QUALITY = 75  # Never go below this for quality

                final_quality = IMAGE_QUALITY
                webp_data = None

                for quality in [IMAGE_QUALITY, 85, 80, MIN_QUALITY]:
                    if quality > IMAGE_QUALITY:
                        continue  # Don't go higher than configured

                    output_buffer = io.BytesIO()
                    # method=6 is slowest but best compression
                    # exact=True preserves RGB values more accurately
                    image.save(
                        output_buffer,
                        format='WEBP',
                        quality=quality,
                        method=6,
                    )
                    webp_data = output_buffer.getvalue()
                    final_quality = quality

                    file_size_kb = len(webp_data) / 1024

                    # If under max size or at minimum quality, we're done
                    if file_size_kb <= MAX_FILE_SIZE_KB or quality == MIN_QUALITY:
                        break

            except ImportError:
                return {
                    "content": [{
                        "type": "text",
                        "text": "SKIPPED: Pillow not installed. Continue without featured image."
                    }]
                }
            except Exception as e:
                # Graceful degradation for processing errors
                return {
                    "content": [{
                        "type": "text",
                        "text": f"SKIPPED: Image processing failed. Continue without featured image."
                    }]
                }

            # Step 3: Upload to Supabase Storage organized by category folder
            # Sanitize slugs for path
            safe_category = "".join(c if c.isalnum() or c in '-_' else '-' for c in category_slug)[:50]
            safe_post = "".join(c if c.isalnum() or c in '-_' else '-' for c in post_slug)[:100]
            
            # Create path: bucket/category/post.webp (e.g., blog-images/golf-tips/best-golf-drivers-2025.webp)
            file_path = f"{safe_category}/{safe_post}.webp"
            
            storage_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{file_path}"

            upload_headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "image/webp",
                "x-upsert": "true",
            }

            async with session.post(storage_url, headers=upload_headers, data=webp_data) as resp:
                if resp.status not in [200, 201]:
                    # Graceful degradation - image generated but upload failed
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"SKIPPED: Storage upload failed ({resp.status}). Continue without featured image."
                        }]
                    }

            # Generate public URL
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{file_path}"

            # Calculate file size
            file_size_kb = len(webp_data) / 1024

            # Note if quality was adjusted
            quality_note = ""
            if final_quality < IMAGE_QUALITY:
                quality_note = f" (reduced from {IMAGE_QUALITY}% to meet size target)"

            return {
                "content": [{
                    "type": "text",
                    "text": f"""Featured image generated successfully!

URL: {public_url}
Path: {SUPABASE_STORAGE_BUCKET}/{file_path}
Dimensions: {target_width}x{target_height}
Format: WebP (optimized)
Quality: {final_quality}%{quality_note}
File size: {file_size_kb:.1f} KB

Use this URL as the featured_image when creating the blog post."""
                }]
            }

    except Exception as e:
        # Graceful degradation for any unexpected errors
        return {
            "content": [{
                "type": "text",
                "text": f"SKIPPED: Unexpected error. Continue without featured image."
            }]
        }


async def delete_image_from_storage(file_path: str) -> bool:
    """
    Delete an image file from Supabase storage.

    Args:
        file_path: The path within the bucket (e.g., "category-slug/post-slug.webp")

    Returns:
        True if deleted successfully or file didn't exist, False on error
    """
    if not file_path:
        return True  # Nothing to delete

    try:
        async with aiohttp.ClientSession() as session:
            storage_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{file_path}"

            headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            }

            async with session.delete(storage_url, headers=headers) as resp:
                # 200 = deleted, 404 = didn't exist (both are fine)
                return resp.status in [200, 204, 404]
    except Exception:
        return False


def extract_storage_path_from_url(image_url: str) -> str:
    """
    Extract the storage file path from a Supabase storage URL.

    Example:
        Input: https://xxx.supabase.co/storage/v1/object/public/blog-images/category/post.webp
        Output: category/post.webp
    """
    if not image_url:
        return ""

    # Look for the bucket name in the URL and extract everything after it
    bucket_marker = f"/public/{SUPABASE_STORAGE_BUCKET}/"
    if bucket_marker in image_url:
        return image_url.split(bucket_marker)[1]

    # Also handle non-public URLs
    bucket_marker = f"/{SUPABASE_STORAGE_BUCKET}/"
    if bucket_marker in image_url:
        return image_url.split(bucket_marker)[1]

    return ""


async def get_post_for_image_cleanup(post_id: str = None, post_slug: str = None) -> dict:
    """
    Fetch a post by ID or slug with category info for image cleanup.

    Returns:
        Post dict with id, slug, title, featured_image, blog_categories(slug)
    """
    try:
        async with aiohttp.ClientSession() as session:
            from tools.write_tools import get_supabase_headers
            headers = get_supabase_headers()

            if post_id:
                query = f"id=eq.{post_id}"
            elif post_slug:
                query = f"slug=eq.{post_slug}"
            else:
                return None

            async with session.get(
                f"{SUPABASE_URL}/rest/v1/blog_posts?{query}&select=id,slug,title,excerpt,featured_image,featured_image_alt,blog_categories(slug)&limit=1",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    posts = await resp.json()
                    return posts[0] if posts else None
                return None
    except Exception:
        return None


async def clear_post_image_fields(post_id: str) -> bool:
    """Set featured_image and featured_image_alt to NULL in the database."""
    from datetime import datetime, timezone
    try:
        async with aiohttp.ClientSession() as session:
            from tools.write_tools import get_supabase_headers
            headers = get_supabase_headers()

            # Use JSON null to set fields to NULL, update timestamp to trigger webhooks
            update_data = {
                "featured_image": None,
                "featured_image_alt": None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            async with session.patch(
                f"{SUPABASE_URL}/rest/v1/blog_posts?id=eq.{post_id}",
                headers=headers,
                json=update_data
            ) as resp:
                return resp.status in [200, 204]
    except Exception:
        return False


async def cleanup_post_image(post_id: str = None, post_slug: str = None, verbose: bool = False) -> dict:
    """
    Clean up a post's featured image:
    1. Set featured_image and featured_image_alt to NULL in the database
    2. Delete the image file from Supabase storage

    Args:
        post_id: Post UUID (provide this OR post_slug)
        post_slug: Post slug (provide this OR post_id)
        verbose: Print detailed progress

    Returns:
        Dict with success status and details
    """
    # Get the post
    post = await get_post_for_image_cleanup(post_id=post_id, post_slug=post_slug)

    if not post:
        return {
            "success": False,
            "error": f"Post not found: {post_id or post_slug}"
        }

    post_id = post["id"]
    slug = post["slug"]
    title = post["title"]
    current_image = post.get("featured_image", "")

    if verbose:
        print(f"Post: {title[:50]}")
        print(f"Current image: {current_image or '(none)'}")

    # Extract storage path from URL
    storage_path = extract_storage_path_from_url(current_image)

    # Step 1: Clear database fields
    db_cleared = await clear_post_image_fields(post_id)
    if not db_cleared:
        return {
            "success": False,
            "error": "Failed to clear database fields",
            "post_slug": slug
        }

    if verbose:
        print("Database fields cleared (featured_image, featured_image_alt → NULL)")

    # Step 2: Delete from storage (if there was an image)
    storage_deleted = True
    if storage_path:
        storage_deleted = await delete_image_from_storage(storage_path)
        if verbose:
            if storage_deleted:
                print(f"Storage file deleted: {storage_path}")
            else:
                print(f"Warning: Could not delete storage file: {storage_path}")
    elif verbose:
        print("No storage file to delete")

    return {
        "success": True,
        "post_id": post_id,
        "post_slug": slug,
        "post_title": title,
        "storage_deleted": storage_deleted,
        "storage_path": storage_path or "(none)"
    }


def _create_alt_text_fallback(title: str, excerpt: str = "") -> str:
    """
    Fallback alt text generation when Claude API is unavailable.
    """
    cleanup_words = [
        "complete guide", "guide to", "how to", "what is", "what are",
        "explained", "tips", "tricks", "best", "top", "ultimate",
        ": complete", "- complete", "for beginners", "for experts",
    ]

    subject = title.lower()
    for word in cleanup_words:
        subject = subject.replace(word.lower(), "")

    subject = " ".join(subject.split()).strip(" :-")

    if subject:
        return subject[0].upper() + subject[1:] if len(subject) > 1 else subject.upper()
    elif excerpt:
        clean_excerpt = excerpt[:100].strip()
        if clean_excerpt:
            return clean_excerpt[0].upper() + clean_excerpt[1:] if len(clean_excerpt) > 1 else clean_excerpt

    return f"Featured image for {title}"


def _create_prompt_fallback(title: str, excerpt: str = "") -> str:
    """
    Fallback prompt generation when Claude API is unavailable.
    """
    cleanup_words = [
        "complete guide", "guide to", "how to", "what is", "what are",
        "explained", "tips", "tricks", "best", "top", "ultimate",
        ": complete", "- complete", "for beginners", "for experts",
    ]

    subject = title.lower()
    for word in cleanup_words:
        subject = subject.replace(word.lower(), "")

    subject = " ".join(subject.split()).strip(" :-")

    if subject:
        return f"A beautiful photograph depicting {subject}, cinematic composition, hero image style"
    else:
        return f"A beautiful photograph related to: {excerpt[:150]}, cinematic composition"


async def generate_image_prompt_and_alt(title: str, excerpt: str = "", verbose: bool = False) -> tuple[str, str]:
    """
    Use Claude to generate an image prompt and alt text for a blog post.

    This ensures refreshed images have the same quality as new posts created
    by the Claude agent - both use AI creativity for prompt and alt generation.

    Returns:
        Tuple of (image_prompt, alt_text)
        Falls back to programmatic generation if API call fails
    """
    from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

    try:
        import anthropic
    except ImportError:
        if verbose:
            print("anthropic not installed, using fallback")
        return _create_prompt_fallback(title, excerpt), _create_alt_text_fallback(title, excerpt)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        prompt = f"""Given this blog post, generate two things:

1. IMAGE_PROMPT: A detailed prompt for generating a featured image. Describe a realistic photograph or scene that would visually represent the topic. Focus on visual elements (lighting, composition, subjects, setting).

CRITICAL RULES for image prompts:
- Do NOT include text, words, or typography
- Do NOT include brand names or product names (AI generators create garbled fake names like "Pinx" instead of "Ping")
- Use generic descriptions instead (e.g., "premium golf driver" not "Titleist driver")
- Avoid words like "article", "blog", "guide" that might cause text to render

2. ALT_TEXT: A concise, SEO-friendly alt text that describes what the image shows. This should be descriptive of the image content itself, NOT "Featured image for [title]". Keep it under 125 characters. Do not mention brand names since the image won't show them.

Blog Title: {title}
Blog Excerpt: {excerpt[:300] if excerpt else 'No excerpt available'}

Respond in exactly this format:
IMAGE_PROMPT: [your image prompt here]
ALT_TEXT: [your alt text here]"""

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response_text = response.content[0].text
        lines = response_text.strip().split("\n")

        image_prompt = None
        alt_text = None

        for line in lines:
            if line.startswith("IMAGE_PROMPT:"):
                image_prompt = line.replace("IMAGE_PROMPT:", "").strip()
            elif line.startswith("ALT_TEXT:"):
                alt_text = line.replace("ALT_TEXT:", "").strip()

        # Validate we got both
        if image_prompt and alt_text:
            if verbose:
                print(f"Claude generated prompt: {image_prompt[:80]}...")
                print(f"Claude generated alt: {alt_text}")
            return image_prompt, alt_text
        else:
            if verbose:
                print("Could not parse Claude response, using fallback")
            return _create_prompt_fallback(title, excerpt), _create_alt_text_fallback(title, excerpt)

    except Exception as e:
        if verbose:
            print(f"Claude API error: {e}, using fallback")
        return _create_prompt_fallback(title, excerpt), _create_alt_text_fallback(title, excerpt)


async def refresh_post_image(post_id: str = None, post_slug: str = None, verbose: bool = False) -> dict:
    """
    Refresh a post's featured image:
    1. Clean up the existing image (clear DB + delete from storage)
    2. Generate a new image
    3. Update the post with the new image

    Args:
        post_id: Post UUID (provide this OR post_slug)
        post_slug: Post slug (provide this OR post_id)
        verbose: Print detailed progress

    Returns:
        Dict with success status and new image URL
    """
    from tools.write_tools import update_post_image

    # Check if image generation is enabled
    if not ENABLE_IMAGE_GENERATION:
        return {
            "success": False,
            "error": "Image generation is disabled. Set ENABLE_IMAGE_GENERATION=true"
        }

    # Get the post first (we need full details for regeneration)
    post = await get_post_for_image_cleanup(post_id=post_id, post_slug=post_slug)

    if not post:
        return {
            "success": False,
            "error": f"Post not found: {post_id or post_slug}"
        }

    post_id = post["id"]
    slug = post["slug"]
    title = post["title"]
    excerpt = post.get("excerpt", "")
    category_data = post.get("blog_categories")
    category_slug = category_data.get("slug") if category_data else "general"

    if verbose:
        print(f"Post: {title[:50]}")
        print(f"Slug: {slug}")
        print(f"Category: {category_slug}")

    # Step 1: Cleanup existing image
    print("Step 1: Cleaning up existing image...")
    cleanup_result = await cleanup_post_image(post_id=post_id, verbose=verbose)

    if not cleanup_result.get("success"):
        return {
            "success": False,
            "error": f"Cleanup failed: {cleanup_result.get('error')}",
            "post_slug": slug
        }

    # Step 2: Generate new image
    print("\nStep 2: Generating new image...")

    # Use Claude to generate image prompt and alt text (same as new posts)
    print("Generating image prompt and alt text with Claude...")
    prompt, alt_text = await generate_image_prompt_and_alt(title, excerpt, verbose=verbose)

    if verbose:
        print(f"Prompt: {prompt[:100]}...")

    result = await generate_featured_image({
        "prompt": prompt,
        "category_slug": category_slug,
        "post_slug": slug
    })

    # Check result
    result_text = ""
    for content in result.get("content", []):
        if content.get("type") == "text":
            result_text = content.get("text", "")

    if "SKIPPED" in result_text:
        return {
            "success": False,
            "error": f"Image generation skipped: {result_text}",
            "post_slug": slug,
            "cleanup_completed": True
        }

    # Extract URL from result
    if "URL:" not in result_text:
        return {
            "success": False,
            "error": "Could not extract URL from generation result",
            "post_slug": slug,
            "cleanup_completed": True
        }

    image_url = None
    for line in result_text.split("\n"):
        if line.startswith("URL:"):
            image_url = line.split("URL:")[1].strip()
            break

    if not image_url:
        return {
            "success": False,
            "error": "No URL in generation result",
            "post_slug": slug,
            "cleanup_completed": True
        }

    # Step 3: Update the post with new image
    print("\nStep 3: Updating post with new image...")
    # alt_text was already generated by Claude in Step 2
    update_success = await update_post_image(post_id, image_url, alt_text)

    if not update_success:
        return {
            "success": False,
            "error": "Failed to update post with new image URL",
            "post_slug": slug,
            "image_url": image_url,
            "cleanup_completed": True
        }

    if verbose:
        print(f"New image URL: {image_url}")

    return {
        "success": True,
        "post_id": post_id,
        "post_slug": slug,
        "post_title": title,
        "image_url": image_url
    }


# Tool definitions for Claude Agent SDK
IMAGE_TOOLS = [
    {
        "name": "generate_featured_image",
        "description": "Generate featured image via AI. Returns SKIPPED if fails (graceful). Stored at blog-images/{category_slug}/{post_slug}.webp",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description (scene, lighting, composition)"},
                "category_slug": {"type": "string", "description": "Category slug for folder"},
                "post_slug": {"type": "string", "description": "Post slug for filename"}
            },
            "required": ["prompt", "category_slug", "post_slug"]
        },
        "function": generate_featured_image
    }
]
