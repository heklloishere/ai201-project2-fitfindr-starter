"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.
"""

import json
from groq import Groq
import os
from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """Main agent entry point. Runs the FitFindr planning loop."""
    # Step 1: Initialize the session
    session = _new_session(query, wardrobe)

    # Step 2: Use LLM structured parsing to extract structured filters from unstructured query
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        client = Groq(api_key=api_key)
        
        parse_prompt = f"""
        Extract the shopping search filters from this natural language fashion request.
        Request: "{query}"
        
        Return JSON format with exactly these three keys:
        - "description": structural keywords or item description string
        - "size": specific size character like "S", "M", "L", "XL" or null if not mentioned
        - "max_price": numerical float budget limit or null if not mentioned
        
        Do not output any introductory or explanatory text. Output valid JSON only.
        """
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.0
        )
        
        cleaned_json = completion.choices[0].message.content.strip()
        parsed_data = json.loads(cleaned_json)
        session["parsed"] = parsed_data
    except Exception:
        # Fallback query parsing if extraction breaks down
        session["parsed"] = {"description": query, "size": None, "max_price": None}

    # Step 3: Run the search tool
    desc = session["parsed"].get("description", query)
    sz = session["parsed"].get("size")
    price = session["parsed"].get("max_price")

    results = search_listings(description=desc, size=sz, max_price=price)
    session["search_results"] = results

    # Early conditional planning loop exit if no listings are found
    if not results:
        session["error"] = f"No listings matched your criteria for '{desc}'. Widen your pricing parameters or simplify search keywords!"
        return session

    # Step 4: Choose the top match
    session["selected_item"] = results[0]

    # Step 5: Generate styling suggestion
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], session["wardrobe"])

    # Step 6: Create shareable fit card string
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])

    # Step 7: Final return
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
