import sys
import os

# Add plugins directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../plugins')))

from ai_search_both import AiSearchBoth

def main():
    # Just set your test query and filter here!
    # query = "articles about productivity or attention"
    # filtered_query = "publication eq 'Better Humans' and claps ge 1000"

    query = "articles about productivity or attention"
    filtered_query = "publication eq 'Better Humans' and date gt 2020-05-10T00:00:00Z and claps ge 1000"

    # Or set filtered_query = None for hybrid-only

    plugin = AiSearchBoth()
    results = plugin.ai_search_both(query=query, filtered_query=filtered_query)

    if not results:
        print("No documents found.")
        return

    print("\n=== Results ===")
    for doc in results:
        print("=" * 40)
        print(f"id:           {doc.get('id')}")
        print(f"title:        {doc.get('title')}")
        print(f"subtitle:     {doc.get('subtitle')}")
        print(f"content:      {doc.get('content')}")
        print(f"responses:    {doc.get('responses')}")
        print(f"claps:        {doc.get('claps')}")
        print(f"reading_time: {doc.get('reading_time')}")
        print(f"date:         {doc.get('date')}")
        print(f"publication:  {doc.get('publication')}")
        print("=" * 40)

if __name__ == "__main__":
    main()
