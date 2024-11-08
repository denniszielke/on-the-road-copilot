#!/bin/bash

set -e

SERVICE_NAME="$1"

if [ "$SERVICE_NAME" == "" ]; then
echo "No phase name provided - aborting"
exit 0;
fi

AZURE_ENV_NAME="$2"

if [ "$AZURE_ENV_NAME" == "" ]; then
echo "No environment name provided - aborting"
exit 0;
fi

if [[ $SERVICE_NAME =~ ^[a-z0-9]{3,12}$ ]]; then
    echo "service name $SERVICE_NAME is valid"
else
    echo "service name $SERVICE_NAME is invalid - only numbers and lower case min 5 and max 12 characters allowed - aborting"
    exit 0;
fi

RESOURCE_GROUP="rg-$AZURE_ENV_NAME"

if [ $(az group exists --name $RESOURCE_GROUP) = false ]; then
    echo "resource group $RESOURCE_GROUP does not exist"
    error=1
else   
    echo "resource group $RESOURCE_GROUP already exists"
    LOCATION=$(az group show -n $RESOURCE_GROUP --query location -o tsv)
fi

OPENAI_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.CognitiveServices/accounts" --query "[0].name" -o tsv)
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
COSMOSDB_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.DocumentDB/databaseAccounts" --query "[0].name" -o tsv)

echo "openai name: $OPENAI_NAME"
echo "cosmosdb name: $COSMOSDB_NAME"