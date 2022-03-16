"""
 © Copyright 2021-2022 University of Surrey

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

 1. Redistributions of source code must retain the above copyright notice,
 this list of conditions and the following disclaimer.

 2. Redistributions in binary form must reproduce the above copyright notice,
 this list of conditions and the following disclaimer in the documentation
 and/or other materials provided with the distribution.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 POSSIBILITY OF SUCH DAMAGE.

"""


import json
import logging
import os
import sqlite3

import firebase_admin
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError
from flask import Flask, Response, g, jsonify, request

#Paths to database and schema
DATABASE = './data/db.sqlite'
SCHEMA = "./schema.sql"

default_app = firebase_admin.initialize_app()

app = Flask(__name__)

#Logging Path
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
        query (str): Query string to run
        args (tuple, optional): arguments to pass to db execute. Defaults to ().
        one (bool, optional): True to only return one. Defaults to False.
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
    """Register endpoint. Receives POST requests from
    Companion Devices to register their Firebase ID
    against their Public Key ID

    This will overwrite an existing FirebaseID for the 
    specified Public Key ID

    Returns:
        JSON: success:True if successful, False if not
    """    """
    """
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



@app.route("/pushmessage", methods=['POST'])
def pushmessage():
    """Routes a message from the sender to the receiver via
    Firebase Cloud Messaging using the Firebase DeviceID 
    associated with the target public key. 
    
    Returns 500 if the target device is not found

    Returns:
        JSON: success:True or 500 error
    """
    content = request.get_json()
    msg = content["msg"]
    companion_public_key = content["pub_key"]
    device = query_db('SELECT * from devices WHERE device_pub_key = ?', (companion_public_key,), one=True)
    if device is None:
        return jsonify(Response(500,"Device not found"))
    try:
        send_to_fcm(device["firebase_id"],msg)
    except FirebaseError:
        logging.error("Error sending to firebase", exc_info=True)
        return jsonify(success=False)    
    except ValueError:
        logging.error("ValueError sending to firebase", exc_info=True)
        return jsonify(success=False)    
    return jsonify(success=True)


def send_to_fcm(target, msg:dict):
    """Internal function to send a message via Firebase
    Cloud Messaging

    Args:
        target (str): target FCM device ID
        msg (dict): JSON message to send
    """
    # This registration token comes from the client FCM SDKs.
    registration_token = target
    
    #Payload sent with high priority
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
