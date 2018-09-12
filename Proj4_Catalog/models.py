#!/usr/bin/env python
from sqlalchemy import create_engine
from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    '''
    User info class
    '''
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class ProduceCategory(Base):
    '''
    Category class to which an item belongs
    '''
    __tablename__ = 'produce_category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name
        }


class ProduceItem(Base):
    '''
    Class representing a produce item
    '''
    __tablename__ = 'produce_item'

    name = Column(String(80), nullable=False, unique=True)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    expiry_date = Column(Date)
    category_id = Column(Integer, ForeignKey('produce_category.id'))
    category = relationship(ProduceCategory)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def formatted_expiry_date(self):
        """Display date as a formatted string"""
        return self.expiry_date.strftime("%a (%b %d, %Y)")

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'category': self.category.name,
            'expiry_date': self.formatted_expiry_date,
            'description': self.description,
            'user': self.user.name
        }


engine = create_engine('sqlite:///produceinventory.db?check_same_thread=False')
Base.metadata.create_all(engine)
