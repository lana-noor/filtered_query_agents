import asyncio

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.filters import FunctionInvocationContext
from plugins.ai_search_both import AiSearchKeyword
from plugins.ai_search_both import AiSearchBoth
from dotenv import load_dotenv
import os 

"""
The following application creates 2 Chat Completion Agents, 
the specalized agent is a filtered query agent that converts 
NL to full text queries, it has a ai search keyword plugin. 
The main agent routes to the specalized agent but also invokes 
ai search hybrid plugin and performs RAG. Main Search Agent 
delegate requests to the specalized agent depending on the query. 
A Function Invocation Filter is used to show the function call 
content and the function result content so the caller
can see which agent was called and what the response was.
"""


# Define the auto function invocation filter that will be used by the kernel
async def function_invocation_filter(context: FunctionInvocationContext, next):
    """A filter that will be called for each function call in the response."""
    if "messages" not in context.arguments:
        await next(context)
        return
    print(f"    Agent [{context.function.name}] called with messages: {context.arguments['messages']}")
    await next(context)
    print(f"    Response from agent [{context.function.name}]: {context.result.value}")

# Load environment variables (keys, endpoint, etc.)
load_dotenv()

# Step 1: Get OpenAI/Azure config from env or hardcoded for testing
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment_name = os.getenv("EXECUTOR_AZURE_OPENAI_DEPLOYMENT_NAME")
openai_key = os.getenv("AZURE_OPENAI_KEY")


# Create and configure the kernel.
kernel = Kernel()

# The filter is used for demonstration purposes to show the function invocation.
kernel.add_filter("function_invocation", function_invocation_filter)

filtered_query_agent = ChatCompletionAgent(
    service=AzureChatCompletion(),
    name="FilteredQueryAgent",
    instructions=(
        "You are a specialized assistant responsible for converting user questions into two parts: "
        "1) a semantic search query (query variable), and 2) a structured filter (filtered_query variable) in OData syntax. "
        "Your task is to analyze the user's request, then extract and output:\n"
        "- query: a concise phrase or question that captures the main unstructured topic or topics the user is searching for (used for semantic/hybrid search)\n"
        "- filtered_query: an OData filter string representing any explicit constraints on fields such as date, claps, responses, publication, or reading_time (used for structured filtering)\n\n"
        "Instructions:\n"
        "• Carefully identify any structured requirements (such as minimum/maximum claps, specific dates or ranges, publication names, reading times, etc.) and include them only in the filtered_query variable.\n"
        "• Everything else related to the general subject or intent goes into the query variable.\n"
        "• For all date filters in filtered_query, you MUST write the date in the format YYYY-MM-DDTHH:MM:SSZ. "
        "For example, May 24, 2020 should be written as 2020-05-24T00:00:00Z. "
        "Always include the 'T00:00:00Z' at the end of the date. "
        "For instance: 'date gt 2020-05-10T00:00:00Z' or 'date lt 2021-01-01T00:00:00Z'.\n"
        "• If no explicit filters are present in the user's request, set filtered_query to None.\n"
        "• Always output your result as valid Python code, assigning values to two variables: query and filtered_query.\n"
        "• AFTER and ONLY AFTER you have output these two variables, you MUST invoke the AiSearchBoth plugin with those variables. "
        "This means you ALWAYS invoke the plugin as the final step, regardless of whether filtered_query is None.\n\n"
        "Example:\n"
        "User input: 'Show me articles about productivity or attention from Better Humans after May 10, 2020, with at least 1000 claps.'\n"
        "Output:\n"
        "query = 'articles about productivity or attention from Better Humans'\n"
        "filtered_query = \"publication eq 'Better Humans' and date gt 2020-05-10T00:00:00Z and claps ge 1000\"\n"
        "AiSearchBoth(query=query, filter_query=filtered_query)\n"
        "\n"
        "If the user provides no filter constraints, set filtered_query to None and still invoke the plugin:\n"
        "query = 'articles about sleep improvement'\n"
        "filtered_query = None\n"
        "AiSearchBoth(query=query, filter_query=filtered_query)"
    ),
    plugins=[AiSearchBoth()]
)

hybrid_query_agent = ChatCompletionAgent(
    service=AzureChatCompletion(),
    name="HybridQueryAgent",
    instructions=(
        "You specialize in handling customer questions related to billing issues. "
        "This includes clarifying invoice charges, payment methods, billing cycles, "
        "explaining fees, addressing discrepancies in billed amounts, updating payment details, "
        "assisting with subscription changes, and resolving payment failures. "
        "Your goal is to clearly communicate and resolve issues specifically about payments and charges."
    ),
    plugins=[AiSearchHybrid()]
)

router_search_agent = ChatCompletionAgent(
    service=AzureChatCompletion(
        deployment_name=deployment_name,
        api_key=openai_key,
        endpoint=endpoint,
        api_version=api_version,
    ),
    kernel=kernel,
    name="RouterSearchAgent",
    instructions=(
        "
    ),
    plugins=[filtered_query_agent, hybrid_query_agent],
)

thread: ChatHistoryAgentThread = None


async def chat() -> bool:
    """
    Continuously prompt the user for input and show the assistant's response.
    Type 'exit' to exit.
    """
    try:
        user_input = input("User:> ")
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting chat...")
        return False

    if user_input.lower().strip() == "exit":
        print("\n\nExiting chat...")
        return False

    response = await triage_agent.get_response(
        messages=user_input,
        thread=thread,
    )

    if response:
        print(f"Agent :> {response}")

    return True



async def main() -> None:
    print("Welcome to the chat bot!\n  Type 'exit' to exit.\n  Try to get some billing or refund help.")
    chatting = True
    while chatting:
        chatting = await chat()


if __name__ == "__main__":
    asyncio.run(main())