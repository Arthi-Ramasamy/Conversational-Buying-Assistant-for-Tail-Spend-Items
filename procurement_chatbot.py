import re
import json
import streamlit as st
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import uuid
import os
from email.mime.text import MIMEText
import smtplib
try:
    from dotenv import load_dotenv
    dotenv_available = True
except ImportError:
    dotenv_available = False
    load_dotenv = lambda: None
    st.warning("python-dotenv not installed. Email functionality disabled.")

# Load environment variables
load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER") if dotenv_available else None
EMAIL_PASS = os.getenv("EMAIL_PASS") if dotenv_available else None
APPROVER_EMAIL = os.getenv("APPROVER_EMAIL") if dotenv_available else "approver@example.com"

# Set page configuration
st.set_page_config(page_title="Conversational Buying Assistant", page_icon="🛍️")

# Initialize Flan-T5-Large model with error handling
@st.cache_resource
def load_model():
    try:
        HF_TOKEN = os.getenv("HF_TOKEN")
        tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large", token=HF_TOKEN)
        model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-large", token=HF_TOKEN)
        return pipeline("text2text-generation", model=model, tokenizer=tokenizer)
    except Exception as e:
        st.error(f"Failed to load model: {str(e)}. Check token, internet, or disk space (~3GB needed).")
        return None

generator = load_model()

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
                if title_elem and price_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True).replace(",", "").replace("$", "")
                    price = float(price_text) if price_text.replace(".", "").isdigit() else float('inf')
                    link = urljoin(base_url, link_elem.get("href"))
                    if price <= budget:
                        products.append({"title": title, "price": price, "link": link, "description": "From Amazon", "availability": "Check site", "delivery_time": "Varies", "product_id": str(uuid.uuid4())})
            if products:
                return products[:3]
            time.sleep(2 ** attempt)  # Exponential backoff
        st.warning("Web scraping failed after retries. Using local catalog only.")
        return []
    except Exception as e:
        st.warning(f"Web scraping failed: {str(e)}. Using local catalog only.")
        return []

def get_products(item, budget):
    try:
        with open("catalog.json", "r") as f:
            catalog = json.load(f)
        local_products = [p for p in catalog if p["price"] <= budget and item.lower() in p["title"].lower()]
        amazon_products = scrape_amazon_products(item, budget)

        # Ensure all products have product_id
        for p in local_products + amazon_products:
            if "product_id" not in p:
                p["product_id"] = str(uuid.uuid4())

        # Update local products with scraped links where possible
        for lp in local_products:
            for ap in amazon_products:
                if item.lower() in ap["title"].lower() and lp["price"] <= budget:
                    lp["link"] = ap["link"]
                    break

        return local_products + [p for p in amazon_products if p not in local_products][:3 - len(local_products)]
    except FileNotFoundError:
        fallback = scrape_amazon_products(item, budget)[:3]
        for p in fallback:
            if "product_id" not in p:
                p["product_id"] = str(uuid.uuid4())
        return fallback
    except Exception as e:
        return [{"title": "Error", "price": 0, "description": f"Error: {str(e)}", "link": "#", "availability": "N/A", "delivery_time": "N/A", "product_id": str(uuid.uuid4())}]


def extract_details(user_input):
    if generator is None:
        return None, None, None, None
    intent_prompt = f"""Classify the user input as one of: purchase_request, greeting, or general_query.
    Input: "{user_input}"
    Output the intent only."""
    intent_result = generator(intent_prompt, max_length=20)[0]["generated_text"]
    intent = intent_result.strip() if intent_result.strip() in ["purchase_request", "greeting", "general_query"] else "general_query"

    if intent == "purchase_request":
        item_prompt = f"""Extract the item the user wants to purchase from the input (e.g., 'I need a X', 'Buy X'). Return the item name only (e.g., chair, desk).
        Input: "{user_input}"
        Output the item only."""
        item_result = generator(item_prompt, max_length=50)[0]["generated_text"]
        item = item_result.strip()

        if not item or len(item) < 2:
            item_match = re.search(r"(?:I need|I want|buy|get|purchase)\s*(?:a|an)?\s*([\w\s]+?)(?:\s*(?:under|below|less than|for|to use for|for)\s*(\$?\d+\.?\d*|\w+))", user_input, re.IGNORECASE)
            item = item_match.group(1).strip() if item_match else ""

        budget_prompt = f"""Extract the budget amount (in dollars) from the input (e.g., 'under $X', 'for $X'). Return the number or 'None'.
        Input: "{user_input}"
        Output the budget as a number (e.g., 200) or 'None'."""
        budget_result = generator(budget_prompt, max_length=20)[0]["generated_text"]
        if budget_result == "None" or not budget_result.replace(".", "").isdigit():
            budget_match = re.search(r"(?:under|below|less than|for)\s*\$?(\d+\.?\d*)", user_input, re.IGNORECASE)
            budget = float(budget_match.group(1)) if budget_match else None
        else:
            budget = float(budget_result)

        purpose_prompt = f"""Extract the purpose of the purchase from the input (e.g., 'for college work', 'for gaming'). Return the purpose or 'None'.
        Input: "{user_input}"
        Output the purpose only or 'None'."""
        purpose = generator(purpose_prompt, max_length=50)[0]["generated_text"].strip()
        if purpose == "None":
            purpose_match = re.search(r"(?:for|to use for)\s*([\w\s]+)", user_input, re.IGNORECASE)
            purpose = purpose_match.group(1).strip() if purpose_match else None

        return item, budget, intent, purpose
    return None, None, intent, None

def check_clarity(context):
    required_slots = ["budget", "purpose", "brand", "features", "urgency"]
    missing_slots = [slot for slot in required_slots if context.get(slot) is None]
    return missing_slots

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

    # Price closeness to budget (max 10 points)
    if budget:
        price_diff = abs(budget - product["price"])
        score += max(0, 10 - (price_diff / budget * 10))

    # Purpose keyword match (5 points)
    if purpose and purpose in product["description"].lower():
        score += 5

    # Bonus for title match with purpose
    if purpose and purpose in product["title"].lower():
        score += 2

    return score

def passes_company_policy(product):
    restricted_keywords = ["gaming", "luxury"]
    max_allowed_budget = 500  # Company budget cap

    if product["price"] > max_allowed_budget:
        return False, "Price exceeds company policy limit ($500)."
    for word in restricted_keywords:
        if word in product["title"].lower() or word in product["description"].lower():
            return False, f"Product rejected due to restricted term: '{word}'."
    return True, ""

def send_approval_email(product, match_score):
    if not EMAIL_USER or not EMAIL_PASS:
        st.warning("Email credentials not configured. Please contact approver manually.")
        return False
    try:
        product_id = product.get("product_id", str(uuid.uuid4()))
        subject = f"Approval Request: {product['title']}"
        body = f"""
        Product Approval Request

        Product: {product['title']}
        Price: ${product['price']:.2f}
        Match Score: {match_score:.2f}
        Link: {product['link']}

        Explanation: This product was selected as the best match for the user's request based on budget and purpose.
        Approve here: https://example.com/approve?product_id={product_id}
        """

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = APPROVER_EMAIL

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        st.success(f"Approval email sent to {APPROVER_EMAIL}.")
        return True

    except Exception as e:
        st.error(f"Failed to send approval email via SMTP: {str(e)}")

                # Fallback to mailto link
        encoded_subject = subject.replace(" ", "%20")
        encoded_body = body.replace(" ", "%20").replace("\n", "%0A")

        mailto_link = (
            f"https://mail.google.com/mail/?view=cm&fs=1"
            f"&to={APPROVER_EMAIL}"
            f"&su={encoded_subject}"
            f"&body={encoded_body}"
        )

        st.markdown(
            f"[📧 Click here to send the approval email manually]({mailto_link})",
            unsafe_allow_html=True
        )
        return False

def generate_response(user_input, context, intent, current_slot=None):
    if generator is None:
        return "I'm sorry, I can't help you right now. Please try again later.", None
    if intent == "purchase_request":
        if current_slot:
            # Handle clarification response
            value = interpret_response(user_input, current_slot)
            if value is not None:
                context[current_slot] = value
            missing_slots = check_clarity(context)
            if missing_slots:
                return generate_clarification_question(missing_slots[0]), missing_slots[0]
            else:
                products = get_products(context["item"], context["budget"])
                if products and "Error" not in products[0]["title"]:
                    # Calculate match scores for all products
                    for p in products:
                        p["match_score"] = score_product(p, context)

                    # Build table with Match Score column
                    table = "| Title | Price | Match Score | Link | Availability | Delivery Time |\n"
                    table += "|-------|-------|-------------|------|--------------|---------------|\n"
                    for p in products:
                        table += f"| {p['title']} | ${p['price']:.2f} | {p['match_score']:.2f} | [View]({p['link']}) | {p['availability']} | {p['delivery_time']} |\n"

                    # Choose best product by highest match score
                    best_product = max(products, key=lambda x: x["match_score"])

                    # Format response with match score below Best Choice
                    explanation = f"\n\n**Best Choice:** \"{best_product['title']}\" because it best fits your budget and purpose.\n**Match Score:** {best_product['match_score']:.2f}"

                    # Check company policy
                    passes_policy, reason = passes_company_policy(best_product)
                    if not passes_policy:
                        explanation += f"\n\nThis product requires approval: {reason}"

                    # Store best product and policy status in session state
                    st.session_state["best_product"] = best_product
                    st.session_state["passes_policy"] = passes_policy
                    st.session_state["policy_reason"] = reason

                    return f"Thank you! Here are some options for a {context['item']} for {context['purpose']} with a budget of ${context['budget']:.2f}:\n\n{table}{explanation}", None

                return f"No suitable {context['item']} found under ${context['budget']:.2f}. Please adjust your budget or try again.", None
        else:
            # Initial purchase request
            item, budget, intent, purpose = extract_details(user_input)
            if item:
                context.update({
                    "item": item,
                    "budget": budget,
                    "purpose": purpose,
                    "brand": None,
                    "features": None,
                    "urgency": None
                })
                missing_slots = check_clarity(context)
                if missing_slots:
                    return generate_clarification_question(missing_slots[0]), missing_slots[0]
                products = get_products(context["item"], context["budget"])
                if products and "Error" not in products[0]["title"]:
                    for p in products:
                        p["match_score"] = score_product(p, context)

                    table = "| Title | Price | Match Score | Link | Availability | Delivery Time |\n"
                    table += "|-------|-------|-------------|------|--------------|---------------|\n"
                    for p in products:
                        table += f"| {p['title']} | ${p['price']:.2f} | {p['match_score']:.2f} | [View]({p['link']}) | {p['availability']} | {p['delivery_time']} |\n"

                    best_product = max(products, key=lambda x: x["match_score"])
                    explanation = f"\n\n**Best Choice:** \"{best_product['title']}\" because it best fits your budget and purpose.\n**Match Score:** {best_product['match_score']:.2f}"

                    passes_policy, reason = passes_company_policy(best_product)
                    if not passes_policy:
                        explanation += f"\n\nThis product requires approval: {reason}"

                    st.session_state["best_product"] = best_product
                    st.session_state["passes_policy"] = passes_policy
                    st.session_state["policy_reason"] = reason

                    return f"Thank you! Here are some options for a {context['item']} for {context['purpose']} with a budget of ${context['budget']:.2f}:\n\n{table}{explanation}", None
                return f"No suitable {context['item']} found under ${context['budget']:.2f}. Please adjust your budget or try again.", None
    elif intent == "greeting":
        prompt = f"""You are a procurement chatbot. The user said: '{user_input}'. Respond politely and offer assistance."""
        return generator(prompt, max_length=150)[0]["generated_text"], None
    else:
        prompt = f"""You are a procurement chatbot. The user said: '{user_input}'. Indicate it's unclear and ask for clarification."""
        return generator(prompt, max_length=150)[0]["generated_text"], None

def main():
    st.title("🛍️ Conversational Buying Assistant")
    st.write("Enter your request (e.g., 'I need a laptop for college work under $500') to get started.")

    # Initialize session state
    if "history" not in st.session_state:
        st.session_state.history = []
    if "context" not in st.session_state:
        st.session_state.context = {"item": None, "budget": None, "purpose": None, "brand": None, "features": None, "urgency": None}
    if "current_slot" not in st.session_state:
        st.session_state.current_slot = None
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    if "last_input" not in st.session_state:
        st.session_state.last_input = ""
    if "best_product" not in st.session_state:
        st.session_state.best_product = None
    if "passes_policy" not in st.session_state:
        st.session_state.passes_policy = None
    if "policy_reason" not in st.session_state:
        st.session_state.policy_reason = ""

    # Initial request input
    if not st.session_state.current_slot:
        initial_input = st.text_input("Your Request:", placeholder="e.g., I need a laptop for college work under $500", key="initial_input")
        if st.button("Submit Initial Request") or (initial_input and st.session_state.last_input != initial_input):
            if initial_input:
                response, new_slot = generate_response(initial_input, st.session_state.context, "purchase_request")
                st.session_state.history.append({
                    "user": initial_input,
                    "bot": response,
                    "item": st.session_state.context["item"],
                    "budget": st.session_state.context["budget"],
                    "purpose": st.session_state.context["purpose"],
                    "brand": st.session_state.context["brand"],
                    "features": st.session_state.context["features"],
                    "urgency": st.session_state.context["urgency"],
                    "intent": "initial",
                    "conversation_id": st.session_state.conversation_id
                })
                if new_slot:
                    st.session_state.current_slot = new_slot
                st.session_state.last_input = initial_input
    else:
        # Dynamic input for clarification questions
        user_input = st.text_input(f"{st.session_state.current_slot.capitalize()} Response:", key=f"clarify_{st.session_state.current_slot}")
        if st.button("Submit Response") or (user_input and st.session_state.get(f"last_{st.session_state.current_slot}") != user_input):
            if user_input:
                response, new_slot = generate_response(user_input, st.session_state.context, "purchase_request", st.session_state.current_slot)
                st.session_state.history.append({
                    "user": user_input,
                    "bot": response,
                    "item": st.session_state.context["item"],
                    "budget": st.session_state.context["budget"],
                    "purpose": st.session_state.context["purpose"],
                    "brand": st.session_state.context["brand"],
                    "features": st.session_state.context["features"],
                    "urgency": st.session_state.context["urgency"],
                    "intent": "clarification",
                    "conversation_id": st.session_state.conversation_id
                })
                if new_slot:
                    st.session_state.current_slot = new_slot
                else:
                    st.session_state.current_slot = None
                st.session_state[f"last_{st.session_state.current_slot if new_slot else 'initial'}"] = user_input

    if st.session_state.history:
        st.subheader("Conversation History")
        for entry in st.session_state.history:
            if entry["conversation_id"] == st.session_state.conversation_id:
                st.write(f"**You**: {entry['user']}")
                if entry["intent"] in ["initial", "purchase_request"] and entry["item"]:
                    context_display = f"Item = {entry['item']}"
                    if entry["budget"]: context_display += f", Budget = ${entry['budget']:.2f}"
                    if entry["purpose"]: context_display += f", Purpose = {entry['purpose']}"
                    if entry["brand"]: context_display += f", Brand = {entry['brand']}"
                    if entry["features"]: context_display += f", Features = {entry['features']}"
                    if entry["urgency"]: context_display += f", Urgency = {entry['urgency']}"
                    st.write(f"**Extracted**: {context_display}")
                st.markdown(entry["bot"])
                st.write("---")

    # Display buttons for best product
    if st.session_state.best_product and st.session_state.current_slot is None:
        if st.session_state.passes_policy:
            if st.button("Order Now", key=f"order_{st.session_state.conversation_id}"):
                st.success(f"Order initiated for {st.session_state.best_product['title']}!")
        else:
            if st.button("Mail Approver", key=f"approval_{st.session_state.conversation_id}"):
                send_approval_email(st.session_state.best_product, st.session_state.best_product["match_score"])

    if st.button("Exit"):
        st.write("Goodbye! The assistant has been stopped.")
        st.stop()

if __name__ == "__main__":
    main()