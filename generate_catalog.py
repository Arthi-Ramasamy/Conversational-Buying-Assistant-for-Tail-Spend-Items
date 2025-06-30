import json
import random

categories = {
    "Office Chairs": ["Ergonomic Chair", "Task Chair", "Mesh Chair", "Executive Chair", "Adjustable Stool"],
    "Office Desks": ["Standing Desk", "Portable Desk", "L-Shaped Desk", "Gaming Desk", "Foldable Desk"],
    "Monitors": ["24-Inch Monitor", "27-Inch Monitor", "32-Inch Monitor", "Curved Monitor", "Portable Monitor"],
    "Laptops": ["Lightweight Laptop", "Gaming Laptop", "Business Laptop", "Ultrabook", "Convertible Laptop"],
    "Keyboards": ["Mechanical Keyboard", "Wireless Keyboard", "Ergonomic Keyboard", "RGB Keyboard", "Compact Keyboard"]
}
descriptions = {
    "Office Chairs": ["with lumbar support", "adjustable height", "breathable mesh", "with headrest", "reclining feature"],
    "Office Desks": ["height-adjustable", "easy assembly", "with storage", "modern design", "portable"],
    "Monitors": ["Full HD", "energy-efficient", "4K resolution", "with speakers", "ultra-thin bezel"],
    "Laptops": ["high performance", "long battery life", "touchscreen", "lightweight", "dedicated GPU"],
    "Keyboards": ["clicky switches", "silent typing", "customizable keys", "durable build", "backlit"]
}
price_ranges = {
    "Office Chairs": (100, 500),
    "Office Desks": (200, 600),
    "Monitors": (150, 400),
    "Laptops": (500, 2000),
    "Keyboards": (50, 150)
}
availability = ["In Stock", "Out of Stock", "Available in 3 days"]
delivery_time = ["1-2 days", "3-5 days", "5-7 days"]

products = []
for category, items in categories.items():
    for i, item in enumerate(items, 1):
        for j in range(3):  # Generate 3 variants per item
            title = f"{item} {i:03d}-{j+1}"
            price = round(random.uniform(price_ranges[category][0], price_ranges[category][1]), 2)
            description = f"{item} {random.choice(descriptions[category])}"
            available = random.choice(availability)
            delivery = random.choice(delivery_time)
            products.append({
                "title": title,
                "price": price,
                "description": description,
                "availability": available,
                "delivery_time": delivery,
                "category": category,
                "link": "https://example.com/product/placeholder"  # Placeholder until scraping
            })

with open("catalog.json", "w") as f:
    json.dump(products, f, indent=2)