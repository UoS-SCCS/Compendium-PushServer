# Compendium Project
This repository is part of the Compendium Project that built a proof of concept for leveraging the biometric security capabilities found on mobile devices for desktop/laptop security. The project developed a number of protocols and applications to provide a general purpose framework for storing and accessing biometrically protected credentials on a mobile device. A security analysis of the protocols has been undertaken using Tamarin.

The project developed both the backend services and an Android demonstrator app. The framework has been integrated with our previously developed virtual authenticator to show the use of biometrics for secure storage of data on the PC and for performing a biometrically protected user verification.

The list of relevant repositories is as follows:
* [Compendium Library](https://github.com/UoS-SCCS/Compendium-Library) - Provides the Python library to be included by the PC based app that wishes to use the protocol
* [Compendium App](https://github.com/UoS-SCCS/Compendium-Android) - The Android app that provides the companion device functionality
* [Compendium PushServer](https://github.com/UoS-SCCS/Compendium-PushServer) - Provides back-end functionality for the communications protocol
* [Virtual Authenticator with Compendium](https://github.com/UoS-SCCS/VirtualAuthenticatorWithCompendium-) - An extension of development Virtual Authenticator which includes Compendium for secure storage of config data and user verification
* [Security Models](https://github.com/UoS-SCCS/Companion-Device---Tamarin-Models-) - Tamarin security models of the protocol

# Compendium Push Server
The Compendium Push Server acts as a relay point between the PC and the Companion Device. When a PC wants to start an interaction it sends the first message via the Push Server by crafting a JSON message containing the message to forward and the Companion Device Public Key. On receipt of such a message the server checks its registration database, indexed by the Public Key to retrieve the Firebase Cloud Messaging (FCM) Device ID. Having retrieved the FCM Device ID it constructs an FCM message with the payload set to the incoming message payload and sends it with high priority. 

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

## Message Structure

### Register
```json
{
    "fb_id":"String Firebase ID",
    "pub_key":"Base64 Encoded DER Public Key"
}
```
### Push Message
```json
{
    "msg":  {
                //JSON Object Containing arbitrary message
            },
    "pub_key":"Base64 Encoded DER Public Key of target"
}
```
### Response
```json
{
    "success":true
}
```

## Future Development
Currently there is no authentication other either updates or sending. This could be expanded to provide greater resilience, in particular from denial of service attacks.

### Signed Firebase ID Updates
Registration requests should be signed by the corresponding private key. In this way only the owner of the private key would be able to update the Firebase ID for their public key. Without this there is a risk that someone could redirect messages to a different device. This doesn't present a confidentiality or integrity risk because the key establishment would subsequently fail, but it would be an effective denial of service to the targeted companion device. It would be relatively small change and would involve some minor additional logic on the push to validate signatures.

### Restrict sending to approved senders
In addition to registering their own public key and Firebase ID mapping, companion devices could also register approved senders by registering the public key of the PC as approved to send to the device. Requiring Push Messages to be signed by the sender would allow the Push Server to verify that the sender was approved before sending a notification.

This would be relatively easy to implement since the companion device receives the PC public key during enrolment and could make an additional request to the Push Server at this point to register it as an approved sender. There would be a slight increase in load on the Push Server through signature checking, but it should be relatively minor. 