# Crawl-Facebook-Data

A tool to crawl Facebook pages and save posts, images, videos, and comments.

## Prerequisites

1. **Python 3.7+**
2. **Chrome Browser**
3. **ChromeDriver** matching your Chrome version
   - Download from: <https://chromedriver.chromium.org/downloads>
   - Place `chromedriver.exe` in the project root directory

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/lunovian/Crawl-Facebook-Data.git
   cd Crawl-Facebook-Data
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

## Setup

1. **Create Environment File:**
   - Create a `.env` file in the project root directory:

   ```plaintext
   FB_EMAIL=your_facebook_email
   FB_PASSWORD=your_facebook_password
   ```

2. **Save Facebook Cookies:**

   ```bash
   python save_cookies.py
   ```

   - This will load credentials from `.env`
   - Creates `my_cookies.pkl` file with your Facebook login session
   - Wait for the login process to complete in browser
   - You may need to handle 2FA if enabled on your account

## Usage

### Basic Usage

1. **Single Page Crawl:**

   ```bash
   python crawl.py --page "https://www.facebook.com/pagename" --name "page_folder_name"
   ```

2. **With Options:**

   ```bash
   python crawl.py --page "https://www.facebook.com/pagename" --name "page_folder_name" --scroll-limit 100 --browsers 2 --resume
   ```

### Advanced Options

- `--driver`: Path to chromedriver (default: ./chromedriver.exe)
- `--cookies`: Path to cookies file (default: my_cookies.pkl)
- `--headless`: Run in headless mode (default: True)
- `--no-headless`: Run with browser visible
- `--scroll-limit`: Number of scrolls (0 for unlimited)
- `--resume`: Resume crawling (skip already crawled posts)
- `--rescan`: Rescan only empty folders
- `--use-ytdl`: Use yt-dlp for video downloads (default: True)
- `--no-ytdl`: Disable yt-dlp for video downloads
- `--browsers`: Number of parallel browsers (default: 2)

### Multi-Page Crawling

1. Create a config file `pages_config.json`:

   ```json
   {
       "pages": [
           {
               "url": "https://www.facebook.com/page1",
               "name": "page1_folder",
               "max_scroll": 100,
               "min_posts": 50,
               "resume": true
           },
           {
               "url": "https://www.facebook.com/page2",
               "name": "page2_folder",
               "max_scroll": 200,
               "min_posts": 100
           }
       ]
   }
   ```

2. Run with config:

   ```bash
   python crawl.py --config pages_config.json --browsers 4
   ```

## Output Structure
