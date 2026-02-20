"""
Chat API routes for Report Designer agent interaction.
"""

from fastapi import APIRouter, HTTPException, Query

from ..models import ChatRequest, ChatResponse, ConversationHistoryResponse
from ..deps import CurrentUser
from ..agent import chat_with_agent
from ...workspace import (
    get_template,
    get_or_create_conversation,
    get_conversation_history,
)

router = APIRouter(tags=["Chat"])


@router.post("/templates/{template_id}/chat", response_model=ChatResponse)
async def chat_endpoint(
    template_id: str,
    request: ChatRequest,
    current_user: CurrentUser,
) -> ChatResponse:
    """
    Chat with the AI agent about a template.

    The agent can:
    - Retrieve data from transcripts, financials, and stock prices
    - Create and organize report sections
    - Configure subsections with data sources
    - Set instructions for content generation
    - Save generated content versions

    Conversation history is automatically persisted per template.
    """
    # Verify template exists
    template = get_template(template_id)
    if "error" in template:
        raise HTTPException(status_code=404, detail=template["error"])

    # Get agent response
    try:
        result = await chat_with_agent(
            template_id=template_id,
            user_message=request.message,
            focus_section_id=request.focus_section_id,
            focus_subsection_id=request.focus_subsection_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return ChatResponse(
        response=result["response"],
        tool_calls=result["tool_calls"],
        conversation_id=result["conversation_id"],
    )


@router.get("/templates/{template_id}/chat/history", response_model=ConversationHistoryResponse)
def get_chat_history_endpoint(
    template_id: str,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200, description="Max messages to return"),
) -> ConversationHistoryResponse:
    """
    Get conversation history for a template.

    Returns messages in chronological order (oldest first).
    """
    # Verify template exists
    template = get_template(template_id)
    if "error" in template:
        raise HTTPException(status_code=404, detail=template["error"])

    # Get or create conversation
    conversation = get_or_create_conversation(template_id)
    history = get_conversation_history(conversation["id"], limit=limit)

    return ConversationHistoryResponse(
        conversation_id=conversation["id"],
        messages=history,
    )
