import asyncio

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.filters import FunctionInvocationContext
from plugins.ai_search_both import AiSearchBoth
from plugins.ai_search_hybrid import AiSearchHybrid
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior, FunctionChoiceType
import os 

"""
The following application uses a single agent to call an 
ai search function that does hybrid + semantic search, or 
full text search with a structured query or both. The
Chat Completions agent is used to convert a NL query to a 
filtered query if necessary. The agent decides what type of
search is needed and can perform all types of search (Hybrid, 
full text only or both) using one plugin. 
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
deployment_name = 'gpt-4.1'
openai_key = os.getenv("AZURE_OPENAI_API_KEY")


# Create and configure the kernel.
kernel = Kernel()

# The filter is used for demonstration purposes to show the function invocation.
kernel.add_filter("function_invocation", function_invocation_filter)

from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior

filtered_query_agent = ChatCompletionAgent(
    service=AzureChatCompletion(
        deployment_name=deployment_name,
        api_key=openai_key,
        endpoint=endpoint,
        api_version=api_version,
    ),
    name="FilteredQueryAgent",
instructions=(
    "You are an AI assistant specialized for searching knowledge articles. "
    "For every user message, you MUST extract two parameters—'query' and 'filtered_query'—and IMMEDIATELY INVOKE the AiSearchBoth plugin with these parameters as a function call. "
    "You MUST NOT respond in text, chat, markdown, or JSON—your ONLY valid action is to call the AiSearchBoth tool. "
    "Never write, display, or explain what you are doing—just call the plugin.\n"
    "\n"
    "Details:\n"
    "- query: a concise natural language search phrase (from the user message)\n"
    "- filtered_query: an OData filter string for explicit constraints (date, claps, responses, publication, reading_time), or null if no filters are needed\n"
    "- Dates must be formatted as YYYY-MM-DDT00:00:00Z\n"
    "- String values in filtered_query must use single quotes (e.g., publication eq 'Better Humans')\n"
    "\n"
    "Examples:\n"
    "User: Show me articles about productivity from Better Humans after May 10, 2020 with at least 1000 claps.\n"
    "You MUST call: AiSearchBoth(query='articles about productivity from Better Humans', filtered_query=\"publication eq 'Better Humans' and date gt 2020-05-10T00:00:00Z and claps ge 1000\")\n"
    "\n"
    "User: Summarize articles about sleep improvement from UX Collective publication with more than 150 claps and less than 10 reading time.\n"
    "You MUST call: AiSearchBoth(query='articles about sleep improvement', filtered_query='publication eq 'UX Collective' and claps ge 150 and reading_time le 20')\n"
    "\n"
    "Repeat: Never respond to the user with JSON or text. Your ONLY action is to invoke the AiSearchBoth plugin/function/tool using the arguments you extract."
),
    plugins=[AiSearchBoth()],
    function_choice_behavior=FunctionChoiceBehavior.Required(
        auto_invoke=True,
        filters={"included_functions": ["AiSearchBoth-ai_search_both"]},
    ),
)


main_search_agent = ChatCompletionAgent(
    service=AzureChatCompletion(
        deployment_name='gpt-4.1',
        api_key=openai_key,
        endpoint=endpoint,
        api_version=api_version,
    ),
    kernel=kernel,
    name="MainSearchAgent",
    instructions=(
        """
Your task is to analyze each user query and route it to the correct plugin:
1. If the query includes any structured constraints (such as date ranges, minimum or maximum claps, specific publication names, response counts, or reading times), you must invoke the filtered_query_agent. 
2. If the query does not include any field-based filters and only requires natural language search, invoke the AiSearchHybrid plugin directly for a hybrid semantic and vector search.
Always choose and invoke only the appropriate plugin based on the user’s request.
"""
    ),
    plugins=[filtered_query_agent, AiSearchHybrid()],
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

    response = await main_search_agent.get_response(
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