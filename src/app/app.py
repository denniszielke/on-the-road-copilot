import logging
import os
from pathlib import Path

from aiohttp import web
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

from backend.tools import _generate_report_tool, _generate_report_tool_schema
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
        "You are a helpful assistant that maintains a conversation with the user, asking questions according to a specific script.\n"
        "The user is an employee who is driving from a customer meeting and talking to you hands-free in the car. "
        "You MUST start the conversation by asking the user the following questions:\n"
        "1. How did your demo meeting with the customer go?\n"
        "2. Please name the customer.\n"
        "3. What is the product that the demo is needed for?\n"
        "4. When is the demo needed?\n"
        "After you have gone through all the questions in the script, output a valid JSON file to the user by calling the 'generate_report' function, "
        "with the schema definition being various customer demo and product attributes derived from the conversation."
    )
    rtmt.tools["generate_report"] = Tool(
        target=_generate_report_tool, schema=_generate_report_tool_schema
    )

    rtmt.attach_to_app(app, "/realtime")

    caller = OutboundCall(
        os.environ.get("ACS_TARGET_NUMBER"),
        os.environ.get("ACS_SOURCE_NUMBER"),
        os.environ.get("ACS_CONNECTION_STRING"),
        os.environ.get("ACS_CALLBACK_PATH"),
    )
    callback_path = os.environ.get("ACS_CALLBACK_PATH")
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
        await caller.call()
        return web.Response(text="OK")

    app.router.add_get('/', index)
    app.router.add_static('/static/', path=str(static_directory), name='static')
    app.router.add_post('/call', call)

    return app

if __name__ == "__main__":
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 8765))
    web.run_app(create_app(), host=host, port=port)
