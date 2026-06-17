# FitFindr — planning.md

Complete this document before writing any implementation code. Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be. Your planning.md will be reviewed as part of your submission. Update it before starting any stretch features.

## Tools

List every tool your agent will use. For each tool, fill in all four fields. You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings
* **What it does:** Searches the mock listings dataset using keywords from the description, size, and maximum price thresholds.
* **Input parameters:**
  * `description` (str): Text description or keywords of the fashion item (e.g., "vintage graphic tee").
  * `size` (str): Size filter (e.g., "M"). Can be `None`.
  * `max_price` (float): Maximum budget cap. Can be `None`.
* **What it returns:** A `list` of dictionaries, where each dictionary represents a matching item with fields like title, price, platform, and condition.
* **What happens if it fails or returns nothing:** Returns an empty list `[]` safely. The planning loop intercepts this, writes a helpful message to the session state, and aborts the downstream workflow immediately.

### Tool 2: suggest_outfit
* **What it does:** Takes a specific target clothing item and the user's current wardrobe data, then uses the Groq LLM to generate a creative Markdown styling guide.
* **Input parameters:**
  * `new_item` (dict): The dictionary representation of the item selected from the search.
  * `wardrobe` (dict): The dictionary containing the user's current clothing collection.
* **What it returns:** A `str` containing a conversational 2-3 sentence styling recommendation combining the old and new pieces.
* **What happens if it fails or returns nothing:** If the wardrobe is empty or a crash happens, it catches the exception and returns a generalized styling guide for that specific item type.

### Tool 3: create_fit_card
* **What it does:** Formulates a short, catchy, all-lowercase social media aesthetic caption optimized for sharing, ensuring high variety across multiple calls.
* **Input parameters:**
  * `outfit` (str): The markdown outfit suggestion text generated previously.
  * `new_item` (dict): The dictionary details of the thrifted piece.
* **What it returns:** A `str` representing a short, human-sounding social media post caption (under 20 words) with emojis.
* **What happens if it fails or returns nothing:** Returns a fallback aesthetic placeholder string: `"copped this absolute gem thrifted and keeping it simple 🖤"` to protect runtime stability.

---

## Planning Loop
The agent uses a conditional branch strategy. It calls `search_listings` first. It immediately inspects the length of the returned array. If `len(results) == 0`, it saves an early termination message to `session["error"]` and exits early, intentionally skipping the remaining tools. If listings exist, it commits `results[0]` to `session["selected_item"]` and proceeds down the chain.

## State Management
Information is passed across tools using a single mutable session dictionary: `session = {"selected_item": None, "outfit_suggestion": None, "fit_card": None, "error": None}`. The planning loop updates this dictionary after each tool finishes execution, allowing subsequent functions to extract their required keyword arguments directly from the current session snapshot.

---

## Error Handling

| Tool | Failure mode | Agent response |
| :--- | :--- | :--- |
| **search_listings** | No results match the query | Saves error text into `session["error"]` telling the user what failed, suggests broadening parameters, and terminates execution early. |
| **suggest_outfit** | Wardrobe is empty | Detects the empty wardrobe array and dynamically pivots to generate a versatile basic styling guide centered exclusively on the new item. |
| **create_fit_card** | Outfit input is missing or incomplete | Intercepts the empty string and returns a highly reliable fallback caption string to prevent system errors. |

---

## Architecture

```mermaid
graph TD
    User([User Query]) --> PL[Planning Loop]
    PL --> T1[search_listings]
    
    T1 -- Empty List [] --> Err1[Set Session Error & Return Early]
    T1 -- Items Found --> S1[State: Store selected_item]
    
    S1 --> T2[suggest_outfit]
    T2 --> S2[State: Store outfit_suggestion]
    
    S2 --> T3[create_fit_card]
    T3 --> S3[State: Store fit_card]
    
    S3 --> End([Return Final Session State to UI])
    Err1 --> End
