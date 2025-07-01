from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import uuid
import json
from urllib.parse import quote
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# In-memory session store
sessions = {}

# Catalog generation logic from generate_catalog.py
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

# Initialize catalog
catalog = generate_catalog()

def extract_details(user_input):
    # Mock Flan-T5-Large with regex-based extraction
    intent = "purchase_request" if any(keyword in user_input.lower() for keyword in ["need", "buy", "purchase", "want", "get"]) else "general_query"
    
    if intent == "purchase_request":
        # Capture item before optional budget or purpose clause
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

    if budget:
        price_diff = abs(budget - product["price"])
        score += max(0, 10 - (price_diff / budget * 10))
    if purpose and purpose in product["description"].lower():
        score += 5
    if purpose and purpose in product["title"].lower():
        score += 2
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

    if current_slot:
        value = interpret_response(user_input, current_slot)
        if value is not None:
            context[current_slot] = value
        missing_slots = check_clarity(context)
        if missing_slots:
            response = generate_clarification_question(missing_slots[0])
            sessions[session_id]["history"].append({"user": user_input, "bot": response, "intent": "clarification", "context": context.copy()})
            return jsonify({
                "response": response,
                "current_slot": missing_slots[0],
                "history": sessions[session_id]["history"],
                "context": context
            })

    # Process initial request
    item, budget, intent, purpose = extract_details(user_input)
    if item:
        context["item"] = item
    if budget:
        context["budget"] = budget
    if purpose:
        context["purpose"] = purpose

    # Fallback intent
    if not intent:
        intent = "purchase_request"

    missing_slots = check_clarity(context)
    if missing_slots:
        response = generate_clarification_question(missing_slots[0])
        sessions[session_id]["history"].append({"user": user_input, "bot": response, "intent": intent, "context": context.copy()})
        return jsonify({
            "response": response,
            "current_slot": missing_slots[0],
            "history": sessions[session_id]["history"],
            "context": context
        })

    # All slots filled, check required fields
    if not context.get("item") or not context.get("budget"):
        response = "I still need the item you're looking for and your budget to show suggestions."
        sessions[session_id]["history"].append({"user": user_input, "bot": response, "intent": intent, "context": context.copy()})
        return jsonify({
            "response": response,
            "current_slot": None,
            "history": sessions[session_id]["history"],
            "context": context
        })

    products = [p for p in catalog if p["price"] <= context["budget"] and context["item"].lower() in p["title"].lower()][:3]
    
    if not products:
        response = f"No suitable {context['item']} found under ${context['budget']:.2f}. Please adjust your budget or try again."
        sessions[session_id]["history"].append({"user": user_input, "bot": response, "intent": intent, "context": context.copy()})
        return jsonify({
            "response": response,
            "current_slot": None,
            "history": sessions[session_id]["history"],
            "context": context
        })

    for p in products:
        p["match_score"] = score_product(p, context)

    table = "| Title | Price | Match Score | Link | Availability | Delivery Time | Category |\n"
    table += "|-------|-------|-------------|------|--------------|---------------|---------|\n"
    for p in products:
        table += f"| {p['title']} | ${p['price']:.2f} | {p['match_score']:.2f} | [View]({p['link']}) | {p['availability']} | {p['delivery_time']} | {p['category']} |\n"

    best_product = max(products, key=lambda x: x["match_score"])
    passes_policy, reason = passes_company_policy(best_product)
    explanation = f"\n\n**Best Choice:** \"{best_product['title']}\" because it best fits your budget and purpose.\n**Match Score:** {best_product['match_score']:.2f}"
    if not passes_policy:
        explanation += f"\n\nThis product requires approval: {reason}"

    sessions[session_id]["best_product"] = best_product
    sessions[session_id]["passes_policy"] = passes_policy
    sessions[session_id]["policy_reason"] = reason
    response = f"Thank you! Here are some options for a {context['item']} for {context['purpose']} with a budget of ${context['budget']:.2f}:\n\n{table}{explanation}"
    sessions[session_id]["history"].append({"user": user_input, "bot": response, "intent": intent, "context": context.copy()})

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
