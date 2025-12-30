from sqlalchemy import (
    Column, BigInteger, Integer, String,
    Float, DateTime
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = {"extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node = Column(String(50))
    session = Column(BigInteger)
    seq = Column(Integer)

    temp = Column(Float)
    hum = Column(Float)

    lat = Column(Float)
    lon = Column(Float)

    flame = Column(Integer)
    smoke = Column(Integer)

    gateway = Column(String(50))
    rssi = Column(Integer)
    snr = Column(Float)

    received_at = Column(DateTime)
    

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(BigInteger, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    organization = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)