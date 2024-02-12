from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Specify the path to chromedriver
chromedriver_path = '../chromedriver-linux64/chromedriver'  # Update this path

# Specify Chrome binary location
chrome_options = Options()
chrome_options.binary_location = "/usr/bin/google-chrome"
chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_options.add_argument("--no-sandbox")  # Bypass OS security model, crucial for running in docker containers
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
chrome_options.add_argument("--disable-gpu")  # Applicable for headless mode and some versions of Chrome


service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Now you can use driver to navigate, for example:
driver.get("http://example.com")
print(driver.title)

# Don't forget to quit the driver
driver.quit()