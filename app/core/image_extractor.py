import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import json
import time
import logging
import random
from functools import lru_cache

from app.utils.logging_config import configure_logging

# Configure logging
logger = configure_logging('image_extractor')

# List of known placeholder images to filter out
PLACEHOLDER_IMAGES = [
    'grey-pixel.gif',
    'transparent-pixel.gif',
    'loading-img',
    'no-img',
    'no-image',
    'placeholder',
    'spinner',
    'loading',
    'blank'
]


class ImageExtractor:
    """Class for extracting book cover images from Amazon product pages"""
    
    def __init__(self, config=None):
        """Initialize the image extractor with configuration"""
        self.config = config or {}
        self.session = self._create_optimized_session()
        self.user_agents = self.config.get('USER_AGENTS', [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        ])
        self.timeout = self.config.get('REQUEST_TIMEOUT', (3.05, 6.05))
    
    def _create_optimized_session(self):
        """Create an optimized session with connection pooling and retry strategy"""
        session = requests.Session()
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,  # Number of connection pools
            pool_maxsize=10,      # Max connections per pool
            max_retries=Retry(
                total=3,           # Maximum number of retries
                backoff_factor=0.5, # Backoff factor for retries
                status_forcelist=[500, 502, 503, 504] # Retry on these status codes
            )
        )
        
        # Apply the adapter to both http and https
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def _get_random_user_agent(self):
        """Get a random user agent from the list"""
        return random.choice(self.user_agents)
    
    def is_valid_image_url(self, url, debug=False):
        """Check if the URL is a valid image URL and not a placeholder"""
        if not url:
            return False
            
        # Check if the URL is a placeholder image
        for placeholder in PLACEHOLDER_IMAGES:
            if placeholder in url.lower():
                if debug:
                    logger.debug(f"Filtered out placeholder image: {url}")
                return False
                
        # Check if the URL is an actual image URL (contains image file extension)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        has_extension = any(ext in url.lower() for ext in image_extensions)
        
        # Check if it's from Amazon's image servers
        is_amazon_image = 'amazon' in url or 'images-na.ssl-images-amazon.com' in url
        
        # Minimum size requirements (reject tiny images that are likely icons)
        if 'SX' in url and 'SY' in url:
            # Extract dimensions from URL if present (common in Amazon image URLs)
            try:
                sx_match = re.search(r'_SX(\d+)_', url)
                sy_match = re.search(r'_SY(\d+)_', url)
                if sx_match and sy_match:
                    width = int(sx_match.group(1))
                    height = int(sy_match.group(1))
                    if width < 100 or height < 100:
                        if debug:
                            logger.debug(f"Filtered out small image: {width}x{height}")
                        return False
            except (ValueError, AttributeError):
                pass
        
        return is_amazon_image and (has_extension or 'images-amazon' in url)

    def _fetch_html(self, url, debug=False, profile=False):
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.amazon.com/'
        }
        if profile:
            request_start = time.time()
            logger.info(f"[TIMING] Starting request to: {url}")
        response = self.session.get(url, headers=headers, timeout=self.timeout, stream=True)
        response.raise_for_status()
        content = response.text
        if debug:
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response content length: {len(content)} bytes")
        if profile:
            request_end = time.time()
            logger.info(f"[TIMING] HTTP Request completed in {request_end - request_start:.2f} seconds")
        return content

    def _parse_html(self, html, profile=False):
        if profile:
            parsing_start = time.time()
            logger.info("[TIMING] Starting HTML parsing")
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        if profile:
            parsing_end = time.time()
            logger.info(f"[TIMING] HTML parsing completed in {parsing_end - parsing_start:.2f} seconds")
        return soup

    # Modular extraction methods
    def _extract_method_1(self, soup, debug=False, profile=False):
        # Main image in product details
        if profile:
            m1_start = time.time()
            logger.info("[TIMING] Starting Method 1: Main image in product details")
        img_element = soup.select_one('#imgBlkFront, #ebooksImgBlkFront')
        if img_element and img_element.has_attr('data-a-dynamic-image'):
            try:
                image_data = json.loads(img_element['data-a-dynamic-image'])
                for url in image_data.keys():
                    if self.is_valid_image_url(url, debug):
                        if profile:
                            logger.info(f"[TIMING] Method 1 completed in {time.time() - m1_start:.2f} seconds (found image)")
                        return url
            except Exception as e:
                if debug:
                    logger.error(f"Error in Method 1: {e}")
        if profile:
            logger.info(f"[TIMING] Method 1 completed in {time.time() - m1_start:.2f} seconds (no image found)")
        return None

    def _extract_method_2(self, soup, debug=False, profile=False):
        # Extract from JavaScript data (imageGalleryData, ImageBlockATF)
        if profile:
            m2_start = time.time()
            logger.info("[TIMING] Starting Method 2: Extract from JavaScript data")
        scripts = soup.find_all('script', type='text/javascript')
        for script in scripts:
            if script.string:
                # Look for image gallery data
                if 'imageGalleryData' in script.string:
                    if debug:
                        logger.debug("Method 2: Found imageGalleryData in script")
                    try:
                        matches = re.findall(r'var data = (\{.*?\});', script.string, re.DOTALL)
                        for match in matches:
                            try:
                                data = json.loads(match)
                                if 'imageGalleryData' in data and data['imageGalleryData']:
                                    for item in data['imageGalleryData']:
                                        if 'mainUrl' in item:
                                            url = item['mainUrl']
                                            if self.is_valid_image_url(url, debug):
                                                if profile:
                                                    logger.info(f"[TIMING] Method 2 completed in {time.time() - m2_start:.2f} seconds (found image)")
                                                return url
                            except json.JSONDecodeError:
                                pass
                    except Exception as e:
                        if debug:
                            logger.error(f"Error parsing imageGalleryData: {e}")
                # Look for initial image data
                if 'ImageBlockATF' in script.string:
                    if debug:
                        logger.debug("Method 2: Found ImageBlockATF in script")
                    try:
                        urls = re.findall(r'https://[^"\s]+\.(?:jpg|jpeg|png|gif)', script.string)
                        for url in urls:
                            if self.is_valid_image_url(url, debug):
                                if profile:
                                    logger.info(f"[TIMING] Method 2 completed in {time.time() - m2_start:.2f} seconds (found image)")
                                return url
                    except Exception as e:
                        if debug:
                            logger.error(f"Error extracting image URLs from script: {e}")
        if profile:
            logger.info(f"[TIMING] Method 2 completed in {time.time() - m2_start:.2f} seconds (no image found)")
        return None

    def _extract_method_3(self, soup, debug=False, profile=False):
        # Image gallery
        if profile:
            m3_start = time.time()
            logger.info("[TIMING] Starting Method 3: Image gallery")
        img_gallery = soup.select_one('#imageBlock_feature_div img, #main-image-container img, #imgTagWrapperId img')
        if img_gallery and img_gallery.has_attr('src'):
            if debug:
                logger.debug("Method 3: Found image in image gallery")
            src = img_gallery['src']
            if self.is_valid_image_url(src, debug):
                if profile:
                    logger.info(f"[TIMING] Method 3 completed in {time.time() - m3_start:.2f} seconds (found image)")
                return src
            if img_gallery.has_attr('data-old-hires'):
                old_hires = img_gallery['data-old-hires']
                if self.is_valid_image_url(old_hires, debug):
                    if profile:
                        logger.info(f"[TIMING] Method 3 completed in {time.time() - m3_start:.2f} seconds (found high-res image)")
                    return old_hires
        if profile:
            logger.info(f"[TIMING] Method 3 completed in {time.time() - m3_start:.2f} seconds (no image found)")
        return None

    def _extract_method_4(self, soup, debug=False, profile=False):
        # Main content area
        if profile:
            m4_start = time.time()
            logger.info("[TIMING] Starting Method 4: Main content area")
        main_image = soup.select_one('#landingImage, #imgBlkFront, #main-image, #img-canvas img')
        if main_image and main_image.has_attr('src'):
            if debug:
                logger.debug("Method 4: Found image in main content area")
            src = main_image['src']
            if self.is_valid_image_url(src, debug):
                if profile:
                    logger.info(f"[TIMING] Method 4 completed in {time.time() - m4_start:.2f} seconds (found image)")
                return src
            if main_image.has_attr('data-a-dynamic-image'):
                try:
                    image_data = json.loads(main_image['data-a-dynamic-image'])
                    image_urls = list(image_data.keys())
                    for url in image_urls:
                        if self.is_valid_image_url(url, debug):
                            if profile:
                                logger.info(f"[TIMING] Method 4 completed in {time.time() - m4_start:.2f} seconds (found image in data-a-dynamic-image)")
                            return url
                except json.JSONDecodeError:
                    pass
        if profile:
            logger.info(f"[TIMING] Method 4 completed in {time.time() - m4_start:.2f} seconds (no image found)")
        return None

    def _extract_method_5(self, soup, debug=False, profile=False):
        # Book details section
        if profile:
            m5_start = time.time()
            logger.info("[TIMING] Starting Method 5: Book details section")
        book_image = soup.select_one('.a-fixed-left-grid-col img, .a-fixed-right-grid-col img, .dp-title-col img')
        if book_image and book_image.has_attr('src'):
            if debug:
                logger.debug("Method 5: Found image in book details section")
            src = book_image['src']
            if self.is_valid_image_url(src, debug):
                if profile:
                    logger.info(f"[TIMING] Method 5 completed in {time.time() - m5_start:.2f} seconds (found image)")
                return src
        if profile:
            logger.info(f"[TIMING] Method 5 completed in {time.time() - m5_start:.2f} seconds (no image found)")
        return None

    def _extract_method_6(self, soup, debug=False, profile=False):
        # Any image with 'book' or 'cover' in the URL or alt text
        if profile:
            m6_start = time.time()
            logger.info("[TIMING] Starting Method 6: Images with book/cover in alt text")
        for img in soup.find_all('img'):
            if img.has_attr('src'):
                src = img['src']
                alt = img.get('alt', '').lower()
                if ('book' in alt or 'cover' in alt or 'product' in alt) and self.is_valid_image_url(src, debug):
                    if debug:
                        logger.debug(f"Method 6: Found image with book/cover in alt text: {alt}")
                    if profile:
                        logger.info(f"[TIMING] Method 6 completed in {time.time() - m6_start:.2f} seconds (found image)")
                    return src
        if profile:
            logger.info(f"[TIMING] Method 6 completed in {time.time() - m6_start:.2f} seconds (no image found)")
        return None

    def _extract_method_7(self, soup, debug=False, profile=False):
        # Any large image that might be a book cover
        if profile:
            m7_start = time.time()
            logger.info("[TIMING] Starting Method 7: Large images")
        for img in soup.find_all('img'):
            if img.has_attr('src') and img.has_attr('width') and img.has_attr('height'):
                try:
                    width = int(img['width'])
                    height = int(img['height'])
                    src = img['src']
                    if width >= 200 and height >= 200 and self.is_valid_image_url(src, debug):
                        if debug:
                            logger.debug(f"Method 7: Found large image: {width}x{height}")
                        if profile:
                            logger.info(f"[TIMING] Method 7 completed in {time.time() - m7_start:.2f} seconds (found image)")
                        return src
                except (ValueError, TypeError):
                    pass
        if profile:
            logger.info(f"[TIMING] Method 7 completed in {time.time() - m7_start:.2f} seconds (no image found)")
        return None

    def extract_image_url(self, url, debug=False, profile=False):
        try:
            import time
            total_start = time.time()
            step_times = {}

            # Step 1: Fetch HTML
            fetch_start = time.time()
            html = self._fetch_html(url, debug=debug, profile=profile)
            fetch_end = time.time()
            step_times['fetch_html'] = fetch_end - fetch_start
            logger.info(f"[TIMING] HTML fetch took {step_times['fetch_html']:.3f} seconds")

            # Step 2: Parse HTML
            parse_start = time.time()
            soup = self._parse_html(html, profile=profile)
            parse_end = time.time()
            step_times['parse_html'] = parse_end - parse_start
            logger.info(f"[TIMING] HTML parse took {step_times['parse_html']:.3f} seconds")

            # Step 3: Extraction methods
            methods = [
                self._extract_method_1,
                self._extract_method_2,
                self._extract_method_3,
                self._extract_method_4,
                self._extract_method_5,
                self._extract_method_6,
                self._extract_method_7
            ]
            for idx, method in enumerate(methods, 1):
                method_start = time.time()
                image_url = method(soup, debug=debug, profile=profile)
                method_end = time.time()
                step_times[f'method_{idx}'] = method_end - method_start
                logger.info(f"[TIMING] Method {idx} took {step_times[f'method_{idx}']:.3f} seconds")
                if image_url:
                    total_time = time.time() - total_start
                    logger.info(f"[TIMING] Total extraction time: {total_time:.3f} seconds")
                    return image_url
            total_time = time.time() - total_start
            logger.info(f"[TIMING] Total extraction time (no image found): {total_time:.3f} seconds")
            return None
        except Exception as e:
            logger.error(f"Error extracting image: {e}", exc_info=True)
            return None