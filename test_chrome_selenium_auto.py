from selenium import webdriver

# Set up options for Chrome (optional)
options = webdriver.ChromeOptions()
# Example of adding options: headless mode, disable GPU acceleration, etc.
options.add_argument('--headless')
options.add_argument('--disable-gpu')

# Initialize the WebDriver with the specified options
driver = webdriver.Chrome(options=options)

# Make a request to a webpage
driver.get("https://example.com")

# Optional: Print the title of the webpage to verify
print(driver.title)

# Close the browser
driver.quit()
