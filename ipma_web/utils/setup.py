from selenium import webdriver

from selenium.webdriver.chrome.options import Options

# from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from django.conf import settings

# Logging!
import logging

logger = logging.getLogger(__name__)


def selenium_setup(headless=False, implicitly_wait=10):
    # Utility function to setup the Selenium driver with all the parameters.
    # The bot can be seen on noVNC (http://localhost:7901/)

    try:
        options = Options()

        if headless:  # avoid display on
            options.add_argument("--headless")

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-fre")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")

        driver = webdriver.Remote(
            command_executor=settings.SELENIUM_HUB_URL,
            options=options,
        )
        driver.implicitly_wait(implicitly_wait)
        logger.info("Selenium driver successfully initialized.")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Selenium driver: {e}")
        return None
