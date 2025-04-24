import streamlit as st
import pandas as pd
from src.scrape_businesses import scrape_businesses, generate_custom_columns
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import subprocess
import time
import streamlit.components.v1 as components
import socket
import os
from datetime import datetime
from state_city_mapping import STATE_CITY_MAPPING

# Import STATE_ZIPCODE_MAPPING with strict validation
try:
    from state_zipcode_mapping import STATE_ZIPCODE_MAPPING
    if not isinstance(STATE_ZIPCODE_MAPPING, dict):
        raise ValueError("STATE_ZIPCODE_MAPPING is not a dictionary")
    if 'Alabama' not in STATE_ZIPCODE_MAPPING:
        raise ValueError("STATE_ZIPCODE_MAPPING is missing Alabama")
    alabama_zipcodes = STATE_ZIPCODE_MAPPING.get('Alabama', [])
    if not alabama_zipcodes or not all(len(zipcode) == 5 and zipcode.isdigit() for zipcode in alabama_zipcodes):
        raise ValueError(f"Invalid zip codes for Alabama in STATE_ZIPCODE_MAPPING: {alabama_zipcodes[:10]}")
except ImportError as e:
    st.error(f"Error importing state_zipcode_mapping.py: {e}. Please run generate_state_zipcode_mapping.py to create it.")
    STATE_ZIPCODE_MAPPING = {}
    st.stop()
except Exception as e:
    st.error(f"Unexpected error with state_zipcode_mapping.py: {e}. Please regenerate the file by running generate_state_zipcode_mapping.py.")
    STATE_ZIPCODE_MAPPING = {}
    st.stop()

STATE_NAME_TO_CODE = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Puerto Rico": "PR",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virgin Islands": "VI",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY"
}

BUSINESS_TYPES = [
    "shopping center",
    "department store",
    "mall",
    "food court",
    "entertainment",
    "smoke shop",
    "retailer",
    "wholesaler",
    "cigar shop",
    "tobacco shop",
    "tobacco wholesaler",
    "tobacco retailer",
    "convenience store",
    "cigar wholesaler",
    "gas station",
    "vaporizer store",
    "liquor store",
    "vape shop",
    "supermarket",
    "restaurant",
    "bar",
]

def find_available_port(start_port=8502):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                port += 1

def is_streamlit_running(port, max_attempts=8, wait_time=0.3):
    for attempt in range(max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            try:
                s.connect(("localhost", port))
                import urllib.request
                url = f"http://localhost:{port}"
                try:
                    with urllib.request.urlopen(url, timeout=1) as response:
                        if response.getcode() == 200:
                            return True
                except urllib.error.URLError:
                    pass
                st.write(f"Attempt {attempt + 1}/{max_attempts}: Waiting for port {port}...")
                time.sleep(wait_time)
            except (ConnectionRefusedError, socket.timeout):
                st.write(f"Attempt {attempt + 1}/{max_attempts}: Waiting for port {port}...")
                time.sleep(wait_time)
    return False

def launch_new_instance(max_retries=2):
    if 'used_ports' not in st.session_state:
        st.session_state.used_ports = [8501]

    with st.spinner("Launching new Streamlit instance..."):
        for attempt in range(max_retries):
            st.write(f"Attempt {attempt + 1}/{max_retries} to launch new instance...")
            new_port = find_available_port(max(st.session_state.used_ports) + 1)
            st.session_state.used_ports.append(new_port)
            try:
                app_path = os.path.abspath("app.py")
                cmd = ["streamlit", "run", app_path, "--server.port", str(new_port)]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if is_streamlit_running(new_port):
                    st.success(f"New Streamlit instance launched on port {new_port}")
                    return new_port, process
                else:
                    stderr_output = process.stderr.read() if process.stderr else "No stderr output"
                    st.warning(f"Attempt {attempt + 1} failed on port {new_port}. Error: {stderr_output}")
                    st.session_state.used_ports.remove(new_port)
                    process.terminate()
                    time.sleep(0.3)
            except Exception as e:
                st.warning(f"Attempt {attempt + 1} failed on port {new_port}: {str(e)}")
                st.session_state.used_ports.remove(new_port)
                time.sleep(0.3)
        st.error(f"Failed to launch new Streamlit instance after {max_retries} attempts.")
        return None, None

st.title("US Business Scraper")

if st.button("Open New Window"):
    new_port, process = launch_new_instance()
    if new_port:
        new_url = f"http://localhost:{new_port}"
        js_code = f"""
        <script>
            window.open("{new_url}", "_blank");
        </script>
        """
        components.html(js_code, height=0)
        if 'processes' not in st.session_state:
            st.session_state.processes = []
        st.session_state.processes.append(process)
    else:
        st.error("Could not open a new window. Check the error messages above.")

if 'selected_cities' not in st.session_state:
    st.session_state.selected_cities = []
if 'selected_zipcodes' not in st.session_state:
    st.session_state.selected_zipcodes = []
if 'selected_business_types' not in st.session_state:
    st.session_state.selected_business_types = ["liquor store"]
if 'selected_state' not in st.session_state:
    st.session_state.selected_state = None
if 'filter_type' not in st.session_state:
    st.session_state.filter_type = "City"

st.subheader("Select State")
selected_state = st.selectbox("Select a State:", sorted(list(STATE_CITY_MAPPING.keys())), key="state_select")

if selected_state != st.session_state.selected_state:
    st.session_state.selected_state = selected_state
    st.session_state.selected_cities = []
    st.session_state.selected_zipcodes = []

st.subheader("Select Filter Type")
filter_type = st.radio("Filter by:", ["City", "Zip Code"], key="filter_type_radio")
if filter_type != st.session_state.filter_type:
    st.session_state.filter_type = filter_type
    st.session_state.selected_cities = []
    st.session_state.selected_zipcodes = []

if selected_state:
    if filter_type == "City":
        st.subheader(f"Select Cities in {selected_state}")
        cities = STATE_CITY_MAPPING.get(selected_state, [])
        if not cities:
            st.warning(f"No cities available for {selected_state}. Please check state_city_mapping.py.")
        if st.button("Select All Cities"):
            st.session_state.selected_cities = cities
        def update_selected_cities():
            st.session_state.selected_cities = st.session_state.city_multiselect
        st.multiselect(
            f"Cities:",
            sorted(cities),
            key="city_multiselect",
            on_change=update_selected_cities,
            default=st.session_state.selected_cities
        )
    else:
        st.subheader(f"Select Zip Codes in {selected_state}")
        zipcodes = STATE_ZIPCODE_MAPPING.get(selected_state, [])
        if not zipcodes:
            st.warning(f"No zip codes available for {selected_state}. Please check state_zipcode_mapping.py.")
        st.write(f"DEBUG: Zip codes for {selected_state} before display:", zipcodes[:10], "..." if len(zipcodes) > 10 else "")
        if st.button("Select All Zip Codes"):
            st.session_state.selected_zipcodes = zipcodes
        def update_selected_zipcodes():
            st.session_state.selected_zipcodes = st.session_state.zipcode_multiselect
        valid_zipcodes = [zipcode for zipcode in zipcodes if len(zipcode) == 5 and zipcode.isdigit()]
        if len(valid_zipcodes) != len(zipcodes):
            st.error(f"Invalid zip codes detected for {selected_state}. Expected 5-digit codes, but found: {set(zipcodes) - set(valid_zipcodes)}. Regenerate state_zipcode_mapping.py.")
        st.multiselect(
            f"Zip Codes:",
            sorted(valid_zipcodes),
            key="zipcode_multiselect",
            on_change=update_selected_zipcodes,
            default=st.session_state.selected_zipcodes
        )

st.subheader("Select Business Types")
if st.button("Select All Business Types"):
    st.session_state.selected_business_types = BUSINESS_TYPES
def update_selected_business_types():
    st.session_state.selected_business_types = st.session_state.business_multiselect
st.multiselect(
    "Select Business Types:",
    sorted(BUSINESS_TYPES),
    key="business_multiselect",
    on_change=update_selected_business_types,
    default=st.session_state.selected_business_types
)

if st.button("Run Scraper"):
    if not st.session_state.selected_business_types:
        st.error("Please select at least one business type before running the scraper.")
    elif st.session_state.filter_type == "City" and not st.session_state.selected_cities:
        st.error("Please select at least one city before running the scraper.")
    elif st.session_state.filter_type == "Zip Code" and not st.session_state.selected_zipcodes:
        st.error("Please select at least one zip code before running the scraper.")
    else:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            st.error(f"Error initializing WebDriver: {e}")
            st.stop()
        all_results = []
        state_code = STATE_NAME_TO_CODE.get(selected_state, selected_state)
        locations = st.session_state.selected_cities if st.session_state.filter_type == "City" else st.session_state.selected_zipcodes
        for location in locations:
            for business_type in st.session_state.selected_business_types:
                query = f"{business_type} in {location}, {state_code}"
                st.write(f"Scraping: {query}")
                try:
                    results = scrape_businesses(driver, query, custom_column_base=business_type)
                    if results:
                        filtered_results = []
                        for result in results:
                            if st.session_state.filter_type == "Zip Code":
                                scraped_zipcode = result.get('Zipcode')
                                if scraped_zipcode == location:
                                    result['Search Zipcode'] = location
                                    filtered_results.append(result)
                            else:
                                scraped_city = result.get('City')
                                if scraped_city and scraped_city.lower() == location.lower():
                                    filtered_results.append(result)
                        all_results.extend(filtered_results)
                        st.write(f"Scraped {len(results)} businesses for {query}, kept {len(filtered_results)} after filtering")
                except Exception as e:
                    st.error(f"Error scraping {query}: {e}")
        driver.quit()
        if all_results:
            df = pd.DataFrame(all_results)
            expected_columns = list(generate_custom_columns(None).values())
            if st.session_state.filter_type == "Zip Code":
                if 'Search Zipcode' not in expected_columns:
                    expected_columns.insert(0, 'Search Zipcode')
            else:
                if 'City' not in expected_columns:
                    expected_columns.insert(0, 'City')
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = ""
            df = df[expected_columns]
            st.dataframe(df)

            # Get current date for folder structure
            current_date = datetime.now()
            year = current_date.strftime("%Y")  # e.g., "2025"
            month = current_date.strftime("%B")  # e.g., "January"
            day = current_date.strftime("%d")   # e.g., "23"

            # Create folder structure: 2025/Month/Day
            base_output_dir = os.path.join("output", year, month, day)
            os.makedirs(base_output_dir, exist_ok=True)

            # Format timestamp for filename: full date and time
            timestamp = current_date.strftime("%Y-%m-%dT%H-%M-%S")
            state_name = selected_state.replace(" ", "_")  # Replace spaces in state name for filename
            output_file = os.path.join(
                base_output_dir,
                f"leads_scraped_{state_name}_{timestamp}.csv"
            )

            # Save the CSV file
            df.to_csv(output_file, index=False)
            st.success(f"Data saved to {output_file}")

            # Provide download button
            with open(output_file, "rb") as file:
                st.download_button(
                    label="Download CSV",
                    data=file,
                    file_name=os.path.basename(output_file),
                    mime="text/csv"
                )
        else:
            st.warning("No businesses were scraped after filtering.")