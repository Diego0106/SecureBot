import logging

import azure.functions as func  # Import Azure Functions for handling HTTP requests
from openai import AzureOpenAI  # Import AzureOpenAI client
import requests  # Import requests library for making HTTP requests

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    req_body = req.get_json()  # Parse the JSON body of the HTTP request
    ip = req_body.get('ip')  # Extract the IP address from the request
    idioma = req_body.get('idioma')  # Extract the language from the request

    def verificar_ip_virustotal(ip):
        url = f'https://www.virustotal.com/api/v3/ip_addresses/{ip}'  # API URL for VirusTotal IP address lookup
        headers = {
            'x-apikey': 'REDACTED'  # API key for VirusTotal (Sensitive information redacted)
        }

        try:
            respuesta = requests.get(url, headers=headers)  # Make the request to VirusTotal
            respuesta.raise_for_status()  # Ensure the request was successful

            datos = respuesta.json()  # Parse the JSON response

            # Process the data as needed. This is just an example.
            resultado = {
                'reputacion': datos['data']['attributes']['last_analysis_stats'],  # Reputation stats
                'detalles': datos['data']['attributes']['last_analysis_results']  # Detailed analysis results
            }
            return True, resultado
        except requests.RequestException as e:
            return False, f"Error making request to VirusTotal API: {e}"

    es_segura, resultado = verificar_ip_virustotal(ip)  # Verify the IP address with VirusTotal
    reputacion_general = resultado['reputacion']  # Extract general reputation
    reputacion_str = ", ".join([f"{key}: {value}" for key, value in reputacion_general.items()])  # Format reputation string

    # Create a client for Azure OpenAI
    client = AzureOpenAI(
                    api_version="2023-12-01-preview",
                    azure_endpoint="https://bitchatgpt.openai.azure.com/",
                    api_key="PASS",
                )

    # Create a chat completion using the IP analysis
    completion = client.chat.completions.create(
            model="yourModelName",
            messages=[
                {
                "role": "system",
                "content": "You are a bot specialized in analyzing IPs to determine risk and conclude if the IP is safe."
                },
                {
                "role": "user",
                "content": "IP: "+ip+"||\n"+"Analysis: "+reputacion_str+"||\n"+" Question: "+". Answer in "+idioma
                }
            ])
    resp = completion.choices[0].message.content  # Extract the completion response

    if resp:
        return func.HttpResponse(resp)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
