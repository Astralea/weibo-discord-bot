from selenium import webdriver

# Set up options for Firefox (optional)
options = webdriver.FirefoxOptions()
# Example of adding options: headless mode, disable GPU acceleration, etc.
options.add_argument('--headless')
options.add_argument('--disable-gpu')

# Initialize the WebDriver with the specified options
driver = webdriver.Firefox(options=options)

# Make a request to a webpage
driver.get("https://example.com")  # This is an example; adjust based on your needs

# Optional: Print the title of the webpage to verify
print(driver.title)

# Close the browser
driver.quit()
