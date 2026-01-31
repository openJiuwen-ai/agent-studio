from sqlalchemy import BigInteger, Boolean, Integer, JSON, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from openjiuwen_studio.ops.config import settings


# ==================== user 表 ====================
class UserDB(Base, DBFunBase):
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("email", name="uniq_email"),
        UniqueConstraint("user_id", name="uniq_user_id"),
        UniqueConstraint("user_unique_name", name="uniq_user_unique_name"),
    )

    # 主键 
    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(
            Integer, primary_key=True, autoincrement=True, comment="Primary Key ID"
        )
    else:
        id: Mapped[int] = mapped_column(
            BigInteger, primary_key=True, autoincrement=True, comment="Primary Key ID"
        )

    # 必填字段
    user_id_str: Mapped[str] = mapped_column(String(100), comment="USER ID", nullable=False, name="user_id")
    email: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    user_unique_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    username: Mapped[str] = mapped_column(String(128), default="", nullable=False, name="user_name")
    password: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    session_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    role_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_verified: Mapped[int] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[int] = mapped_column(Boolean, default=False, nullable=False)

    # 可选字段
    description: Mapped[str | None] = mapped_column(String(512), default=None, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), default=None, nullable=True, name="icon_uri")
    locale: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True)
    company: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(512), default=None, nullable=True)
    skills: Mapped[list | dict | None] = mapped_column(JSON, default=None, nullable=True)
    _rest_: Mapped[list | dict | None] = mapped_column(JSON, default=None, nullable=True)

    # 时间戳
    user_create_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="create_time")
    user_update_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="update_time")
    user_deleted_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="delete_time")

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"email='{self.email}', "
            f"user_id={self.user_id_str}, "
            f"user_unique_name={self.user_unique_name}, "
            f"user_verified='{self.user_verified}', "
            f"is_active={self.is_active})>"
        )


class SpaceDB(Base, DBFunBase):
    __tablename__ = "space"
    __table_args__ = (
        UniqueConstraint("space_id", name="uniq_space_id"),
        Index("idx_creator_id", "creator_id"),
        Index("idx_owner_id", "owner_id"),
    )

    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(
            Integer, primary_key=True, autoincrement=True, comment="Primary Key ID"
        )
    else:
        id: Mapped[int] = mapped_column(
            BigInteger, primary_key=True, autoincrement=True, comment="Primary Key ID"
        )

    space_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id_str: Mapped[str] = mapped_column(String(100), nullable=False, name="owner_id")
    spacename: Mapped[str | None] = mapped_column(String(200), default=None, nullable=True, name="space_name")
    icon_url: Mapped[str | None] = mapped_column(String(200), default=None, nullable=True, name="icon_uri")
    creator_id_str: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True, name="creator_id")
    description: Mapped[str | None] = mapped_column(String(2000), default=None, nullable=True)
    _rest_: Mapped[list | dict | None] = mapped_column(JSON, default=None, nullable=True)

    # 时间戳
    space_create_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="create_time")
    space_update_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="update_time")
    space_deleted_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="delete_time")

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"id={self.id}, "
            f"space_id={self.space_id}, "
            f"owner_id={self.user_id_str})>"
        )


class SpaceUserDB(Base, DBFunBase):
    __tablename__ = "space_user"
    __table_args__ = (
        UniqueConstraint("space_id", "user_id", name="uniq_space_user"),
        Index("idx_user_id", "user_id"),
    )

    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(
            Integer, primary_key=True, autoincrement=True, comment="Primary Key ID"
        )
    else:
        id: Mapped[int] = mapped_column(
            BigInteger, primary_key=True, autoincrement=True, comment="Primary Key ID"
        )

    space_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="Space ID")
    user_id_str: Mapped[str] = mapped_column(String(100), nullable=False, comment="User ID", name="user_id")
    # 时间戳
    user_create_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="created_time")
    user_update_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, name="update_time")

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"id={self.id}, "
            f"user_id={self.user_id_str})>"
        )

