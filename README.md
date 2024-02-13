# SecureBot

Welcome to SecureBot, a pioneering RAG chatbot developed for **The AI Chat App** Hackathon. This innovative solution is crafted using Microsoft Copilot Studio, integrating Power Platform components and Azure Functions to harness Python's versatility for dynamic code execution. At its core, SecureBot specializes in cybersecurity, offering real-time insights and answers drawn from an extensive knowledge base of over 80 documents, including podcasts, videos, websites, and books.

Utilizing Azure Cognitive Search, SecureBot excels in retrieving precise information, ensuring users have access to the latest and most relevant cybersecurity advice and data. Whether you're a professional in the field, a student learning about cybersecurity, or simply curious, SecureBot is designed to assist you with accurate information retrieval, leveraging AI to navigate through a vast array of resources efficiently.

Join us in exploring the future of cybersecurity with SecureBot, where AI meets expertise to provide you with reliable, cutting-edge information.

# How does RAG work?

A RAG bot is short for Retrieval-Augmented Generation. This means that we are going to "augment" the knowledge of our LLM with new information that we are going to pass in our prompt. We first vectorize all the text that we want to use as "augmented knowledge" and then look through the vectorized text to find the most similar text to our prompt. We then pass this text to our LLM as a prefix.

![RAG](https://github.com/diegocodx/SecureBot/assets/158774382/24ac157a-fc59-43a5-bb39-bbd9b43a52e4)

### **RAG improvements for Spanish data**

`search_client = SearchClient(vector_store_address, index_name, AzureKeyCredential(vector_store_password))
r = search_client.search(search_text=query_text,
                        query_language="es-es", 
                        vector=compute_embedding(query_text),
                        select=["content", "sourcefile"],
                        top_k=3,
                        vector_fields="embedding", 
                        search_mode="all")`

This code snippet contributes to enhancing search results in Spanish by leveraging Azure Cognitive Search in conjunction with a hybrid search approach. Initially, a search client is created, configuring it to access the vector store and index specified. Subsequently, a search query is executed, where the query_text parameter is set to Spanish ("es-es"), indicating the language of the query. Additionally, the vector parameter incorporates computed embedding vectors, which capture the semantic meaning of the query text, thus improving the relevance of search results. By utilizing a hybrid method that combines traditional text-based search with semantic understanding through embedding vectors, the search algorithm can deliver more accurate and contextually relevant results, particularly beneficial when dealing with Spanish language queries where semantic nuances play a crucial role in search relevance.

To obtain answers in English, I used prompting techniques so that the model gave me answers in the language that the user was speaking. This is done automatically in the azure function triggered by a power automate flow that translates the question into Spanish using Azure AI translator.

### **Architecture**

<img width="490" alt="Architecture" src="https://github.com/diegocodx/SecureBot/assets/158774382/ac603d71-ba04-4778-ae44-6161bb821315">

SecureBot leverages Microsoft Copilot Studio, integrating Power Platform components and Azure Functions. These components work in harmony to provide real-time insights and answers from an extensive knowledge base of over 80 documents, including podcasts, videos, websites, and books. The architecture includes:

- Copilot Studio: The development environment where SecureBot is crafted.
- Power Automate: Integrated with Copilot Studio for automation workflows and trigger Azure functions and APIS.
- Azure Functions: The dynamic code execution engine.
- Python: Used for its versatility in SecureBot’s code execution.
- Azure Translator Service: Allow language translation.
- Azure Cognitive Search: The powerhouse for precise information retrieval.
- Blob Storage: Stores data, including content like PDFs and videos.

### **Power Automate Flows**

This flow is activated from Copilot Studio and receives the question and response language as input.
It is used to execute an Azure Function that executes the python code that calls the Azure AI search and Azure OpenAI services.
If the language is English, the prompt is translated into Spanish with Azure Translator to send it as input to the Azure Function.

<img width="254" alt="PA_FlowRetrival" src="https://github.com/diegocodx/SecureBot/assets/158774382/f3c8a380-8f61-4349-909d-9d242b60d7af">
<img width="697" alt="Flow-Translate" src="https://github.com/diegocodx/SecureBot/assets/158774382/85856a89-0ad7-4b76-bd62-502b5ea07035">

This flow allows the IP analysis function to be executed. An azure function is executed and receives the IP and language as input.

<img width="285" alt="PA_FlowAnalyzeIP" src="https://github.com/diegocodx/SecureBot/assets/158774382/20251271-1ffa-4fb7-8cc4-ec059cfc2aaf">


You can follow me on [LinkedIn](https://www.linkedin.com/in/da-ramos/)
