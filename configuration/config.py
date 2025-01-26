from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
import pickle
import random
from time import sleep

def login(driver_path, cookies_path, headless=True):
    """
    Logs into Facebook using saved cookies, with enhanced bot detection avoidance.

    Args:
        driver_path: Path to the chromedriver executable.
        cookies_path: Path to the file containing saved cookies.
        headless: Whether to run in headless mode (default: True)
    """

    options = Options()
    
    # Add USB and device error handling
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-usb-devices')
    options.add_argument('--disable-usb-keyboard')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-tools')
    
    # Add logging preferences
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # Add WebGL and hardware acceleration settings
    options.add_argument('--enable-unsafe-webgl')
    options.add_argument('--enable-unsafe-swiftshader')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--ignore-gpu-blocklist')
    
    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

    # Performance optimizations
    options.add_argument('--disable-animations')
    options.add_argument('--disable-smooth-scrolling')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-notifications')
    
    # Memory management
    options.add_argument('--js-flags="--max_old_space_size=4096"')
    options.add_argument('--memory-pressure-off')
    
    # Add page load strategy
    options.page_load_strategy = 'eager'
    
    # System specific settings
    options.add_argument('--use-angle=swiftshader')
    
    # Stealth options
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Disable certain features that can be used for detection
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Random User-Agent
    user_agents = [
        # Windows 10 - Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        
        # Windows 10 - Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        
        # Windows 10 - Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        
        # macOS - Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # macOS - Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        
        # Linux - Chrome
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Linux - Firefox
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    # Use the Service object to specify the path to chromedriver
    service = Service(executable_path=driver_path)

    # Pass the Service object to the webdriver
    browser = webdriver.Chrome(service=service, options=options)

    # Apply selenium-stealth
    stealth(browser,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    # Open Facebook with initial sleep
    browser.get('https://www.facebook.com/')
    sleep(random.uniform(3, 5))  # Initial longer sleep

    # Load cookies
    try:
        cookies = pickle.load(open(cookies_path, "rb"))
        for cookie in cookies:
            # Ensure the 'sameSite' attribute is set, or it will be ignored by Chrome
            if 'sameSite' not in cookie:
                cookie['sameSite'] = 'None' # You might need 'Strict' or 'Lax' depending on the website and cookie
            if cookie.get('expiry', None) is not None:
                cookie['expiry'] = int(cookie['expiry'])
            browser.add_cookie(cookie)
    except FileNotFoundError:
        print(f"Error: Cookies file not found at {cookies_path}")
        browser.quit()
        return None
    except Exception as e:
        print(f"Error loading cookies: {e}")
        browser.quit()
        return None

    # Refresh with human-like delay
    browser.get('https://www.facebook.com/')
    sleep(random.uniform(2, 4))  # Shorter sleep after refresh

    return browser


def login_mobile(driver_path, cookies_path, headless=True):
    """
    Logs into Facebook using saved cookies, emulating a mobile device, 
    with enhanced bot detection avoidance.

    Args:
        driver_path: Path to the chromedriver executable.
        cookies_path: Path to the file containing saved cookies.
        headless: Whether to run in headless mode (default: True)
    """

    mobile_emulation = {
        "deviceName": "iPhone X"  # Or any other supported device
    }

    options = Options()
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    
    # Add USB and device error handling
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-usb-devices')
    options.add_argument('--disable-usb-keyboard')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-tools')
    
    # Add logging preferences
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # Add WebGL and hardware acceleration settings
    options.add_argument('--enable-unsafe-webgl')
    options.add_argument('--enable-unsafe-swiftshader')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--ignore-gpu-blocklist')

    # Add codec and video support
    options.add_argument('--use-fake-ui-for-media-stream')
    options.add_argument('--use-fake-device-for-media-stream')
    options.add_argument('--autoplay-policy=no-user-gesture-required')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-web-security')
    
    # Configure video/media settings
    prefs = {
        "profile.managed_default_content_settings.media_stream": 1,
        "profile.default_content_settings.cookies": 1,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.images": 1,
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1
    }
    options.add_experimental_option("prefs", prefs)

    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=414,896')  # iPhone X resolution

    # Performance optimizations
    options.add_argument('--disable-animations')
    options.add_argument('--disable-smooth-scrolling')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-notifications')
    
    # Memory management
    options.add_argument('--js-flags="--max_old_space_size=4096"')
    options.add_argument('--memory-pressure-off')
    
    # Add page load strategy
    options.page_load_strategy = 'eager'
    
    # System specific settings
    options.add_argument('--use-angle=swiftshader')

    # Stealth options - Important even when emulating a mobile device
    options.add_argument("start-maximized") # Even in mobile emulation, maximizing can be helpful
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Disable certain features that can be used for detection
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Random User-Agent (matching the emulated device)
    user_agents = [
        # iOS 17 - iPhone 15 Pro Max
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        
        # iOS 16 - iPhone 14 Series
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        
        # iOS 15 - iPhone 13 Series
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7_9 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.7 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.1 Mobile/15E148 Safari/604.1",
        
        # iPadOS
        "Mozilla/5.0 (iPad; CPU OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        
        # Android 14 - Pixel devices
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
        
        # Android 13 - Samsung devices
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
        
        # Android 12 - Various devices
        "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12; OnePlus 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    # Use the Service object to specify the path to chromedriver
    service = Service(executable_path=driver_path)

    # Pass the Service object to the webdriver
    browser = webdriver.Chrome(service=service, options=options)

    # Apply selenium-stealth
    stealth(browser,
            languages=["en-US", "en"],
            vendor="Apple Inc.", # Match vendor to the emulated device
            platform="iPhone",   # Match platform to the emulated device
            webgl_vendor="Apple Inc.", # Or "Google Inc." if you emulate an Android
            renderer="Apple GPU",       # Be sure to use appropriate WebGL renderer for your device
            fix_hairline=True,
            )

    # Open Facebook with initial sleep
    browser.get('https://m.facebook.com/') # Use the mobile version of Facebook
    sleep(random.uniform(3, 5))  # Initial longer sleep

    # Load cookies
    try:
        cookies = pickle.load(open(cookies_path, "rb"))
        for cookie in cookies:
            # Ensure the 'sameSite' attribute is set correctly
            if 'sameSite' not in cookie:
                cookie['sameSite'] = 'None' # Or 'Strict', 'Lax'
            if cookie.get('expiry', None) is not None:
                cookie['expiry'] = int(cookie['expiry'])
            browser.add_cookie(cookie)
    except FileNotFoundError:
        print(f"Error: Cookies file not found at {cookies_path}")
        browser.quit()
        return None
    except Exception as e:
        print(f"Error loading cookies: {e}")
        browser.quit()
        return None

    # Refresh with human-like delay
    browser.get('https://m.facebook.com/') # Use the mobile version of Facebook
    sleep(random.uniform(2, 4))  # Shorter sleep after refresh

    return browser