import logging
import os
from flask import Flask, request, g, jsonify,Response
import sqlite3
import json
import firebase_admin
from firebase_admin import messaging
DATABASE = './data/db.sqlite'
SCHEMA = "./schema.sql"
default_app = firebase_admin.initialize_app()

app = Flask(__name__)
if not os.path.exists("./logs/"):
    os.mkdir("./logs/")
logging.basicConfig(filename='./logs/access.log', level=logging.DEBUG)


def get_db() -> sqlite3.Connection:
    """Example from Flask documentation for efficient db access
    Returns:
        Connection: database connection
    """

    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = 1")
    db.row_factory = make_dicts
    init_db(db)
    return db


def make_dicts(cursor, row):
    """Converts a database row into a dictionary used as
    as row factory with sqlite
    """
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))


def query_db(query, args=(), one=False):
    """Example from Flask documentation for easy querying
    Args:
        query ([type]): [description]
        args (tuple, optional): [description]. Defaults to ().
        one (bool, optional): [description]. Defaults to False.
    Returns:
        Either a list or a single row if only one
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def init_db(db: sqlite3.Connection):
    """Checks whether the database has been created, denotated by the
    presence of a .created file. If not, runs the schema to construct
    a new database.
    Args:
        db (Connection): database connection to use
    """

    if not os.path.exists(DATABASE+".created"):
        with app.app_context():
            with app.open_resource(SCHEMA, mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            with open(DATABASE+".created", 'w') as fp:
                pass


@app.route("/register", methods=['POST'])
def register():
    content = request.get_json()
    firebaseId = content["fb_id"]
    companion_public_key = content["pub_key"]
    logging.debug("Registering: %s, %s", companion_public_key, firebaseId)
    db = get_db()
    try:
        cursor = db.cursor()
        reg_device_param = """INSERT INTO devices
                          (device_pub_key, firebase_id)
                          VALUES (?, ?);"""

        cursor.execute(reg_device_param, (companion_public_key, firebaseId))
        db.commit()
        logging.debug("Registration complete: %s", companion_public_key)
        last_row_id = cursor.lastrowid
        cursor.close()
        return jsonify(success=True)
    except sqlite3.Error:
        logging.error("Failed to register user", exc_info=True)
        return jsonify(success=False)

    return "<p>Hello, World!</p>"


@app.route("/pushmessage", methods=['POST'])
def pushmessage():
    content = request.get_json()
    msg = content["msg"]
    companion_public_key = content["pub_key"]
    device = query_db('SELECT * from devices WHERE device_pub_key = ?', (companion_public_key,), one=True)
    if device is None:
        return jsonify(Response(500,"Device not found"))
    send_to_fcm(device["firebase_id"],msg)
    return jsonify(success=True)


def send_to_fcm(target, msg:dict):

    # This registration token comes from the client FCM SDKs.
    registration_token = target
    
    # See documentation on defining a message payload.
    message = messaging.Message(
        data=msg,
        token=registration_token,
        android=messaging.AndroidConfig(priority="high")
    )

    # Send a message to the device corresponding to the provided
    # registration token.
    response = messaging.send(message)
    # Response is a message ID string.
    logging.debug('Successfully sent message: %s', response)


@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request
    and cleans up and uninstalls the TPM.
    Args:
        exception ([type]): [description]
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)
