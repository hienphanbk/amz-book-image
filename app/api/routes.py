from flask import Blueprint, request, jsonify, current_app, Response, redirect, url_for
from app.core.image_extractor import ImageExtractor
from app.utils.cache import BookImageCache
from app.utils.logging_config import configure_logging
import os

try:
    import markdown
except ImportError:
    markdown = None

api_bp = Blueprint('api', __name__)
logger = configure_logging('api')

# Instantiate the extractor with config from Flask app

def get_extractor():
    config = getattr(current_app, 'config', {})
    return ImageExtractor(config=config)

@api_bp.route('/', methods=['GET'])
def home():
    """Display API documentation at the root path."""
    return render_readme()

# This is a helper function, not a route
def render_readme():
    """API documentation page: show README.md as HTML with styling."""
    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, encoding='utf-8') as f:
            content = f.read()
        if markdown:
            # Convert markdown to HTML
            html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
            
            # Add CSS styling for better appearance
            styled_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Amazon Book Image API</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 900px;
                        margin: 0 auto;
                        padding: 2rem;
                    }}
                    h1, h2, h3 {{
                        color: #0066cc;
                        margin-top: 1.5em;
                    }}
                    h1 {{
                        border-bottom: 1px solid #eaecef;
                        padding-bottom: 0.3em;
                    }}
                    code {{
                        background-color: #f6f8fa;
                        padding: 0.2em 0.4em;
                        border-radius: 3px;
                        font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
                        font-size: 85%;
                    }}
                    pre {{
                        background-color: #f6f8fa;
                        border-radius: 3px;
                        padding: 16px;
                        overflow: auto;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin-bottom: 1rem;
                    }}
                    th, td {{
                        border: 1px solid #dfe2e5;
                        padding: 8px 12px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f6f8fa;
                    }}
                    a {{
                        color: #0366d6;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                {html_content}
                <footer style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eaecef; color: #6a737d; font-size: 0.9rem;">
                    <p>Amazon Book Image API - By James, 2025</p>
                </footer>
            </body>
            </html>
            '''
            return Response(styled_html, mimetype='text/html')
        else:
            # Fallback if markdown module is not available
            return f"<pre style='font-family: monospace; padding: 20px; background-color: #f6f8fa;'>{content}</pre>"
    return "<h1>README.md not found</h1><p>Please create a README.md file in the project root.</p>", 404

@api_bp.route('/book-image', methods=['GET'])
def get_book_image():
    """
    API endpoint to get a book image URL from an Amazon book URL
    Query parameters:
        url (str): The Amazon book URL
        debug (bool): Whether to enable debug mode
        profile (bool): Whether to enable performance profiling
    Returns:
        JSON response with image_url or error message
    """
    import time
    start_time = time.time()
    book_url = request.args.get('url')
    debug = request.args.get('debug', '').lower() == 'true'
    profile = request.args.get('profile', '').lower() == 'true'

    if not book_url:
        processing_time = time.time() - start_time
        return jsonify({
            'success': False,
            'error': 'Missing book URL parameter',
            'book_url': book_url,
            'processing_time_seconds': round(processing_time, 3)
        }), 400
    if 'amazon' not in book_url.lower():
        processing_time = time.time() - start_time
        return jsonify({
            'success': False,
            'error': 'Only Amazon book URLs are supported',
            'book_url': book_url,
            'processing_time_seconds': round(processing_time, 3)
        }), 400

    try:
        extractor = get_extractor()
        cache = getattr(current_app, '_book_image_cache', None)
        if cache is None:
            cache = BookImageCache(current_app.config)
            setattr(current_app, '_book_image_cache', cache)

        # Check cache first
        image_url = cache.get(book_url)
        if image_url:
            processing_time = time.time() - start_time
            logger.info(f"[API][CACHE][HIT] Cache hit for book_url: {book_url}")
            return jsonify({
                'success': True,
                'image_url': image_url,
                'book_url': book_url,
                'processing_time_seconds': round(processing_time, 3),
                'cached': True,
                'cache_backend': 'redis' if cache.use_redis else 'file'
            })
        # Not cached, extract
        image_url = extractor.extract_image_url(book_url, debug=debug, profile=profile)
        processing_time = time.time() - start_time
        if image_url:
            cache.set(book_url, image_url)
            logger.info(f"[API][CACHE][SET] Cached image for book_url: {book_url}")
            return jsonify({
                'success': True,
                'image_url': image_url,
                'book_url': book_url,
                'processing_time_seconds': round(processing_time, 3),
                'cached': False,
                'cache_backend': 'redis' if cache.use_redis else 'file'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not find book cover image',
                'book_url': book_url,
                'processing_time_seconds': round(processing_time, 3)
            }), 404
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error in API: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'book_url': book_url,
            'processing_time_seconds': round(processing_time, 3)
        }), 500
