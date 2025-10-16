import time
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROMEDRIVER_PATH = '/home/mitu/Documents/Apps/chromedriver-linux64/chromedriver'
CHROMEHEADLESSSHELL_PATH = "/home/mitu/Documents/Apps/chrome-headless-shell-linux64/chrome-headless-shell"
CHROME_PATH = "/home/mitu/Documents/Apps/chrome-linux64/chrome"

# Set Chrome options
chrome_options = Options()
chrome_options.binary_location = CHROME_PATH  # Specify custom Chrome binary path
# chrome_options.add_argument("--headless")  # Optional: run in headless mode
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Set ChromeDriver service
service = Service(CHROMEDRIVER_PATH)

# Start WebDriver
browser = webdriver.Chrome(service=service, options=chrome_options)

# Open Website
browser.get("https://www.farmasib.ro")

time.sleep(2)

# Accept Cookies
try:
    accept_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))  # Modify XPath as needed
        )
    accept_button.click()
except:
    print("No Accept button found or already accepted")

try:
    accepta_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Acceptă')]"))  # Modify XPath as needed
        )
    accepta_button.click()
except:
    print("No Accept button found or already accepted")



# Set Website Dimension
desktop_width = 1920
desktop_height = 1080
viewport_height = 1080

mobile_width = 430
mobiel_height = 930

browser.set_window_size(desktop_width, desktop_height)

# Get total page height
total_height = browser.execute_script("return document.body.scrollHeight")
page_width = browser.execute_script("return document.body.scrollWidth")

# Create an empty image to store the full screenshot
screenshot = Image.new("RGB", (page_width, total_height))

# Get the header height - adjust the selector to match your website's header
header_height = browser.execute_script("""
    // Try to find the header element - adjust these selectors as needed for your specific website
    const header = document.querySelector('#masthead') || 
               document.querySelector('.site-header') || 
               document.querySelector('#site-header') ||
               document.querySelector('.main-header') ||
               document.querySelector('header.header') ||
               document.querySelector('.wp-site-header') ||
               document.querySelector('#header') ||
               // Then fall back to the generic selectors
               document.querySelector('header') || 
               document.querySelector('.header') ||
               document.querySelector('.sticky-header') ||
               document.querySelector('.navbar-fixed') ||
               document.querySelector('.fixed-top');
    if (header) {
        return header.offsetHeight;
    }
    // If no header is found, use a default value (adjust as needed)
    return 100;
""")

# Take first screenshot (including header)
browser.save_screenshot("temp_screenshot.png")
first_part = Image.open("temp_screenshot.png")
screenshot.paste(first_part, (0, 0))

# Calculate how much of the page is visible in the first screenshot
first_visible_height = min(viewport_height, total_height)

# Now capture the rest of the page in pieces, but ignore the header area
remaining_height = total_height - first_visible_height
current_scroll = first_visible_height - header_height  # Subtract header height for overlap

while current_scroll < total_height:
    # Scroll to position
    browser.execute_script(f"window.scrollTo(0, {current_scroll});")
    time.sleep(1.5)  # Allow time for the page to render
    
    # Capture screenshot
    browser.save_screenshot("temp_screenshot.png")
    part = Image.open("temp_screenshot.png")
    
    # Calculate where to paste this piece
    # We're pasting it at the scroll position plus header height
    paste_y = current_scroll + header_height
    
    # Get the part of the image below the header
    part_height = viewport_height - header_height
    part_without_header = part.crop((0, header_height, page_width, viewport_height))
    
    # Paste the part without the header
    screenshot.paste(part_without_header, (0, paste_y))
    
    # Increment scroll position
    current_scroll += part_height

# Save the full screenshot
full_screenshot_path = "full_screenshot.png"
screenshot.save(full_screenshot_path)
screenshot.show()

# Quit browser
browser.quit()
