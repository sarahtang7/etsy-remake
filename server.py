
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, flash

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = 'mysecretkey'

DATABASE_USERNAME = "sarah.tang"
DATABASE_PASSWRD = "4183"
DATABASE_HOST = "34.148.107.47" # change to 34.28.53.86 if you used database 2 for part 2
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/project1"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI, future=True)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
with engine.connect() as conn:
    create_table_command = """
    CREATE TABLE IF NOT EXISTS test (
        id serial,
        name text
    )
    """
    res = conn.execute(text(create_table_command))
    insert_table_command = """INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace')"""
    res = conn.execute(text(insert_table_command))
    # you need to commit for create, insert, update queries to reflect
    conn.commit()


@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request 
    (every time you enter an address in the web browser).
    We use it to setup a database connection that can be used throughout the request.

    The variable g is globally accessible.
    """
    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, this makes sure to close the database connection.
    If you don't, the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
    """
    request is a special object that Flask provides to access web request information:

    request.method:   "GET" or "POST"
    request.form:     if the browser submitted a form, this contains the data in the form
    request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

    See its API: https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
    """

    # DEBUG: this is debugging code to see what request looks like
    print(request.args)


    #
    # example of a database query
    #
    select_query = "SELECT name from test"
    cursor = g.conn.execute(text(select_query))
    names = []
    for result in cursor:
        names.append(result[0])
    cursor.close()

    return render_template('index.html', variable=names) # prints to index.html

    #
    # Flask uses Jinja templates, which is an extension to HTML where you can
    # pass data to a template and dynamically generate HTML based on the data
    # (you can think of it as simple PHP)
    # documentation: https://realpython.com/primer-on-jinja-templating/
    #
    # You can see an example template in templates/index.html
    #
    # context are the variables that are passed to the template.
    # for example, "data" key in the context variable defined below will be 
    # accessible as a variable in index.html:
    #
    #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
    #     <div>{{data}}</div>
    #     
    #     # creates a <div> tag for each element in data
    #     # will print: 
    #     #
    #     #   <div>grace hopper</div>
    #     #   <div>alan turing</div>
    #     #   <div>ada lovelace</div>
    #     #
    #     {% for n in data %}
    #     <div>{{n}}</div>
    #     {% endfor %}
    #
    context = dict(data = names)

    #
    # render_template looks in the templates/ folder for files.
    # for example, the below file reads template/index.html
    #
    return render_template("index.html", **context)

### CUSTOMER LOG IN PAGE
@app.route('/customerlogin')
def customer_login():
    return render_template("customerlogin.html")

### CUSTOMER LOG IN CHECK 
@app.route('/customerlogincheck', methods=['POST'])
def customer_login_check():
    email = request.form['email']
    password = request.form['password']

    query_1 = """SELECT CASE 
                WHEN EXISTS (
                    SELECT * FROM customers
                    WHERE email_address = '"""+email+"""' AND 
                        password = '"""+password+"""'
                ) THEN 1 ELSE 0
                END"""
    cursor = g.conn.execute(text(query_1))
    for result in cursor:
        if result[0] == 1:
            session['email'] = email # store customer as logged in

            query_2 = """SELECT first_name, last_name, customer_id
                        FROM customers
                        WHERE email_address = '"""+email+"""'"""
            cursor = g.conn.execute(text(query_2))
            for result in cursor:
                session['curruser'] = result[0] + " " + result[1]
                session['custID'] = result[2]
            return redirect('/customer')
        else:
            flash('Incorrect login information', 'error')
            return redirect('/customerlogin')
        
    
    cursor.close()

    #print(email)
    #print(password)
    return redirect('/')
    #return render_template("customerlogin.html")

### CUSTOMER PAGE
@app.route('/customer', methods=['POST', 'GET'])
def customer():

    # from added to cart
    if request.method == 'POST':
        prodid = request.form['product_id']

        query_1 = "SELECT MAX(order_id) FROM carts"
        cursor = g.conn.execute(text(query_1))
        new_order_id = ""
        for result in cursor:
            new_order_id = str(int(result[0])+1)
        cursor.close()

        totalcost = float(request.form['price'].replace('$', '')) # initially set to cost of 1
        quantity = int(request.form.get('quantity'))
        if quantity > 1:
            totalcost = totalcost * quantity

        # if product is already in cart
        select_query_2 = """SELECT CASE WHEN EXISTS (
                                SELECT * FROM carts
                                WHERE product_id = '"""+prodid+"""' AND 
                                    customer_id = '"""+session['custID']+"""'
                        ) THEN 1 ELSE 0
                        END"""
        cursor = g.conn.execute(text(select_query_2))

        for result in cursor:
            if result[0] == 1:
                update_order = "UPDATE carts SET quantity = quantity + "+str(quantity)+", total_price = total_price + "+str(totalcost)+"::money WHERE product_id = '"+prodid+"' AND customer_id = '"+session['custID']+"'"
                g.conn.execute(text(update_order))
                g.conn.commit()
            else:
                add_to_order = """INSERT INTO carts (order_id, order_date, shop_id, customer_id, product_id,
                            total_price, quantity) 
                            VALUES ('"""+new_order_id+"""', CURRENT_DATE, '"""+request.form['shop_id']+"""',
                            '"""+session['custID']+"""', '"""+prodid+"""', """+str(totalcost)+""", '"""+str(quantity)+"""')"""
                g.conn.execute(text(add_to_order))
                g.conn.commit()
        cursor.close()

        # increase shop sales_count by quantity
        increase_shop_sales = "UPDATE shops SET sales_count = sales_count + "+str(quantity)+" WHERE shop_id = '"+request.form['shop_id']+"'"
        g.conn.execute(text(increase_shop_sales))
        g.conn.commit()
        
    # get all shops for customer homepage
    select_query = "SELECT shop_name from shops"
    cursor = g.conn.execute(text(select_query))
    shops = []
    for result in cursor:
        shops.append(result[0])
    cursor.close()

    context = dict(shops = shops)

    # get all products info for customer homepage
    select_query = "SELECT url, product_name, shop_name, avg_review, products.review_count, product_id FROM products, shops WHERE products.shop_id = shops.shop_id"
    cursor = g.conn.execute(text(select_query))
    product_imgs = []
    product_names = []
    shop_names = []
    ratings = []
    ratings_num = []
    product_ids = []
    for result in cursor:
        product_imgs.append(result[0])
        product_names.append(result[1])
        shop_names.append(result[2])
        ratings.append(result[3])
        ratings_num.append(result[4])
        product_ids.append(result[5])
    cursor.close()

    print(session['curruser'])
    context = dict(shops=shops, curruser=session['curruser'], product_info={name: {'img': img, 'shop': shop, 'rating': rating, 'numratings': numratings, 'pid': pid} for name, img, shop, rating, numratings, pid in zip(product_names, product_imgs, shop_names, ratings, ratings_num, product_ids)})

    return render_template("customer.html", **context)

### SEARCH ON CUSTOMER PAGE
@app.route('/search', methods=['GET'])
def searchGet_handler():
    value = request.args.get('value')
    if value:
        value = value.lower()

    # get all shops for customer homepage
    select_query = "SELECT shop_name from shops WHERE LOWER(shop_name) LIKE '%"+value+"%'"
    cursor = g.conn.execute(text(select_query))
    shops = []
    for result in cursor:
        shops.append(result[0])
    cursor.close()

    context = dict(shops = shops)

    # match query with shop name
    select_query = """SELECT url, product_name, shop_name, avg_review, products.review_count, product_id 
                        FROM products, shops 
                        WHERE products.shop_id = shops.shop_id AND 
                        (LOWER(shops.shop_name) LIKE '%"""+value+"""%' OR
                        LOWER(products.product_name) LIKE '%"""+value+"""%' OR
                        (SELECT LOWER(product_type) FROM product_types WHERE products.product_type_id = product_types.product_type_id) LIKE '%"""+value+"""%')"""
    cursor = g.conn.execute(text(select_query))
    product_imgs = []
    product_names = []
    shop_names = []
    ratings = []
    ratings_num = []
    product_ids = []
    for result in cursor:
        product_imgs.append(result[0])
        product_names.append(result[1])
        shop_names.append(result[2])
        ratings.append(result[3])
        ratings_num.append(result[4])
        product_ids.append(result[5])
    cursor.close()

    context = dict(shops=shops, product_info={name: {'img': img, 'shop': shop, 'rating': rating, 'numratings': numratings, 'pid': pid} for name, img, shop, rating, numratings, pid in zip(product_names, product_imgs, shop_names, ratings, ratings_num, product_ids)})
    
    return render_template("customer.html", **context)


### PRODUCT PAGES
@app.route('/product/<string:product_id>')
def product(product_id):
    select_query = """SELECT product_name, url, shop_name, shops.average_review, shops.review_count, 
                        shops.sales_count, shops.state, shops.city, shops.country_code, price, product_id, shops.shop_id
                    FROM products, shops 
                    WHERE product_id = '"""+product_id+"""' AND products.shop_id = shops.shop_id"""
    cursor = g.conn.execute(text(select_query))
    product_name = ''
    product_image = ''
    shop_name = ''
    shop_rating = ''
    shop_numreviews = ''
    shop_sales = ''
    shop_loc = ''
    shop_country = ''
    price = ''
    prodid = ''
    shopid = ''
    #product_rating = ''
    #product_numreviews = ''
    for result in cursor:
        product_name = result[0]
        product_image = result[1]
        shop_name = result[2]
        shop_rating = result[3]
        shop_numreviews = result[4]
        shop_sales = result[5]

        shop_loc = result[6]
        if shop_loc == '':
            shop_loc = result[7]

        shop_country = result[8]

        price = result[9]
        prodid = result[10]
        shopid = result[11]
        #product_rating = result[10]
        #product_numreviews = result[11]

    cursor.close()

    select_query_2 = """SELECT CASE 
                        WHEN EXISTS (
                            SELECT * FROM products, downloadable_products
                            WHERE products.product_id = downloadable_products.product_id AND 
                                    products.product_id = '"""+product_id+"""'
                        ) THEN 1 ELSE 0
                        END"""
    cursor = g.conn.execute(text(select_query_2))
    product_substance = ''
    for result in cursor:
        if result[0] == 1:
            product_substance = 'Downloadable Product'
        else:
            product_substance = 'Physical Product'
    cursor.close()

    select_query_3 = """SELECT reviews.rating, reviews.review, review_id FROM products, reviews 
                        WHERE products.product_id = '"""+product_id+"""' AND reviews.product_id = products.product_id"""
    cursor = g.conn.execute(text(select_query_3))
    ratings = []
    reviews = []
    review_ids = []
    for result in cursor:
        ratings.append(result[0])
        reviews.append(result[1])
        review_ids.append(result[2])
    cursor.close()

    context = dict(reviews_info={name: {'rating': rating, 'review': review} for name, rating, review in zip(review_ids, ratings, reviews)})

    # number of product reviews
    select_query_4 = "SELECT COUNT(*) FROM reviews WHERE product_id = '"+product_id+"'"
    cursor = g.conn.execute(text(select_query_4))
    product_numreviews = 0
    for result in cursor:
        product_numreviews = result[0]

    update_query_4 = "UPDATE products SET review_count = "+str(product_numreviews)+" WHERE product_id = '"+product_id+"'"
    g.conn.execute(text(update_query_4))
    g.conn.commit()
    cursor.close()

    # average product rating
    select_query_5 = "SELECT rating FROM reviews WHERE product_id = '"+product_id+"'"
    cursor = g.conn.execute(text(select_query_5))
    all_ratings_sum = 0
    for result in cursor:
        all_ratings_sum += result[0]

    product_rating = all_ratings_sum / product_numreviews

    update_query_5 = "UPDATE products SET avg_review = "+str(product_rating)+" WHERE product_id = '"+product_id+"'"
    g.conn.execute(text(update_query_5))
    g.conn.commit()

    return render_template('product.html', product_name=product_name, product_image=product_image, 
                           shop_name=shop_name, shop_rating=shop_rating, shop_numreviews=shop_numreviews,
                           shop_sales=shop_sales, shop_loc=shop_loc, shop_country=shop_country, price=price,
                           product_substance=product_substance, product_rating=product_rating,
                           product_numreviews=product_numreviews, **context, curruser = session['curruser'],
                           prodid=prodid, shopid=shopid)


### CHECKOUT PAGE
@app.route('/checkout', methods=['POST', 'GET'])
def checkout():

    if request.method == 'POST':

        # move from carts to orders2
        move_to_orders = """INSERT INTO orders2 (order_id, order_date, shop_id, customer_id, product_id, total_price, quantity) 
                            (SELECT * FROM carts WHERE customer_id = '"""+session['custID']+"""')"""
        g.conn.execute(text(move_to_orders))
        g.conn.commit()

        # delete from carts
        delete_from_cart = "DELETE FROM carts WHERE customer_id = '"+session['custID']+"'"
        g.conn.execute(text(delete_from_cart))
        g.conn.commit()

    firstname, lastname = session['curruser'].split()

    select_query_1 = """SELECT product_name, url, quantity, total_price
                        FROM carts NATURAL JOIN products
                        WHERE customer_id = '"""+session['custID']+"""'"""
    cursor = g.conn.execute(text(select_query_1))
    product_names = []
    images = []
    quantities = []
    totalcosts = []
    for result in cursor:
        product_names.append(result[0])
        images.append(result[1])
        quantities.append(result[2])
        totalcosts.append(result[3])
    cursor.close()

    # get card information
    select_query_2 = """SELECT card_number, card_security_code, expiration_date, street_address, city,
                        state, zip_code, country_code
                        FROM customers
                        WHERE customer_id = '"""+session['custID']+"""'"""
    cursor = g.conn.execute(text(select_query_2))
    cardnum = ""
    seccode = ""
    expdate = ""
    street = ""
    city = ""
    state = ""
    zipcode = ""
    countrycode = ""
    for result in cursor:
        cardnum = result[0]
        seccode = result[1]
        expdate = result[2]
        street = result[3]
        city = result[4]
        state = result[5]
        zipcode = result[6]
        countrycode = result[7]
    cursor.close()

    # physical or downloadable products
    select_query_3 = """SELECT CASE WHEN EXISTS (
                            SELECT * FROM physical_products
                            WHERE physical_products.product_id IN (SELECT product_id FROM carts WHERE customer_id = '"""+session['custID']+"""')
                ) THEN 1 ELSE 0
                END"""
    cursor = g.conn.execute(text(select_query_3))
    physical_present = false
    for result in cursor:
        if result[0] == 1: # there are physical products
            physical_present = true
    cursor.close()

    select_query_4 = """SELECT CASE WHEN EXISTS (
                            SELECT * FROM downloadable_products
                            WHERE downloadable_products.product_id IN (SELECT product_id FROM carts WHERE customer_id = '"""+session['custID']+"""')
                ) THEN 1 ELSE 0
                END"""
    cursor = g.conn.execute(text(select_query_3))
    downloadable_present = false
    for result in cursor:
        if result[0] == 1: # there are physical products
            downloadable_present = true
    cursor.close()

    # get total cost of order
    select_query_4 = "SELECT SUM(total_price) FROM carts WHERE customer_id = '"+session['custID']+"'"
    cursor = g.conn.execute(text(select_query_4))
    totalordercost = ''
    for result in cursor:
        totalordercost = result[0]
    cursor.close()

    context = dict(carts_info={name: {'image': image, 'quantity':quantity, 'cost': cost} for name, image, quantity, cost in zip(product_names, images, quantities, totalcosts)})

    return render_template("checkout.html", curruser = session['curruser'], **context, firstname=firstname,
                           lastname=lastname, cardnum=cardnum, seccode=seccode, expdate=expdate,
                           physical_present=physical_present, downloadable_present=downloadable_present, street=street,
                           city=city, state=state, zipcode=zipcode, countrycode=countrycode, totalordercost=totalordercost)


### SHOP PAGE
@app.route('/shop')
def shop():
	# get all products for an individual shop homepage           
    select_query = "SELECT product_id from products WHERE products.shop_id = shops.shop_id"
    cursor = g.conn.execute(text(select_query))
    products = []
    for result in cursor:
        products.append(result[0])
    cursor.close()
    
    context = dict(products = products)
    
	# get all products info for shop homepage
    select_query = "SELECT url, product_name, shop_name, avg_review, products.review_count, product_id FROM products, shops WHERE products.shop_id = shops.shop_id"
    cursor = g.conn.execute(text(select_query))
    product_imgs = []
    product_names = []
    ratings = []
    ratings_num = []
    product_ids = []
    for result in cursor:
        product_imgs.append(result[0])
        product_names.append(result[1])
        ratings.append(result[2])
        ratings_num.append(result[3])
        product_ids.append(result[4])
    cursor.close()

    context = dict(products=products, product_info={name: {'img': img, 'shop': shop, 'rating': rating, 'numratings': numratings, 'pid': pid} for name, img, shop, rating, numratings, pid in zip(product_names, product_imgs, ratings, ratings_num, product_ids)})
    return render_template("shop.html", **context)

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#
'''@app.route('/another')
def another():
    return render_template("another.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
    # accessing form inputs from user
    name = request.form['name']
    
    # passing params in for each variable into query
    params = {}
    params["new_name"] = name
    g.conn.execute(text('INSERT INTO test(name) VALUES (:new_name)'), params)
    g.conn.commit()
    return redirect('/')


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()'''


if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using:

            python server.py

        Show the help text using:

            python server.py --help

        """

        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()
