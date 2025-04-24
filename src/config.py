import json
import csv
import os

def load_config():
    with open("data/config.json", "r") as f:
        return json.load(f)

def load_cities_states():
    cities_states = []
    with open("data/input/cities_states.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cities_states.append({"city": row["city"], "state": row["state"]})
    return cities_states

def generate_queries(business_types, cities_states):
    queries = []
    for business_type in business_types:
        for cs in cities_states:
            query = f"{business_type} in {cs['city']}, {cs['state']}"
            queries.append({"query": query, "city": cs['city'], "state": cs['state'], "business_type": business_type})
    return queries