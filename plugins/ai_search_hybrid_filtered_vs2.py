import os
from dotenv import load_dotenv
from semantic_kernel.functions import kernel_function
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizableTextQuery

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

class AiSearchHybrid:
    @kernel_function(name="ai_search_both", description="Hybrid search for 50 docs, then apply Azure Search filter on those docs and return top 5. If no filter, returns hybrid top 5.")
    def ai_search_both(self, query: str, filtered_query: str = None):
        credential = AzureKeyCredential(AZURE_SEARCH_KEY)
        client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX_NAME,
            credential=credential,
        )

        # If no filtered_query, do hybrid search for top 5
        if not filtered_query:
            results = client.search(
                search_text=query,
                vector_queries=[
                    VectorizableTextQuery(text=query, k_nearest_neighbors=30, fields="titlesVector"),
                    VectorizableTextQuery(text=query, k_nearest_neighbors=30, fields="contentVector")
                ],
                query_type="semantic",
                semantic_configuration_name="my-semantic-config",
                search_fields=["content", "title", "subtitle"],
                top=5,
                include_total_count=True,
            )
            return [doc for doc in results]

        # Otherwise, run two-pass logic: hybrid 50 → filter
        results = client.search(
            search_text=query,
            vector_queries=[
                VectorizableTextQuery(text=query, k_nearest_neighbors=30, fields="titlesVector"),
                VectorizableTextQuery(text=query, k_nearest_neighbors=30, fields="contentVector")
            ],
            query_type="semantic",
            semantic_configuration_name="my-semantic-config",
            search_fields=["content", "title", "subtitle"],
            top=50,
            include_total_count=True,
        )
        top_docs = [doc for doc in results]
        top_ids = [str(doc["id"]) for doc in top_docs if "id" in doc]
        if not top_ids:
            return []

        # Build ID filter for just these docs
        id_filter = " or ".join([f"id eq {id}" for id in top_ids])
        combined_filter = f"({id_filter}) and ({filtered_query})"

        # Second search: only on these 50 docs, with structured filtering
        filtered_results = client.search(
            search_text="*",
            filter=combined_filter,
            select=["id", "title", "subtitle", "content", "reading_time", "responses", "claps", "date", "publication"],
            top=5
        )
        final_docs = [doc for doc in filtered_results]
        return final_docs
