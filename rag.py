import cohere
import os
import hnswlib
import json
import uuid
from typing import List, Dict
from unstructured.partition.html import partition_html
from unstructured.chunking.title import chunk_by_title
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import requests

#Set Google API key and Custom Search Engine ID
google_api_key = "AIzaSyBY_E4r5d-y-06hCuPneLVaLoBHt5XXLbI"
custom_search_engine_id = "570f458fa5be541ce"

#Set Cohere API Key
os.environ["COHERE_API_KEY"] = "rEDlJlDVQ8BKoOJidO6LbaE16anJ4LeBQZED7Swr"

#Instantiate the cohere client
co = cohere.Client(os.environ["COHERE_API_KEY"])

#Documents class to store indexed documents
class Documents:
    """
    A class representing a collection of documents.

    Parameters:
    sources (list): A list of dictionaries representing the sources of the documents. Each dictionary should have 'title' and 'url' keys.

    Attributes:
    sources (list): A list of dictionaries representing the sources of the documents.
    docs (list): A list of dictionaries representing the documents, with 'title', 'content', and 'url' keys.
    docs_embs (list): A list of the associated embeddings for the documents.
    retrieve_top_k (int): The number of documents to retrieve during search.
    rerank_top_k (int): The number of documents to rerank after retrieval.
    docs_len (int): The number of documents in the collection.
    index (hnswlib.Index): The index used for document retrieval.

    Methods:
    load(): Loads the data from the sources and partitions the HTML content into chunks.
    embed(): Embeds the documents using the Cohere API.
    index(): Indexes the documents for efficient retrieval.
    retrieve(query): Retrieves documents based on the given query.

    """

    def __init__(self, sources: List[Dict[str, str]]):
        self.sources = sources
        self.docs = []
        self.docs_embs = []
        self.retrieve_top_k = 10
        self.rerank_top_k = 3
        self.load()
        self.embed()
        self.index()

    def load(self) -> None:
        """
        Loads the documents from the sources and chunks the HTML content.
        """
        print("Loading documents...")

        for source in self.sources:
            try:
                elements = partition_html(url=source["url"])
                chunks = chunk_by_title(elements)
                for chunk in chunks:
                    self.docs.append(
                        {
                            "title": source["title"],
                            "text": str(chunk),
                            "url": source["url"],
                        }
                    )
            except:
                pass

    def embed(self) -> None:
        """
        Embeds the documents using the Cohere API.
        """
        print("Embedding documents...")

        batch_size = 90
        self.docs_len = len(self.docs)

        for i in range(0, self.docs_len, batch_size):
            batch = self.docs[i : min(i + batch_size, self.docs_len)]
            texts = [item["text"] for item in batch]
            docs_embs_batch = co.embed(
                texts=texts, model="embed-english-v3.0", input_type="search_document"
            ).embeddings
            self.docs_embs.extend(docs_embs_batch)

    def index(self) -> None:
        """
        Indexes the documents for efficient retrieval.
        """
        print("Indexing documents...")

        self.idx = hnswlib.Index(space="ip", dim=1024)
        self.idx.init_index(max_elements=self.docs_len, ef_construction=512, M=64)
        self.idx.add_items(self.docs_embs, list(range(len(self.docs_embs))))

        print(f"Indexing complete with {self.idx.get_current_count()} documents.")

    def retrieve(self, query: str) -> List[Dict[str, str]]:
        """
        Retrieves documents based on the given query.

        Parameters:
        query (str): The query to retrieve documents for.

        Returns:
        List[Dict[str, str]]: A list of dictionaries representing the retrieved documents, with 'title', 'text', and 'url' keys.
        """
        docs_retrieved = []
        query_emb = co.embed(
            texts=[query], model="embed-english-v3.0", input_type="search_query"
        ).embeddings

        doc_ids = self.idx.knn_query(query_emb, k=self.retrieve_top_k)[0][0]

        docs_to_rerank = []
        for doc_id in doc_ids:
            docs_to_rerank.append(self.docs[doc_id]["text"])

        rerank_results = co.rerank(
            query=query,
            documents=docs_to_rerank,
            top_n=self.rerank_top_k,
            model="rerank-english-v2.0",
        )

        doc_ids_reranked = []
        for result in rerank_results:
            doc_ids_reranked.append(doc_ids[result.index])

        for doc_id in doc_ids_reranked:
            docs_retrieved.append(
                {
                    "title": self.docs[doc_id]["title"],
                    "text": self.docs[doc_id]["text"],
                    "url": self.docs[doc_id]["url"],
                }
            )

        return docs_retrieved
    

from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
 
def extract_search_query(argument):
    """
    Given an input argument, extracts a relevant search query using GPT-4

    Parameters: Original argument generated pre-RAG

    Returns: 
    str: Search query, that will be used for the google search API
    """
    chat = ChatOpenAI(temperature=0, model_name='gpt-4', openai_api_key="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")

    messages = [
        HumanMessage(
            content=f"""Given a certain argument, you are supposed to find evidence online supporting that argument using a search engine.
            \n
            Argument - {argument}
            \n
            What search query would you use for this task? Provide just the search query and nothing else.
            """
        ),
    ]

    response = chat(messages)

    return str(response.content)


def retrieve_docs(docs, response):
    """
    Retrieves documents based on the search queries in the response.

    Parameters:
    response: The response object containing search queries.

    Returns:
    List[Dict[str, str]]: A list of dictionaries representing the retrieved documents.

    """
    # Get the query(s)
    queries = []
    for search_query in response.search_queries:
        queries.append(search_query["text"])

    # Retrieve documents for each query
    retrieved_docs = []
    for query in queries:
        retrieved_docs.extend(docs.retrieve(query))

    # # Uncomment this code block to display the chatbot's retrieved documents
    # print("DOCUMENTS RETRIEVED:")
    # for idx, doc in enumerate(retrieved_docs):
    #     print(f"doc_{idx}: {doc}")
    # print("\n")

    return retrieved_docs

def generate_response(message, documents):
    """
    Generates a response to the user's message.

    Parameters:
    message (str): The user's message.

    Yields:
    Event: A response event generated by the chatbot.

    Returns:
    List[Dict[str, str]]: A list of dictionaries representing the retrieved documents.

    """
    # Generate search queries (if any)
    response = co.chat(message=message, search_queries_only=True)

    # If there are search queries, retrieve documents and respond
    if response.search_queries:
        print("Retrieving information...")

        documents = retrieve_docs(response)

        response = co.chat(
            message=message,
            documents=documents,
            conversation_id=str(uuid.uuid4()),
            stream=True,
        )
        for event in response:
            yield event

    # If there is no search query, directly respond
    else:
        response = co.chat(
            message=message,
            conversation_id=str(uuid.uuid4()),
            stream=True
        )
        for event in response:
            yield event

#Function to perform google search and return the urls of search results
def google_search(query, api_key=google_api_key, cx=custom_search_engine_id, limit=10):
    """
    Performs a Google Search using the Custom Search JSON API and return the links of the search results
    """
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'key': api_key,
        'cx': cx,
    }
    response = requests.get(base_url, params=params)

    #Retrieve search results for the given query
    search_results = response.json().get('items', [])

    #Extract the url links of the webpages
    search_results_urls = [result['link'] for result in search_results]

    return search_results_urls

def rewrite_with_evidence(argument,evidence):
    """
    Rewrites the original argument such that it contains in-line citations for the evidence that was generated using RAG
    """

    chat = ChatOpenAI(temperature=0, model_name='gpt-4', openai_api_key="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")

    messages = [
        HumanMessage(
            content=f"""Given an argument and evidence supporting that argument, you have to rewrite the argument citing the evidence in necessary places. Make sure to avoid adding, removing or changing the words in the existing argument significantly and just having inline citations wherever appropriate to cite the evidence. I will provide you an example first, so that you can understand better.
            \n
            Example:
            \n
            Argument: Good morning, esteemed colleagues. I stand before you today to unequivocally refute the notion that vaccines cause autism. This assertion is not only scientifically unfounded but also deeply harmful to public health. Over two decades of rigorous research have consistently demonstrated that vaccines do not increase the risk of autism or any other developmental disorders. The overwhelming consensus among medical experts is that vaccines are safe and effective, and they play a crucial role in protecting our children from serious, and potentially life-threatening diseases.
            \n
            Evidence: Here is some evidence to support the argument that vaccines do not cause autism:
            - One study found that the risk of autism in vaccinated children is the same as that in unvaccinated children [1]
            - There was no association found between the development of autism and factors such as the age at the time of vaccination, the time since vaccination, or the date of vaccination [1]
            - A 1998 hypothesis proposed that the measles-mumps-rubella vaccine may cause autism due to persistent measles virus infection in the gastrointestinal tract [2]. However, early studies did not find support for this hypothesis. Moreover, a review by the Institute of Medicine in 2001 concluded that there is no evidence supporting a causal relationship between the measles-mumps-rubella vaccine and autistic spectrum disorder [2].

            Therefore, multiple rigorous studies and reviews have found no evidence supporting a link between vaccines and autism.

            [1] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5789217/
            [2]https://www.chop.edu/centers-programs/vaccine-education-center/vaccines-and-other-conditions/vaccines-autism

            \n
            Rewritten Argument: Here is the rewritten argument citing the evidence in necessary places:

            Good morning, esteemed colleagues. I stand before you today to unequivocally refute the notion that vaccines cause autism. This assertion is not only scientifically unfounded but also deeply harmful to public health. Over two decades of rigorous research have consistently demonstrated that vaccines do not increase the risk of autism or any other developmental disorders 1. One study found that the risk of autism in vaccinated children is the same as that in unvaccinated children 1. There was no association found between the development of autism and factors such as the age at the time of vaccination, the time since vaccination, or the date of vaccination 1. A 1998 hypothesis proposed that the measles-mumps-rubella vaccine may cause autism due to persistent measles virus infection in the gastrointestinal tract 2. However, early studies did not find support for this hypothesis. Moreover, a review by the Institute of Medicine in 2001 concluded that there is no evidence supporting a causal relationship between the measles-mumps-rubella vaccine and autistic spectrum disorder 2. The overwhelming consensus among medical experts is that vaccines are safe and effective, and they play a crucial role in protecting our children from serious, and potentially life-threatening diseases 1.

            1: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5789217/ 2: https://www.chop.edu/centers-programs/vaccine-education-center/vaccines-and-other-conditions/vaccines-autism

            Now, you have to rewrite the argument using the evidence given below:
            \n
            Argument: {argument}
            \n
            Evidence: {evidence}

            Rewritten Argument:
            """
        ),
        # HumanMessage(
        #     content="Translate this sentence from English to French. I love programming."
        # ),
    ]

    response = chat(messages)

    return response.content

def cohere_rag_pipeline(argument):

    """
    Combines all the different steps involved in the RAG pipeline and executes them sequentially to return the final rewritten argument
    """

    #Extract search query from the argument using GPT-4
    search_query = extract_search_query(argument)
    print(search_query,'\n\n')

    #Perform google search using the extracted search query
    search_results = google_search(argument, google_api_key, custom_search_engine_id)
    print(search_results,'\n\n')
    sources = [{"title":f"Link{i+1}","url":search_results[i]} for i in range(len(search_results))]
    print(sources,'\n\n')

    #Create indexed docs using the obtained search results
    documents = Documents(sources)

    #Use the indexed docs to generate a response from Cohere Chat
    prompt = f"Provide evidence to support this argument: {argument}"
    response = generate_response(prompt, documents)
    print(response,'\n\n')

    #Re-write the RAG response in proper citation format

    #Re-write the original argument with in-line citations using GPT-4
    rewritten_argument = rewrite_with_evidence(argument, response)

    #Return the rewritten argument
    return rewritten_argument