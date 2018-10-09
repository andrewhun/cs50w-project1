
# SQLAlchemy ORM version
import os

from flask import Flask, flash, redirect, session, request, render_template, jsonify, abort
from flask_session import Session
from sqlalchemy import create_engine, Table, Column, Integer, String, Sequence, MetaData, or_, and_
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text
from helpers import login_required
from werkzeug.security import check_password_hash, generate_password_hash
import requests

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))

# create a session for the database
db = scoped_session(sessionmaker(bind=engine))


# ORM-version
# create a declarative mapping
Base = declarative_base()
# create a class which will be connected to the users table in the database
class User(Base):
	__tablename__ = "users"

	id = Column(Integer, Sequence("users_id_seq"))
	username = Column(String, primary_key = True)
	hashed = Column(String)

	def __repr__(self):
		return ("<User(username='%s', hashed='%s')>" %(self.username, self.hashed))

# create a class which will be connected to the books table in the database
class Book(Base):
	__tablename__ = "books"
	
	id = Column(Integer, Sequence("Books_id_seq"), primary_key = True)
	isbn = Column(String)
	title = Column(String)
	author = Column(String)
	year = Column(Integer)

	def __repr__(self):
		return ("<Book(isbn = '%s', title = '%s', author = '%s', year = '%i')>" 
		%(self.isbn, self.title, self.author, self.year))

# create a class which will be conneted to the comments table
class Comment(Base):
	__tablename__ = "comments"

	id = Column(Integer, Sequence("comments_id_seq"), primary_key = True)
	book_isbn = Column(String)
	username = Column(String)
	message = Column(String)
	rating = Column(Integer)

	def __repr__(self):
		return("<Comment(book_isbn = '%s', username = '%s', message = '%s', rating = '%i')>"
			%(self.book_isbn, self.username, self.message, self.rating))

@app.route("/")
@login_required
def index():
	'''Show main page to the user'''	
	return render_template("index.html")


@app.route("/register", methods = ["GET", "POST"])
def register():
	'''Register new user'''
	
	# If the user reaches the route via the GET method render the register form for them.
	if request.method == "GET":
		return render_template("register.html")
	# If the user reaches the route via the POST method process their input
	else:
		# prepare the variables
		username = request.form.get("reg_username")
		hashed = generate_password_hash(request.form.get("reg_password"))		
		
		# username already in the database
		if db.query(User).filter_by(username = username).first() != None:
			return jsonify({"error": "1"})

		# success
		else:
			# add the new user's username and hashed password to the users table			
			new_user = User(username = username, hashed = hashed)
			db.add(new_user)
			db.commit()

		# redirect the user to the login page
		return redirect("/login")

@app.route("/login", methods = ["GET", "POST"])
def login():
	'''Log user in'''
	
	# Forget any user_id
	session.clear()
	# If the user reaches the route via the GET method, render the login form for them
	if request.method == "GET":
		return render_template("login.html")
	# If the user reaches the route via the POST method, process their input
	else:
		# prepare variables to use
		login_user = request.form.get("login_user")
		login_pw = request.form.get("login_pw")
		# Query the database for the user
		my_user = db.query(User).filter_by(username = login_user).first()
		
		# Username is not in the database
		if my_user == None:
			return jsonify({"error": "1"})
		# Invalid password
		elif not check_password_hash(my_user.hashed, login_pw):			
			return jsonify({"error": "2"})
		# Success
		else:
			# Log user in by adding their ID to the session
			session["user_id"] = my_user.id			
		db.commit()
		# Redirect user to the main page
		return redirect("/")

@app.route("/logout")
def logout():
	'''Log user out'''

	# Forget any user_id
	session.clear()

	# Redirect user to the register form
	return redirect("/")

@app.route("/search")
# @login_required
def search():
	'''Search for books that match the query'''
	
	# put the user's search terms into a variable
	q = request.args.get("q")
	
	# ORM version
	# format q to match LIKE syntax
	q = '%' + q + '%'
	
	# query the database using the search term
	my_books = db.query(Book).filter(or_(Book.isbn.ilike(q), Book.author.ilike(q), Book.title.ilike(q))).all()[0:9]
	
	# format results as a list of dictonaries so that jsonify does not choke
	my_list = []
	for book in my_books:
		my_list.append({'isbn': book.isbn, 'title': book.title, 'author': book.author})

	db.commit()
	
	# return query results in a json format
	return jsonify(my_list)

# @app.route("/book", methods = ["GET", "POST"]) (I will leave this here just in case I need it)
@app.route("/book/<string:isbn>", methods = ["GET", "POST"])
@login_required 
def book(isbn):
	'''Show info and comments of the selected book, allow users to comment'''
	
	# the user reached the route via the GET method
	if request.method == "GET":
		
		# ORM version
		# grab the selected book and the comments that belong to it
		my_book = db.query(Book).filter_by(isbn = isbn).first()
		my_comments = db.query(Comment).filter_by(book_isbn = isbn).all()
		db.commit()
		# get the Goodreads ratings data through the API
		goodreads = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "4NAeoxfZQc0UXGetcSEzEA", "isbns": isbn})
		ratings_count = goodreads.json()["books"][0]["work_ratings_count"]
		average_rating = goodreads.json()["books"][0]["average_rating"]
		# return the information, ratings and reviews of the selected book
		return render_template("book.html", isbn = my_book.isbn, author = my_book.author,
		 title = my_book.title, year = my_book.year, my_comments = my_comments, j = len(my_comments),
		 ratings_count = ratings_count, average_rating = average_rating)
	# the user reached the route via the POST method
	else:
		
		# get the user's comment and rating
		user_comment = request.form.get("user_comment")
		rating = request.form.get("rating")
		
		# see if the user has commented on the selected book yet
		my_user = db.query(User).filter_by(id = session["user_id"]).first()
		result = db.query(Comment).filter(and_(Comment.username == my_user.username, Comment.book_isbn == isbn)).all()
		if len(result) != 0:
			return jsonify({"error": "1"})
		else:
			# add the comment to the comments table
			new_comment = Comment(book_isbn = isbn, username = my_user.username, message = user_comment, rating = rating)
			db.add(new_comment)
			db.commit()

		return redirect("/book/"+isbn)

@app.route("/api/<string:isbn>", methods = ["GET"])
@login_required
def api(isbn):
	'''Return a JSON object with relevant info on the selected book'''
	
	# find out if the book is in the database
	my_book = db.query(Book).filter_by(isbn = isbn).first()
	db.commit()
	# book is not found in the database
	if my_book == None:
		# return a 404 error
		abort(404)
	# book is found in the database
	else:
		#grab the relevant info from Goodreads API
		goodreads = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "4NAeoxfZQc0UXGetcSEzEA", "isbns": isbn})
		review_count = goodreads.json()["books"][0]["work_reviews_count"]
		average_rating = goodreads.json()["books"][0]["average_rating"]
		
		# arrange the data in a dictionary
		details = {'title': my_book.title, 'author': my_book.author, 'year': my_book.year,
		'isbn': my_book.isbn, 'review_count': review_count, 'average_score': average_rating}
		# return the data in a JSON format
		return jsonify(details)
		
