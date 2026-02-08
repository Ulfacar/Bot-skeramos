import ssl as _ssl

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings

connect_args = {}
if settings.database_ssl:
    ssl_ctx = _ssl.create_default_context()
    connect_args["ssl"] = ssl_ctx

engine = create_async_engine(settings.database_url, echo=settings.debug, connect_args=connect_args)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
