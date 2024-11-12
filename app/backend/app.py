import logging
import os
from pathlib import Path
from typing import Any

from aiohttp import web
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

from tools import _generate_report_tool, _generate_report_tool_schema
from rtmt import RTMiddleTier, Tool, ToolResult, ToolResultDirection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voicerag")


async def create_app():
    if not os.environ.get("RUNNING_IN_PRODUCTION"):
        logger.info("Running in development mode, loading from .env file")
        load_dotenv()
    llm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_REALTIME_DEPLOYMENT")
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
    rtmt.system_message = "You are a helpful assistant that maintains a conversation with the user, asking questions according to a specific script. \n"
    "The user is an employee who is driving from a customer meeting and talking to you hands-free in the car. "
    "You MUST start the conversation by asking the user the following questions:\n"
    "1. How did your demo meeting with the customer go?\n"
    "2. Please name the customer.\n"
    "3. What is the product that the demo is needed for?\n"
    "4. When is the demo needed?\n"
    "After you have gone through all the questions in the script, output a valid JSON file to the user by calling the 'generate_report' function, "
    "with the schema definition being various customer demo and product attributes derived from the conversation."
    rtmt.tools["generate_report"] = Tool(
        target=_generate_report_tool, schema=_generate_report_tool_schema)

    rtmt.attach_to_app(app, "/realtime")

 #   current_directory = Path(__file__).parent
 #   app.add_routes(
 #       [web.get('/', lambda _: web.FileResponse(current_directory / 'static/index.html'))])
 #   app.router.add_static('/', path=current_directory /
 #                         'static', name='static')

#  return app

if __name__ == "__main__":
    host = "localhost"
    port = 8765
    web.run_app(create_app(), host=host, port=port)
