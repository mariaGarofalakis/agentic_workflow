from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import AgentRunner
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository


class ChatService:
    def __init__(
        self,
        agent: AgentRunner,
        session: AsyncSession,
    ) -> None:
        self.agent = agent
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.message_repository = MessageRepository(session)

    async def reply_stream(
        self,
        *,
        conversation_id: str,
        message: str,
    ) -> AsyncIterator[dict[str, str]]:
        # Step 1: short transaction to claim the conversation
        async with self.session.begin():
            conversation = await self.conversation_repository.claim_for_processing(
                conversation_id
            )

            previous_response_id = conversation.last_response_id

            await self.message_repository.create(
                conversation_id=conversation_id,
                role="user",
                content=message,
            )

        chunks: list[str] = []
        final_response_id: str | None = None

        try:
            # Step 2: run the model outside the DB transaction
            async for event in self.agent.run_stream(
                user_input=message,
                previous_response_id=previous_response_id,
            ):
                if event["type"] == "chunk":
                    chunk = event["content"]
                    chunks.append(chunk)
                    yield {"type": "chunk", "content": chunk}
                elif event["type"] == "completed":
                    final_response_id = event["final_response_id"]

            assistant_content = "".join(chunks)

            # Step 3: short transaction to finalize
            async with self.session.begin():
                await self.message_repository.create(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                    openai_response_id=final_response_id,
                )

                await self.conversation_repository.release_processing(
                    conversation_id,
                    new_last_response_id=final_response_id,
                )

            yield {"type": "done"}

        except Exception:
            # Step 4: ensure processing flag is released on failure
            async with self.session.begin():
                await self.conversation_repository.release_processing(
                    conversation_id,
                    new_last_response_id=None,
                )
            raise