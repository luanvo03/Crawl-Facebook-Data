import warnings
# Filter out TensorFlow warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='.*MapAsync.*')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from time import sleep
import os
import requests
from selenium.webdriver.common.keys import Keys
import keyboard
import re
import time
import random
from functools import wraps
from .config import login, login_mobile  # Import login functions
from yt_dlp import YoutubeDL
import yt_dlp

# Add new utility functions at the top
def smart_delay(min_delay=1, max_delay=3):
    """Smart random delay with noise"""
    base_delay = random.uniform(min_delay, max_delay)
    noise = random.uniform(0.1, 0.3)
    time.sleep(base_delay + noise)

def retry_on_failure(retries=3, delay=1):
    """Decorator for retrying failed operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        raise e
                    smart_delay(delay, delay + 1)
            return None
        return wrapper
    return decorator

# Add new post processing functions
def process_post_content(browser, folder, post_type):
    """Process post content based on type"""
    try:
        if post_type == "posts":
            return process_regular_post(browser, folder)
        elif post_type == "videos":
            return process_video_post(browser, folder)
        elif post_type == "reel":
            return process_reel_post(browser, folder)
        return False
    except Exception as e:
        print(f"Error processing {post_type}: {e}")
        return False

@retry_on_failure(retries=3)
def process_regular_post(browser, folder):
    """Process regular post content with enhanced logging"""
    print("\n=== Processing Regular Post ===")
    try:
        # Step 1: Handle See More button
        print("→ Step 1: Expanding post content...")
        try:
            if click_see_more(browser):
                print("  ✓ Content expanded")
            else:
                print("  ⚠️ Could not expand content, continuing anyway")
        except Exception as e:
            print(f"  ⚠️ Error expanding content: {e}")

        # Step 2: Get captions
        print("→ Step 2: Getting captions...")
        try:
            captions = get_captions_emojis(browser)
            if captions:
                save_text(captions, f"{folder}/caption.txt")
                print(f"  ✓ Saved {len(captions)} caption lines")
            else:
                print("  ⚠️ No captions found")
        except Exception as e:
            print(f"  ❌ Error getting captions: {e}")

        # Step 3: Get images
        print("→ Step 3: Getting images...")
        try:
            img_urls = get_image_urls(browser)
            if img_urls:
                download_images(img_urls, folder)
                print(f"  ✓ Downloaded {len(img_urls)} images")
            else:
                print("  ⚠️ No images found")
        except Exception as e:
            print(f"  ❌ Error getting images: {e}")

        # Step 4: Get comments
        print("→ Step 4: Getting comments...")
        try:
            click_comment_button(browser)
            smart_delay(1, 2)
            comments = get_comments_with_retry(browser)
            if comments:
                save_text(comments, f"{folder}/comments.txt")
                print(f"  ✓ Saved {len(comments)} comments")
            else:
                print("  ⚠️ No comments found")
        except Exception as e:
            print(f"  ❌ Error getting comments: {e}")

        print("=== Post Processing Complete ===")
        return True

    except Exception as e:
        print(f"❌ Error in regular post processing: {e}")
        return False

@retry_on_failure(retries=3)
def process_desktop_content(browser, folder, is_video=False):
    """Process desktop-only content with video optimization"""
    print("→ Processing desktop content...")
    try:
        # Disable smooth scrolling and save original position
        browser.execute_script("document.documentElement.style.scrollBehavior = 'auto';")
        original_position = browser.execute_script("return window.pageYOffset;")
        
        # Get captions first (no scrolling needed)
        try:
            click_see_more(browser)
            smart_delay(0.5, 1)
            captions = get_captions_spe(browser)
            save_text(captions, f"{folder}/caption.txt")
            print("✓ Captions saved")
            
            try:
                click_see_less(browser)
            except:
                pass
        except Exception as e:
            print(f"⚠️ Error getting captions: {e}")
        
        # For video posts, skip comment loading to avoid stalls
        if is_video:
            print("ℹ️ Skipping comments for video content")
            return True
            
        # Get comments with controlled scrolling
        try:
            with TimeoutManager(15):  # 15 second timeout for comment operations
                comments = get_comments_safe(browser)
                if comments:
                    save_text(comments, f"{folder}/comments.txt")
                    print("✓ Comments saved")
                else:
                    print("⚠️ No comments found")
                    
        except TimeoutException:
            print("⚠️ Comment loading timed out")
        except Exception as e:
            print(f"⚠️ Error processing comments: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error processing desktop content: {e}")
        return False
    finally:
        # Restore scroll behavior and position
        browser.execute_script("document.documentElement.style.scrollBehavior = '';")
        browser.execute_script(f"window.scrollTo(0, {original_position});")

@retry_on_failure(retries=3)
def process_mobile_video(browser_mobile, url, folder, use_ytdl=False):
    """Process mobile-only content (video download and comments)"""
    print("\n→ Processing mobile content...")
    try:
        if use_ytdl and download_video_ytdl(url, folder):
            # Try to get comments after successful video download
            try:
                comments = get_comments_mobile(browser_mobile)
                if comments:
                    save_text(comments, f"{folder}/comments.txt")
                    print("✓ Comments saved")
            except:
                print("⚠️ Could not get comments")
            return True
            
        smart_delay(5, 6)
        browser_mobile.get(url.replace('www.facebook.com', 'm.facebook.com'))
        smart_delay(5, 6)
        
        if not wait_for_mobile_video_load(browser_mobile):
            return False
            
        video_urls = get_video_urls(browser_mobile)
        if video_urls:
            download_videos(video_urls, folder)
            # Try to get comments after video download
            try:
                comments = get_comments_mobile(browser_mobile)
                if comments:
                    save_text(comments, f"{folder}/comments.txt")
                    print("✓ Comments saved")
            except:
                print("⚠️ Could not get comments")
            return True
        
        print("❌ No video URLs found")
        return False
    except Exception as e:
        print(f"❌ Error processing mobile content: {e}")
        return False

def get_comments_mobile(browser):
    """Get comments from mobile view"""
    comments_list = []
    try:
        # Find comment elements in mobile view
        comment_elements = browser.find_elements(By.XPATH, 
            "//div[contains(@class, '_2b04')]//div[contains(@class, '_14ye')]"
        )
        
        for comment in comment_elements:
            try:
                text = comment.text.strip()
                if text and text not in comments_list:
                    comments_list.append(text)
            except:
                continue
                
    except Exception as e:
        print(f"Error getting mobile comments: {e}")
        
    return comments_list

@retry_on_failure(retries=3)
def process_video_post(browser, browser_mobile, url, folder, use_ytdl=False):
    """Process a Facebook video post"""
    print("\n=== Processing Video Post ===")
    print("→ Step 1: Getting captions from desktop version")
    
    # Process only captions in desktop view
    try:
        browser.get(url)
        smart_delay(2, 3)
        print("  • Page loaded in desktop view")
        
        # Get captions without scrolling
        try:
            print("  • Attempting to expand caption...")
            click_see_more(browser)
            smart_delay(0.5, 1)
            print("  • Extracting caption text...")
            captions = get_captions_spe(browser)
            
            if captions:
                save_text(captions, f"{folder}/caption.txt")
                print("  ✓ Captions saved successfully")
                print(f"  • Caption length: {len(captions)} lines")
            else:
                print("  ⚠️ No captions found")
            
            try:
                click_see_less(browser)
            except:
                pass
        except Exception as e:
            print(f"  ⚠️ Error getting captions: {e}")
    except Exception as e:
        print(f"  ❌ Desktop content processing failed: {e}")
        
    print("\n→ Step 2: Processing video content in mobile view")
    if process_mobile_video(browser_mobile, url, folder, use_ytdl):
        print("\n=== Video Post Processing Summary ===")
        print("✓ Captions: Processed")
        print("✓ Video: Downloaded")
        if os.path.exists(f"{folder}/comments.txt"):
            print("✓ Comments: Saved")
        else:
            print("- Comments: None found")
        print("=== Processing Complete ===\n")
        return True
    else:
        print("\n=== Video Post Processing Failed ===")
        print("✓ Captions: Processed")
        print("❌ Video: Failed to download")
        print("=== Processing Incomplete ===\n")
        return False

@retry_on_failure(retries=3)
def process_reel_post(browser, browser_mobile, url, folder):
    """Process a Facebook reel post"""
    print("\n=== Processing Reel Post ===")
    
    # Process desktop content first
    browser.get(url)
    smart_delay(2, 3)
    
    # Get desktop content
    if not process_desktop_content(browser, folder):
        print("⚠️ Desktop content processing failed")
        
    # Process mobile content
    if not process_mobile_video(browser_mobile, url, folder):
        print("❌ Mobile video processing failed")
        return False
        
    print("=== Reel Post Processing Complete ===\n")
    return True

def try_action(action, retries=3):
    """Safely try an action with retries"""
    for _ in range(retries):
        try:
            action()
            return True
        except:
            smart_delay(0.5, 1)
    return False

def get_comments_with_retry(browser):
    """Get comments with enhanced retry logic"""
    print("  → Getting comments...")
    try:
        # First try to click comment button
        if not click_comment_button(browser):
            print("  ⚠️ Could not access comments section")
            return []
            
        # Try to click 'See all comments' if present
        try:
            show_all_comments(browser)
            smart_delay(1, 2)
        except:
            pass
            
        # Load more comments
        comments_loaded = 0
        no_new_comments = 0
        max_attempts = 3
        
        while no_new_comments < max_attempts:
            previous_count = len(browser.find_elements(By.XPATH, "//div[@role='article']//div[contains(@class, 'x1n2onr6')]"))
            
            try:
                click_view_more_comments(browser)
                smart_delay(1, 2)
                
                current_count = len(browser.find_elements(By.XPATH, "//div[@role='article']//div[contains(@class, 'x1n2onr6')]"))
                
                if current_count > previous_count:
                    comments_loaded += (current_count - previous_count)
                    no_new_comments = 0
                    print(f"  → Loaded {comments_loaded} comments...", end="\r")
                else:
                    no_new_comments += 1
                    
            except:
                no_new_comments += 1
                
        print(f"  ✓ Found {comments_loaded} comments total")
        return get_comments(browser)
        
    except Exception as e:
        print(f"  ❌ Error getting comments: {e}")
        return []

def show_all_comments(driver):
    '''Change Most relevant to All comments to show all comments'''

    # Click on the Most relevant button
    view_more_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Most relevant')]")))
    view_more_btn.click()
    # Click on the All comment button
    all_comments = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'All comments')]")))
    all_comments.click()
    # Scroll to the bottom, ensure all comments are loaded
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    return None

def click_see_more(driver, max_retries=3):
    """Click see more with improved reliability"""
    print("  → Attempting to click 'See more'...")
    
    for attempt in range(max_retries):
        try:
            # Find the See more button with multiple possible selectors
            selectors = [
                '//div[contains(text(), "See more")]',
                '//div[@aria-label="See more"]',
                '//div[@role="button"]//div[contains(text(), "See more")]'
            ]
            
            for selector in selectors:
                try:
                    # Wait for element and ensure it's in view
                    see_more_btn = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    
                    # Scroll element into view
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_more_btn)
                    smart_delay(0.5, 1)
                    
                    # Try different click methods
                    try:
                        # First try JavaScript click
                        driver.execute_script("arguments[0].click();", see_more_btn)
                    except:
                        try:
                            # Then try ActionChains
                            actions = ActionChains(driver)
                            actions.move_to_element(see_more_btn)
                            actions.click()
                            actions.perform()
                        except:
                            # Finally try native click
                            see_more_btn.click()
                    
                    print("  ✓ Successfully clicked 'See more'")
                    smart_delay(0.5, 1)
                    return True
                except:
                    continue
            
            if attempt < max_retries - 1:
                print(f"  ⚠️ Retry {attempt + 1}/{max_retries}")
                smart_delay(1, 2)
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  ❌ Failed to click 'See more': {e}")
                return False
            print(f"  ⚠️ Attempt {attempt + 1} failed, retrying...")
            smart_delay(1, 2)
    
    return False

def click_see_less(driver, max_retries=3):
    """Click see less with improved reliability"""
    for attempt in range(max_retries):
        try:
            see_less_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'See less')]"))
            )
            
            # Scroll into view and click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_less_btn)
            smart_delay(0.5, 1)
            driver.execute_script("arguments[0].click();", see_less_btn)
            return True
        except:
            if attempt < max_retries - 1:
                smart_delay(1, 2)
            continue
    return False

def click_comment_button(driver, max_retries=3):
    """Click comment button with improved reliability"""
    print("  → Attempting to click comment button...")
    
    for attempt in range(max_retries):
        try:
            # Try multiple selectors in order of reliability
            selectors = [
                '//div[@aria-label="Comment"]',  # Primary selector
                '//div[@role="button"]//div[text()="Comment"]',  # Alternate text-based
                '//div[contains(@class, "x1i10hfl")]//div[contains(text(), "Comment")]',  # Class-based
                '//span[contains(text(), "Comment")]//ancestor::div[@role="button"]'  # Ancestor approach
            ]
            
            for selector in selectors:
                try:
                    # Wait for element with timeout
                    comment_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    
                    # Try different click methods
                    try:
                        comment_button.click()
                    except:
                        # Fallback to JavaScript click
                        driver.execute_script("arguments[0].click();", comment_button)
                    
                    print("  ✓ Comment button clicked successfully")
                    smart_delay(1, 2)  # Wait for comments to load
                    return True
                    
                except Exception:
                    continue
            
            if attempt < max_retries - 1:
                print(f"  ⚠️ Retry {attempt + 1}/{max_retries}")
                smart_delay(1, 2)
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  ❌ Failed to click comment button: {e}")
                return False
                
            print(f"  ⚠️ Attempt {attempt + 1} failed, retrying...")
            smart_delay(1, 2)
    
    return False

def click_view_more_comments(driver, retries=3, smooth_scroll=False):
    """Clicks 'View more comments' with controlled scrolling"""
    for attempt in range(retries):
        try:
            selectors = [
                "//span[contains(text(), 'View more comments')]",
                "//div[contains(text(), 'View more comments')]",
                "//div[@role='button' and contains(., 'View more comments')]"
            ]
            
            for selector in selectors:
                try:
                    button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if not button.is_displayed():
                        continue
                    
                    # Controlled scrolling
                    if smooth_scroll:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                            button
                        )
                    else:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", 
                            button
                        )
                    smart_delay(0.5, 1)
                    
                    # Try click methods
                    try:
                        driver.execute_script("arguments[0].click();", button)
                    except:
                        ActionChains(driver).move_to_element(button).click().perform()
                        
                    return True
                except:
                    continue
                    
            if attempt < retries - 1:
                smart_delay(1, 2)
                
        except Exception as e:
            if attempt == retries - 1:
                return False
            smart_delay(1, 2)
    return False

def click_see_all(driver, retries=3):
    """Clicks 'See all' button to show comments with enhanced reliability"""
    for attempt in range(retries):
        try:
            # Try multiple selectors
            selectors = [
                "//span[contains(text(), 'See all')]",
                "//a[contains(text(), 'See all')]",
                "//div[@role='button' and contains(., 'See all')]"
            ]
            
            for selector in selectors:
                try:
                    button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if not button.is_displayed():
                        continue
                        
                    # Try different click methods
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                        smart_delay(0.5, 1)
                        driver.execute_script("arguments[0].click();", button)
                    except:
                        ActionChains(driver).move_to_element(button).click().perform()
                        
                    smart_delay(2, 3)
                    return True
                except:
                    continue
                    
            if attempt < retries - 1:
                smart_delay(1, 2)
                
        except Exception as e:
            if attempt == retries - 1:
                print(f"Failed to click see all: {e}")
                return False
            smart_delay(1, 2)
    return False

def wait_for_comments_load(driver, timeout=10):
    """Wait for comments section to fully load"""
    try:
        # Wait for comments container
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='article']//div[contains(@class, 'x1n2onr6')]"))
        )
        # Small delay for dynamic content
        sleep(random.uniform(1, 2))
        return True
    except TimeoutException:
        return False

def get_comments(driver, controlled_scroll=False):
    """Get comments with memory-optimized deduplication"""
    seen_comments = set()  # Use set for O(1) lookups
    retry_count = 0
    max_retries = 3
    no_new_comments = 0
    max_no_new = 3
    
    def is_valid_comment(text):
        """Check if comment is valid and not seen before"""
        if not text or text.isspace():
            return False
        cleaned = clean_comment_text(text)
        if not cleaned or is_ui_text(cleaned):
            return False
        if cleaned in seen_comments:
            return False
        seen_comments.add(cleaned)
        return True

    try:
        # Find comment container first
        comment_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
        )
        
        while retry_count < max_retries and no_new_comments < max_no_new:
            try:
                # Get comments count before loading more
                previous_count = len(seen_comments)
                
                # Optimized comment selectors
                selectors = [
                    "//div[contains(@class, 'x1y1aw1k')]//div[@dir='auto']",
                    "//div[@role='article']//div[contains(@class, 'xdj266r')]",
                    "//div[contains(@class, '_7a9a')]"
                ]
                
                # Process comments in batches
                for selector in selectors:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        try:
                            text = element.text.strip()
                            if is_valid_comment(text):
                                continue
                        except:
                            continue
                
                # Check if we found new comments
                if len(seen_comments) == previous_count:
                    no_new_comments += 1
                else:
                    no_new_comments = 0
                
                # Try to load more comments
                if not click_view_more_comments(driver):
                    no_new_comments += 1
                else:
                    smart_delay(1, 2)
                
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    break
                smart_delay(1, 2)

    except Exception as e:
        print(f"Error in comment extraction: {e}")

    # Convert set to list for final output
    return list(seen_comments)

def is_ui_text(text):
    """Check if text is Facebook UI element"""
    ui_patterns = [
        r'^Like$', 
        r'^Comment$',
        r'^Share$',
        r'^Follow$',
        r'^Reply$',
        r'^See translation$',
        r'^Write a comment',
        r'^View more comments$',
        r'^Most relevant$',
        r'^All comments$',
        r'^\d+[dwmy]$',  # Timestamps like 4d, 1w, etc.
        r'^Reply to.*$',
        r'^·.*$'
    ]
    return any(re.match(pattern, text.strip()) for pattern in ui_patterns)

def clean_comment_text(text):
    """Memory-optimized comment cleaning"""
    if not text:
        return ""
    
    # Use string replacement for simple UI elements
    text = text.replace('Follow', '').replace('Like', '').replace('Comment', '') \
              .replace('Share', '').replace('Reply', '').replace('See translation', '') \
              .replace('Write a comment…', '').replace('Most relevant', '') \
              .replace('All comments', '').replace('See more', '')
    
    # Use single regex replacement for timestamp patterns
    text = re.sub(r'\b\d+[dwmy]\b|\bReply to.*?\n?|·.*?(?=\n|$)', '', text)
    
    # Clean whitespace efficiently
    text = ' '.join(filter(None, text.split()))
    
    return text.strip()

def collect_comments(browser):
    """Enhanced helper function to collect all comments"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Temporarily disable smooth scrolling
            browser.execute_script("document.documentElement.style.scrollBehavior = 'auto';")
            
            # Try to show all comments first
            click_see_all(browser)
            smart_delay(1, 2)
            
            # Ensure comments are loaded
            if not wait_for_comments_load(browser):
                continue

            # Click view more comments repeatedly
            while True:
                try:
                    view_more = WebDriverWait(browser, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'View more comments')]"))
                    )
                    if not view_more.is_displayed():
                        break
                    view_more.click()
                    smart_delay(0.5, 1)
                except TimeoutException:
                    break
                except:
                    smart_delay(1, 2)
                    continue
            
            return True
        finally:
            # Restore default scroll behavior
            browser.execute_script("document.documentElement.style.scrollBehavior = '';")
    return False

def click_see_all(driver):
    """Click See all button with improved reliability"""
    try:
        # Try multiple possible selectors
        selectors = [
            "//span[contains(text(), 'See all')]",
            "//span[contains(text(), 'View all')]",
            "//a[contains(text(), 'All Comments')]"
        ]
        
        for selector in selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if element.is_displayed():
                    # Try JavaScript click first
                    driver.execute_script("arguments[0].click();", element)
                    return True
            except:
                continue

        return False
    except:
        return False

def get_captions(driver):
    """
    Crawls Facebook posts and extracts their captions.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A list of the post's captions.
    """
    captions = []
    caption_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs x126k92a') or contains(@class, 'x11i5rnm xat24cr x1mh8g0r x1vvkbs xtlvy1s x126k92a')]")
    for caption_element in caption_elements:
        caption = caption_element.text
        captions.append(caption)

    return captions


def get_emojis(driver):
    """
    Crawls a Facebook post's caption, extracting each line and any following emojis.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A list of all emojis of the Facebook post's caption
    """
    # Find the caption element
    caption_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs x126k92a') or contains(@class, 'x11i5rnm xat24cr x1mh8g0r x1vvkbs xtlvy1s x126k92a')]")

    # Get all lines and emojis, handling <br> tags for line breaks
    lines_and_emojis = []

    for caption_element in caption_elements:
            # Handle image-based emojis
            try:
                img_elements = caption_element.find_elements(By.XPATH, ".//img")  # Find <img> tags within the element
                if img_elements:
                    for img in img_elements:
                        alt_text = img.get_attribute("alt")
                        if alt_text:
                            lines_and_emojis.append(alt_text)

            except NoSuchElementException:
                pass

    return lines_and_emojis


def get_captions_emojis(driver):
    """
    Extracts text and emojis from Facebook post captions.
    """
    caption_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs x126k92a') or contains(@class, 'x11i5rnm xat24cr x1mh8g0r x1vvkbs xtlvy1s x126k92a')]")
    
    captions = []
    for caption_element in caption_elements:
        try:
            soup = BeautifulSoup(caption_element.get_attribute("outerHTML"), 'html.parser')
            for div in soup.find_all('div', dir="auto"):
                result = []
                for child in div.descendants:
                    if child.name == 'img' and 'alt' in child.attrs:
                        result.append(child['alt'])  # Extract emoji from 'alt' attribute
                    elif child.name is None:  # This is text
                        text = child.strip()
                        if text:
                            result.append(text)
            
                captions.append(' '.join(result))

        except AttributeError as e:
            print(f"Error processing caption: {e}")

    return captions

def get_captions_spe(driver):
    """
    Extracts text and emojis from Facebook post captions.
    """
    captions = []

    try:
        caption_title = driver.find_element(By.XPATH, "//div[contains(@class, 'xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs')]")
        try:
            soup = BeautifulSoup(caption_title.get_attribute("outerHTML"), 'html.parser')
            for div in soup.find_all('div', dir="auto"):
                result = []
                for child in div.descendants:
                    if child.name == 'img' and 'alt' in child.attrs:
                        result.append(child['alt'])  # Extract emoji from 'alt' attribute
                    elif child.name is None:  # This is text
                        text = child.strip()
                        if text:
                            result.append(text)
            
                captions.append(' '.join(result))
        except AttributeError as e:
            print(f"Error processing caption: {e}")
    except:
        pass

    caption_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'x11i5rnm xat24cr x1mh8g0r x1vvkbs xtlvy1s')]")

    for caption_element in caption_elements:
        try:
            soup = BeautifulSoup(caption_element.get_attribute("outerHTML"), 'html.parser')
            for div in soup.find_all('div', dir="auto"):
                result = []
                for child in div.descendants:
                    if child.name == 'img' and 'alt' in child.attrs:
                        result.append(child['alt'])  # Extract emoji from 'alt' attribute
                    elif child.name is None:  # This is text
                        text = child.strip()
                        if text:
                            result.append(text)
            
                captions.append(' '.join(result))
        except AttributeError as e:
            print(f"Error processing caption: {e}")

    return captions

def get_captions_reel(driver):

    captions = []

    try:
        click_see_more(driver)
    except:
        pass

    try:

        caption_title = driver.find_element(By.XPATH, "//div[contains(@class, 'xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs x126k92a') ]")

        # print(caption_element.get_attribute("outerHTML"))

        # Parse the HTML
        soup = BeautifulSoup(caption_title.get_attribute("outerHTML"), 'html.parser')

        # Extract caption text
        caption_div = soup.find("div", class_="xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs x126k92a")
        caption_text = caption_div.get_text(separator=" ").strip()

        # Remove "See less" if present
        if "See less" in caption_text:
            caption_text = caption_text.replace("See less", "").strip()

        captions.append(caption_text)

    except:
        pass
    
    try:
        captions_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'x11i5rnm xat24cr x1mh8g0r x1vvkbs xtlvy1s x126k92a') ]")

        for captions_element in captions_elements:
            # Parse the HTML
            soup = BeautifulSoup(captions_element.get_attribute("outerHTML"), 'html.parser')

            # Extract caption text
            caption_div = soup.find("div", class_="x11i5rnm xat24cr x1mh8g0r x1vvkbs xtlvy1s x126k92a")
            caption_text = caption_div.get_text(separator=" ").strip()

            # Remove "See less" if present
            if "See less" in caption_text:
                caption_text = caption_text.replace("See less", "").strip()

            captions.append(caption_text)
    except:
        pass

    return captions

def get_image_urls(driver):
    """
    Crawls a Facebook post and extracts image URLs.
    """
    # Wait for media container to be present
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//div[contains(@class, 'x10l6tqk x13vifvy')] | .//div[contains(@class, 'xz74otr x1gqwnh9 x1snlj24')]"))
        )
        # Additional delay for images to load
        sleep(2)
    except TimeoutException:
        print("No media container found")
        return []

    # Find image elements
    image_elements = driver.find_elements(By.XPATH, ".//div[contains(@class, 'x10l6tqk x13vifvy') or contains(@class, 'xz74otr x1gqwnh9 x1snlj24')]/img")
    image_urls = []
    for img in image_elements:
        try:
            # Wait for each image to be present and visible
            WebDriverWait(driver, 5).until(
                EC.visibility_of(img)
            )
            src = img.get_attribute('src')
            if src and src not in image_urls:
                image_urls.append(src)
        except:
            continue

    return image_urls

def download_images(image_urls, download_dir="images"):
    """
    Downloads images from a list of URLs.

    Args:
        image_urls: A list of image URLs.
        download_dir: The directory to save the images to.
    """
    if not image_urls:
        print("No image URLs provided.")
        return

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    for i, url in enumerate(image_urls):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for bad status codes

            with open(os.path.join(download_dir, f"image_{i+1}.jpg"), "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            # print(f"Downloaded image {i+1} from {url}")

        except requests.exceptions.RequestException as e:
            print(f"Error downloading image from {url}: {e}")

def get_video_urls(driver):
    """Get video URLs by first clicking the video icon"""
    video_urls = []
    
    try:
        print("  → Looking for video player...")
        # Try to find and click the video icon button
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "inline-video-icon"))
        )
        print("  ✓ Found video player button")
        button.click()
        smart_delay(1, 2)  # Wait for video to load after click
        
        # Look for video elements
        video_elements = driver.find_elements(By.XPATH, ".//div[contains(@class, 'inline-video-container')]/video")
        if video_elements:
            print(f"  → Found {len(video_elements)} video element(s)")
            for video in video_elements:
                src = video.get_attribute("src")
                if src and src not in video_urls:
                    video_urls.append(src)
        
        if not video_urls:
            print("  ⚠️ No video sources found after clicking player")
            
    except Exception as e:
        print(f"  ⚠️ Could not interact with video player: {e}")
        # Fallback to direct video element search
        try:
            video_elements = driver.find_elements(By.XPATH, "//video[@src]")
            for video in video_elements:
                src = video.get_attribute("src")
                if src and src not in video_urls:
                    video_urls.append(src)
        except:
            pass
    
    return video_urls

def download_videos(video_urls, download_dir="videos"):
    """Downloads videos from a list of URLs"""
    if not video_urls:
        print("No video URLs provided.")
        return
        
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    for i, url in enumerate(video_urls):
        try:
            print(f"  → Downloading video {i+1}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(os.path.join(download_dir, f"video_{i+1}.mp4"), "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"  ✓ Video {i+1} downloaded successfully")

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error downloading video {i+1}: {e}")

def download_video_ytdl(url, download_dir):
    """Download video using yt-dlp"""
    try:
        print("  → Downloading video using yt-dlp...")
        ydl_opts = {
            'format': 'best',  # Download best quality
            'outtmpl': f'{download_dir}/video_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("  ✓ Video download complete")
        return True
    except Exception as e:
        print(f"  ❌ Error downloading with yt-dlp: {e}")
        return False

def get_post_links(driver, fanpage_url, scroll_limit=0):
    """
    Crawls a Facebook fanpage and extracts post links.
    """
    post_urls = []
    scroll_count = 0
    last_height = 0
    no_new_content_count = 0
    consecutive_same_count = 0
    last_post_count = 0
    
    try:
        driver.get(fanpage_url)
        sleep(3)
        
        while True:
            try:
                # Manual interrupt check
                if keyboard.is_pressed("enter"):
                    print("\nStopping the scrolling (manual interrupt).")
                    break

                # Extract links before scrolling
                try:
                    link_post_elements = driver.find_elements(
                        By.CSS_SELECTOR, 
                        "a[href*='/posts/'], a[href*='/videos/'], a[href*='/reel/']"
                    )
                    for link in link_post_elements:
                        url = link.get_attribute("href")
                        if url and url not in post_urls:
                            post_urls.append(url)
                except Exception:
                    pass

                # Scroll operation
                scroll_distance = random.randint(300, 700)
                driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
                smart_delay(0.5, 1.5)
                
                scroll_count += 1
                
                # Check conditions based on scroll_limit
                if scroll_limit > 0:
                    # If limit is set, only check if we've reached it
                    if scroll_count >= scroll_limit:
                        print(f"\nReached scroll limit of {scroll_limit}")
                        break
                else:
                    # Only check for end of content if no limit is set
                    current_height = driver.execute_script("return document.documentElement.scrollHeight")
                    if len(post_urls) == last_post_count:
                        consecutive_same_count += 1
                    else:
                        consecutive_same_count = 0
                        last_post_count = len(post_urls)

                    if current_height == last_height:
                        no_new_content_count += 1
                        if no_new_content_count >= 5 and consecutive_same_count >= 5:
                            print("\nReached end of page (no new content)")
                            break
                    else:
                        no_new_content_count = 0
                        last_height = current_height

                # Progress update
                if scroll_count % 5 == 0:
                    print(f"\rScrolls: {scroll_count}, Posts found: {len(post_urls)}", end="")

            except Exception as e:
                print(f"\nError during scrolling: {e}")
                sleep(2)
                continue

        post_urls = remove_duplicate_links(post_urls)
        print(f"\nTotal unique posts found: {len(post_urls)}")
        return post_urls

    except TimeoutException:
        print("Timed out waiting for the page to load.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def clean_comment_text(text):
    """Clean Facebook comment text with improved UI element removal"""
    if not text:
        return ""
        
    # Remove UI elements
    ui_elements = {
        'Follow': '',
        'Like': '',
        'Write a comment…': '',
        'Comment': '',
        'Share': '',
        'Reply': '',
        'See translation': '',
        'Most relevant': '',
        'All comments': '',
        'Previous comments': '',
        'View more comments': '',
        'View previous comments': '',
        'See more': '',
        '· Follow': '',
        '· Share': '',
        '· Reply': ''
    }
    
    cleaned_text = text
    for ui_text, replacement in ui_elements.items():
        cleaned_text = cleaned_text.replace(ui_text, replacement)
    
    # Remove timestamps
    cleaned_text = re.sub(r'\b\d+[dwmy]\b', '', cleaned_text)
    
    # Remove "Reply to..." lines
    cleaned_text = re.sub(r'^Reply to.*?\n?', '', cleaned_text, flags=re.MULTILINE)
    
    # Clean up whitespace
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    cleaned_text = re.sub(r'^\s+|\s+$', '', cleaned_text, flags=re.MULTILINE)
    
    # Remove empty lines
    cleaned_text = '\n'.join(line for line in cleaned_text.splitlines() if line.strip())
    
    return cleaned_text.strip()

def save_text(text_list, file_path):
    """Memory-efficient text saving with deduplication"""
    if not text_list:
        return
        
    try:
        # Process in chunks to save memory
        chunk_size = 1000
        seen = set()
        
        with open(file_path, "w", encoding="utf-8") as file:
            for i in range(0, len(text_list), chunk_size):
                chunk = text_list[i:i + chunk_size]
                
                # Process chunk
                for text in chunk:
                    if "comments.txt" in file_path:
                        cleaned = clean_comment_text(text)
                    else:
                        cleaned = text.strip()
                        
                    # Check for duplicates
                    if cleaned and not cleaned.isspace() and cleaned not in seen:
                        seen.add(cleaned)
                        file.write(cleaned + "\n")
                        
                # Clear chunk from memory
                del chunk
                
        # Clear sets
        seen.clear()
        
    except Exception as e:
        print(f"Error saving text: {e}")

def extract_facebook_post_id(url):
    """
    Extracts the post ID from a Facebook post URL.

    Args:
        url: The Facebook post URL.

    Returns:
        The post ID, or None if no ID could be found.
    """
    match = re.search(r"(?:reel/|posts/|videos/|pfbid)([\w\d]+)", url)
    if match:
        return match.group(1)
    return None

def remove_duplicate_links(links):
    """
    Remove links with duplicate IDs and keep only one for each unique ID.
    """
    unique_links = {}
    for link in links:
        post_id = extract_facebook_post_id(link)
        if post_id and post_id not in unique_links:
            unique_links[post_id] = link
    return list(unique_links.values())

def initialize_browsers(driver_path, cookies_path, headless=True):
    """Initialize both regular and mobile browsers"""
    try:
        # Initialize regular browser
        print("\n=== Initializing Browsers ===")
        print("→ Starting regular browser...")
        browser = login(driver_path, cookies_path, headless)
        if not browser:
            raise Exception("❌ Failed to initialize regular browser")
        print("✓ Regular browser initialized successfully")
        
        # Initialize mobile browser
        print("\n→ Starting mobile browser...")
        browser_mobile = login_mobile(driver_path, cookies_path, headless)
        if not browser_mobile:
            browser.quit()
            raise Exception("❌ Failed to initialize mobile browser")
        print("✓ Mobile browser initialized successfully")
        print("=== Browser Setup Complete ===\n")
            
        return browser, browser_mobile
        
    except Exception as e:
        print(f"\n❌ Error initializing browsers: {e}")
        if 'browser' in locals() and browser:
            browser.quit()
        if 'browser_mobile' in locals() and browser_mobile:
            browser_mobile.quit()
        return None, None

def wait_for_mobile_video_load(browser, max_retries=3):
    """Wait for video content to load in mobile view with better debugging"""
    print("\n→ Checking video content...")
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}")
            
            WebDriverWait(browser, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            selectors = [
                "//div[contains(@class, 'story_body_container')]//video",
                "//div[contains(@class, '_53mw')]//video",
                "//video[@src]",
                "//div[contains(@class, 'video-player')]//video"
            ]
            
            for selector in selectors:
                try:
                    WebDriverWait(browser, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print("  ✓ Video element found")
                    return True
                except:
                    continue
                    
            print(f"  ⚠️ No video found in attempt {attempt + 1}")
            browser.refresh()
            smart_delay(2, 3)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            if attempt < max_retries - 1:
                browser.refresh()
                smart_delay(2, 3)
    
    return False

def process_post(browser, browser_mobile, url, folder, use_ytdl=False):
    """Process a single post based on its type"""
    try:
        print(f"\n=== Processing Post: {url} ===")
        print("→ Loading desktop version...")
        browser.get(url)
        smart_delay(2, 3)
        
        # Get current URL and check if it's a valid Facebook post
        current_url = browser.current_url
        if not is_valid_facebook_post(current_url):
            print("❌ Invalid post URL after redirect")
            print(f"  Redirected to: {current_url}")
            return False
            
        print("✓ URL validation successful")
            
        # Check if the post contains video content
        try:
            print("→ Checking for video content...")
            video_element = WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//video | //div[contains(@class, 'inline-video-container')]"))
            )
            print("✓ Video content detected")
            print("→ Initiating video processing workflow...")
            return process_video_post(browser, browser_mobile, url, folder, use_ytdl)
        except TimeoutException:
            print("→ No video content found")
            pass
            
        # Process based on URL type
        if "videos" in url or "reel" in url:
            print("→ URL indicates video/reel content")
            mobile_url = url.replace('www.facebook.com', 'm.facebook.com')
            print(f"→ Switching to mobile version: {mobile_url}")
            browser_mobile.get(mobile_url)
            smart_delay(2, 3)
            
            if "videos" in url:
                print("→ Processing as video post...")
                return process_video_post(browser, browser_mobile, url, folder, use_ytdl)
            else:
                print("→ Processing as reel post...")
                return process_reel_post(browser, browser_mobile, url, folder)
        else:
            print("→ Processing as regular post...")
            return process_regular_post(browser, folder)
                
    except Exception as e:
        print(f"❌ Error processing post: {e}")
        print(f"  URL: {url}")
        print(f"  Folder: {folder}")
        return False

def is_valid_facebook_post(url):
    """Check if URL is a valid Facebook post after redirection"""
    if not url:
        return False
    
    # List of valid Facebook URL patterns
    valid_patterns = [
        r'facebook\.com/[^/]+/posts/',
        r'facebook\.com/[^/]+/videos/',
        r'facebook\.com/[^/]+/photos/',
        r'facebook\.com/photo/',
        r'facebook\.com/watch/?\?v=',
        r'facebook\.com/reel/',
        r'facebook\.com/[^/]+/permalink/',
        r'facebook\.com/story\.php'
    ]
    
    return any(re.search(pattern, url) for pattern in valid_patterns)

class TimeoutManager:
    """Context manager for handling timeouts"""
    def __init__(self, timeout):
        self.timeout = timeout
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if time.time() - self.start_time > self.timeout:
            raise TimeoutException("Operation timed out")
        return False

def get_comments_safe(browser, max_attempts=3):
    """Get comments with safety checks"""
    for attempt in range(max_attempts):
        try:
            # Try to find the comments section without scrolling
            comments_section = WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
            )
            
            # Only proceed if comments section is visible
            if comments_section.is_displayed():
                return get_comments(browser, controlled_scroll=True)
            else:
                print("⚠️ Comments section not visible")
                return []
                
        except TimeoutException:
            if attempt == max_attempts - 1:
                print("⚠️ Comments section not found")
                return []
            smart_delay(1, 2)
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"⚠️ Error getting comments: {e}")
                return []
            smart_delay(1, 2)
    return []
