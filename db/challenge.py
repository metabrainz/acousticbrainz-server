from hashlib import sha256
import logging
import copy
import time
import json
import os
import db
import db.exceptions
from sqlalchemy import text
import db
import db.exceptions
import sqlalchemy
import string
import random

KEY_LENGTH = 40


def create(user_id, name, start_time, end_time):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO challenge (id, creator, name, start_time, end_time)
                 VALUES (uuid_generate_v4(), :creator, :name, :start_time, :end_time)
              RETURNING id
        """), {
            "creator": user_id,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
        })
        return result.fetchone()["id"]


def get(id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, creator, name, start_time, end_time, created
              FROM challenge
             WHERE id = :id
        """), {"id": id})
        row = result.fetchone()
        if not row:
            raise db.exceptions.NoDataFoundException("Can't find challenge with a specified ID.")
        return dict(row)


def list_all():
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, creator, name, start_time, end_time, created
              FROM challenge
        """))
        return [dict(row) for row in result.fetchall()]


def update(id, name, start_time, end_time):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE challenge
               SET name = :name, start_time = :start_time, end_time = :end_time
             WHERE id = :id
        """), {
            "id": id,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
        })


def delete(id):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM challenge
             WHERE id = :id
        """), {"id": id})
