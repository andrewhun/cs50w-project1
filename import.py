# ORM version
import os

from sqlalchemy import create_engine, Table, Column, Integer, String, Sequence, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text
import csv


# connect database
engine = create_engine(os.getenv("DATABASE_URL"))

# create (scoped) session
db = scoped_session(sessionmaker(bind=engine))


# declare a mapping
Base = declarative_base()

# create a class which will be mapped to the database
class Book(Base):
	__tablename__ = "Books"
	
	id = Column(Integer, Sequence("Books_id_seq"), primary_key = True)
	isbn = Column(String)
	title = Column(String)
	author = Column(String)
	year = Column(Integer)

	def __repr__(self):
		return ("<Book(isbn = '%s', title = '%s', author = '%s', year = '%i')>" 
		%(self.isbn, self.title, self.author, self.year))


# open books.csv and read it
with open("books.csv") as csv_file:
	csv_reader = csv.reader(csv_file, delimiter = ",")
	line_count = 0
	# iterate through each entry
	for row in csv_reader:
		# skip the headers
		if line_count == 0:
			line_count += 1
		# add each entry to the Books table in the database
		else:
			new_book = Book(isbn = row[0], title = row[1], author = row[2], year = int(row[3]))
			db.add(new_book)

			line_count += 1
# commit the changes in the database
db.commit()
