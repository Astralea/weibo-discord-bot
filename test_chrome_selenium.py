from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Step 1: Set up ChromeDriver (assumes ChromeDriver is in PATH or using WebDriver Manager)
service = Service(ChromeDriverManager().install())

# Step 2: Set up options for Chrome (optional)
options = webdriver.ChromeOptions()
# For example, use headless mode (no GUI window)
# options.add_argument('--headless')

# Step 3: Initialize the WebDriver
driver = webdriver.Chrome(service=service, options=options)

# Step 4: Make a request to a webpage
driver.get("http://example.com")

# Optional: print the title of the webpage to verify
print(driver.title)

# Step 5: Close the browser
driver.quit()
