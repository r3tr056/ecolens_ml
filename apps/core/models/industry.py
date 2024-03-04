from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, Session
from apps.core.db import Base

class Process(Base):
    __tablename__ = "processes"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)

    inputs = relationship('Input', back_populate='process')
    outputs = relationship('Output', back_populates='process')

class Input(Base):
    __tablename__ = "inputs"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    quantity = Column(Integer)
    process_id = Column(Integer, ForeignKey('process.id'))

    process = relationship('Process', back_populates='inputs')

class Output(Base):
    __tablename__ = "outputs"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    quantity = Column(Integer)
    process_id = Column(Integer, ForeignKey('process.id'))

    process = relationship('Process', back_populates='outputs')

