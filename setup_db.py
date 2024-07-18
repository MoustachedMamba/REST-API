import psycopg2
import configparser
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


create_database = False
create_tables = True


config = configparser.ConfigParser()
config.read("config.ini")

# Connect to PostgreSQL and create new database.
if create_database:
    conn = psycopg2.connect(dbname='postgres',
                            user='postgres',
                            host='127.0.0.1',
                            password='16511')

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE {config['Config']['dbname']}")
    cursor.execute()
    cursor.execute(f"ALTER DATABASE {config['Config']['dbname']} OWNER TO {config['Config']['user']}")
    conn.close()

if create_tables:
    # Connect as user assigned to DB.
    conn = psycopg2.connect(dbname=config["Config"]["dbname"],
                            user=config["Config"]["user"],
                            password=config["Config"]["password"],
                            host=config["Config"]["host"],
                            port=config["Config"]["port"])
    print(f'Connected to {config["Config"]["dbname"]}, {config["Config"]["host"]}:{config["Config"]["port"]} as {config["Config"]["user"]}')
    cursor = conn.cursor()
    conn.autocommit = True

    # Create users table
    query = "CREATE TABLE IF NOT EXISTS Users (id SERIAL PRIMARY KEY, email VARCHAR(60) UNIQUE NOT NULL, " \
            "password VARCHAR(63) NOT NULL, is_logged BOOLEAN NOT NULL, user_token VARCHAR(30)) "
    cursor.execute(query)

    # Create articles table
    query = "CREATE TABLE IF NOT EXISTS Articles (id SERIAL PRIMARY KEY, user_id SERIAL NOT NULL, name VARCHAR(120) " \
            "NOT NULL, article TEXT) "
    cursor.execute(query)

    # Create video table
    query = "CREATE TABLE IF NOT EXISTS Videos (id SERIAL PRIMARY KEY, user_id SERIAL NOT NULL, name VARCHAR(120) NOT " \
            "NULL, url VARCHAR(200) NOT NULL) "
    cursor.execute(query)

    # Create comments table
    query = "CREATE TABLE IF NOT EXISTS Comments (id SERIAL PRIMARY KEY, user_id SERIAL NOT NULL, comment TEXT NOT " \
            "NULL, media_type VARCHAR(3) NOT NULL, media_id SERIAL NOT NULL) "
    cursor.execute(query)


def purge_database():
    q = "TRUNCATE users, articles, videos, comments"
    cursor.execute(q)
