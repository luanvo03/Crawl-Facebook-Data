from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import pickle
from time import sleep
from configuration.secure_config import SecureConfig

def save_facebook_cookies(driver_path="./chromedriver.exe"):
    try:
        # Initialize secure config
        config = SecureConfig()
        credentials = config.get_credentials()
        
        # Setup Chrome driver
        service = Service(executable_path=driver_path)
        browser = webdriver.Chrome(service=service)
        
        # Open Facebook
        browser.get('https://www.facebook.com/')
        sleep(3)
        
        # Enter login information securely
        user = browser.find_element(By.ID, "email")
        user.send_keys(credentials['email'])
        
        password = browser.find_element(By.ID, "pass")
        password.send_keys(credentials['password'])
        
        # Login
        login_button = browser.find_element(By.NAME, "login")
        login_button.click()
        
        # Wait for login to complete
        sleep(20)
        
        # Save cookies
        cookies_file = "my_cookies.pkl"
        pickle.dump(browser.get_cookies(), open(cookies_file, "wb"))
        print(f"✓ Cookies saved successfully to {cookies_file}")
        
    except Exception as e:
        print(f"❌ Error saving cookies: {str(e)}")
    finally:
        browser.quit()

if __name__ == "__main__":
    save_facebook_cookies()