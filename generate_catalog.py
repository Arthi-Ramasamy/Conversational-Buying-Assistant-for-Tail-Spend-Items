import random
import json
from bs4 import BeautifulSoup
import requests

# Define price ranges for different categories
price_ranges = {
    "laptop": (300, 2000),
    "headphones": (20, 150),
    "keyboard": (30, 100),
    "mouse": (10, 50),
    "monitor": (100, 500)
}

def scrape_product_info(category, max_price, purpose, preferences):
    try:
        # Example URL (replace with actual scraping target)
        url = f"https://example.com/search?q={category}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Placeholder for scraping logic (adjust based on actual site structure)
        products = []
        for item in soup.select('.product-item'):  # Adjust selector
            name = item.select_one('.product-name').text.strip()
            price_text = item.select_one('.product-price').text.strip().replace('$', '')
            price = float(price_text)
            if price <= max_price:
                # Simulate delivery info (replace with actual scraping)
                delivery_text = "Free delivery"  # Example
                products.append({"name": name, "price": price, "delivery": delivery_text})
        return products
    except Exception:
        print(f"Web scraping failed for {category}: Unable to retrieve data. Returning empty list.")
        return []

def generate_dynamic_catalog(category, max_price, purpose, preferences):
    # Scrape initial product data
    products = scrape_product_info(category, max_price, purpose, preferences)
    
    if not products:
        # Fallback to synthetic data if scraping fails
        products = [{"name": f"{category} {i+1}", "price": round(random.uniform(price_ranges.get(category, (100, 500))[0], price_ranges.get(category, (100, 500))[1])), "delivery": "Free delivery"} for i in range(5)]
    
    # Filter and enhance based on purpose and preferences
    filtered_products = []
    for product in products:
        if "high performance" in preferences.lower() and product["price"] < max_price * 0.7:
            continue  # Skip low-end items for high performance
        if "long battery life" in preferences.lower() and random.random() > 0.3:  # 70% chance to include
            product["features"] = "Long battery life"
        filtered_products.append(product)
    
    return filtered_products

if __name__ == "__main__":
    sample_catalog = generate_dynamic_catalog("laptop", 1000, "college work", "high performance, long battery life")
    print(json.dumps(sample_catalog, indent=2))