import configparser
import psycopg2
import smtplib
import bcrypt
import json
import ast

from math import ceil
from email_validator import validate_email, EmailNotValidError
from email.mime.text import MIMEText

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


smtpObj = smtplib.SMTP_SSL(config["Email"]["host"] + ":" + config["Email"]["port"])
#smtpObj.login(config["Email"]["login"], config["Email"]["password"])


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

    def validate_data(self):
        return True

    def sanitize_db_output(self, value):
        if type(value) is str:
            value = value.replace("'", "''")
            return value.strip()
        else:
            return value

    def check_fields(self):  # Checks if self.data contains only keys listed in self.fields.
        unchecked_data = self.data.copy()
        print("Unchecked:", unchecked_data)
        print("ROD", self.data)
        self.data = dict()
        for k in unchecked_data.keys():
            if k not in self.fields and k != "id":
                print("Удалили ненужный ключ:", k, "значение", unchecked_data[k])
            else:
                self.data[k] = unchecked_data[k]
        print("AFTER:", self.data)

    def check_values(self):  # TODO: Add more checks
        for k in self.data.keys():
            self.data[k] = self.sanitize_db_output(self.data[k])

    def get_obj(self, uid=None):  # Checks if object is present in DB by ID and returns it, returns False otherwise.

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
        except psycopg2.Error as err:
            print("Error getting obj by ID.")
            print(err)
            return False

    def load_obj(self, uid):  # Searches for object by ID and loads it's values in self.data.
        db_data = list(map(self.sanitize_db_output, self.get_obj(uid=uid)))
        print(db_data)
        all_fields = ('id',) + self.fields
        for i in range(len(all_fields)):
            self.data[all_fields[i]] = db_data[i]

    def push_update(self):  # Push changes made in object to DB. Returns False if failed, True if succeeded.
        self.check_fields()
        self.check_values()
        if not self.get_obj():
            return False
        d = self.get_obj()
        if not self.validate_data():
            return False
        fields_to_update = []
        for i in range(len(self.fields)):
            if self.data[self.fields[i]] != d[i]:
                fields_to_update.append(self.fields[i])

        value_setting = []
        for f in fields_to_update:
            if type(self.data[f]) in (int, float):
                value_setting.append(f + " = " + str(self.data[f]))
            elif self.data[f] is None:
                value_setting.append(f + " = " + "null")
            else:
                value_setting.append(f + " = '" + str(self.data[f]) + "'")
        value_setting = ", ".join(value_setting)
        if not value_setting:
            print("Nothing to change?")
            return False
        query = f"UPDATE {self.table} SET {value_setting} WHERE {self.id_field} = {self.data['id']}"
        try:
            cursor.execute(query)
            return True
        except psycopg2.Error as e:
            print(e)
            return False

    def insert_obj(self):  # Adds object to DB. Returns False if fails to do so.
        self.check_fields()
        if self.data["id"] is not None:
            if self.get_obj():  # There is already object with such ID in DB, aborting.
                print("There is already object with this ID in DB.")
                return False
        if not self.validate_data():
            print("Data validation failed, aborting.")
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
        query = f"INSERT INTO {self.table} ({columns}) VALUES ({values}) RETURNING {self.id_field}"

        try:
            cursor.execute(query)
            return cursor.fetchone()[0]
        except psycopg2.Error as err:
            print("Error executing query.")
            print(err)
            return False

    def delete_obj(self, uid=None):  # Deletes object from database, returns False if fails.
        if uid is not None:
            self.data["id"] = uid
        if not self.get_obj(uid=self.data["id"]):
            return False
        query = f'DELETE FROM {self.table} WHERE {self.id_field} = {self.data["id"]}'
        try:
            cursor.execute(query)
            print(cursor.fetchall)
            return True
        except psycopg2.Error as e:
            print(e)
            return False

    def obj2json(self):  # Turns self.data into JSON string.
        self.check_fields()
        print(self.data)
        return json.dumps(self.data)


class User(APIEntity):
    table = "Users"
    fields = ("email", "password", "is_logged", "user_token", "is_admin")

    def validate_data(self):
#        try:
#            validate_email(self.data["email"])
#        except EmailNotValidError as e:
#            print(str(e))
#            print("Email is not valid!")
#            return False
        return super().validate_data()

    def insert_obj(self):
        self.data["password"] = bcrypt.hashpw(self.data["password"].encode(), bcrypt.gensalt()).decode("utf-8")
        return super().insert_obj()

    def push_update(self):  # Вынужденный копипаст
        self.check_fields()
        self.check_values()

        if not self.get_obj():
            print("Skill issue")
            return False
        d = self.get_obj()

        if not self.validate_data():
            print("Validation problem")
            return False

        fields_to_update = []
        for i in range(len(self.fields)):
            if self.data[self.fields[i]] != d[i]:
                fields_to_update.append(self.fields[i])

        if "password" in fields_to_update:  # Если пароль в полях, которые нужно поменять - мы его хэшируем.
            self.data["password"] = bcrypt.hashpw(self.data["password"].encode(), bcrypt.gensalt()).decode("utf-8")

        value_setting = []
        for f in fields_to_update:
            if type(self.data[f]) in (int, float):
                value_setting.append(f + " = " + str(self.data[f]))
            elif self.data[f] is None:
                value_setting.append(f + " = " + "null")
            else:
                value_setting.append(f + " = '" + str(self.data[f]) + "'")
        print(value_setting)
        value_setting = ", ".join(value_setting)
        if not value_setting:
            print("Value setting problem")
            return False
        query = f"UPDATE {self.table} SET {value_setting} WHERE {self.id_field} = {self.data['id']}"
        try:
            print('pizad')
            cursor.execute(query)
            return True
        except psycopg2.Error as e:
            print(e)
            print("A HU ET")
            return False

    def send_email(self, subject: str, content: str):
        if self.validate_data():
            print("Data validation failed, aborting.")
            return False
        address = self.data["email"]

        msg = MIMEText(content, "plain")
        msg['Subject'] = subject
        msg['From'] = config["Email"]["email"]
        smtpObj.sendmail(config["Email"]["email"], address, msg.as_string())
        return True

    def check_password(self, user_pw, uid=None):
        if uid is not None:
            self.data["id"] = uid
        if not self.get_obj(self.data["id"]):
            return False
        hashed_pw = User(uid=self.data["id"]).data["password"].encode("utf-8")
        return bcrypt.checkpw(user_pw.encode("utf-8"), hashed_pw)


class Article(APIEntity):
    table = "Articles"
    fields = ("user_id", "name", "article")

    def validate_data(self):
        u = User()
        if not u.get_obj(self.data["user_id"]):
            return False
        if not (10 < len(self.data["name"]) <= 255):
            return False
        return super().validate_data()


class Video(APIEntity):
    table = "Videos"
    fields = ("user_id", "name", "url")

    def validate_data(self):
        u = User()
        if not u.get_obj(self.data["user_id"]):
            return False
        if not (10 < len(self.data["name"]) <= 255):
            return False
        return super().validate_data()


class Comment(APIEntity):
    table = "Comments"
    fields = ("user_id", "comment", "media_type", "media_id")

    def validate_data(self):
        u = User()
        if not u.get_obj(self.data["user_id"]):
            return False
        if self.data["media_type"] not in ("vid", "art"):
            return False

        comment_validation_dict = {
            "vid": Video,
            "art": Article}
        i = comment_validation_dict[self.data["media_type"]]()
        if not i.get_obj(self.data["media_id"]):
            return False
        return super().validate_data()


entity_dict = {
    "users": User,
    "articles": Article,
    "videos": Video,
    "comments": Comment
}


def get_collection(table: str, limit: int, page: int, search_filter: dict):
    if search_filter is None:
        search_filter = dict()
    query = f"SELECT COUNT(*) FROM {table}"
    cursor.execute(query)
    row_count = cursor.fetchone()[0]
    page_count = ceil(row_count / limit)
    query = f"SELECT id FROM {table} ORDER BY id OFFSET {limit * (page - 1)} ROWS FETCH NEXT {limit} ROWS ONLY"
    cursor.execute(query)
    fetch = cursor.fetchall()
    print(fetch)
    collection = []
    for i in fetch:
        entity = entity_dict[table](uid=i[0])

        for k in search_filter.keys():

            if k.startswith("has_in_") and k[7:] in entity.fields:
                for value in search_filter[k]:
                    if value in entity.data[k[7:]]:
                        collection.append(entity.data.copy())
                        break

            if k.startswith("from_user") and type(entity) in (Article, Video, Comment):
                for value in search_filter[k]:
                    u = User()
                    if u.get_obj(uid=value) and entity.data["user_id"] == value:
                        collection.append(entity.data.copy())

    result = {"data": collection, "meta": {"current_page": page,
                                           "last_page": page_count,
                                           "per_page": limit,
                                           "total": row_count}}
    return json.dumps(result, indent=4)
