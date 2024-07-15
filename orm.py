import configparser
import psycopg2
import json
import ast


from helpers import sanitize_db_output
from math import ceil


config = configparser.ConfigParser()
config.read("config.ini")


try:
    conn = psycopg2.connect(dbname=config["Config"]["dbname"],
                            user=config["Config"]["user"],
                            password=config["Config"]["password"],
                            host=config["Config"]["host"],
                            port=config["Config"]["port"])
    print(f'Connected to {config["Config"]["dbname"]}, {config["Config"]["host"]}:{config["Config"]["port"]} as {config["Config"]["user"]}')
    cursor = conn.cursor()
    conn.autocommit = True
except psycopg2.Error as e:
    print(e)
    print("Подключиться к БД не получилось, всё пропало, выключаем нахуй.")
    exit()


class NoAPIEntityFound(Exception):
    def lol(self):
        pass


class APIEntity:
    table = "None"
    id_field = "id"
    data = dict()
    fields = tuple()

    def __init__(self, uid=None):
        self.generate_data_dict()
        if uid is not None:
            self.load_obj(uid=uid)

    def generate_data_dict(self):
        self.data[self.id_field] = None
        for k in self.fields:
            self.data[k] = None

    def check_fields(self):  # Checks if self.data contains only keys listed in self.fields.
        unchecked_data = self.data.copy()
        self.data = dict()
        for k in unchecked_data.keys():
            if k not in self.fields and k != "id":
                print("Удалили ненужный ключ:", k)
            else:
                self.data[k] = unchecked_data[k]

    def sanitize_values(self):  # TODO: Add more checks
        for k in self.data.keys():
            self.data[k] = sanitize_db_output(self.data[k])

    def get_obj(self, uid=None):  # Checks if object is present in DB and returns it.

        if uid is not None:
            self.data["id"] = uid

        query = f"SELECT * FROM {self.table} WHERE {self.id_field} = {self.data['id']}"
        try:
            cursor.execute(query)
            fetched_obj = cursor.fetchone()
            if fetched_obj is not None:
                return fetched_obj
            else:
                return False
        except psycopg2.Error as e:
            print("Error getting obj by ID.")
            print(e)
            return False

    def load_obj(self, uid):
        db_data = list(map(sanitize_db_output, self.get_obj(uid=uid)))
        all_fields = ('id',) + self.fields
        for i in range(len(all_fields)):
            self.data[all_fields[i]] = db_data[i]
        print(self.data)

    def push_update(self):  # Push changes made in object to DB. Returns False if failed, True if succeeded.
        self.check_fields()
        if not self.get_obj():
            return False
        d = self.get_obj()

        fields_to_update = []
        for i in range(len(self.fields)):
            if self.data[self.fields[i]] != d[i]:
                fields_to_update.append(self.fields[i])

        value_setting = []
        for f in fields_to_update:
            if type(self.data[f]) in (int, float):
                value_setting.append(f + " = " + str(self.data[f]))
            else:
                value_setting.append(f + " = '" + str(self.data[f]) + "'")
        print(value_setting)
        value_setting = ", ".join(value_setting)
        if not value_setting:
            return False
        query = f"UPDATE {self.table} SET {value_setting} WHERE {self.id_field} = {self.data['id']}"

        try:
            cursor.execute(query)
            return True
        except psycopg2.Error as e:
            print(e)
            return False

    def add_obj(self):  # Adds object to DB. Returns False if fails to do so.
        self.check_fields()
        if self.get_obj():  # There is already object with such ID in DB, aborting.
            return False
        columns = ", ".join(self.fields)
        values = []
        for k in self.fields:
            current_value = self.data[k]
            if type(current_value) in (int, float):
                values.append(str(current_value))
            else:
                values.append("'" + str(current_value) + "'")
        values = ", ".join(values)
        query = f"INSERT INTO users ({columns}) VALUES ({values})"

        try:
            cursor.execute(query)
        except psycopg2.Error as e:
            print(e)
            return False
        else:
            return True

    def obj2json(self):
        self.check_fields()
        print(self.data)
        return json.dumps(self.data)


class User(APIEntity):
    table = "Users"
    fields = ("email", "password")


class Article(APIEntity):
    table = "Articles"
    fields = ("user_id", "name", "article")


class Video(APIEntity):
    table = "Videos"
    fields = ("user_id", "name", "url")


class Comment(APIEntity):
    table = "Comments"
    fields = ("user_id", "comment", "entity_id", "entity_type")


entity_dict = {
    "users": User,
    "articles": Article,
    "videos": Video,
    "comments": Comment
}


def get_collection(table, limit, page):
    query = f"SELECT COUNT(*) FROM {table}"
    cursor.execute(query)
    row_count = cursor.fetchone()[0]
    page_count = ceil(row_count / limit)
    query = f"SELECT id FROM {table} ORDER BY id OFFSET {limit * (page - 1)} ROWS FETCH NEXT {limit} ROWS ONLY"
    cursor.execute(query)
    fetch = cursor.fetchall()
    collection = []
    for i in fetch:
        collection.append(entity_dict[table](uid=i[0]).data)
    result = {"data": collection, "meta": {"current_page": page,
                                           "last_page": page_count,
                                           "per_page": limit,
                                           "total": row_count}}
    return json.dumps(result, indent=4)
