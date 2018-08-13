#!/usr/bin/env python2.7

import psycopg2

DBNAME = 'news'


def pg_connection(query_fn):
    '''
    Decorator to handle db connection open and close before and after execution
    of query function. Generates
    and passes cursor to query function
    :param query_fn: Must take the cursor and do the execute, fetchall and
    formatted printing of the fetchall result
    :return: db connection wrapper around query_fn
    '''
    def wrapper(*args, **kwargs):
        db = psycopg2.connect(database=DBNAME)
        c = db.cursor()
        print("")
        print("#################")
        query_fn(c, *args, **kwargs)
        print("#################")
        db.close()
    return wrapper


# Helper methods for inspecting structure of tables
@pg_connection
def get_table_head(cursor, tablename, n):
    '''
    Display table head
    :param cursor:
    :param tablename: tables of news db
    :param n: head num entries
    :return:
    '''
    if tablename == "log":
        cursor.execute("SELECT * FROM log LIMIT %s;", (n, ))
    elif tablename == "articles":
        cursor.execute("SELECT * FROM articles LIMIT %s;", (n, ))
    elif tablename == "authors":
        cursor.execute("SELECT * FROM authors LIMIT %s;", (n, ))
    else:
        raise Exception("Invalid table name")
    message = cursor.fetchall()
    print(message)


@pg_connection
def get_log_method_count(cursor):
    '''
    Checking method field for non-GET methods
    :param cursor:
    :return:
    '''
    cursor.execute("SELECT method, count(*) as num FROM log "
                   "GROUP BY method ORDER BY num DESC;")
    message = cursor.fetchall()
    print(message)


@pg_connection
def get_log_status_count(cursor):
    '''
    Check status column to see if redirects, errors need to be considered apart
    from status OK
    :param cursor:
    :return:
    '''
    cursor.execute("SELECT status, count(*) as num "
                   "FROM logGROUP BY status ORDER BY num DESC;")
    message = cursor.fetchall()
    print(message)
# End helpers


# Report generation methods
@pg_connection
def get_most_popular_articles(cursor, n):
    '''
    Groups the contents of `articles_log_view` by article title and orders them
    in decreasing order of number of accesses, limiting results to top n.
    :param cursor:
    :param n: top n most popular articles' title will be printed
    :return:
    '''
    print("The top %d most popular articles of all time, "
          "based on number of accesses are:" % (n))
    cursor.execute(
        "SELECT title, COUNT(path) AS num FROM articles_log_view "
        "WHERE method = 'GET' AND status = '200 OK' GROUP BY title "
        "ORDER BY num DESC LIMIT %s;", (n,))
    records = cursor.fetchall()
    for article_title, access_count in records:
        print("\"%s\" -- %d views" % (article_title, access_count))


@pg_connection
def get_most_popular_authors(cursor):
    '''
     Merges the `articles_log_view` with `authors` table and groups by
     author id, ordering them in decreasing order of number of accesses.
    :param cursor:
    :return:
    '''
    print("The authors in the order of popularity are:")
    cursor.execute(
        "SELECT authors.name, COUNT(articles_log_view.method) AS num "
        "FROM authors JOIN articles_log_view "
        "ON authors.id = articles_log_view.author "
        "WHERE method = 'GET' AND status = '200 OK' "
        "GROUP BY authors.name ORDER BY num DESC;")
    records = cursor.fetchall()
    for author_name, access_count in records:
        print("%s -- %d views" % (author_name, access_count))


@pg_connection
def get_days_with_greater_than_percent_errors(cursor, x):
    '''
    Filters the contents of `log_access_daily_error_percent_view` to rows with
    error values with greater than x%, and then orders them in decreasing order
    of error percent.
    :param cursor:
    :param x: threshold of error percent beyond which print the date
    :return:
    '''
    print("The following days had more than %d percent of requests ending "
          "up in errors:" % (x))
    cursor.execute(
        "SELECT TO_CHAR(date, 'Mon dd, yyyy'), ROUND(daily_error_percent, 2) "
        "FROM log_access_daily_error_percent_view "
        "WHERE daily_error_percent > %s "
        "ORDER BY daily_error_percent DESC;", (x,))
    records = cursor.fetchall()
    for access_date, error_pct in records:
        print("%s -- %0.2f%% errors" % (access_date, error_pct))


if __name__ == '__main__':

    # Create view from psql prompt for the right outer join of
    # articles table with log table matching the slug in the
    # former with the path column in the latter
    # news=> CREATE VIEW articles_log_view AS
    # news-> SELECT log.*, articles.author, articles.title,
    # news-> articles.slug, articles.lead, articles.body, articles.time
    # news-> AS article_time, articles.id AS articles_id
    # news-> FROM log RIGHT JOIN articles
    # news-> ON log.path = '/article/' || articles.slug;

    # Q1. What are the most popular three articles of all time?
    get_most_popular_articles(3)

    # Q2. Who are the most popular article authors of all time?
    get_most_popular_authors()

    # Create views from psql prompt to get the total counts and
    # num errors by date
    # news=> CREATE VIEW log_access_daily_totals_view AS
    # news-> SELECT DATE(time), COUNT(*) as num FROM log GROUP BY DATE(time);
    # news=> CREATE VIEW log_access_daily_num_errors_view AS
    # news-> SELECT DATE(time), COUNT(*) as num FROM log
    # news-> WHERE status = '404 NOT FOUND' GROUP BY DATE(time);

    # Create view from psql prompt for getting percentage error for each day
    # by doing a join of the totals table with errors table
    # news=> CREATE VIEW log_access_daily_error_percent_view AS
    # news-> SELECT log_access_daily_num_errors_view.date,
    # news-> (100.0 * log_access_daily_num_errors_view.num /
    # news-> log_access_daily_totals_view.num)
    # news-> AS daily_error_percent FROM log_access_daily_num_errors_view
    # news-> JOIN log_access_daily_totals_view
    # news-> ON log_access_daily_num_errors_view.date =
    # news-> log_access_daily_totals_view.date;

    # Q3. On which days did more than 1% of requests lead to errors?
    get_days_with_greater_than_percent_errors(1.0)

    # Misc methods for unit-test
    # get_table_head("articles", 5)
    # get_table_head("authors", 5)
    # get_table_head("log", 5)
    # get_log_method_count()
    # get_log_status_count()
