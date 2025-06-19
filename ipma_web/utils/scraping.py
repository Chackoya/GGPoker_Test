# import requests
# from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from ipma_web.utils.setup import selenium_setup
from ipma_web.utils.configs import ALLOWED_DISTRICTS

from django.conf import settings

import time

# Logging!
import logging

logger = logging.getLogger(__name__)

from django.core.cache import cache


class IpmaWebScriptLib:
    def __init__(self):
        self.driver = None

    def run_script(
        self,
        district: str,
        city: str,
        day_index: int,
        using_cache=False,
        use_selenium_for_locations=False,
    ):
        # Main method for the execution flow with Selenium
        # Returns the forecast data obtained from IPMA website.
        try:
            cache_key = f"ipma:{district.lower()}:{city.lower()}:{day_index}"
            if using_cache:
                cached = cache.get(cache_key)
                if cached:
                    return cached

            self.driver = selenium_setup()

            # ? 2 Approaches:
            # ? A- use Selenium to click on the locations options in IPMA website;
            # ? B- modify the URL directly, example: url with fragments 'https://www.ipma.pt/pt/otempo/prev.localidade.hora#Braga&Vizela'
            if use_selenium_for_locations:
                self.driver.get(settings.START_URL_IPMA)
                self._select_location(district=district, city=city)
            else:
                # faster method
                modified_url = f"{settings.START_URL_IPMA}#{district}&{city}"
                self.driver.get(modified_url)

            # res = self._extract_all_days()

            forecast_result = self._extract_data_day(day_index=day_index)
            if forecast_result:  # and using_cache:
                # always caching...

                cache.set(cache_key, forecast_result, timeout=900)
                # NOTE cache w/ *900seconds (15min)

            return forecast_result

        except Exception as e:
            logger.error("Error:", e)

        finally:
            # cleaning step to close Selenium
            try:
                if self.driver:
                    # print("Closing Chrome!")
                    logger.debug("Closing Chrome!")
                    self.driver.quit()
            except Exception as cleanup_error:
                logger.error(
                    f"Warning - Cleanup failed (attempt to close selenium browser): {cleanup_error}"
                )

    def _select_location(self, district, city):
        # Method that given a district and city, will use Selenium to intereact with the IPMA website to pick those choices.

        try:
            # select the District
            # district_select_el = self.driver.find_element(By.ID, "district")
            district_select = self._get_selector_selenium(
                "district"
            )  # Select(district_select_el)

            # get district name to check if OK
            available_districts = [opt.text.strip() for opt in district_select.options]
            logger.info("Available districts:", available_districts)

            if district not in available_districts:
                logger.warning(f"District '{district}' not found.")
                return

            logger.info(f"Selecting district: {district}")
            district_select.select_by_visible_text(district)

            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "locations"))
            )
            # time.sleep(2)

            # select the City
            if city:
                # city_select_el = self.driver.find_element(By.ID, "locations")
                # city_select = Select(city_select_el)
                city_select = self._get_selector_selenium("locations")
                available_cities = [opt.text.strip() for opt in city_select.options]

                # ensure we find a match in case input is lowercase...
                available_cities_lower = [c.lower() for c in available_cities]

                logger.info("Available cities:", available_cities)

                if city.lower() not in available_cities_lower:
                    logger.warning(f"City '{city}' not found.")
                    return

                matched_city = available_cities[
                    available_cities_lower.index(city.lower())
                ]

                logger.info(f"Selecting city: {matched_city}")

                city_select.select_by_visible_text(matched_city)
                # time.sleep(2)
            return
        except NoSuchElementException as e:
            logger.error(f"Element not found: {e}")

        except TimeoutException as e:
            logger.error(f"Timeout waiting for dropdowns to load: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def _extract_data_day(self, day_index):
        # Method that extracts the data for a specific 'day_index' (int) with Selenium.

        # day_index : int from 0 - 9 ; 0 corresponds to "today", 1 "tomorrow" etc

        """
        NOTE:
        * Example data for a day column:

        <div id="18" class="weekly-column active">
            <div class="date">Quarta, 18</div>
            <img class="weatherImg" src="/opencms/bin/icons/svg/weather/w_ic_d_02anim.svg" title="Céu pouco nublado" />
                <span class="tempMin">19°</span>
                <span class="tempMax">34°</span>
            <img class="windImg d90" src="/opencms/bin/icons/svg/wind/wind-1.svg" alt="Vento: Fraco de W" title="Vento: Fraco de W" />
            <div class="windDir">W</div>
            <div class="precProb" alt="Probabilidade precipitação: 0%" title="Probabilidade precipitação: 0%">
                0% <sup><i class="fa fa-tint low" aria-hidden="true"></i></sup>
            </div>
            <div class="wrapper">
                <div class="warning wc-yellow"><a href="https://www.ipma.pt/pt/otempo/prev-sam/timeline.jsp?p=BRG">Amarelo</a></div>
            </div>
            <img class="iuvImg" src="/opencms/bin/icons/svg/uv/iuv8.svg" alt="I. Ultravioleta: 8" title="IUV: 8" />
        </div>

        """

        forecast_data = {}
        try:

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#weekly .weekly-column")
                )
            )

            day_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "#weekly .weekly-column"
            )

            # NOTE at this point we got all forecast weather data from all columns in day_element, only need to extract the day_index

            day = day_elements[day_index]

            date = day.find_element(By.CLASS_NAME, "date").text.strip()
            temp_min = day.find_element(By.CLASS_NAME, "tempMin").text.strip()
            temp_max = day.find_element(By.CLASS_NAME, "tempMax").text.strip()

            weather_desc = day.find_element(By.CLASS_NAME, "weatherImg").get_attribute(
                "title"
            )
            precipitation = day.find_element(By.CLASS_NAME, "precProb").text.strip()
            wind_dir = day.find_element(By.CLASS_NAME, "windDir").text.strip()

            try:
                iuv = day.find_element(By.CLASS_NAME, "iuvImg").get_attribute("title")
            except:
                iuv = None
            # warning = day.find_element(By.CSS_SELECTOR, ".warning a").text.strip()

            try:
                # double check district & location to be sure of the data we obtained
                district_selected = self._get_selected_location_text(id="district")
                city_selected = self._get_selected_location_text(id="locations")
            except:
                district_selected = None
                city_selected = None

            forecast_data = {
                "district": district_selected,
                "city_selected": city_selected,
                "date": date,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "weather": weather_desc,
                "precipitation": precipitation,
                "wind_dir": wind_dir,
                "iuv": iuv,
                # "warning": warning,
            }

            logger.info(f"Extracted data for the index {day_index} (date: {date})")
            return forecast_data
        except Exception as e:
            logger.error(f" Failed to parse day: {e}")

    def _get_selector_selenium(self, id):
        # refactor method to get selector for district or locations
        select_el = self.driver.find_element(By.ID, id)
        res = Select(select_el)

        return res

    def _get_selected_location_text(self, id):
        selector = self._get_selector_selenium(id)

        return selector.first_selected_option.text
