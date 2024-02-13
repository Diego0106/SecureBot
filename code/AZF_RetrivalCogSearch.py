import logging
import azure.functions as func  # Import Azure Functions
import os
from openai import AzureOpenAI  # Import OpenAI Azure client
from azure.core.credentials import AzureKeyCredential  # Credential handling for Azure services
from azure.search.documents import SearchClient  # Azure Cognitive Search client

model = "text-embedding-ada-002"  # Model identifier for embeddings

# Azure Cognitive Search credentials and endpoint (Sensitive information redacted)
vector_store_address = "https://endpointname.search.windows.net"
vector_store_password = "PASS"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    req_body = req.get_json()  # Parse the JSON body of the HTTP request
    query_text = req_body.get('pregunta')  # Extract 'question' from the request
    index_name = req_body.get('index')  # Extract 'index' from the request
    idioma = req_body.get('idioma')  # Extract 'language' from the request

    # Create a client for Azure OpenAI
    client = AzureOpenAI(
                api_version="2023-12-01-preview",
                azure_endpoint="https://endpointname.openai.azure.com/",
                api_key="PASS",
            )

    def compute_embedding(text):
        # Generate embeddings for the input text
        return client.embeddings.create(input=text, model="TestEmbeding").data[0].embedding

    # Create a search client for querying Azure Cognitive Search
    search_client = SearchClient(vector_store_address, index_name, AzureKeyCredential(vector_store_password))

    # Perform a search query
    r = search_client.search(search_text=query_text,
                            query_language="es-es",  # Language set to Spanish (Spain)
                            vector=compute_embedding(query_text),  # Use computed embedding for the search
                            select=["content", "sourcefile"],  # Select fields to return
                            top_k=3,  # Return top 3 results
                            vector_fields="embedding",  # Specify vector field
                            search_mode="all")

    context = []
    listFiles = []

    # Process search results
    for dat in r:
        context.append(dat['content'])  # Add content to context list
        listFiles.append(dat['sourcefile'])  # Add source file names to listFiles list

    # Deduplicate and format source file names
    source = ' // '.join(list(set(listFiles)))
    source = source.replace(".pdf", "")  # Remove '.pdf' extension from file names

    # Create a chat completion using the context and question
    completion = client.chat.completions.create(
        model="modelName",
        messages=[
            {
            "role": "system",
            "content": "Eres un asistente que se especializa en ayudar a las personas con sus dudas sobre ciberseguridad, proporcionando respuestas informadas y consejos prácticos de manera amable. Su enfoque abarca desde la protección de la privacidad y la seguridad de datos hasta la prevención de fraudes y ataques cibernéticos. Está diseñado para ser accesible para usuarios de todos los niveles de habilidad, ofreciendo clarificaciones cuando sea necesario y adaptando sus respuestas para ser lo más útiles y amables posible."
            },
            {
            "role": "user",
            "content": "Context 1: "+context[0]+"||\n"+" Context 2: "+context[1]+"||\n"+" Context 3: "+context[2]+"||\n"+" Question: "+query_text+". Answer in "+idioma
            }
        ])

    infoResp = completion.choices[0].message.content  # Extract the completion response
    resp = source+"|"+infoResp  # Format the final response

    # Return the response if there's a query text, else return a default message
    if query_text:
        return func.HttpResponse(resp)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
