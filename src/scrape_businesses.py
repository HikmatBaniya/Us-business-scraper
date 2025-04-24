import re
import urllib.parse
import usaddress
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
import time
from selenium.webdriver.chrome.options import Options

# Define broad category mappings
CATEGORY_MAPPING = {
    "Tobacco shop": "Retail",
    "Smoke shop": "Retail",
    "Liquor store": "Retail",
    "Gas station": "Services",
    "Convenience store": "Retail",
    "Department store": "Retail",
    "Mall": "Retail",
    "Entertainment": "Entertainment",
}

def clean_phone_number(phone_raw):
    """Clean phone number by removing leading non-digit characters."""
    if phone_raw:
        return re.sub(r'^[^\d]+', '', phone_raw).strip()
    return ""

def extract_rating(driver):
    """Extract overall rating from the webpage."""
    try:
        rating_element = driver.find_element(By.CSS_SELECTOR, '.F7nice span:nth-child(1)')
        return float(rating_element.text)
    except Exception:
        return 0.0

def parse_address(address):
    """Parse a U.S. address into street, city, state, zip_code, and country with robust fallback."""
    print(f"Parsing address: {address}")  # Debug log
    if not address:
        print("No address provided, returning defaults")
        return {
            "street": "",
            "city": "",
            "state": "",
            "zip_code": "",
            "country": "United States"
        }

    try:
        parsed = usaddress.tag(address)[0]
        street = " ".join([
            parsed.get("AddressNumber", ""),
            parsed.get("StreetNamePreDirectional", ""),
            parsed.get("StreetName", ""),
            parsed.get("StreetNamePostType", ""),
            parsed.get("OccupancyType", ""),
            parsed.get("OccupancyIdentifier", "")
        ]).strip()
        city = parsed.get("PlaceName", "")
        state = parsed.get("StateName", "")
        zip_code = parsed.get("ZipCode", "")
        country = "United States"
        result = {
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country
        }
        print(f"Parsed address components: {result}")  # Debug log
        return result
    except Exception as e:
        print(f"usaddress parsing failed: {e}")  # Debug log
        # Fallback: split by commas and assign components
        parts = [part.strip() for part in address.split(",") if part.strip()]
        result = {
            "street": "",
            "city": "",
            "state": "",
            "zip_code": "",
            "country": "United States"
        }
        if len(parts) >= 4:
            result["street"] = parts[0]
            result["city"] = parts[1]
            result["state"] = parts[2].split()[0] if " " in parts[2] else parts[2]
            result["zip_code"] = parts[2].split()[1] if " " in parts[2] and len(parts[2].split()) > 1 else ""
            result["country"] = parts[3] if len(parts) > 3 else "United States"
        elif len(parts) == 3:
            result["street"] = parts[0]
            result["city"] = parts[1]
            result["state"] = parts[2].split()[0] if " " in parts[2] else parts[2]
            result["zip_code"] = parts[2].split()[1] if " " in parts[2] and len(parts[2].split()) > 1 else ""
        elif len(parts) == 2:
            result["street"] = parts[0]
            result["city"] = parts[1]
        elif len(parts) == 1:
            result["street"] = parts[0]
        print(f"Fallback address components: {result}")  # Debug log
        return result

DEFAULT_COLUMNS = {
    "place_id": "LocationID",
    "name": "BusinessName",
    "rating": "Score",
    "website": "URL",
    "phone": "Contact",
    "main_category": "Type",
    "broad_category": "Category",
    "street": "Street",
    "city": "City",
    "state": "State",
    "zip_code": "Zipcode",
    "country": "Country",
    "full_address": "Address",
    "link": "MapLink",
    "query": "SearchQuery"
}

def generate_custom_columns(base_name):
    """Generate custom column names."""
    return DEFAULT_COLUMNS

def scrape_businesses(driver, query, url=None, custom_column_base=None):
    """Scrape all businesses from a Google Maps search results page."""
    if not query:
        print("Error: Missing 'query' argument in scrape_businesses call")
        return []

    # Generate column names based on custom_column_base
    columns = generate_custom_columns(custom_column_base)
    print(f"Generated columns for custom_column_base='{custom_column_base}': {columns}")  # Debug log

    try:
        # Generate URL if not provided
        if not url:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.google.com/maps/search/{encoded_query}/?hl=en"

        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.hfpxzc'))  # Business result links
        )

        # Scroll to load all businesses
        scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        previous_count = 0
        max_attempts = 20  # Prevent infinite loops
        attempt = 0

        while attempt < max_attempts:
            try:
                # Get current business links
                business_links = driver.find_elements(By.CSS_SELECTOR, '.hfpxzc')
                current_count = len(business_links)
                print(f"Attempt {attempt + 1}: Found {current_count} business links")

                if current_count == previous_count and attempt > 0:
                    # No new results loaded
                    try:
                        # Check for "You've reached the end" message
                        end_message = driver.find_element(By.CSS_SELECTOR, '.m6QErb.tLjsW')
                        if "end" in end_message.text.lower():
                            print("Reached the end of results")
                            break
                    except:
                        print("No end message found, assuming all results loaded")
                        break

                previous_count = current_count

                # Scroll to the bottom of the feed
                driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable_div)
                time.sleep(2)  # Wait for new results to load

                # Refresh business links to avoid stale elements
                business_links = driver.find_elements(By.CSS_SELECTOR, '.hfpxzc')
                if business_links:
                    ActionChains(driver).move_to_element(business_links[-1]).perform()
                    time.sleep(1)

                attempt += 1

            except StaleElementReferenceException:
                print("Stale element encountered, retrying...")
                time.sleep(1)
                continue
            except Exception as e:
                print(f"Error during scrolling: {e}")
                break

        # Collect all business URLs
        business_links = driver.find_elements(By.CSS_SELECTOR, '.hfpxzc')
        business_urls = []
        for link in business_links:
            try:
                href = link.get_attribute('href')
                if href:
                    business_urls.append(href)
            except StaleElementReferenceException:
                print("Stale element when collecting URLs, skipping...")
                continue

        print(f"Collected {len(business_urls)} business URLs")
        results = []

        for idx, business_url in enumerate(business_urls):
            print(f"Scraping business {idx + 1}/{len(business_urls)}: {business_url}")
            try:
                driver.get(business_url)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1'))
                )
                current_url = driver.current_url
                place_id = current_url.split('/place/')[-1].split('/')[0] if '/place/' in current_url else ""

                # Initialize default data structure
                place_data = {
                    "place_id": "",
                    "name": "",
                    "rating": 0.0,
                    "website": "",
                    "phone": "",
                    "main_category": "",
                    "broad_category": "",
                    "street": "",
                    "city": "",
                    "state": "",
                    "zip_code": "",
                    "country": "",
                    "full_address": "",
                    "link": "",
                    "query": query
                }

                # Populate fields
                place_data["place_id"] = place_id
                place_data["name"] = driver.find_element(By.CSS_SELECTOR, 'h1').text.strip() if driver.find_elements(By.CSS_SELECTOR, 'h1') else ""
                place_data["rating"] = extract_rating(driver)
                place_data["website"] = driver.find_element(By.CSS_SELECTOR, '[data-item-id^=authority]').get_attribute('href') if driver.find_elements(By.CSS_SELECTOR, '[data-item-id^=authority]') else ""
                
                # Extract and clean phone number
                phone_raw = driver.find_element(By.CSS_SELECTOR, '[data-item-id^=phone]').text if driver.find_elements(By.CSS_SELECTOR, '[data-item-id^=phone]') else ""
                place_data["phone"] = clean_phone_number(phone_raw)

                # Extract category and map to broad category
                main_category = driver.find_element(By.CSS_SELECTOR, '.fontBodyMedium span button').text if driver.find_elements(By.CSS_SELECTOR, '.fontBodyMedium span button') else ""
                place_data["main_category"] = main_category
                place_data["broad_category"] = CATEGORY_MAPPING.get(main_category, "Other")

                # Extract and parse address
                try:
                    # Wait for address element to be visible
                    address_element = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, '//div[contains(@class, "Io6YTe") or @data-tooltip="Copy address"]'))
                    )
                    address = address_element.text.strip()
                    print(f"Raw address extracted: {address}")  # Debug log
                except (TimeoutException, NoSuchElementException) as e:
                    print(f"Address extraction failed: {e}")  # Debug log
                    address = ""
                    # Fallback: Try alternative selectors
                    for selector in [
                        'div.RcCsl.fVHpi.w4vB1d span.AhqS1e',  # Address in some layouts
                        'div.rogA2c div.Io6YTe',  # Another common address class
                        'div[data-section-id="ad"] div.Io6YTe'  # Address section
                    ]:
                        try:
                            address = driver.find_element(By.CSS_SELECTOR, selector).text.strip()
                            print(f"Fallback address extracted with {selector}: {address}")  # Debug log
                            if address:
                                break
                        except:
                            continue
                
                # Ensure address is not contaminated with irrelevant data
                if address and not any(keyword in address.lower() for keyword in ["closed", "open", "phone", "website", "hours"]):
                    address_components = parse_address(address)
                else:
                    print("Address invalid or empty, using defaults")  # Debug log
                    address_components = parse_address("")

                place_data["street"] = address_components["street"]
                place_data["city"] = address_components["city"]
                place_data["state"] = address_components["state"]
                place_data["zip_code"] = address_components["zip_code"]
                place_data["country"] = address_components["country"]

                # Combine address components into full_address
                address_parts = [
                    address_components["street"],
                    address_components["city"],
                    f"{address_components['state']} {address_components['zip_code']}".strip(),
                    address_components["country"]
                ]
                # Filter out empty parts and join with commas
                address_parts = [part for part in address_parts if part.strip()]
                place_data["full_address"] = ", ".join(address_parts) if address_parts else address if address else "Unknown Address"
                print(f"Full address generated: {place_data['full_address']}")  # Debug log

                place_data["link"] = current_url

                # Map to custom or default columns
                mapped_data = {
                    columns.get(key, key): value
                    for key, value in place_data.items()
                    if key in columns
                }
                results.append(mapped_data)

            except Exception as e:
                print(f"Error scraping business at {business_url}: {e}")
                continue

        print(f"Scraped {len(results)} businesses for query: {query}")
        return results

    except Exception as e:
        print(f"Error scraping {query}: {e}")
        return []

def main():
    """Main function to scrape a liquor store in Mobile, AL."""
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return

    query = "liquor store in Mobile, AL"
    try:
        results = scrape_businesses(driver, query, custom_column_base="liquor_store")
        print(f"Total results: {len(results)}")
        for result in results:
            print(result)
    except Exception as e:
        print(f"Error in main execution: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()