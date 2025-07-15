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
  - Main Search Agent (`ChatCompletionsAgent`): routes the user query based to the filtered query agent if query has filter or if it not not include a filter, agent invokes the hybrid search plugin (filter vs. semantic)
      - **2 plugin:**
          - `ai_search_hybrid` (only hybrid/ semantic ranker search (retireves top 5 documents)
          -  `filtered_query_agent` (agent plugin)
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
---

## Testing Plugins: `ai_search_both` and `ai_search_hybrid`
The repo includes two test folders designed to demonstrate and validate the behavior of different Azure AI Search plugin strategies:
1. ai_search_both Plugin:
- Enables hybrid search, combining full-text/keyword search with vector-based semantic search in a single query. Use this to evaluate how well the system retrieves results when both classic and vector retrieval are combined.
2. ai_search_hybrid Plugin:
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
python app_multi_agent.py
```




