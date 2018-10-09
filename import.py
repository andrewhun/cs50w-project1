import os

from sqlalchemy import create_engine, Table, Column, Integer, String, Sequence, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text
import csv


# connect database
engine = create_engine(os.getenv("DATABASE_URL"))
conn = engine.connect()

# create a catalog of Tables
metadata = MetaData()

# create the books table
books = Table("books", metadata,
	Column("id", Integer, Sequence("Books_id_seq"), primary_key = True),
	Column("isbn", String),
	Column("title", String),
	Column("author", String),
	Column("year", Integer))

# create (scoped) session
db = scoped_session(sessionmaker(bind=engine))


# prepare the SQL statement to be used
s = text("INSERT INTO books(isbn, title, author, year) VALUES(:a, :b, :c, :d)")

#open books.csv and read it
with open("books.csv") as csv_file:
	csv_reader = csv.reader(csv_file, delimiter = ",")
	line_count = 0
	
	# iterate through each entry
	for row in csv_reader:
		
		# skip the headers
		if line_count == 0:
			line_count += 1
		
		# add each entry to the books table in the database
		else:
			conn.execute(s, a = row[0], b = row[1], c = row[2], d = row[3])
			line_count += 1
