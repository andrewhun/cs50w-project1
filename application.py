
import os

from flask import Flask, flash, redirect, session, request, render_template, jsonify, abort
from flask_session import Session
from sqlalchemy import create_engine, Table, Column, Integer, String, Sequence, MetaData, or_
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
conn = engine.connect()

# create  catalog of Tables
metadata = MetaData()

# create the users table
users = Table('users', metadata,
	Column('id', Integer, Sequence('users_id_seq')),
	Column('username', String, primary_key = True),
	Column('hashed', String))

# create the books table
books = Table("books", metadata,
	Column("id", Integer, Sequence("Books_id_seq"), primary_key = True),
	Column("isbn", String),
	Column("title", String),
	Column("author", String),
	Column("year", Integer))

# create the comments table
comments = Table("comments", metadata,
	Column("id", Integer, Sequence("comments_id_seq"), primary_key = True),
	Column ("book_isbn", String),
	Column("username", String),
	Column("message", String),
	Column("rating", Integer))

# create a session for the database
db = scoped_session(sessionmaker(bind=engine))


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
		s = text("SELECT * FROM users WHERE username = :username")
		result = db.execute(s, {'username': username}).fetchall()
		if len(result) != 0:
			return jsonify({"error": "1"})
		
		# success
		else:
			
			# add the new user's username and hashed password to the users table
			i = text("INSERT INTO users(username, hashed) VALUES(:username, :hashed)")
			db.execute(i,{'username': username, 'hashed': hashed})
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
		s = text("SELECT * FROM users WHERE username = :login_user")
		result = db.execute(s, {'login_user': login_user}).fetchone()
		
		# Username is not in the database
		if result == None:
			return jsonify({"error": "1"})
		
		# Invalid password
		elif not check_password_hash(result['hashed'], login_pw):			
			return jsonify({"error": "2"})
		
		# Success
		else:
			
			# Log user in by adding their ID to the session	
			session["user_id"] = result['id']
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

	# query the database using the search term
	s = text("SELECT * FROM books WHERE isbn LIKE :q OR title LIKE :q or author LIKE :q LIMIT 10")
	my_books = db.execute(s, {'q': ('%' + q + '%')}).fetchall()
	
	# format results as a dictionary (so that jsonify does not choke)
	my_list = []
	for row in my_books:
		my_list.append({'isbn': row[1], 'title': row[2], 'author': row[3]})
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
		
		# find the book the user has selected
		s = text("SELECT * FROM books WHERE isbn = :isbn")
		my_book = db.execute(s, {'isbn': isbn}).fetchone()
		
		# find all ratings and reviews for the selected book
		t = text("SELECT username, message, rating FROM comments WHERE book_isbn = :isbn")
		my_comments = db.execute(t, {'isbn': isbn}).fetchall()
		
		# get the Goodreads ratings data through the API
		goodreads = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "4NAeoxfZQc0UXGetcSEzEA", "isbns": isbn})
		ratings_count = goodreads.json()["books"][0]["work_ratings_count"]
		average_rating = goodreads.json()["books"][0]["average_rating"]
		db.commit()
		
		# return the information, ratings and reviews of the selected book
		return render_template("book.html", isbn = my_book['isbn'], author = my_book['author'],
		 title = my_book['title'], year = my_book['year'], my_comments = my_comments, j = len(my_comments),
		 ratings_count = ratings_count, average_rating = average_rating)
	
	# the user reached the route via the POST method
	else:
		
		# get the user's comment
		user_comment = request.form.get("user_comment")
		rating = request.form.get("rating")
		
		# get the user's username
		a = text("SELECT username FROM users WHERE id = :iden")
		my_user = db.execute(a, {'iden': session["user_id"]}).fetchone()
		
		# find out if the user left a comment on the selected book already
		b = text("SELECT * FROM comments WHERE username = :my_user AND book_isbn = :isbn")
		result = db.execute(b, {'my_user': my_user['username'], 'isbn': isbn}).fetchall()
		
		# the user did leave a comment already
		if len(result) != 0:
			return jsonify({"error": "1"})
		
		# the user did not leave a comment yet
		else:
			
			# add the comment to the comments table
			ins = text("INSERT INTO comments(book_isbn, username, message, rating) VALUES(:isbn, :username, :message, :rating)")
			db.execute(ins, {'isbn': isbn, 'username': my_user['username'], 'message': str(user_comment), 'rating': rating})
		db.commit()
		
		# refresh the page for the user
		return redirect("/book/"+isbn)

@app.route("/api/<string:isbn>", methods = ["GET"])
@login_required
def api(isbn):
	'''Return a JSON object with relevant info on the selected book'''
	
	# find out if the book is in the database
	s = text("SELECT * FROM books WHERE isbn = :isbn")
	my_book = db.execute(s, {'isbn': isbn}).fetchone()
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
		details = {'title': my_book["title"], 'author': my_book["author"], 'year': my_book["year"],
		'isbn': my_book["isbn"], 'review_count': review_count, 'average_score': average_rating}
		
		# return the data in a JSON format
		return jsonify(details)
		
