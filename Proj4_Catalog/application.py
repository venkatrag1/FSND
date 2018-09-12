#!/usr/bin/env python
# Flask base CRUD imports
from flask import Flask
from flask import render_template, url_for, request, redirect, flash

# DB imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

# Flask auth imports
from flask import session as login_session, make_response, jsonify
import json
import random
import string
import httplib2
import requests
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

from models import Base, ProduceCategory, ProduceItem, User
import datetime

from functools import wraps

app = Flask(__name__)

engine = create_engine('sqlite:///produceinventory.db?check_same_thread=False')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

EXPIRY_WINDOW_DAYS = 7


def login_required(f):
    """Decorator to redirect to login page if not logged
    with appropriately credentials"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session and 'user_id' in login_session:
            return f(*args, **kwargs)
        else:
            flash("You are not allowed to access there without logging"
                  " in as the appropriate user.")
            return redirect(url_for('showLogin'))

    return decorated_function


# Routes
@app.route('/login')
def showLogin():
    """Route for Login page showing google sign in button"""
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """POST endpoint invoked using ajax callback with the
    one-time authorization code"""
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    # print("Got access token: %s" % (access_token))
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        login_session['access_token'] = credentials.access_token
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output


@app.route('/gdisconnect')
def gdisconnect():
    """Disconnect logged in user and route to homepage"""
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    # print("Revoking token: %s" % (access_token))
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    del login_session['access_token']
    del login_session['gplus_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    if result['status'] == '200':
        flash("You have successfully been logged out.")
        return redirect(url_for('inventoryHome'))
    else:
        flash("You were not logged in")
        return redirect(url_for('inventoryHome'))


@app.route('/api/v1/producecategories/')
def getCategoriesJSON():
    """API endpoint to get all category names"""
    ordered_categories = get_categories_in_name_order(
        session.query(ProduceCategory).all())
    return jsonify([c.serialize for c in ordered_categories])


@app.route('/')
@app.route('/produce/')
def inventoryHome():
    """Home page showing category bar on left and items expiring within next
     EXPIRY_WINDOW_DAYS"""
    ordered_categories = get_categories_in_name_order(
        session.query(ProduceCategory).all())
    end_date = datetime.date.today() + datetime.timedelta(
        days=EXPIRY_WINDOW_DAYS)
    items_expiring_soon = session.query(ProduceItem).filter(
        ProduceItem.expiry_date <= end_date)
    ordered_items = get_items_in_date_order(items_expiring_soon)
    return render_template('home.html',
                           categories=ordered_categories,
                           items=ordered_items,
                           expiry_window=EXPIRY_WINDOW_DAYS)


@app.route('/api/v1/produce/')
def inventoryHomeJSON():
    """API endpoint returning Items expiring in next EXPIRY_WINDOW_DAYS"""
    end_date = datetime.date.today() + datetime.timedelta(
        days=EXPIRY_WINDOW_DAYS)
    items_expiring_soon = session.query(ProduceItem).filter(
        ProduceItem.expiry_date <= end_date)
    ordered_items = get_items_in_date_order(items_expiring_soon)
    return jsonify([i.serialize for i in ordered_items])


@app.route('/produce/all/')
@app.route('/produce/all/items/')
def produceCategoryAll():
    """Special keyword 'all' in the category slot which displays items
     of all categories"""
    ordered_categories = get_categories_in_name_order(
        session.query(ProduceCategory).all())
    items = session.query(ProduceItem).all()
    ordered_items = get_items_in_date_order(items)
    return render_template('producecategory.html',
                           categories=ordered_categories,
                           selected_category_name='All',
                           items=ordered_items)


@app.route('/api/v1/produce/all/')
@app.route('/api/v1/produce/all/items/')
def produceCategoryAllJSON():
    """API endpoint that returns items belonging to all categories"""
    items = session.query(ProduceItem).all()
    ordered_items = get_items_in_date_order(items)
    return jsonify([i.serialize for i in ordered_items])


@app.route('/produce/<string:category_name>/')
@app.route('/produce/<string:category_name>/items/')
def produceCategory(category_name):
    """
    Show items belonging to a particular category
    :param category_name: Name of the item category such as Dairy, Veggies...
    :return: producecategory page with appropriate items
    """
    ordered_categories = get_categories_in_name_order(
        session.query(ProduceCategory).all())
    selected_category = session.query(ProduceCategory).filter_by(
        name=category_name).one_or_none()
    if not selected_category:
        flash('Invalid category')
        return redirect(url_for('inventoryHome'))
    items = session.query(ProduceItem).filter_by(
        category_id=selected_category.id)
    ordered_items = get_items_in_date_order(items)
    return render_template('producecategory.html',
                           categories=ordered_categories,
                           selected_category_name=selected_category.name,
                           items=ordered_items)


@app.route('/api/v1/produce/<string:category_name>/')
@app.route('/api/v1/produce/<string:category_name>/items/')
def produceCategoryJSON(category_name):
    """
    API endpoint returning items of particular category
    :param category_name: Name of the item category such as Dairy, Veggies...
    :return: JSON objects of the corresponding items
    """
    selected_category = session.query(ProduceCategory).filter_by(
        name=category_name).one_or_none()
    if not selected_category:
        return jsonify({})
    items = session.query(ProduceItem).filter_by(
        category_id=selected_category.id)
    ordered_items = get_items_in_date_order(items)
    return jsonify([i.serialize for i in ordered_items])


@app.route('/produce/new/', methods=['GET', 'POST'])
@app.route('/produce/<string:selected_category_name>/new/',
           methods=['GET', 'POST'])
@login_required
def newProduceItem(selected_category_name='Other'):
    """
    Form to create a new item
    :param selected_category_name: Category to create the item under
    :return: Returns to appropriate category page
    """
    category_query = session.query(ProduceCategory)
    if request.method == 'POST':
        category = category_query.filter_by(
            name=request.form['category']).one()
        expiry_date = datetime.datetime.strptime(request.form['expiry_date'],
                                                 '%Y-%m-%d')
        newItem = ProduceItem(name=request.form['name'],
                              description=request.form['description'],
                              expiry_date=expiry_date,
                              category_id=category.id,
                              user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("New item created!")
        return redirect(url_for('produceCategory',
                                category_name=category.name))
    else:
        categories = category_query.all()
        try:
            selected_category = category_query.filter_by(
                name=selected_category_name).one()
        except NoResultFound:
            if selected_category_name == 'Other':
                selected_category = ProduceCategory(
                    name=selected_category_name)
                session.add(selected_category)
                session.commit()
                return redirect(url_for('newProduceItem'))
            else:
                raise NoResultFound("Invalid: %s" % (selected_category_name))
        return render_template('newproduceitem.html',
                               categories=categories,
                               selected_category=selected_category)


@app.route('/produce/<string:category_name>/<string:item_name>/')
def produceItem(category_name, item_name):
    """
    Show item details
    :param category_name: Category such as Dairy, Veggies etc
    :param item_name: Item name such as Milk
    :return: Item detail page
    """
    category = session.query(ProduceCategory).filter_by(
        name=category_name).one_or_none()
    item = session.query(ProduceItem).filter_by(name=item_name).one_or_none()
    if item and category:
        return render_template('produceitem.html', category=category,
                               item=item)
    flash('Invalid route specified')
    return redirect(url_for('inventoryHome'))


@app.route('/api/v1/produce/<string:category_name>/<string:item_name>/')
def produceItemJSON(category_name, item_name):
    """
    API endpoint for getting individual item detail
    :param category_name: Category such as Dairy, Veggies etc
    :param item_name: Item name such as Milk
    :return: Serialized JSON corresponding to item
    """
    item = session.query(ProduceItem).filter_by(name=item_name).one_or_none()
    if item:
        return jsonify(item.serialize)
    return jsonify({})


@app.route('/produce/<string:category_name>/<string:item_name>/edit/',
           methods=['GET', 'POST'])
@login_required
def editProduceItem(category_name, item_name):
    """
    Edit existing item
    :param category_name: Category such as Dairy, Veggies etc
    :param item_name: Item name such as Milk
    :return: Return to category view after editing
    """
    categories = session.query(ProduceCategory).all()
    selected_category = session.query(ProduceCategory).filter_by(
        name=category_name).one()
    editedItem = session.query(ProduceItem).filter_by(name=item_name).one()
    if login_session['user_id'] != editedItem.user_id:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to edit items created by a different user.');}</script><body"\
               "onload='myFunction()'>"

    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['expiry_date']:
            editedItem.expiry_date = datetime.datetime.strptime(
                request.form['expiry_date'], '%Y-%m-%d')
        if request.form['category']:
            selected_category = session.query(ProduceCategory).filter_by(
                name=request.form['category']).one()
            editedItem.category_id = selected_category.id
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect(url_for('produceItem',
                                category_name=selected_category.name,
                                item_name=editedItem.name))
    else:
        return render_template('editproduceitem.html',
                               categories=categories,
                               selected_category=selected_category,
                               item=editedItem)


@app.route('/produce/<string:category_name>/<string:item_name>/delete/',
           methods=['GET', 'POST'])
@login_required
def deleteProduceItem(category_name, item_name):
    """
    Delete an item
    :param category_name: Category such as Dairy, Veggies etc
    :param item_name: Item name such as Milk
    :return: Return to home page on delete
    """
    category = session.query(ProduceCategory).filter_by(
        name=category_name).one()
    item = session.query(ProduceItem).filter_by(name=item_name).one()
    if login_session['user_id'] != item.user_id:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to delete items created by a different user.');}</script>" \
               "<body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(item)
        flash("Item deleted")
        session.commit()
        return redirect(url_for('produceCategory',
                                category_name=category.name))
    else:
        return render_template('deleteproduceitem.html',
                               category=category, item=item)


@app.route('/api/v1/items/')
def produceItemsJSON():
    """API endpoint to get all items in database"""
    items = session.query(ProduceItem).all()
    return jsonify([i.serialize for i in items])


# Helpers
def get_categories_in_name_order(categories):
    """
    Helper routine to sort list of categories by their name.
    'All' is at start, 'Other' is at end and remaining are arranged
    in alphabetical order
    :param categories: list of category objects
    :return: ordered list of category objects
    """
    ordered_categories = sorted([x for x in categories if x.name != 'Other'],
                            key=lambda ProduceCategory: ProduceCategory.name)
    ordered_categories.append(session.query(ProduceCategory).filter_by(
        name='Other').one())
    return ordered_categories


def get_items_in_date_order(items):
    """
    Helper routine to sort list of items in increasing order of expiration date
    :param items: list of item objects
    :return: ordered list of item objects
    """
    return sorted(items,
                  key=lambda ProduceItem: ProduceItem.expiry_date)


# User credentials methods

def createUser(login_session):
    """Create a new user"""
    newUser = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    """Get user object for a given primary key"""
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    """Get user id for Email"""
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except NoResultFound:
        return None


if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'my_secret_key'
    app.run(host='0.0.0.0', port=5000)
