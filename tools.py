"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """
    try:
        listings = load_listings()
    except Exception:
        return []

    filtered_listings = []
    keywords = description.lower().split()

    for item in listings:
        # 1. Filter by max_price (inclusive) if provided
        if max_price is not None:
            try:
                if float(item.get("price", 0)) > float(max_price):
                    continue
            except (ValueError, TypeError):
                continue

        # 2. Filter by size (case-insensitive substring match) if provided
        if size:
            item_size = str(item.get("size", "")).lower()
            if size.lower() not in item_size:
                continue

        # 3. Score by keyword overlap with title and description
        title_desc = f"{item.get('title', '')} {item.get('description', '')}".lower()
        score = sum(1 for kw in keywords if kw in title_desc)

        # 4. Drop items with no keyword match
        if score > 0:
            # Temporarily add score field for sorting
            item_copy = item.copy()
            item_copy["_search_score"] = score
            filtered_listings.append(item_copy)

    # 5. Sort by score (highest first), then clean up temporary score field
    filtered_listings.sort(key=lambda x: x["_search_score"], reverse=True)
    for item in filtered_listings:
        item.pop("_search_score", None)

    return filtered_listings


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    """
    if not new_item:
        return "No item selected to style."

    try:
        client = _get_groq_client()
    except Exception as e:
        return "Could not initialize fashion engine. Try pairing this piece with your favorite timeless denim!"

    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        # Step 2: Empty wardrobe prompt fallback
        prompt = f"""
        You are an expert fashion stylist. The user wants to style this new secondhand find:
        Item: {new_item.get('title')} ({new_item.get('description')})
        Price: ${new_item.get('price')}
        Category: {new_item.get('category')}
        Colors: {', '.join(new_item.get('colors', []))}
        
        The user's personal wardrobe data is currently empty. Provide general, highly versatile styling advice (what types of silhouettes, fits, basics, and footwear look best with this piece). Keep it distinct and stylish.
        """
    else:
        # Step 3: Available wardrobe structured prompt
        formatted_wardrobe = "\n".join([
            f"- {w.get('title')} ({w.get('category')}, Colors: {', '.join(w.get('colors', []))})"
            for w in wardrobe_items
        ])
        prompt = f"""
        You are an expert fashion stylist. Suggest 1-2 complete outfit combinations using the new item and named pieces from the user's wardrobe.
        
        New Item: {new_item.get('title')} ({new_item.get('description')}, Colors: {', '.join(new_item.get('colors', []))})
        
        User's Wardrobe Pieces available:
        {formatted_wardrobe}
        
        Provide a brief, stylish 2-3 sentence markdown response explaining how to pair them into cohesive outfits. Reference specific wardrobe items by name.
        """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"Style this {new_item.get('title')} with classic neutral layers and your favorite worn-in sneakers!"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    # Step 1: Guard against missing or empty inputs
    if not outfit or not outfit.strip() or not new_item:
        return "copped this absolute gem thrifted and keeping it simple 🖤"

    try:
        client = _get_groq_client()
    except Exception:
        return f"scored this {new_item.get('title', 'find')} for ${new_item.get('price', 'low')} ✨"

    prompt = f"""
    Write a short, casual, all-lowercase social media aesthetic caption (like an Instagram post or TikTok story clip).
    
    Item Name: {new_item.get('title')}
    Price: ${new_item.get('price')}
    Platform Source: {new_item.get('platform')}
    Outfit Vibe: {outfit}
    
    Guidelines:
    - Must be entirely lowercase
    - Mention the item name, price, and platform naturally exactly once each
    - Keep it short, casual, and completely human (under 20 words)
    - Include 1-2 emojis
    - Do not use quotation marks
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95  # High variance as requested by spec
        )
        return response.choices[0].message.content.strip().replace('"', '')
    except Exception:
        return f"thrifted this {new_item.get('title')} off {new_item.get('platform')} for ${new_item.get('price')} and it goes hard 🪐"
