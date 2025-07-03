from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import uuid
import json
from urllib.parse import quote, urljoin
import random
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# In-memory session store
sessions = {}

# Web scraping function
def scrape_amazon_products(item, budget):
    try:
        base_url = f"https://www.amazon.com/s?k={item.replace(' ', '+')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        for attempt in range(3):  # Retry 3 times
            response = requests.get(base_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            products = []
            for product in soup.select(".s-result-item"):
                title_elem = product.select_one(".a-text-normal")
                price_elem = product.select_one(".a-price-whole")
                link_elem = product.select_one(".a-link-normal")
                availability_elem = product.select_one(".a-row.a-size-base:contains('In Stock')") or product.select_one(".a-row.a-size-base:contains('Only')")
                delivery_elem = product.select_one(".a-row:contains('FREE delivery')") or product.select_one(".a-row:contains('Get it as soon as')")
                
                if title_elem and price_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True).replace(",", "").replace("$", "")
                    price = float(price_text) if price_text.replace(".", "").isdigit() else float('inf')
                    link = urljoin(base_url, link_elem.get("href"))
                    
                    # Extract availability
                    availability = "In Stock" if availability_elem and "In Stock" in availability_elem.get_text() else "Check site"
                    if availability_elem and "Only" in availability_elem.get_text():
                        availability = "Limited Stock"
                    
                    # Extract delivery time
                    delivery_time = "Varies"
                    if delivery_elem:
                        delivery_text = delivery_elem.get_text(strip=True).lower()
                        if "free delivery" in delivery_text or "get it as soon as" in delivery_text:
                            if "tomorrow" in delivery_text or "next day" in delivery_text:
                                delivery_time = "1 day"
                            elif "2 days" in delivery_text or "two days" in delivery_text:
                                delivery_time = "2 days"
                            elif "mon" in delivery_text or "tue" in delivery_text or "wed" in delivery_text or "thu" in delivery_text or "fri" in delivery_text or "sat" in delivery_text or "sun" in delivery_text:
                                delivery_time = "2-5 days"  # Approximate based on typical Amazon delivery

                    if price <= budget:
                        products.append({
                            "title": title,
                            "price": price,
                            "link": link,
                            "description": "From Amazon",
                            "availability": availability,
                            "delivery_time": delivery_time,
                            "product_id": str(uuid.uuid4()),
                            "category": item.capitalize()  # Use the search item as category
                        })
            if products:
                return products[:3]
            time.sleep(2 ** attempt)  # Exponential backoff
        print("Web scraping failed after retries. Using local catalog only.")
        return []
    except Exception as e:
        print(f"Web scraping failed: {str(e)}. Using local catalog only.")
        return []

# Catalog generation
def generate_catalog():
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
                    "link": "https://example.com/product/placeholder",
                    "product_id": str(uuid.uuid4())
                })
    return products

catalog = generate_catalog()

def extract_details(user_input):
    intent = "purchase_request" if any(keyword in user_input.lower() for keyword in ["need", "buy", "purchase", "want", "get"]) else "general_query"
    
    if intent == "purchase_request":
        item_match = re.search(r"(?:I need|I want|buy|get|purchase)\s*(?:a|an)?\s*([\w\s]+?)(?=\s*(?:under|below|less than|for|to use for|$)|\s*$)", user_input, re.IGNORECASE)
        item = item_match.group(1).strip() if item_match else ""
        
        budget_match = re.search(r"(?:under|below|less than|for)\s*\$?(\d+\.?\d*)", user_input, re.IGNORECASE)
        budget = float(budget_match.group(1)) if budget_match else None
        
        purpose_match = re.search(r"(?:for|to use for)\s*([\w\s]+)", user_input, re.IGNORECASE)
        purpose = purpose_match.group(1).strip() if purpose_match else None
        
        return item, budget, intent, purpose
    return None, None, intent, None

def check_clarity(context):
    required_slots = ["budget", "purpose", "brand", "features", "urgency"]
    return [slot for slot in required_slots if context.get(slot) is None]

def generate_clarification_question(missing_slot):
    questions = {
        "budget": "What's your approximate budget for this purchase?",
        "purpose": "What will you be using the item for? (e.g., college work, gaming)",
        "brand": "Do you have any brand preferences?",
        "features": "Are there specific features you need? (e.g., screen size, RAM)",
        "urgency": "How soon do you need the item delivered?"
    }
    return questions.get(missing_slot, "Could you provide more details about your request?")

def interpret_response(user_input, current_slot):
    if current_slot == "budget":
        budget_match = re.search(r"\$?(\d+\.?\d*)", user_input, re.IGNORECASE)
        return float(budget_match.group(1)) if budget_match else None
    elif current_slot in ["purpose", "brand", "features", "urgency"]:
        return user_input.strip() if user_input.strip() else None
    return None

def score_product(product, context):
    score = 0
    budget = context.get("budget", 0)
    purpose = context.get("purpose", "").lower()
    brand = context.get("brand", "").lower()

    if budget:
        price_diff = abs(budget - product["price"])
        score += max(0, 10 - (price_diff / budget * 10))
    if purpose and purpose in product["description"].lower():
        score += 5
    if purpose and purpose in product["title"].lower():
        score += 2
    if brand and brand in product["title"].lower():
        score += 5  # Bonus for matching brand preference
    return score 

def passes_company_policy(product):
    restricted_keywords = ["gaming", "luxury"]
    max_allowed_budget = 500
    if product["price"] > max_allowed_budget:
        return False, "Price exceeds company policy limit ($500)."
    for word in restricted_keywords:
        if word in product["title"].lower() or word in product["description"].lower():
            return False, f"Product rejected due to restricted term: '{word}'."
    return True, ""

@app.route('/api/submit', methods=['POST'])
def submit_request():
    data = request.get_json()
    user_input = data.get('input', '')
    session_id = data.get('session_id', str(uuid.uuid4()))
    current_slot = data.get('current_slot', None)

    if session_id not in sessions:
        sessions[session_id] = {
            "context": {"item": None, "budget": None, "purpose": None, "brand": None, "features": None, "urgency": None},
            "history": [],
            "best_product": None,
            "passes_policy": None,
            "policy_reason": ""
        }

    context = sessions[session_id]["context"]

    # Handle clarification response for a current slot
    if current_slot:
        value = interpret_response(user_input, current_slot)
        if value is not None:
            context[current_slot] = value
            sessions[session_id]["history"].append({
                "user": user_input,
                "bot": f"Got it, {current_slot} set to {value}.",
                "intent": "clarification",
                "context": context.copy()
            })
        else:
            # If the input is invalid, ask again for the same slot
            response = generate_clarification_question(current_slot)
            sessions[session_id]["history"].append({
                "user": user_input,
                "bot": response,
                "intent": "clarification",
                "context": context.copy()
            })
            return jsonify({
                "response": response,
                "current_slot": current_slot,
                "history": sessions[session_id]["history"],
                "context": context
            })

    # Extract details from new input only if no current slot is being clarified
    if not current_slot:
        item, budget, intent, purpose = extract_details(user_input)
        if item and not context["item"]:
            context["item"] = item
        if budget and not context["budget"]:
            context["budget"] = budget
        if purpose and not context["purpose"]:
            context["purpose"] = purpose
        if intent:
            sessions[session_id]["history"].append({
                "user": user_input,
                "bot": "Processing your request...",
                "intent": intent,
                "context": context.copy()
            })

    # Check for missing slots
    missing_slots = check_clarity(context)
    if missing_slots:
        next_slot = missing_slots[0]
        response = generate_clarification_question(next_slot)
        sessions[session_id]["history"].append({
            "user": user_input,
            "bot": response,
            "intent": "clarification",
            "context": context.copy()
        })
        return jsonify({
            "response": response,
            "current_slot": next_slot,
            "history": sessions[session_id]["history"],
            "context": context
        })

    # Ensure required fields are present
    if not context.get("item") or not context.get("budget"):
        response = "I still need the item you're looking for and your budget to show suggestions."
        sessions[session_id]["history"].append({
            "user": user_input,
            "bot": response,
            "intent": "purchase_request",
            "context": context.copy()
        })
        return jsonify({
            "response": response,
            "current_slot": None,
            "history": sessions[session_id]["history"],
            "context": context
        })

    # Filter products by budget, item, and urgency (if applicable)
    local_products = [
        p for p in catalog
        if p["price"] <= context["budget"] and
        context["item"].lower() in p["title"].lower() and
        (context["urgency"] in p["delivery_time"] if context["urgency"] else True)
    ][:3]
    amazon_products = scrape_amazon_products(context["item"], context["budget"])
    
    products = local_products + amazon_products
    for p in products:
        p["match_score"] = score_product(p, context)
    products = sorted(products, key=lambda x: x["match_score"], reverse=True)[:3]

    if not products:
        response = f"No suitable {context['item']} found under ${context['budget']:.2f}. Please adjust your budget or try again."
        sessions[session_id]["history"].append({
            "user": user_input,
            "bot": response,
            "intent": "purchase_request",
            "context": context.copy()
        })
        return jsonify({
            "response": response,
            "current_slot": None,
            "history": sessions[session_id]["history"],
            "context": context
        })

    # Create table for display
    table = "| Title | Price | Match Score | Link | Availability | Delivery Time | Category |\n"
    table += "|-------|-------|-------------|------|--------------|---------------|----------|\n"
    for p in products:
        table += f"| {p['title']} | ${p['price']:.2f} | {p['match_score']:.2f} | [View]({p['link']}) | {p['availability']} | {p['delivery_time']} | {p['category']} |\n"

    best_product = max(products, key=lambda x: x["match_score"])
    passes_policy, reason = passes_company_policy(best_product)
    
    # Professional explanation below the table with clear separation
    explanation = f"\n\n---\n\n**Best Product Selection Rationale**:\n"
    explanation += f"The selected product, \"{best_product['title']}\", achieved the highest match score of {best_product['match_score']:.2f}, making it the optimal choice based on your requirements. "
    explanation += f"Priced at ${best_product['price']:.2f}, it aligns closely with your specified budget of ${context['budget']:.2f}, ensuring cost-effectiveness. "
    if context.get("purpose"):
        explanation += f"It is well-suited for your intended use of '{context['purpose']}'"
        if context.get("purpose").lower() in best_product["description"].lower() or context.get("purpose").lower() in best_product["title"].lower():
            explanation += ", as its features or title directly support this purpose"
        explanation += ". "
    if context.get("brand") and context.get("brand").lower() in best_product["title"].lower():
        explanation += f"Additionally, it satisfies your preference for the '{context['brand']}' brand, enhancing its relevance to your needs. "
    if context.get("urgency"):
        explanation += f"The product also accommodates your delivery requirement of '{context['urgency']}', based on available delivery information. "
    explanation += f"This combination of factors results in its superior match score and selection as the best option."
    if not passes_policy:
        explanation += f"\n\n**Note**: This product requires approval due to the following policy violation: {reason}"

    sessions[session_id]["best_product"] = best_product
    sessions[session_id]["passes_policy"] = passes_policy
    sessions[session_id]["policy_reason"] = reason
    response = f"Thank you! Here are some options for a {context['item']} for {context['purpose']} with a budget of ${context['budget']:.2f}:\n\n{table}\n{explanation}"
    sessions[session_id]["history"].append({
        "user": user_input,
        "bot": response,
        "intent": "purchase_request",
        "context": context.copy()
    })

    return jsonify({
        "response": response,
        "current_slot": None,
        "history": sessions[session_id]["history"],
        "context": context,
        "best_product": best_product,
        "passes_policy": passes_policy,
        "policy_reason": reason,
        "products": products
    })

@app.route('/api/approval', methods=['POST'])
def send_approval():
    data = request.get_json()
    session_id = data.get('session_id')
    if session_id not in sessions or not sessions[session_id]["best_product"]:
        return jsonify({"error": "No product selected for approval"}), 400

    product = sessions[session_id]["best_product"]
    match_score = product["match_score"]
    subject = f"Approval Request: {product['title']}"
    body = f"""
    Product Approval Request

    Product: {product['title']}
    Price: ${product['price']:.2f}
    Match Score: {match_score:.2f}
    Link: {product['link']}
    Category: {product['category']}

    Explanation: This product was selected as the best match for the user's request based on budget and purpose.
    Approve here: https://example.com/approve?product_id={product['product_id']}
    """
    encoded_subject = quote(subject)
    encoded_body = quote(body)
    mailto_link = f"https://mail.google.com/mail/?view=cm&fs=1&to=approver@example.com&su={encoded_subject}&body={encoded_body}"

    return jsonify({"mailto_link": mailto_link})

if __name__ == '__main__':
    app.run(debug=True)