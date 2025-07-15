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
The data in the index was taken from [Kaggle Medium Articles Data](https://www.kaggle.com/datasets/shlokramteke/sdfadgdadfda). The dataset includes the following columns: id, url, title, subtitle, claps, responses, reading_time, publication, date. 
This repo uses the `ingestion/Push_Ingestion_Notebook_ArticlesData.ipynb` notebook to ingest this data to Azure AI Search using the Push API: 

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
- The repo uses the [Push API](https://learn.microsoft.com/en-us/azure/search/search-what-is-data-import) via the `azure-search-documents` Python SDK.
- Batch processing of JSON documents is pushed to index using `SearchIndexingBufferedSender` from `azure.search.documents`. 

9. **Test Index with Full Text Search**
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
You can deploy either a Single Agent Filtered Query system or a Multi-Agent system with a dedicated agent for filtered queries.
The repo provides different agent workflows, allowing you to choose the right approach for your use case. 
- Use app_single_agent.py to run the single filtered query agent architecture.
- Use app_multi_agent.py for the multi-agent workflow, which routes queries to a specialized filtered query agent when needed.

### 1. Single Agent – Filtered Query Agent
<img width="5225" height="1907" alt="Single Agent Filtered Query REPO" src="https://github.com/user-attachments/assets/e06f968c-6a8b-4a30-9176-8e482b41a97c" />

- **1 agent:** Filtered Query Agent (`ChatCompletionsAgent`)
- **1 plugin:** `ai_search_both` (full text/keyword with filters and hybrid/ semantic search)
- **Flow:**  
  User query → Filtered Query Agent → JSON filtered query → ai_search_both plugin → Azure AI Search

**When to use:**  
Use this approach when you need to convert natural language (NL) queries directly into filtered search (e.g., “claps > 1000, date after X”), and when you expect most users to ask questions that combine both hybrid search and filtering. This workflow is ideal when queries are typically a mix of semantic relevance and structured filters, rather than being exclusively one or the other.

---

### 2. Main Search Agent + Filtered Query Agent (Multi-Agent)
<img width="6292" height="2520" alt="Multi Agent Filtered Query REPO" src="https://github.com/user-attachments/assets/74a02ee3-a470-4dd4-a195-b41fa6a232ee" />

- **2 agents:**
  - Main Search Agent (`ChatCompletionsAgent`): routes the user query to the filtered query agent if query has filter or if it not not include a filter, agent invokes the hybrid search plugin (filter vs. semantic)
      - **2 plugin:**
          - `hybrid_search_agent`: agent plugin for hybrid search
          - `filtered_query_agent`: agent plugin for filtering with hybrid search
  - Filtered Query Agent (`ChatCompletionsAgent`): handles conversion to filtered queries and invokes  `ai_search_both` plugin.
      - **1 plugin:** `ai_search_both` (full text/keyword with filters and hybrid/ semantic search)
- **Flow:**  
  User query → Main Search Agent → (Filtered Query Agent, if filter intent detected) → Filtered Query Agent → JSON filtered query → ai_search_both plugin → Azure AI Search
  User query → Main Search Agent → (no filtered query detected) → ai_search_hybrid plugin → Azure AI Search
  
**When to use:**  
For mixed queries, where the system must decide dynamically how to search:
- Use filtered search for queries with explicit filters, such as date ranges, minimum claps, or specific publications (e.g., “articles from 2023 with more than 100 responses”).
- Use semantic or hybrid search otherwise, for open-ended or relevance-based questions (e.g., “What are the best productivity tips?”).
- Ideal when user queries are unpredictable and may contain a mix of structured and unstructured requirements.
- Enables a seamless user experience, letting the agent route queries intelligently without user intervention.

### 3. Router Agent + Filtered Query Agent + Hybrid Search Agent (Multi-Agent)
<img width="6367" height="2106" alt="Router Agent Multi Agent Filtered Query REPO" src="https://github.com/user-attachments/assets/84608bd3-0147-4935-bcdf-e974bbbd396e" />

- **3 agents:**
  - **Router Agent (`ChatCompletionsAgent`):**
    - Examines each user query and routes it based on intent:
      - If a filter (e.g., date range, minimum claps) is detected, routes to the Filtered Query Agent.
      - If no filter is present, routes to the Hybrid Search Agent.
    - **2 plugins:**
      - `hybrid_search_agent`: agent plugin for hybrid search
      - `filtered_query_agent`: agent plugin for filtering with hybrid search
  - **Filtered Query Agent (`ChatCompletionsAgent`):**
    - Converts natural language queries into explicit filtered queries, then invokes `ai_search_both` for hybrid + filtered search.
    - **1 plugin:** `ai_search_both`
  - **Hybrid Search Agent (`ChatCompletionsAgent`):**
    - Handles semantic/hybrid search queries that do not require filtering, invoking `ai_search_hybrid`.
    - **1 plugin:** `ai_search_hybrid`

- **Flow:**  
  - **Filtered query intent:**  
    User query → Router Agent → Filtered Query Agent → JSON filtered query → `ai_search_both` plugin → Azure AI Search
  - **No filter intent:**  
    User query → Router Agent → Hybrid Search Agent → `ai_search_hybrid` plugin → Azure AI Search

**When to use:**
For complex queries where an LLM is needed to determine whether a filter is present and how it should be applied:
- Use this architecture when user questions are **unpredictable and may combine natural language, full text, and structured filtering**—for example, “Show me articles about AI from 2023 with more than 1,000 claps, sorted by responses.”
- Ideal for scenarios where the **data model is rich and contains many filterable fields** (e.g., date ranges, authors, categories, response counts, etc.), and you want your system to intelligently parse and apply these filters based on user intent.
- Perfect if users are likely to ask both open-ended (“What are the latest trends in data science?”) and highly structured (“List productivity articles from UX Collective published after May 2022 with at least 10 responses.”) questions.
- This approach leverages the Router Agent to let an LLM decide the best search strategy for each query:
    - **If the query includes a filter,** it is routed to the Filtered Query Agent, which constructs and executes an advanced filter query using `ai_search_both`.
    - **If no filter is detected,** the query is routed to the Hybrid Search Agent, which runs semantic/hybrid search via `ai_search_hybrid`.
- Recommended when you need to **combine flexible LLM-powered search with strict business constraints** (like regulatory reporting, compliance, or tailored insights) where sometimes a semantic result is best, and other times exact field matching is required.
- **Also useful when you need specialized post-processing on hybrid search results**—for example, if the Hybrid Search Agent is programmed to summarize, generate insights, or trigger automated actions based on retrieved content.

---

##  Plugins: `ai_search_both` and `ai_search_hybrid`

### `ai_search_both` Plugin

The `ai_search_both` plugin implements a two-step **hybrid + filtered search** on your Azure AI Search index:

1. **Hybrid Search:**  
   - Uses both vector search (on `titlesVector` and `contentVector`) and full-text/semantic search.
   - Retrieves the top 50 most relevant documents for the given query, leveraging Azure AI Search’s hybrid and semantic capabilities.

2. **Filtered Re-Ranking:**  
   - Optionally applies a structured filter (e.g., by date, claps, publication) to the top 50 results from step 1.
   - This filter can handle advanced conditions like `responses > 10 and publication eq 'UX Collective'`.
   - Returns only the top 5 documents matching both semantic/hybrid relevance and your structured filter.

**How it works:**  
- The plugin first performs a broad hybrid search to capture the most semantically relevant candidates.
- It then narrows the results down using classic structured filtering (like a SQL WHERE clause) — but only among those top candidates, combining the strengths of both approaches.

**Use case:**  
> Perfect when you want the flexibility of semantic search but still need to enforce strict filters, such as date ranges, authors, or numerical thresholds.

**Example usage:**  
- "Show me articles about Microsoft published after 2021 with more than 500 claps."
- The plugin finds the most relevant articles, then applies the filters to those results, ensuring both relevance and precision.

### `ai_search_hybrid` Plugin

The `ai_search_hybrid` plugin performs a **pure hybrid and semantic search** on your Azure AI Search index.

- **How it works:**
  - Runs a hybrid query that combines vector similarity (using both `titlesVector` and `contentVector`) with full-text and semantic search across `title`, `subtitle`, and `content` fields.
  - Retrieves the top results (default: top 5) that are most relevant to the user’s query—*without applying any structured filters or field constraints*.
  - Returns a concise summary for each result, combining title, subtitle, and content for context.

- **Use case:**  
  > Ideal when you want the highest relevance from both semantic (vector) and keyword search, and you don’t need to filter by metadata such as date, claps, or author.

- **Example usage:**  
  - "Find articles about boosting productivity with sleep science."
  - "What are the best tips for learning Python quickly?"

This plugin is optimized for open-ended, natural language queries where semantic context and keyword matching are both important, but no additional field-based filtering is required.

## Testing Plugins: 
The repo includes two test folders designed to demonstrate and validate the behavior of different Azure AI Search plugin strategies:
1. test_ai_search_both:
- Enables hybrid search, combining full-text/keyword search with vector-based semantic search in a single query. Use this to evaluate how well the system retrieves results when both classic and vector retrieval are combined.
2. test_ai_search_hybrid:
- Focuses on pure hybrid or semantic search, leveraging Azure AI Search’s vector and semantic ranking capabilities. Use this to test scenarios where deep semantic understanding or vector similarity is prioritized.

### Test Folder:
- Each test folder contains example scripts and data to help you quickly verify that the corresponding plugin is functioning correctly and returning expected search results.
- Run these tests to compare the output, understand the strengths of each approach, and ensure your deployment is configured for your specific retrieval needs.

---
## How to Deploy

### 1. Clone the Repo

```bash
git clone https://github.com/lana-noor/filtered_query_agents.git
cd filtered_query_agents
```

### 2.  Configure Environment Variables
Set your Azure Search, OpenAI, and any Cosmos DB credentials in a .env file or as environment variables.

### 3. Ingest Data 
Upload your data to the data folder and use the notebook to ingest data to Azure AI Search Index 

### 4. Create a Virtual Environment and Install Requirements
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
### 5. Test Plugins 
```bash
python test_ai_search_both.py
python test_ai_search_hybrid.py
```

### 6. Run the App 
Interact with the application conversational AI using the CLI (no frontend integrated) 
```bash
python app_single_agent.py
python app_multi_agent_2agents.py
python app_multi_agent_3agents.py
```




