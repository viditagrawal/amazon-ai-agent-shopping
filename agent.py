from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers.json import SimpleJsonOutputParser
from typing import TypedDict, List, Dict, Any, Annotated
from amazon_scraper import fetch_amazon_page_selenium, parse_product_listings
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# --- 1. Define State ---
class AgentState(TypedDict):
    user_request: str
    search_query: str
    filters: Dict[str, Any]  # Add filters to state
    product_listings: List[Dict[str, str]]
    comparison_results: str
    response: str  # Add response to state
    stage: str

# --- 2. Define Nodes (Agent Functions) ---
def parse_user_request(state: AgentState) -> Dict[str, Any]:
    print("Node: parse_user_request")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful shopping assistant. Your goal is to understand the user's product request and extract structured search query and filters for Amazon.\n"
                 "Identify the core product keywords for the Amazon search bar and any specific filters mentioned by the user.\n"
                 "For price ranges, return them in the format: {{'min': number, 'max': number}} (without $ signs).\n"
                 "Common filter categories on Amazon are: 'price_range', 'brand', 'category', 'rating', 'features'.\n"
                 "If no filters are explicitly mentioned, the 'filters' should be an empty dictionary.\n"
                 "Return a JSON object with keys 'search_query' and 'filters'."),
        ("user", "{user_request}\n\nProvide your response as a JSON object.")
    ])
    
    parser = SimpleJsonOutputParser()
    chain = prompt | ChatOpenAI(temperature=0) | parser
    output = chain.invoke({"user_request": state['user_request']})
    
    return {
        "search_query": output.get("search_query", ""),
        "filters": output.get("filters", {}),
        "stage": "query_parsed"
    }

def search_amazon(state: AgentState) -> Dict[str, Any]:
    print("Node: search_amazon")
    search_url = f"https://www.amazon.com/s?k={state['search_query'].replace(' ', '+')}"
    
    # Apply filters if they exist
    if state['filters']:
        print(f"Applying filters: {state['filters']}")
        # Add price range filter if specified
        if 'price_range' in state['filters']:
            price_range = state['filters']['price_range']
            if isinstance(price_range, str):
                # Handle string format like "$500-$1000"
                try:
                    min_price, max_price = price_range.replace('$', '').split('-')
                    search_url += f"&low-price={min_price.strip()}&high-price={max_price.strip()}"
                except ValueError:
                    print("Could not parse price range string")
            elif isinstance(price_range, dict):
                if 'min' in price_range:
                    search_url += f"&low-price={price_range['min']}"
                if 'max' in price_range:
                    search_url += f"&high-price={price_range['max']}"
    html_content = fetch_amazon_page_selenium(search_url)
    if html_content:
        product_listings = parse_product_listings(html_content)
        if product_listings:
            return {
                "product_listings": product_listings[:5],  # Limit to top 5 products for comparison
                "stage": "product_extraction_done"
            }
    return {
        "product_listings": [],
        "stage": "search_failed"
    }

def compare_products(state: AgentState) -> Dict[str, Any]:
    print("Node: compare_products")
    if not state['product_listings']:
        return {
            "comparison_results": "No products found to compare.",
            "stage": "comparison_failed"
        }

    product_info_list = "\n".join([
        f"- {p['title']} (Price: {p['price']}, Link: {p['link']})" 
        for p in state['product_listings'][:5]
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful shopping assistant. Compare the following products based on available information and user preferences. Focus on key features and price. Provide a concise summary."),
        ("user", "Compare these products:\n{product_info_list}")
    ])
    
    chain = prompt | ChatOpenAI(temperature=0)
    comparison_summary = chain.invoke({"product_info_list": product_info_list}).content
    
    return {
        "comparison_results": comparison_summary,
        "stage": "comparison_done"
    }

def generate_response(state: AgentState) -> Dict[str, Any]:
    print("Node: generate_response")
    if state['stage'] == "search_failed":
        response_message = "Sorry, I couldn't retrieve product listings for your search. Please try again with a different query."
    elif state['stage'] == "comparison_failed":
        response_message = "No products were found to compare. Please refine your search."
    elif state['stage'] == "comparison_done":
        response_message = f"Here are the top product comparisons:\n{state['comparison_results']}\n\nWould you like to refine your search or explore specific products further?"
    else:
        response_message = "I'm processing your request..."
    
    return {
        "response": response_message,
        "stage": "response_generated"
    }

def respond_to_user(state: AgentState) -> Dict[str, Any]:
    print("Node: respond_to_user")
    print(f"Agent Response: {state['response']}")
    return {"stage": "completed"}

def handle_error(state: AgentState) -> Dict[str, Any]:
    print("Node: handle_error")
    return {
        "response": "An error occurred during processing. Please try again.",
        "stage": "error"
    }

# --- 3. Define Graph ---
def create_shopping_agent() -> Annotated[StateGraph, AgentState]:
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("parse_request", parse_user_request)
    workflow.add_node("search_amazon", search_amazon)
    workflow.add_node("compare_products", compare_products)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("respond_to_user", respond_to_user)
    workflow.add_node("handle_error", handle_error)

    # Add edges
    workflow.add_edge("parse_request", "search_amazon")

    workflow.add_conditional_edges(
        "search_amazon",
        lambda state: "compare_products" if state['stage'] == "product_extraction_done" else "handle_error"
    )

    workflow.add_conditional_edges(
        "compare_products",
        lambda state: "generate_response" if state['stage'] == "comparison_done" else "handle_error"
    )

    workflow.add_edge("generate_response", "respond_to_user")
    workflow.add_edge("respond_to_user", END)

    workflow.set_entry_point("parse_request")
    return workflow.compile()

# --- 5. Run Agent ---
if __name__ == "__main__":
    user_request_example = "skis for less than $100"
    initial_state = {
        "user_request": user_request_example,
        "search_query": "",
        "filters": {},
        "product_listings": [],
        "comparison_results": "",
        "response": "",
        "stage": "initial"
    }
    
    graph = create_shopping_agent()
    results = graph.invoke(initial_state)
    print("\n--- Agent Execution Completed ---")