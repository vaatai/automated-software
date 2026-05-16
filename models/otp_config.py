import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from configs.database import Base


class OTPProvider(str, enum.Enum):
    MAILSLURP = "mailslurp"
    FIVESIM = "5sim"
    PVAPINS = "pvapins"


class OTPType(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class OTPConfig(Base):
    __tablename__ = "otp_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[OTPProvider] = mapped_column(Enum(OTPProvider), nullable=False)
    otp_type: Mapped[OTPType] = mapped_column(Enum(OTPType), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<OTPConfig(id={self.id}, provider={self.provider})>"
