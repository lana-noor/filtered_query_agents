import os
from semantic_kernel.kernel import Kernel
from semantic_kernel.agents import ChatHistoryAgentThread
import asyncio
from utils.util import create_agent_from_yaml
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
from azure.ai.inference.aio import ChatCompletionsClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.filters import FunctionInvocationContext
from dotenv import load_dotenv

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

    # Step 2: Create the Azure AI service and register to kernel
ai_service = AzureAIInferenceChatCompletion(
    ai_model_id="executor",
    service_id="default",  # This must match the service_id you use below!
    client=ChatCompletionsClient(
        endpoint=f"{endpoint}/openai/deployments/{deployment_name}",
        api_version=api_version,
        credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_KEY")),
    ),
)

kernel = Kernel()
kernel.add_service(service=ai_service)
kernel.add_filter("function_invocation", function_invocation_filter)


impact_analyzer_agent = create_agent_from_yaml(
    kernel=kernel,
    service_id="default",
    definition_file_path="agents/impact_analyzer.yaml",
)

incident_details_fetcher_agent = create_agent_from_yaml(
    kernel=kernel,
    service_id="default",
    definition_file_path="agents/incident_details_fetcher.yaml",
)

search_agent = create_agent_from_yaml(
    kernel=kernel,
    service_id="default",
    definition_file_path="agents/search.yaml",
)

session_agent = create_agent_from_yaml(
    kernel=kernel,
    service_id="default",
    definition_file_path="agents/session_test.yaml",
)


netcopilot_agent = ChatCompletionAgent(
    service=AzureChatCompletion(
        deployment_name=deployment_name,
        api_key=openai_key,
        endpoint=endpoint,
        api_version=api_version,
    ),
    kernel=kernel,
    name="NetCopilotAgent",
    instructions=(
        """You are a Telecom Network Engineer AI assistant designed to assist in:
          - diagnosing and resolving network incidents efficiently by coordinating two specialized agents: Impact_Anlyzer and Incident_details_fetcher
          - perform user session tests
          - search troubleshooting guides for network issues
          
    Your goal is to perfrom the following depending on the user input, if a user input is missing ask the user to provide it:
    
    If you are given an incident Nr, perfrom the following tasks in EXACT order: 
    
      Step 1: Incident Analysis and Resolution Plan Generation
      Invoke the incident_details_fetcher_agent using the incident_ID given by the user:
      -Display the output of the Incident_details_fetcher_Agent plugin
      
      Step 2: Impact Assessment:
      Use the impact_analyzer_agent plugin with the node names from Step1 to  generate an impact assessment report.
        (Display the output of the plugin above)
     
      Output:
        Return a structured response containing:
        -Detailed Incident Analysis and Resolution Action Plan.
        -Impact Assessment Report.
        
    If you are given a user session: 
      - Test sessions impact — delegated to the Session_Agent plugin using the User/Session given by the user
      Output:
      - Display the exact session_agent plugin output

    if you are given an issue description: 
      - Search for troubleshooting guides and resolution steps use the  the search_agent plugin. 
      Output:
      - Use the Search Agent to formulate a structured and clear response and include references 
      - If the Search Agent does not return any results, use your own knowledge to respond and DO NOT include references

      Make sure you complete each step in depth and are very detailed in your response. ALWAYS follow the steps in order and consolidate all the agents output. Do not say fetching data, only output the plugin output or agent output. 
"""
    ),
    plugins=[search_agent, impact_analyzer_agent, incident_details_fetcher_agent, session_agent],
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

    response = await netcopilot_agent.get_response(
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
