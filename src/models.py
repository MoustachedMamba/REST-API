import os
import json
import bcrypt
from typing import List
from string import ascii_letters, digits
from configparser import ConfigParser
from email_validator import validate_email, EmailNotValidError
from urllib.parse import urlparse
from sqlalchemy import create_engine, inspect
from sqlalchemy import ForeignKey, String, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session
from sqlalchemy.orm import mapped_column, relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import database_exists, create_database


config = ConfigParser()
config.read("src\\config.ini")
dbname = config["DB"]["dbname"]
username = config["DB"]["user"]
password = config["DB"]["password"]
host = config["DB"]["host"]
port = config["DB"]["port"]

engine = create_engine(f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}")
session = Session(engine)


if not database_exists(engine.url):
    create_database(engine.url)

try:
    engine.connect()
    print("Connection successful:\n", engine)
except Exception as error:
    print("Error connecting to DB, aborting.\n", error)
    exit()


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(65), nullable=False)

    def __repr__(self):
        return f"User(id={self.id!r}, email={self.email!r}, password={self.password!r})"

    @validates("email")
    def validate_email(self, key, value):
        validate_email(value)
        return value

    @validates("password")
    def validate_password(self, key, value):
        for letter in value:
            if letter not in ascii_letters + digits:
                raise ValueError("Use only ASCII letters and digits in password!")
        return bcrypt.hashpw(value.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def check_password(self, user_password: str):
        return bcrypt.checkpw(user_password, self.password)

    def convert_to_json(self):
        result = dict()
        result["id"] = self.id
        result["email"] = self.email
        result["password"] = self.password
        return json.dumps(result)


class Article(Base):
    __tablename__ = "articles"

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    article: Mapped[str] = mapped_column(Text)

    @validates("name")
    def validate_name(self, key, value):
        if not (10 <= len(value) <= 255):
            raise ValueError("Name length should be between 10 and 255 characters!")
        return value

    def convert_to_json(self):
        result = dict()
        result["id"] = self.id
        result["user_id"] = self.user_id
        result["name"] = self.name
        result["article"] = self.article
        return json.dumps(result)


class Video(Base):
    __tablename__ = "videos"

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text)

    @validates("name")
    def validate_name(self, key, name):
        if not (10 <= len(name) <= 255):
            raise ValueError("Name length should be between 10 and 255 characters!")
        return name

    @validates("url")
    def validate_url(self, key, unchecked_url):
        try:
            result = urlparse(unchecked_url)
            if all([result.scheme, result.netloc]):
                return unchecked_url
            else:
                raise AttributeError
        except AttributeError:
            raise ValueError("Something is wrong with URL!")

    def convert_to_json(self):
        result = dict()
        result["id"] = self.id
        result["user_id"] = self.user_id
        result["name"] = self.name
        result["url"] = self.url
        return json.dumps(result)


class Comment(Base):
    __tablename__ = "comments"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(String(3))
    article_id: Mapped[int] = mapped_column(ForeignKey(Article.id), nullable=True)
    video_id: Mapped[int] = mapped_column(ForeignKey(Video.id), nullable=True)

    @validates("media_type")
    def validate_media_type(self, key, value):
        if value not in ("art", "vid"):
            raise ValueError("media_type should only be 'vid' or 'art'!")
        return value

    @hybrid_property
    def media_id(self):
        if self.media_type == "art" and self.article_id is not None:
            return self.article_id
        elif self.media_type == "vid" and self.video_id is not None:
            return self.video_id
        else:
            raise ValueError("Wrong media ID assignment!")

    def convert_to_json(self):
        result = dict()
        result["id"] = self.id
        result["user_id"] = self.user_id
        result["comment"] = self.comment
        result["media_type"] = self.media_type
        result["media_id"] = self.media_id
        return json.dumps(result)


ENTITY_DICT = {
    "users": User,
    "articles": Article,
    "videos": Video,
    "comments": Comment
}


for table in ENTITY_DICT.keys():
    if not inspect(engine).has_table(table):
        print("Creating table:", table)
        ENTITY_DICT[table].metadata.create_all(engine)
