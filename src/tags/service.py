from fastapi import status
from fastapi.exceptions import HTTPException
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.books.service import BookService
from src.db.models import Tag

from .schemas import TagCreateModel

book_service = BookService()


server_error = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Something went wrong'
)


class TagService:
    async def get_all_tags(self, session: AsyncSession):
        statement = select(Tag).order_by(desc(Tag.created_at))

        result = await session.exec(statement)

        return result.all()

    async def get_tag_by_uid(self, tag_uid: str, session: AsyncSession):
        statement = select(Tag).where(Tag.uid == tag_uid)
        result = await session.exec(statement)

        return result.first()

    async def add_tag(self, tag_data: TagCreateModel, session: AsyncSession):
        statement = select(Tag).where(Tag.name == tag_data.name)
        result = await session.exec(statement)
        tag = result.first()

        if tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        new_tag_dict = tag_data.model_dump()
        new_tag = Tag(**new_tag_dict)
        new_tag.name = tag_data.name

        session.add(new_tag)
        await session.commit()

        return new_tag

    async def update_tag(
        self, tag_uid, tag_update_data: TagCreateModel, session: AsyncSession
    ):
        tag = await self.get_tag_by_uid(tag_uid, session)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        update_data_dict = tag_update_data.model_dump()

        for k, v in update_data_dict.items():
            setattr(tag, k, v)

            await session.commit()
            await session.refresh(tag)

        return tag

    async def delete_tag(self, tag_uid: str, session: AsyncSession):
        """Delete a tag"""

        tag = await self.get_tag_by_uid(tag_uid, session)

        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        await session.delete(tag)
        await session.commit()
