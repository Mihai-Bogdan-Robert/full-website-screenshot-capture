import time
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROMEDRIVER_PATH = '/home/mitu/Documents/Apps/chromedriver-linux64/chromedriver'
CHROME_PATH = "/home/mitu/Documents/Apps/chrome-linux64/chrome"

# Configure Chrome options
chrome_options = Options()
chrome_options.binary_location = CHROME_PATH
chrome_options.add_argument("--headless=new")  # Use headless mode
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--hide-scrollbars")  # Hide scrollbars

service = Service(CHROMEDRIVER_PATH)
browser = webdriver.Chrome(service=service, options=chrome_options)

browser.get("https://www.farmasib.ro")

# Handle cookie acceptance
try:
    accept_button = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept') or contains(., 'Acceptă')]"))
    )
    accept_button.click()
except Exception as e:
    print("Cookie acceptance not required or already accepted:", e)

# Set window dimensions
viewport_width = 1920
viewport_height = 1080
browser.set_window_size(viewport_width, viewport_height)

# Calculate page dimensions
total_height = browser.execute_script(
    "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);"
)
page_width = browser.execute_script("return document.body.scrollWidth")

# Detect header and footer heights
header_height = browser.execute_script("""
    const header = document.querySelector('header, .header, #header');
    return header ? header.offsetHeight : 0;
""")

footer_height = browser.execute_script("""
    const footer = document.querySelector('footer, .footer, #footer');
    return footer ? footer.offsetHeight : 0;
""")

# Initialize full screenshot
screenshot = Image.new("RGB", (page_width, total_height))

# Capture header
browser.save_screenshot("temp_header.png")
header_img = Image.open("temp_header.png").crop((0, 0, page_width, header_height))
screenshot.paste(header_img, (0, 0))

current_position = header_height

# Capture content between header and footer
while current_position < total_height - footer_height:
    scroll_position = current_position - (header_height if current_position > header_height else 0)
    browser.execute_script(f"window.scrollTo(0, {scroll_position});")
    time.sleep(1.5)  # Allow content to load
    
    browser.save_screenshot("temp_content.png")
    content_part = Image.open("temp_content.png")
    
    # Determine visible area height
    crop_top = header_height if current_position > header_height else 0
    crop_bottom = viewport_height - footer_height
    content_height = crop_bottom - crop_top
    
    # Adjust for remaining space
    remaining_space = total_height - footer_height - current_position
    if remaining_space < content_height:
        crop_bottom = crop_top + remaining_space
    
    content_cropped = content_part.crop((0, crop_top, page_width, crop_bottom))
    screenshot.paste(content_cropped, (0, current_position))
    
    current_position += content_cropped.height

# Capture footer
browser.execute_script(f"window.scrollTo(0, {total_height - viewport_height});")
time.sleep(1.5)
browser.save_screenshot("temp_footer.png")
footer_img = Image.open("temp_footer.png").crop(
    (0, viewport_height - footer_height, page_width, viewport_height)
)
screenshot.paste(footer_img, (0, total_height - footer_height))

# Save and clean up
screenshot.save("full_screenshot.png")
browser.quit()