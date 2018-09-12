#!/usr/bin/env python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, ProduceCategory, ProduceItem, User

import datetime
engine = create_engine('sqlite:///produceinventory.db?check_same_thread=False')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create admin user
Admin = User(name="Admin", email="admin@produceInventory.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/"'
                     '"18debd694829ed78203a5a36dd364160_400x400.png')
session.add(Admin)
session.commit()

session.add(Admin)
session.commit()


# Default category
default_category = ProduceCategory(name='Other', user=Admin)

session.add(default_category)
session.commit()

# Items for Dairy
category = ProduceCategory(name="Dairy", user=Admin)

session.add(category)
session.commit()

item1 = ProduceItem(user=Admin, name="Milk", description="2% reduced fat",
                    expiry_date=datetime.date(2018, 9, 9), category=category)

session.add(item1)
session.commit()

# Items for Poultry
category = ProduceCategory(name="Poultry", user=Admin)

session.add(category)
session.commit()


item1 = ProduceItem(user=Admin, name="Egg", description="Cage-free",
                    expiry_date=datetime.date(2018, 9, 11), category=category)

session.add(item1)
session.commit()

# Items for Veggies
category = ProduceCategory(name="Veggies", user=Admin)

session.add(category)
session.commit()


item1 = ProduceItem(user=Admin, name="Spinach", description="Packets",
                    expiry_date=datetime.date(2018, 9, 19), category=category)

session.add(item1)
session.commit()

item2 = ProduceItem(user=Admin, name="Carrot", description="Organic",
                    expiry_date=datetime.date(2018, 9, 21), category=category)

session.add(item2)
session.commit()

# Items for Grains
category = ProduceCategory(name="Grains", user=Admin)

session.add(category)
session.commit()

item1 = ProduceItem(user=Admin, name="Bread", description="Multi-grain",
                    expiry_date=datetime.date(2018, 9, 19), category=category)
session.add(item1)
session.commit()

# Items for Fruits
category = ProduceCategory(name="Fruits", user=Admin)

session.add(category)
session.commit()

print("Added items")
