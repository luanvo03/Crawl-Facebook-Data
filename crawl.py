import configuration as cf
from time import time
import os
from tqdm import tqdm
import argparse
import concurrent.futures
from functools import partial
from math import ceil
import json

def get_crawled_posts(page_name):
    """Get list of already crawled post IDs"""
    crawled_ids = set()
    data_path = f"data/{page_name}"
    
    if os.path.exists(data_path):
        for folder in os.listdir(data_path):
            if os.path.isdir(os.path.join(data_path, folder)):
                # Check if folder has content
                folder_path = os.path.join(data_path, folder)
                if any(os.path.getsize(os.path.join(folder_path, f)) > 0 
                      for f in os.listdir(folder_path) 
                      if os.path.isfile(os.path.join(folder_path, f))):
                    crawled_ids.add(folder)
                else:
                    # Remove empty folders
                    try:
                        os.rmdir(folder_path)
                    except:
                        pass
    
    return crawled_ids

def get_empty_folders(page_name):
    """Get list of folder IDs that need processing"""
    empty_folders = []
    data_path = f"data/{page_name}"
    
    if os.path.exists(data_path):
        for folder in os.listdir(data_path):
            folder_path = os.path.join(data_path, folder)
            if os.path.isdir(folder_path):
                # Check if folder needs processing
                if not any(os.path.getsize(os.path.join(folder_path, f)) > 0 
                          for f in os.listdir(folder_path) 
                          if os.path.isfile(os.path.join(folder_path, f))):
                    empty_folders.append(folder)
    return empty_folders

def construct_url_from_id(page_name, folder_id):
    """Construct Facebook URL from folder ID"""
    base_url = f"https://www.facebook.com/{page_name}"
    if folder_id.isdigit():
        return f"{base_url}/posts/{folder_id}"
    elif len(folder_id) > 20:  # Likely a video/reel ID
        return f"{base_url}/videos/{folder_id}"
    return None

def check_folder_content(folder_path):
    """Check if folder has all required content"""
    missing = []
    
    # Check for caption.txt
    if not os.path.exists(os.path.join(folder_path, "caption.txt")):
        missing.append("caption")
    elif os.path.getsize(os.path.join(folder_path, "caption.txt")) == 0:
        missing.append("caption")
        
    # Check for comments.txt
    if not os.path.exists(os.path.join(folder_path, "comments.txt")):
        missing.append("comments")
    elif os.path.getsize(os.path.join(folder_path, "comments.txt")) == 0:
        missing.append("comments")
    
    # Check for media content
    has_images = any(f.endswith('.jpg') for f in os.listdir(folder_path))
    has_video = any(f.endswith('.mp4') for f in os.listdir(folder_path))
    
    if not (has_images or has_video):
        missing.append("media")
    
    return missing if missing else None

def get_incomplete_folders(page_name):
    """Get list of folder IDs that need processing"""
    incomplete_folders = []
    data_path = f"data/{page_name}"
    
    if os.path.exists(data_path):
        for folder in os.listdir(data_path):
            folder_path = os.path.join(data_path, folder)
            if os.path.isdir(folder_path):
                missing_content = check_folder_content(folder_path)
                if missing_content:
                    print(f"Folder {folder} missing: {', '.join(missing_content)}")
                    incomplete_folders.append(folder)
    return incomplete_folders

def crawl(driver_path, cookies_path, page_link, page_name, headless=True, 
          scroll_limit=0, resume=False, rescan=False, use_ytdl=False):
    """Main crawling function with resume and rescan capabilities"""
    try:
        # Initialize both browsers
        print("Initializing browsers...")
        browser, browser_mobile = cf.initialize_browsers(driver_path, cookies_path, headless)
        if not browser or not browser_mobile:
            raise Exception("Failed to initialize browsers")

        # Get URLs to process
        post_urls = []
        page_username = page_link.split('/')[-1]  # Extract page name from URL

        if rescan:
            # Check for incomplete folders
            incomplete_folders = get_incomplete_folders(page_name)
            if incomplete_folders:
                print(f"Found {len(incomplete_folders)} incomplete folders to process")
                for folder_id in incomplete_folders:
                    url = construct_url_from_id(page_username, folder_id)
                    if url:
                        post_urls.append(url)
            else:
                print("No incomplete folders found")
                return
        elif resume:
            # In resume mode, crawl new posts and skip existing non-empty folders
            post_urls = cf.get_post_links(browser, page_link, scroll_limit)
            if post_urls:
                crawled_ids = get_crawled_posts(page_name)
                original_count = len(post_urls)
                post_urls = [url for url in post_urls 
                           if cf.extract_facebook_post_id(url) not in crawled_ids]
                print(f"Found {original_count} posts, {len(post_urls)} are new")
        else:
            # Normal crawling mode
            post_urls = cf.get_post_links(browser, page_link, scroll_limit)
            if not post_urls:
                raise Exception("No posts found or error occurred while getting posts")

        # Process posts
        for url in tqdm(post_urls, desc="Processing Posts"):
            try:
                id = cf.extract_facebook_post_id(url)
                if not id:
                    continue
                    
                folder = f"data/{page_name}/{id}"
                if not os.path.exists(folder):
                    os.makedirs(folder)
                success = cf.process_post(browser, browser_mobile, url, folder, use_ytdl)
                
                if not success:
                    print(f"⚠️ Post {id} has no content or failed to process")
                
            except Exception as e:
                print(f"Error processing post {url}: {e}")
                continue

    except Exception as e:
        print(f"Critical error in crawl process: {e}")
    finally:
        # Clean up browsers
        if 'browser' in locals() and browser:
            browser.quit()
        if 'browser_mobile' in locals() and browser_mobile:
            browser_mobile.quit()

def crawl_parallel(driver_path, cookies_path, page_link, page_name, 
                  num_browsers=2, headless=True, scroll_limit=0, 
                  resume=False, rescan=False, use_ytdl=False):
    """Parallel crawling function using multiple browser instances"""
    try:
        # Initialize first browser to get posts
        print("Initializing primary browser to get post list...")
        browser, _ = cf.initialize_browsers(driver_path, cookies_path, headless)
        if not browser:
            raise Exception("Failed to initialize primary browser")

        # Get URLs to process
        post_urls = []
        page_username = page_link.split('/')[-1]

        if rescan:
            incomplete_folders = get_incomplete_folders(page_name)
            if incomplete_folders:
                print(f"Found {len(incomplete_folders)} incomplete folders to process")
                for folder_id in incomplete_folders:
                    url = construct_url_from_id(page_username, folder_id)
                    if url:
                        post_urls.append(url)
            else:
                print("No incomplete folders found")
                browser.quit()
                return
        elif resume:
            post_urls = cf.get_post_links(browser, page_link, scroll_limit)
            if post_urls:
                crawled_ids = get_crawled_posts(page_name)
                original_count = len(post_urls)
                post_urls = [url for url in post_urls 
                           if cf.extract_facebook_post_id(url) not in crawled_ids]
                print(f"Found {original_count} posts, {len(post_urls)} are new")
        else:
            post_urls = cf.get_post_links(browser, page_link, scroll_limit)

        browser.quit()

        if not post_urls:
            print("No posts to process")
            return

        # Split posts into chunks for parallel processing
        chunk_size = ceil(len(post_urls) / num_browsers)
        post_chunks = [post_urls[i:i + chunk_size] for i in range(0, len(post_urls), chunk_size)]
        print(f"Split {len(post_urls)} posts into {len(post_chunks)} chunks")

        # Create worker function
        def process_chunk(urls, page_name, browser_id):
            try:
                print(f"Initializing browser {browser_id}...")
                browser, browser_mobile = cf.initialize_browsers(driver_path, cookies_path, headless)
                if not browser or not browser_mobile:
                    raise Exception(f"Failed to initialize browsers for worker {browser_id}")

                # Extract page username from first URL for validation
                page_username = urls[0].split('/')[3] if urls else None
                print("Page username - " + str(page_username))
                for url in urls:
                    try:
                        id = cf.extract_facebook_post_id(url)
                        if not id:
                            continue
                        folder = f"data/{page_name}/{id}"
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                        # Pass page_username for validation
                        cf.process_post(browser, browser_mobile, url, folder, 
                                      page_username=page_username, use_ytdl=use_ytdl)
                    except Exception as e:
                        print(f"Error processing post {url} in worker {browser_id}: {e}")
                        continue

            except Exception as e:
                print(f"Critical error in worker {browser_id}: {e}")
            finally:
                if 'browser' in locals() and browser:
                    browser.quit()
                if 'browser_mobile' in locals() and browser_mobile:
                    browser_mobile.quit()

        # Process chunks in parallel
        print(f"\nStarting {num_browsers} parallel workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_browsers) as executor:
            futures = []
            for i, chunk in enumerate(post_chunks):
                futures.append(executor.submit(process_chunk, chunk, page_name, i+1))

            # Wait for all workers to complete
            concurrent.futures.wait(futures)
            print("\nAll workers completed")

    except Exception as e:
        print(f"Critical error in parallel crawl process: {e}")

def crawl_multi_pages(driver_path, cookies_path, pages_config, num_browsers=2, headless=True):
    """Crawl multiple pages in parallel"""
    try:
        print("\n=== Starting Multi-Page Crawler ===")
        
        # First pass: Get all post URLs for each page
        print("→ Phase 1: Collecting post URLs from all pages...")
        browser, _ = cf.initialize_browsers(driver_path, cookies_path, headless)
        if not browser:
            raise Exception("Failed to initialize browser for URL collection")
            
        all_posts = {}
        total_pages = len(pages_config)
        
        # Add progress bar for page processing
        for i, page_config in enumerate(tqdm(pages_config, desc="Collecting pages", unit="page")):
            page_link = page_config['url']
            page_name = page_config['name']
            page_username = page_link.rstrip('/').split('/')[-1]
            
            print(f"\n→ Processing page {i+1}/{total_pages}: {page_name}")
            max_scroll = page_config.get('max_scroll', 1000)
            min_posts = page_config.get('min_posts', 100)
            
            posts = cf.get_post_links(browser, page_link, max_scroll, min_posts)
            if posts:
                if page_config.get('resume', False):
                    crawled_ids = get_crawled_posts(page_name)
                    posts = [url for url in posts 
                            if cf.extract_facebook_post_id(url) not in crawled_ids]
                all_posts[page_name] = {
                    'urls': posts,
                    'config': page_config,
                    'username': page_username
                }
                print(f"  ✓ Found {len(posts)} posts")
                
        browser.quit()
        
        if not all_posts:
            print("No posts found to process")
            return
            
        # Second pass: Process posts in parallel
        print("\n→ Phase 2: Processing posts in parallel...")
        total_posts = sum(len(page['urls']) for page in all_posts.values())
        print(f"Total posts to process: {total_posts}")
        
        def process_page_chunk(urls, page_name, page_config, worker_id, pbar):
            try:
                print(f"\nWorker {worker_id}: Initializing browsers...")
                browser, browser_mobile = cf.initialize_browsers(
                    driver_path, cookies_path, headless
                )
                if not browser or not browser_mobile:
                    raise Exception(f"Failed to initialize browsers for worker {worker_id}")
                
                page_username = all_posts[page_name]['username']
                print(f"Worker {worker_id}: Processing {len(urls)} posts for {page_name}")
                
                for url in urls:
                    try:
                        id = cf.extract_facebook_post_id(url)
                        if not id:
                            continue
                        folder = f"data/{page_name}/{id}"
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                        cf.process_post(browser, browser_mobile, url, folder, 
                                     page_username=page_username)
                        pbar.update(1)  # Update progress bar
                    except Exception as e:
                        print(f"\nError processing {url} in worker {worker_id}: {e}")
                        continue
                        
            finally:
                if 'browser' in locals() and browser:
                    browser.quit()
                if 'browser_mobile' in locals() and browser_mobile:
                    browser_mobile.quit()
        
        # Create work chunks
        chunks = []
        for page_name, page_data in all_posts.items():
            urls = page_data['urls']
            chunk_size = ceil(len(urls) / num_browsers)
            for i in range(0, len(urls), chunk_size):
                chunk = urls[i:i + chunk_size]
                chunks.append((chunk, page_name, page_data['config']))
        
        print(f"Created {len(chunks)} work chunks")
        
        # Process chunks in parallel with progress bar
        with tqdm(total=total_posts, desc="Processing posts", unit="post") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_browsers) as executor:
                futures = []
                for i, (chunk, page_name, config) in enumerate(chunks):
                    futures.append(
                        executor.submit(process_page_chunk, chunk, page_name, config, i+1, pbar)
                    )
                
                # Wait for all workers
                concurrent.futures.wait(futures)
                
        print("\nAll workers completed")
            
    except Exception as e:
        print(f"Critical error in multi-page crawl: {e}")

def format_elapsed_time(elapsed_minutes):
    """Format elapsed time into hours, minutes, and seconds"""
    hours = int(elapsed_minutes // 60)
    minutes = int(elapsed_minutes % 60)
    seconds = int((elapsed_minutes * 60) % 60)
    
    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not time_parts:  # Include seconds if no hours/minutes or if there are remaining seconds
        time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return ", ".join(time_parts)

def main():
    """Entry point of the script"""
    # Add start_time before argument parsing
    start_time = time()
    
    parser = argparse.ArgumentParser(description='Facebook Page Crawler')
    
    # Add command line arguments
    parser.add_argument('--driver', type=str, default='./chromedriver.exe',
                      help='Path to chromedriver (default: ./chromedriver.exe)')
    parser.add_argument('--cookies', type=str, default='my_cookies.pkl',
                      help='Path to cookies file (default: my_cookies.pkl)')
    
    # Make page and name optional
    parser.add_argument('--page', type=str,
                      help='Facebook page URL to crawl (required if not using config file)')
    parser.add_argument('--name', type=str,
                      help='Name for the output folder (required if not using config file)')
    
    # Rest of the arguments
    parser.add_argument('--headless', action='store_true', default=True,
                      help='Run in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless',
                      help='Run with browser visible')
    parser.add_argument('--scroll-limit', type=int, default=0,
                      help='Number of scrolls (0 for unlimited, default: 0)')
    parser.add_argument('--resume', action='store_true',
                      help='Resume crawling from last point (skip already crawled posts)')
    parser.add_argument('--rescan', action='store_true',
                      help='Rescan only empty folders without crawling new posts')
    parser.add_argument('--use-ytdl', action='store_true', default=True,
                      help='Use yt-dlp for video downloads (default: True)')
    parser.add_argument('--no-ytdl', action='store_false', dest='use_ytdl',
                      help='Disable yt-dlp for video downloads')
    parser.add_argument('--browsers', type=int, default=2,
                      help='Number of parallel browsers to use (default: 2)')
    parser.add_argument('--config', type=str, help='Path to pages config JSON file')

    args = parser.parse_args()

    # Validate arguments based on mode
    if args.config:
        # Config file mode - page and name not required
        try:
            with open(args.config) as f:
                pages_config = json.load(f)
            crawl_multi_pages(args.driver, args.cookies, pages_config['pages'], 
                            num_browsers=args.browsers, headless=args.headless)
        except Exception as e:
            print(f"Error loading config file: {e}")
            return
    else:
        # Single page mode - require page and name
        if not args.page or not args.name:
            parser.error("--page and --name are required when not using a config file")
            return
            
        if args.browsers > 1:
            crawl_parallel(args.driver, args.cookies, args.page, args.name,
                         num_browsers=args.browsers, headless=args.headless,
                         scroll_limit=args.scroll_limit, resume=args.resume,
                         rescan=args.rescan, use_ytdl=args.use_ytdl)
        else:
            crawl(args.driver, args.cookies, args.page, args.name,
                 args.headless, args.scroll_limit, args.resume,
                 args.rescan, args.use_ytdl)
              
    elapsed_time = (time() - start_time) / 60
    print(f"Processing completed in {format_elapsed_time(elapsed_time)}")

if __name__ == "__main__":
    main()