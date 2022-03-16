# Compendium Push Server
The Compendium Push Server acts as a relay point between the PC and the Companion Device. When a PC wants to start an interaction it sends the first message via the Push Server by crafting a JSON message containing the message to forward and the Companion Device Public Key ID. This Public Key ID is a SHA256 hash of the public key and acts as a universal identifiers for the Companion Device. On receipt of such a message the server checks its registration database, indexed by the Public Key ID to retrieve the Firebase Cloud Messaging (FCM) Device ID. Having retrieved the FCM Device ID it constructs an FCM message with the payload set to the incoming message payload and sends it with high priority. 

## Setup
In order to run your own server you need to have a Google Firebase account and credential file. In particular you will need to have the `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to your credential file.

## Pip Install
There is a pip Pipfile and Pipfile.lock provided in the repository, however, note that this appears to have some problems when run on low resource machines, in particular small AWS instances (512mb RAM), to the extent that it appears to hang the instance and requires a reboot. If needing to install on a low resource machine download the requirements in advance (although note: the cryptography requirement does not seem to be met with this method):
```
pip freeze > requirements.txt
mkdir wheelhouse && pip download -r requirements.txt -d wheelhouse
cp requirements.txt ./wheelhouse/
tar -zcf wheelhouse.tar.gz wheelhouse
```
Upload `wheelhouse.tar.gz` to the server

```
tar -zxf wheelhouse.tar.gz
pip install -r wheelhouse/requirements.txt --no-index --find-links wheelhouse
```