# Produce Tracker
## Introduction
This website is used to catalog produce items into various pre-defined categories.
All items and categories can be viewed by public.
Users will have to login using their Google Account to be able to add new items,
or edit/delete items that they have previously created.
Users cannot modify items created by other users, and also the POST/DELETE pages
are protected from direct URL access as well.
The item list GET is also exposed as JSON API end point.

## Running the app
First run the `populate_database.py` to create the prefilled produce_inventory.db
to create the categories and prefill items.
```
./populate_database.py
```

The actual Flask webserver is invoked by running the `application.py` file.
The server is served on localhost port 5000.

```
./application.py
```

The Homepage at `http://localhost:5000/` displays the items expiring/expired
within the next 7 days along with the available categories.

Item list within a category can be viewed by selecting the corresponding category.
Individual items can then be selected from this view.

Items can be edited/deleted from item level view and new items can be added from
the category level view, upon logging in.

Items are always sorted in order of expiration date, with the latest date first.

## API endpoints

All the API endpoints are prefixed with `/api/v1` and only unauthenticated GET
APIs are currently available

#### /api/v1/items/
This endpoint returns all the available items in the inventory, in a JSON format.

Eg:
```
curl -X GET 'localhost:5000/api/v1/items/'
```

Kindly note the trailing slash

#### /api/v1/producecategories/

This endpoint returns all the available categories

#### /api/v1/produce/<string:category_name>/<string:item_name>/

This endpoint allows us to view an individual item, selected by category_name and item_name









