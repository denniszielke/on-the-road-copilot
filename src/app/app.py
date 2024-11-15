import logging
import os
from pathlib import Path

from aiohttp import web
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

from backend.tools import _generate_report_tool, _generate_report_tool_schema, _validate_input_tool, _validate_input_tool_schema
from backend.rtmt import RTMiddleTier, Tool

from acs.caller import OutboundCall

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voicerag")

async def create_app():
    if not os.environ.get("RUNNING_IN_PRODUCTION"):
        logger.info("Running in development mode, loading from .env file")
        load_dotenv()
    llm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME")
    llm_key = os.environ.get("AZURE_OPENAI_API_KEY")

    credential = None
    if not llm_key:
        if tenant_id := os.environ.get("AZURE_TENANT_ID"):
            logger.info(
                "Using AzureDeveloperCliCredential with tenant_id %s", tenant_id)
            credential = AzureDeveloperCliCredential(
                tenant_id=tenant_id, process_timeout=60)
        else:
            logger.info("Using DefaultAzureCredential")
            credential = DefaultAzureCredential()
    llm_credential = AzureKeyCredential(llm_key) if llm_key else credential

    app = web.Application()

    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, llm_credential)
    rtmt.system_message = (
        "You are a helpful assistant that maintains a conversation with the user, while asking questions according to a specific script.\n"
        "The user is an employee who is driving from a customer meeting and talking to you hands-free in the car. "
        "You MUST start the conversation by asking the user the following questions:\n"
        "1. How did your demo meeting with the customer go?\n"
        "2. Please name the customer.\n"
        "3. What is the product that the demo is needed for?\n"
        "4. When is the demo needed?\n"
        "You must engage the user in a conversation and ask the questions in the script. The user will provide the answers to the questions.\n"
        "Make sure you ask the questions in the correct order and that you ask all the questions in the script.\n"
        "For each input provided by a user you MUST validate the input using the validate_input tool to verify that the value is valid.\n"
        "If the input is not valid you should ask the user again until you are given valid input. You should repeat until you are receiving valid input. \n"
    )
    
    # rtmt.system_message = (
    #     "You are a helpful assistant that maintains a conversation with the user, while asking questions according to a specific script.\n"
    #     "The user is an employee who is driving from a customer meeting and talking to you hands-free in the car. "
    #     "You MUST start the conversation by asking the user the following questions:\n"
    #     "1. How did your demo meeting with the customer go?\n"
    #     "2. Please name the customer.\n"
    #     "3. What is the product that the demo is needed for?\n"
    #     "4. When is the demo needed?\n"
    #     "After you have gone through all the questions in the script, output a valid JSON file to the user by calling the 'generate_report' function,\n "
    #     "with the schema definition being various customer demo and product attributes derived from the conversation.\n "
    #     "You must engage the user in a conversation and ask the questions in the script. The user will provide the answers to the questions.\n"
    #     "Make sure you ask the questions in the correct order and that you ask all the questions in the script.\n"
    #     "For each input provided by a user you MUST validate the input using the validate_input tool to verify that the value is valid.\n"
    #     "If the input is not valid you should ask the user again until you are given valid input. You should repeat until you are receiving valid input. \n"
    # )
    # rtmt.tools["generate_report"] = Tool(
    #     target=_generate_report_tool, schema=_generate_report_tool_schema
    # )

    rtmt.tools["validate_input"] = Tool(
        target=_validate_input_tool, schema=_validate_input_tool_schema
    )

    rtmt.attach_to_app(app, "/realtime")

    if (os.environ.get("ACS_TARGET_NUMBER") is not None and
            os.environ.get("ACS_SOURCE_NUMBER") is not None and
            os.environ.get("ACS_CONNECTION_STRING") is not None and
            os.environ.get("ACS_CALLBACK_PATH") is not None):
        caller = OutboundCall(
            os.environ.get("ACS_TARGET_NUMBER"),
            os.environ.get("ACS_SOURCE_NUMBER"),
            os.environ.get("ACS_CONNECTION_STRING"),
            os.environ.get("ACS_CALLBACK_PATH"),
        )
        caller.attach_to_app(app, "/acs")


    # Serve static files and index.html
    current_directory = Path(__file__).parent  # Points to 'app' directory
    static_directory = current_directory / 'static'

    # Ensure static directory exists
    if not static_directory.exists():
        raise FileNotFoundError("Static directory not found at expected path: {}".format(static_directory))

    # Serve index.html at root
    async def index(request):
        return web.FileResponse(static_directory / 'index.html')

    async def call(request):
        if (caller is not None):
            await caller.call()
            return web.Response(text="Created outbound call")
        else:
            return web.Response(text="Outbound calling is not configured")

    app.router.add_get('/', index)
    app.router.add_static('/static/', path=str(static_directory), name='static')
    app.router.add_post('/call', call)

    return app

if __name__ == "__main__":
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 8765))
    web.run_app(create_app(), host=host, port=port)
