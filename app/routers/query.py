from fastapi import APIRouter, Depends, HTTPException, status
from langchain.vectorstores.base import VectorStoreRetriever

from app.models.schemas import QueryRequest, QueryResponse, GenericErrorResponse, HTTPValidationError
from app.core.dependencies import get_retriever
from app.services.rag import perform_rag_query

router = APIRouter()

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the RAG system",
    description="Sends a query to the RAG system, retrieves relevant documents from the vector store, and generates an answer using the selected LLM.",
    responses={
        422: {"model": HTTPValidationError, "description": "Validation Error"},
        500: {"model": GenericErrorResponse, "description": "Internal Server Error during query processing"},
        503: {"model": GenericErrorResponse, "description": "Vector DB or LLM Service Unavailable"}
    }
)
async def query_rag(
    request: QueryRequest,
    retriever: VectorStoreRetriever = Depends(get_retriever)
):
    """
    Handles RAG queries by:
    1. Receiving the user query and parameters.
    2. Using the injected retriever (which depends on the vector store).
    3. Calling the RAG service to perform retrieval and generation.
    4. Returning the generated answer and source documents.
    """
    if not request.query:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query cannot be empty.")

    try:
        # Adjust the retriever's k based on the request
        retriever.search_kwargs['k'] = request.top_k

        # perform_rag_query is async
        response = await perform_rag_query(
            query=request.query,
            llm_provider=request.llm_provider, # Pass the requested provider (or None for default)
            retriever=retriever
        )
        return response
    except HTTPException as http_exc: # Re-raise known HTTP errors
        raise http_exc
    except Exception as e:
        # Catch-all for unexpected errors during the RAG process
        print(f"Unexpected error during RAG query: {e}")
        # Consider logging the traceback here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the query: {e}"
        ) 