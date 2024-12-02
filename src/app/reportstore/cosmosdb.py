import os
import logging
import json
from logging import INFO
from typing import Any
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
import azure.cosmos.exceptions as exceptions
from typing import List, Optional, Union, TYPE_CHECKING
from backend.rtmt import RTMiddleTier, Tool, ToolResult, ToolResultDirection

class CosmosDBStore:
    db_host: str
    db_name: str
    container_name: str
    cosmos_client: CosmosClient
    logging.basicConfig(level=logging.INFO)

    def load_from_file(self, file_path: str):
        with open(file_path, "r") as file:
            return json.load(file)

    def insert_departments(self, container_name: str, departments: List[any]):
        self.logger.info("Inserting departments into database")
        try:
            container = self.db.get_container_client(container_name)
            for department in departments:
                container.create_item( department )
        except exceptions.CosmosResourceExistsError as e:
            print("Item already exists.")
            logging.error(e)
        except exceptions.CosmosHttpResponseError as e:
            print("Request to the Azure Cosmos database service failed.")
            logging.error(e)

    def create_container(self, container_name: str):
        self.logger.info("Creating container in database")
        templates_path = os.path.join(os.path.dirname(__file__), 'templates.json')
        templates = self.load_from_file(templates_path)
        try:
            container = self.db.get_container_client(container_name)
            self.db.create_container(id=container_name, partition_key=PartitionKey(path="/department"))
            print(f"Container created or returned: {container.id}")
            self.insert_departments(container_name, templates)
        except exceptions.CosmosResourceExistsError as e:
            print("Container already exists.")
            logging.error(e)
            self.insert_departments(container_name, templates)
        except exceptions.CosmosHttpResponseError as e:
            print("Request to the Azure Cosmos database service failed.")
            logging.error(e)

    def __init__(self, db_host: str, db_name:str, container_name: str):
        self.logger = logging.getLogger("cosmosdb")
        self.logger.info("Initializing CosmosDBStore")
        self.db_host = db_host
        self.db_name = db_name
        self.container_name = container_name
        self.cosmos_client = CosmosClient(db_host, DefaultAzureCredential())
        self.db = self.cosmos_client.get_database_client(db_name)
        container = self.db.get_container_client(container_name)
        self.create_container(container_name)

    
    async def get_schema_from_database(self, department: str):
        self.logger.info("Getting schema from database")
        try:
            container = self.cosmos_client.get_container_client(self, self.container_name)
        
            query = "SELECT * FROM c WHERE c.department = @department"
            parameters = [{"name": "@department", "value": department}]
            items = container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True)
        
            items_list = [item async for item in items]
            
            return items_list
        except exceptions.CosmosHttpResponseError:
            print("Request to the Azure Cosmos database service failed.")

    async def write_report(args: Any) -> ToolResult:
        report = {
            "customer_name": args["customer_name"],
            "demo_product": args["demo_product"],
            "demo_date": args["demo_date"],
            "meeting_feedback": args["meeting_feedback"]
        }
        # Return the result to the client
        return ToolResult(report, ToolResultDirection.TO_CLIENT)

    async def get_schema(self, args: Any) -> ToolResult:
        return await self.get_schema_from_database(args["department"])
            
