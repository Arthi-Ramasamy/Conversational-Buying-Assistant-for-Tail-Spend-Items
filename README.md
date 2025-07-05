
# 🛒 Conversational Buying Assistant for Tail Spend Items

A smart, AI-powered procurement assistant that enables users to purchase low-cost tail spend items using natural language. It classifies user intent, extracts item details (like budget, brand, features), fetches real-time product data from e-commerce platforms, validates purchases against company policy, and automates the approval flow if needed.

> 🚀 Built using **Flan-T5**, **Python (Flask)**, **React + Vite (Material UI)**, and **Web Scraping**.


## 🌟 Features

* 🗣️ **Natural Language Input**: Users can request items like “I need a wireless mouse under ₹1000.”
* 🧠 **Prompt Classification**: Uses **Flan-T5** to classify user requests and extract missing info.
* 🔍 **Slot Filling**: Gathers missing details like budget, brand, features via follow-up questions.
* 🛍️ **Product Matching**: Scrapes Amazon and matches the best-fit product from the catalog.
* ✅ **Policy Check**: Verifies if the product is within company budget or approval limits.
* 📧 **Approval Flow**: If needed, sends an email to approver and waits for confirmation.
* 💬 **Chat UI**: Sleek Material UI frontend with chat-based interaction flow.
* 📦 **Catalog Fallback**: Falls back to local product catalog if scraping fails.

---

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Dakshin-priya/Conversational-Buying-Assistant-for-Tail-Spend-Items.git
cd Conversational-Buying-Assistant-for-Tail-Spend-Items
```

### 2. Backend Setup (Python + Flask)

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Rename `.env.example` to `.env` and add your Hugging Face API key:

```env
HUGGINGFACEHUB_API_TOKEN=your_token_here
```

### 3. Frontend Setup (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

---

## ▶️ Running the App

In one terminal, start the **Flask backend**:

```bash
python app.py
```

In another terminal (inside the `frontend/` directory), start the **Vite frontend**:

```bash
npm run dev
```

Access the chatbot at: [http://localhost:5173](http://localhost:5173)


