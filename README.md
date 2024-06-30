# bellows

This repository was cloned from https://github.com/zigpy/bellows

See that repository for bellows documentation.

I have added a command of my own called script which starts a background script that turns on a ZibBee controlled light at sundown and turns it off 45 minutes later.  It also starts a simple web server that allows the user to turn on or off any light in the ZigBee network.  The web page displayed by the server has been specifically crafted for my particular test network.

I have also added a command, zcl-server, which is similar to script but runs only a server/gateway that accepts zcl commands via TCP port 8125 and sends status reports via a websocket at 8126 to clients that are expected to be in JavaScript scripts running on a browser.  http_server_zcl_client.py and index.html implement an example server that standard browsers can connect to.

This is a prototype for a future project.