import os
from dotenv import load_dotenv
from semantic_kernel.functions import kernel_function
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizableTextQuery

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_API_KEY")
SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

class AiSearchHybrid:
    @kernel_function(name="ai_search", description="Hybrid semantic/keyword search with structured filtering.")
    def ai_search(self, query: str, filter_query: str = None, top: int = 3) -> str:
        """
        Perform a hybrid search on the AI Search index, optionally applying a structured filter.
        Args:
            query (str): The natural language or keyword query for semantic/keyword search.
            filter_query (str, optional): OData filter string (e.g., "claps gt 1000 and publication eq 'Better Humans'").
            top (int): Number of results to return.
        Returns:
            str: Concatenated string of retrieved documents or "No documents found."
        """
        credential = AzureKeyCredential(AZURE_SEARCH_KEY)
        client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX_NAME,
            credential=credential,
        )

        search_kwargs = {
            "search_text": query,
            "vector_queries": [
                VectorizableTextQuery(
                    text=query, k_nearest_neighbors=50, fields="vector"
                )
            ],
            "query_type": "semantic",
            "semantic_configuration_name": "my-semantic-config",
            "search_fields": ["chunk"],
            "top": top,
            "include_total_count": True,
        }
        if filter_query:
            search_kwargs["filter"] = filter_query

        results = client.search(**search_kwargs)
        retrieved_texts = [result.get("chunk") for result in results]
        context_str = (
            "\n".join(retrieved_texts) if retrieved_texts else "No documents found."
        )
        return context_str
