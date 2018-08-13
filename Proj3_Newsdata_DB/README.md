# Log Analysis Project

## Introduction
The file newsdata.py connects to a postgres database named `news` which contains three tables namely `authors`, 
`articles` and `log`, and fetches the answers to the following questions using a single query in each case.

1. What are the most popular three articles of all time? 
2. Who are the most popular article authors of all time?
3. On which days did more than 1% of requests lead to errors?

## Generating the necessary views
The database is generated on the VM using the `newsdata.sql` file that was provided.
```
> psql -d news -f newsdata.sql
```

We then connect to the database in `psql` command line and inspect the structure of each of the tables, using `\d` to determine their relationships.

```
> psql news
news=> \d articles;
news=> \d authors;
news=> \d log;
```

We notice that the `author` column in `articles` table is a foreign key that references the primary key
`id` of the `authors` table. 

In the case of `log` table, there is no explicit foreign key relationship. However, the `slug` column in `articles` table
has a unique key constraint and it matches the text following `/article/` in the `log` table.

So, let us define our first view, namely `articles_log_view` to represent this join of `articles` and `log` using a match between the `slug`
and `path`.

If you have a script that contains the create view statements called
create_views.sql, then import the views from the
command line by typing:
psql -d news -f create_views.sql
Or, in the main python script insert:
create_views = open("create-views.sql").read()
and,
cursor.execute(create_views)

#### articles_log_view
```
news=> CREATE VIEW articles_log_view AS
news-> SELECT log.*, articles.author, articles.title, articles.slug, articles.lead, articles.body, articles.time AS article_time, articles.id AS articles_id
news-> FROM log RIGHT JOIN articles ON log.path = '/article/'  || articles.slug;

```
This view will help us answer the first two questions by helping us join all the three tables.


To answer the third question, we need to know the percentage of access for each date that resulted in error.
Towards, this end we will generate two views, representing number of errors by date, and number of total accesses by date,
and perform a join of these two views to compute the proportion of errors.


#### log_access_daily_totals_view
```
news=> CREATE VIEW log_access_daily_totals_view AS
news-> SELECT DATE(time), COUNT(*) as num FROM log GROUP BY DATE(time);

```


#### log_access_daily_num_errors_view
```
news=> CREATE VIEW log_access_daily_num_errors_view AS
news-> SELECT DATE(time), COUNT(*) as num FROM log
news-> WHERE status = '404 NOT FOUND' GROUP BY DATE(time);

```


#### log_access_daily_error_percent_view
```
news=> CREATE VIEW log_access_daily_error_percent_view AS
news-> SELECT log_access_daily_num_errors_view.date, (100.0 * log_access_daily_num_errors_view.num / log_access_daily_totals_view.num) AS daily_error_percent
news-> FROM log_access_daily_num_errors_view JOIN log_access_daily_totals_view ON log_access_daily_num_errors_view.date = log_access_daily_totals_view.date;

```

From this view we can extract the days with error percent > 1 % using the `WHERE` clause.


## Running the program 

The shebang is set to pick up python2.7 as the interpreter, so the file `newsdata.py` can be invoked from terminal 
directly after setting the exec permission
```
> chmod +x newsdata.py
> ./newsdata.py 
```
This will invoke the three functions that print the output to the three questions. 

## Program Design

All the three methods are decorated using the `pg_connection` function which takes care of opening and closing the 
database connection and passes the cursor to the functions for executing, fetching results and displaying them as needed.

All the functions are written as to avoid sql injection possiblity by not using string interpolation and instead passing 
variable int/decimal parameters using the query paramters. 

#### get_most_popular_articles(cursor, n)
This function groups the contents of `articles_log_view` by article title and orders them in decreasing order of number 
of accesses, limiting results to top n most popular articles. The results are filtered by status OK and method = GET 
just to be sure.

#### get_most_popular_authors(cursor)
This merges the `articles_log_view` with `authors` table and groups by author id, ordering them in decreasing order of
number of accesses. Results are restricted to successful fetches.


#### get_days_with_greater_than_percent_errors(cursor, x)
This filters the contents of `log_access_daily_error_percent_view` to rows with error values with greater than x%, and 
then orders them in decreasing order of error percent. 


## Output

Shown below is the program execution output

```
vagrant@vagrant:/vagrant/newsdata$ ./newsdata.py 

#################
The top 3 most popular articles of all time, based on number of accesses are:
"Candidate is jerk, alleges rival" -- 338647 views
"Bears love berries, alleges bear" -- 253801 views
"Bad things gone, say good people" -- 170098 views
#################

#################
The authors in the order of popularity are:
Ursula La Multa -- 507594 views
Rudolf von Treppenwitz -- 423457 views
Anonymous Contributor -- 170098 views
Markoff Chaney -- 84557 views
#################

#################
The following days had more than 1 percent of requests ending up in errors:
Jul 17, 2016 -- 2.26% errors
#################
```
