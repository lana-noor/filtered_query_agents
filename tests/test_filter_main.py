import sys
import os

# Add plugins directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../plugins')))

from ai_search_hybrid_filtered import AiSearchHybrid

def main():
    print("=== Azure AI Search Filtered Query Tester (No Hybrid/Semantic) ===")
    filter_query = input("OData Filter Query (e.g., \"claps gt 1000 and date ge 2020-01-01T00:00:00Z\"): ").strip()
    if not filter_query:
        print("You must provide a filter query.")
        return

    # Instantiate the plugin class
    plugin = AiSearchHybrid()
    
    # Always returns top 5 results now, with no semantic/hybrid search
    results = plugin.ai_search(query="", filter_query=filter_query)

    if not results:
        print("No documents found.")
        return

    print("\n=== Results ===")
    for doc in results:
        print("=" * 40)
        print(f"id:           {doc.get('id')}")
        print(f"title:        {doc.get('title')}")
        print(f"subtitle:     {doc.get('subtitle')}")
        print(f"content:      {doc.get('chunk')}")
        print(f"responses:    {doc.get('responses')}")
        print(f"claps:        {doc.get('claps')}")
        print(f"reading_time: {doc.get('reading_time')}")
        print(f"date:         {doc.get('date')}")
        print("=" * 40)

if __name__ == "__main__":
    main()
