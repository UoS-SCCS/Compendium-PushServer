DROP TABLE IF EXISTS devices;

CREATE TABLE devices (
    device_pub_key TEXT NOT NULL PRIMARY KEY,
	firebase_id TEXT NOT NULL
);
