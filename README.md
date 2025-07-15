# Filtered Query Agents – Multi-Agent and Hybrid Search with Azure AI

## What is this Application?

This repo provides a practical implementation of **filtered query agents** for document retrieval using Azure AI Search, Azure OpenAI (GPT-4o/4.1), and Python (Semantic Kernel Agent Framework).  
It demonstrates agentic RAG patterns where user queries are routed and transformed by LLM agents and plugins, supporting both **semantic/hybrid search** and **advanced filtered search** (e.g., by date, author, category).

**Benefits:**
- Combine LLM-powered natural language understanding with structured search and filtering.
- Out-of-the-box (OOB), Azure AI Search’s native semantic search does not support structured filtering or range queries—meaning you can’t natively filter by fields like date ranges, number of claps, or exact matches for metadata when using only semantic or vector search.
- However, by adopting a hybrid agentic approach with Azure OpenAI, this application enables both full-text (keyword and semantic) search and powerful structured filter queries. Using LLM agents to interpret user intent and convert natural language into precise search + filter expressions, you can now easily run queries such as “articles about Microsoft with more than 500 claps after 2021,” combining the best of free-text and structured search. This approach unlocks advanced RAG scenarios and truly enterprise-grade search workflows, all orchestrated in Python using the Semantic Kernel Agent Framework.
- Easily answer questions like:  
  > “Show me articles about productivity from ‘Better Humans’ with more than 500 claps after May 2020”
- Modular architecture: add or swap agents and plugins for new use cases.

---

## What Does It Use?

- **Azure AI Search** (vector, semantic, and keyword search with filtering)
- **Azure OpenAI** (GPT-4o/4.1) as agent “brains”
- **Azure Container Apps** (for scalable backend deployment)
- **Cosmos DB** (optional, for chat history)
- **Python (Semantic Kernel Agent Framework SDK)** for agent and plugin orchestration

**Services to Deploy:**
- Azure AI Search service
- Azure OpenAI resource
- (Optional) Azure Cosmos DB
- (Recommended) Azure Container Apps

---

## Ingestion Folder & Data Prep

### How to Process an Excel File and Ingest to Azure AI Search
This repo uses the `ingestion/Push_Ingestion_Notebook_ArticlesData.ipynb` notebook to ingest data to Azure AI Search using the Push API: 

1. **Convert Excel to CSV**  
   Place your CSV in the `ingestion/` folder.

2. **Preprocess CSV file and JSON Conversion**
The following steps are taken for preprocessing excel file: 
   - Remove NaNs from excel file
   - Filter for rows with all required columns
   - Generate summaries/content with Azure OpenAI
   - Create vector embeddings (title/subtitle and content)
   - Output a JSON array of objects to ingest to index in Azure AI Search

4. **Create Index Schema**
- Python SDK is used to define and deploy the search index schema.
- The index includes both text fields (for search/filter/sort) and vector fields for hybrid/semantic search.
- Key field types:
  - `id` (string, key, filterable, sortable)
  - `title`, `subtitle`, `publication`, `content` (searchable text fields)
  - `claps`, `responses`, `reading_time` (integers, filterable/sortable)
  - `date` (DateTimeOffset, filterable/sortable, for date range queries)
  - `titlesVector`, `contentVector` (vector fields, 3072 dimensions, for vector search)
- Vector search is enabled with HNSW and Azure OpenAI vectorizer.
- Semantic configuration prioritizes title, subtitle, publication, and content fields for semantic ranking.
- Your index schema must match your JSON data exactly (same field names and types)
  - Why: This ensures ingestion will not fail and all filters, sorts, and search features work as expected.

6.  **Upload with Push API**  
   The repo uses the [Push API](https://learn.microsoft.com/en-us/azure/search/search-howto-upload-data-push-api) via the `azure-search-documents` Python SDK. Batch processing of JSON documents is pushed to index using `SearchIndexingBufferedSender` from `azure.search.documents`. 

7. **Test Index with Full Text Search**
- Full text search allows users to search the content of text fields (such as title, content, subtitle, etc.) for relevant documents based on keywords or natural language queries.
- The search engine analyzes, tokenizes, and indexes all words in the text fields so you can retrieve results that "contain," "match," or are "similar to" your query, regardless of exact phrasing or word order.
- Filtering uses structured (OData-based) queries to return only documents where fields meet specific conditions, similar to SQL WHERE clauses.
- Filtering is performed on fields marked as filterable in your index schema and supports numeric, date, boolean, and string comparisons.

Example: 
`
filter_query = "publication eq 'Better Humans' 
filter_query = (
    "publication eq 'UX Collective' and "
    "date ge 2020-05-01T00:00:00Z and "
    "date le 2020-05-31T00:00:00Z and "
    "responses ge 5"
)
filter_query = "search.ismatch('Google', 'title') and reading_time gt 5"
`

## Architectures Breakdown

### 1. Single Agent – Filtered Query Agent

- **1 agent:** Filtered Query Agent (`ChatCompletionsAgent`)
- **1 plugin:** `ai_search_keyword` (full text/keyword search with filters)
- **Flow:**  
  User query → Filtered Query Agent → JSON filtered query → ai_search_keyword plugin → Azure AI Search

**When to use:**  
When you need to convert NL queries directly into filtered search (e.g., “claps > 1000, date after X”).

---

### 2. Router + Filtered Query Agent (Multi-Agent)

- **2 agents:**
  - Router Agent (`ChatCompletionsAgent`): routes the user query based on intent (filter vs. semantic)
  - Filtered Query Agent (`ChatCompletionsAgent`): handles conversion to filtered queries if needed
- **1 plugin:** `ai_search_keyword`
- **Flow:**  
  User query → Router Agent → (Filtered Query Agent, if filter intent detected) → ai_search_keyword plugin → Azure AI Search

**When to use:**  
For mixed queries, where the system must decide:
- Use filtered search for queries with explicit filters
- Use semantic/hybrid otherwise

---

### 3. Full Multi-Agent: Router, Filtered, Hybrid Agents

- **3 agents:**
  - Router Agent: Detects if query is filterable or semantic/hybrid
  - Filtered Query Agent: For structured/filtered queries
  - Hybrid Query Agent: For unstructured, hybrid, or semantic queries (uses `ai_search_hybrid` plugin)
- **2 plugins:**
  - `ai_search_keyword`: for full-text keyword/filter search
  - `ai_search_hybrid`: for hybrid+semantic vector search
- **Flow:**  
  User query → Router Agent → (Filtered Query Agent or Hybrid Query Agent) → respective plugin → Azure AI Search

**When to use:**  
You want maximum flexibility for both natural and structured queries, and to combine LLM-powered hybrid search with classic filters.

---

## How to Deploy

### 1. Clone the Repo

```bash
git clone https://github.com/lana-noor/filtered_query_agents.git
cd filtered_query_agents

