US Business Scraper
This project is a web scraper that extracts business data from Google Maps. It allows you to search for businesses by state, city or zip code, and business type in the United States. The scraper is built using Python, Streamlit for the web interface, and Selenium for web scraping.
What It Does

Scrapes business details like name, address, phone number, website, rating, and category from Google Maps.
Supports filtering by state, city, or zip code, and selecting multiple business types (e.g., liquor store, gas station).
Displays results in a table and saves them as CSV files in an organized folder structure (output/YYYY/Month/Day).

Tech Stack

Python: Core language for the scraper.
Streamlit: Provides the interactive web interface.
Selenium: Handles web scraping with Chrome.
usaddress: Parses US addresses from scraped data.

Dependencies

streamlit==1.31.0
pandas==2.0.3
selenium==4.17.2
usaddress==0.5.10

Project Structure

app.py: Main application with the Streamlit interface.
src/scrape_businesses.py: Scraping logic using Selenium.
state_city_mapping.py: Maps states to cities.
state_zipcode_mapping.py: Maps states to zip codes.
uscities.csv & uszips.csv: Data files for cities and zip codes.
output/: Stores scraped CSV files.

