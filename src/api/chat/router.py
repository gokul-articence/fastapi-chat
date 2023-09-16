from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi_pagination import Page, paginate
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.chat.schemas import CreateDirectChatSchema, DisplayDirectChatSchema, MessageSchema
from src.api.chat.services import (
    create_direct_chat,
    get_chat_by_guid,
    get_direct_chat,
    get_user_by_guid,
    send_message_to_chat,
)
from src.database import get_async_session
from src.dependencies import get_current_user
from src.models import Chat, User

# from fastapi_pagination.ext.sqlalchemy import paginate

chat_router = APIRouter(tags=["Chat Management"])


@chat_router.post("/chat/direct/", summary="Get or create a direct chat", response_model=DisplayDirectChatSchema)
async def get_or_create_direct_chat(
    direct_chat_schema: CreateDirectChatSchema,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    # check if another user (recipient) exists
    recipient_user_guid = direct_chat_schema.recipient_user_guid
    recipient_user: User | None = await get_user_by_guid(db_session, user_guid=recipient_user_guid)

    # TODO: must check that recipient user is not the same as initiator
    if not recipient_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="There is no recipient user with provided guid"
        )

    # return chat if already exists
    chat: Chat | None = await get_direct_chat(db_session, initiator_user=current_user, recipient_user=recipient_user)

    if not chat:
        chat: Chat = await create_direct_chat(db_session, initiator_user=current_user, recipient_user=recipient_user)

    return chat


@chat_router.post("/chat/{chat_guid}/message/", summary="Send a message")  #
async def send_message(
    chat_guid: UUID,
    content: Annotated[str, Body(max_length=5000, embed=True)],
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid is not found")

    await send_message_to_chat(db_session, content=content, user_id=current_user.id, chat_id=chat.id)

    return "Message has been sent"


@chat_router.get(
    "/chat/{chat_guid}/messages/", summary="Get user's chat messages", response_model=Page[MessageSchema]
)  #
async def get_user_messages_in_chat(
    chat_guid: UUID,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid does not exist")

    if current_user not in chat.users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You don't have access to this chat")

    # TODO: standard paginate/chat.messages fetches all messages, probably should messages separately
    return paginate(chat.messages)


# TODO: Get users chats
