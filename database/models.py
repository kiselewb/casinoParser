from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import Integer, String, DateTime, Boolean, func, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime


class Base(DeclarativeBase):
    pass


class ParseResult(Base):
    __tablename__ = 'parse_results'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_methods: Mapped[dict] = mapped_column(JSONB, default=dict)
    site_url: Mapped[str] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str] = mapped_column(String(255), nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False, index=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index('ix_site_latest', 'site_id', 'is_latest'),
        Index('ix_site_date', 'site_id', 'parsed_at'),
    )


# class PaymentMethod(Base):
#     """Методы пополнения (история)"""
#     __tablename__ = 'payment_methods'
#
#     id = Column(Integer, primary_key=True)
#     parse_result_id = Column(Integer, nullable=False, index=True)
#     site_id = Column(String(50), nullable=False, index=True)
#
#     method_name = Column(String(100), nullable=False)
#     min_amount = Column(Float, nullable=False)
#     max_amount = Column(Float, nullable=True)
#     currency = Column(String(10), default='EUR')
#
#     # Для аналитики
#     created_at = Column(DateTime, default=datetime.utcnow)
#
#     __table_args__ = (
#         Index('ix_payment_parse_result', 'parse_result_id'),
#     )