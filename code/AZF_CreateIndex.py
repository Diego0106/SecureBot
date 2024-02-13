import logging

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from PyPDF2 import PdfReader
import io, base64, os, re
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswParameters,
    PrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
)
from azure.search.documents.indexes.models import AnalyzeTextOptions

model = "text-embedding-ada-002"
modelEngine="<you model name>"

#Credenciales azure cognitive search
vector_store_address = "https://<you endpoint>.search.windows.net"
vector_store_password = "<you pass>"


# Configura las credenciales Azure Blob Storage
account_name = '<you account name>'
account_key = '<you api>'
container_name = '<you container name>'

# Parametros config Chunk
MAX_SECTION_LENGTH = 3000
SENTENCE_SEARCH_LIMIT = 200
SECTION_OVERLAP = 200

#Cliente Azure OpenAI
client = AzureOpenAI(
            api_version="2023-12-01-preview",
            azure_endpoint="https://<you endpoint name>.openai.azure.com/",
            api_key="<you api>",
        )

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    req_body = req.get_json()

    index_name = req_body.get('index')
    appNames = req_body.get('files')
    appFilesName = appNames.split('|')

    if index_name and appNames:
        index_client = SearchIndexClient(vector_store_address, AzureKeyCredential(vector_store_password))

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="es.microsoft"),
            SearchField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                                    hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
                                    vector_search_dimensions=1536, vector_search_configuration="default"),
            SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="sourcepage", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="sourcefile", type=SearchFieldDataType.String, filterable=True, facetable=True),
        ]

        vector_search = VectorSearch(
            algorithm_configurations=[
                VectorSearchAlgorithmConfiguration(
                    name="default",
                    kind="hnsw",
                    hnsw_parameters=HnswParameters(metric="cosine")
                )
            ]
        )

        semantic_config = SemanticConfiguration(
            name="default",
            prioritized_fields=PrioritizedFields(
                title_field=None,
                prioritized_content_fields=[SemanticField(field_name="content")]
                )
        )

        # Create the semantic settings with the configuration
        semantic_settings = SemanticSettings(configurations=[semantic_config])

        # Create the search index with the semantic settings
        index = SearchIndex(name=index_name, fields=fields,
                            vector_search=vector_search, semantic_settings=semantic_settings)
        result = index_client.create_index(index)
        #result = index_client.create_or_update_index(index)
        print(f' {result.name} created')

        # Crea el cliente de servicio Blob
        blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)

        # Obtiene el cliente del contenedor
        container_client = blob_service_client.get_container_client(container_name)

        # Lista todos los blobs en el contenedor
        blobs = container_client.list_blobs()

        # Función para extraer el texto de un archivo PDF
        def extract_text_from_pdf(blob_client):
            offset = 0
            page_map = []
            blob_data = blob_client.download_blob()
            pdf_reader = PdfReader(io.BytesIO(blob_data.readall()))
            pages = pdf_reader.pages
            for page_num, p in enumerate(pages):
                page_text = p.extract_text()
                page_map.append((page_num, offset, page_text))
                offset += len(page_text)
            return page_map

        def split_text(page_map):
            # Definición de constantes
            SENTENCE_ENDINGS = [".", "!", "?"]  # Marcadores de fin de oración
            WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]  # Separadores de palabras

            # Mensaje informativo
            print(f"Splitting '{filename}' into sections")

            # Función para encontrar la página en función del desplazamiento
            def find_page(offset):
                num_pages = len(page_map)
                for i in range(num_pages - 1):
                    if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                        return i
                return num_pages - 1

            # Concatenación de todo el texto de las páginas
            all_text = "".join(p[2] for p in page_map)
            length = len(all_text)
            start = 0
            end = length

            # Ciclo para dividir el texto en secciones
            while start + SECTION_OVERLAP < length:
                last_word = -1
                end = start + MAX_SECTION_LENGTH

                if end > length:
                    end = length
                else:
                    # Intentar encontrar el final de la oración
                    while end < length and (end - start - MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                        if all_text[end] in WORDS_BREAKS:
                            last_word = end
                        end += 1
                    if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                        end = last_word  # Retroceder al menos para mantener una palabra completa
                if end < length:
                    end += 1

                # Intentar encontrar el comienzo de la oración o al menos un límite de palabra completa
                last_word = -1
                while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SENTENCE_SEARCH_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
                    if all_text[start] in WORDS_BREAKS:
                        last_word = start
                    start -= 1
                if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                    start = last_word
                if start > 0:
                    start += 1

                # Extracción de la sección de texto y búsqueda de la página correspondiente
                section_text = all_text[start:end]
                yield (section_text, find_page(start))

                # Manejo especial si la sección termina con una tabla sin cerrar
                last_table_start = section_text.rfind("<table")
                if (last_table_start > 2 * SENTENCE_SEARCH_LIMIT and last_table_start > section_text.rfind("</table")):
                    print(f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}")
                    start = min(end - SECTION_OVERLAP, start + last_table_start)
                else:
                    start = end - SECTION_OVERLAP

            # Si hay una sección final sin solapamiento, se agrega
            if start + SECTION_OVERLAP < end:
                yield (all_text[start:end], find_page(start))

        def filename_to_id(file):
            filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", file)
            filename_hash = base64.b16encode(file.encode('utf-8')).decode('ascii')
            return f"file-{filename_ascii}-{filename_hash}"

        def compute_embedding(text):
            return client.embeddings.create(input=text, model="TestEmbeding").data[0].embedding

        def create_sections(file, page_map):
            file_id = filename_to_id(file)
            for i, (content, pagenum) in enumerate(split_text(page_map)):
                section = {
                    "id": f"{file_id}-page-{i}",
                    "content": content,
                    "category": "información de PDF",
                    "sourcepage": blobURL,
                    "sourcefile": file
                }
                section["embedding"] = compute_embedding(content)
                yield section

        def index_sections(file, sections):
            print(f"Indexing sections from '{file}' into search index '{index_name}'")
            search_client = SearchClient(vector_store_address,index_name,AzureKeyCredential(vector_store_password))

            i = 0
            batch = []
            for s in sections:
                batch.append(s)
                i += 1
                if i % 1000 == 0:
                    results = search_client.upload_documents(batch)
                    succeeded = sum([1 for r in results if r.succeeded])
                    print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
                    batch = []

            if len(batch) > 0:
                results = search_client.upload_documents(batch)
                succeeded = sum([1 for r in results if r.succeeded])
                print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")

        # Procesa cada archivo PDF y extrae el texto
        for blob in blobs:
            if blob.name.lower().endswith('.pdf'):
                blob_client = container_client.get_blob_client(blob.name)
                if blob.name in appFilesName:
                    map = extract_text_from_pdf(blob_client)
                    blobURL = blob_client.url
                    filename = blob.name
                    split_text(map)
                    filename_to_id(filename)
                    section = create_sections(filename,map)
                    index_sections(filename,section)


    if index_name:
        return func.HttpResponse(f"La informacion se ha cargado con exito")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
