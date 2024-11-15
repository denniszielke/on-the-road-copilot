import re
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
#from azure.search.documents.aio import SearchClient
#from azure.search.documents.models import VectorizableTextQuery
from backend.rtmt import RTMiddleTier, Tool, ToolResult, ToolResultDirection

async def _validate_input_tool(args: Any) -> ToolResult:
    input_type = args["input_type"]
    input_value = args["input_value"]

    if( input_type == None or input_type == "" ):
        print("Input type is empty:" + input_value)
        return ToolResult("The value is invalid because it has no type", ToolResultDirection.TO_CLIENT)

    if( input_value == None or input_value == "" ):
        print("Input is empty:" + input_value)
        return ToolResult("The value is invalid because it has no value", ToolResultDirection.TO_CLIENT)
    
    if ( input_value.lower() == "unknown" ):
        print("Input is not valid:" + input_value)
        return ToolResult("The value is invalid because it cannot be unknown", ToolResultDirection.TO_CLIENT)
    
    if ( input_type == "customer_name" and input_value.lower() == "microsoft" ):
        print("customer cannot be microsoft:" + input_value)
        return ToolResult("The value is invalid because you are Microsoft and cannot be your customer.", ToolResultDirection.TO_CLIENT)
    
    # Return the result to the client
    return ToolResult("The value is valid", ToolResultDirection.TO_CLIENT)


# Define the schema for the 'validate_input' tool
_validate_input_tool_schema = {
    "type": "function",
    "name": "validate_input",
    "description": "Validates the input provided by the user. It returns True if the input is valid, otherwise False.",
    "parameters": {
        "type": "object",
        "properties": {
            "input_type": {
                "type": "string",
                "description": "The type of input. Can be 'customer_name', 'demo_product', 'demo_date', or 'meeting_feedback'."
            },
            "input_value": {
                "type": "string",
                "description": "The input that has been provided by the customer."
            }
        },
        "required": ["input_type", "input_value"],
        "additionalProperties": False
    }
}


async def _generate_report_tool(args: Any) -> ToolResult:
    report = {
        "customer_name": args["customer_name"],
        "demo_product": args["demo_product"],
        "demo_date": args["demo_date"],
        "meeting_feedback": args["meeting_feedback"]
    }
    # Return the result to the client
    return ToolResult(report, ToolResultDirection.TO_CLIENT)

# Define the schema for the 'generate_report' tool
_generate_report_tool_schema = {
    "type": "function",
    "name": "generate_report",
    "description": "Generates a JSON report of the customer demo and product attributes derived from the conversation.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer_name": {
                "type": "string",
                "description": "The name of the customer."
            },
            "demo_product": {
                "type": "string",
                "description": "The product that the demo is needed for."
            },
            "demo_date": {
                "type": "string",
                "description": "The date when the demo is needed."
            },
            "meeting_feedback": {
                "type": "string",
                "description": "Feedback from the meeting."
            }
        },
        "required": ["customer_name", "demo_product", "demo_date", "meeting_feedback"],
        "additionalProperties": False
    }
}
