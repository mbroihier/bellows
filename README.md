# bellows plus

This repository was cloned from https://github.com/zigpy/bellows

See that repository for bellows documentation.

I have added a bellows gateway command, which starts a websocket server on port 8126 and accepts zcl like commands from clients.  gateway translates these commands to bellows zcl commands and executes them.  Updated status information is sent back to the websock clients (all that are attached).

I have added a bellows buildtools command that builds an HTTP server and a timed event generator that both connect to the gateway.  The HTTP server allows users to push buttons to turn on or off ZigBee devices in the network.  The timed event generator can be configured to send commands based on UTC time, local sunrise, or local sunset to turn on or off the ZigBee devices in the network.

## Installation

  1) Install Raspbian bullseye lite
  2) Install python3.12
  ```
  $ apt-get update
  $ apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libcursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git
  $ wget https:/www.python.org/ftp/python/3.12.2/Python3.12.2.tgz
  $ tar -xf Python-3.12.2.tgz
  $ cd Python-3.12.2
  $ ./configure --enable-optimizations
  $ make
  $ make altinstall
  ```
  3) Install rust
  ```
  $ curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  ```
  4) Make a bellows python virtual environment and clone bellows plus
  ```
  $ python3.12 -m venv bellows
  $ cd bellows
  $ source bin/activate
  $ git clone https://github.com/mbroihier/bellows
  ```
  5) Install python packages
  ```
  $ cd bellows/bellows/cli
  $ pip3 install -r requirements.txt
  ```

## Running bellows plus
This assumes that the user has activated the python virtual environment

  1) Setup the ZigBee network (note: baud rates and device may vary based on hardware)
  ```
  $ export EZSP_BAUDRATE=115200
  $ export EZSP_DEVICE=/dev/ttyACM0
  $ cd ~/bellows/bellows/bellows/cli
  $ mkdir ~/.config/bellows
  $ touch ~/.config/bellows/app.db
  $ bellows permit
  $ bellows buildtools
  ```
  2) Edit the index.txt file to give useful names to the buttons (eg name0 => office light1 on).
  3) Rename the index.txt file to index.html
  4) Rename the httpserver.txt file to httpserver.py and change its file mode bits to add execution privilege.
  ```
  $ mv index.txt index.html
  $ mv httpserver.txt httpserver.py
  $ chmod 755 httpserver.py
  ```
  5) Edit the timedEventGenerator.txt file to add any times you want devices to turn on or off.
  6) Rename the timedEventGenerator.txt file to timedEventGenerator.py and add execution privilege.
  ```
  $ mv timedEventGenerator.txt timedEventGenerator.py
  $ chomd 755 timedEventGenerator.py
  ```
  7) Start the gateway
  ```
  $ bellows gateway
  ```
  8) In another window, start the python virtual environment for bellows plus and start the HTTP server
  ```
  $ source ~/bellows/bin/activate
  $ cd ~/bellows/bellows/bellows/cli
  $ ./httpserver.py
  ```
  9) In another window, start the python virtual environment for bellows plus and start the time server
  ```
  $ source ~/bellows/bin/activate
  $ cd ~/bellows/bellows/bellows/cli
  $ ./timedEventGenerator.py
  ```

## Sunrise/Sunset Files
Sunrise and sunset varies based on location.  For the most part, being exact is not necessary.  These tables are meant to be of the form:

```
1   1  2331
1   2  2332
1   3  2333
.
.
.
.
12 31  2330
```
Where the first number refers to the month, the second the day of the month, and the third the UTC time of day in the format of hour(first two digits) and minute(last two digits).  For February, a 29th day is always to be in this file unless there is no sunset or sunrise on that day ever.  The code will only use February 29th on true leap years.

Because this table and the code is using UTC, there are going to be tables (such as the default txsunrise/set files) that have spots where there are no sunsets or two sunsets in a day.  For instance, February 2ed is missing and October 10th has two entries.  This has to do with the fact that the time between sunsets (or it could happen with sunrises too, but not in Texas) is not going to be a perfect day of 86400 seconds.  When it is shorter than 86400 seconds (days are getting shorter) then when the 0000 to 2359 transition occurs there will be two, in this case, sunsets within the same day.  When the time between sunsets is longer than 86400 (days are getting longer), there will be a day where no sunsets occur.

Both of these tables have been abstracted such that they don't have to represent something that happens once a day.  I've included example tables that crudely simulate sunrise/sunset at the North pole.  There, months will go by with neither sunset or sunrise.  So the fact is, that one can implement other profiles that could be of interest: turning on/off Christmas lights only during the Christmas season, lighting a Happy Birthday sign on you Mom's birthday, or turning off all the house lights on Halloween.  The file names will still be sunset/sunrise.txt, but the contents will mean something different.  These two files can be used to define two different abstract profiles.

## Filling in the Time arrays

In timedEventGenerator.py, there is a section that looks like this:

```
    timeOn = {
              "b0:c7:de:ff:fe:52:ca:58": [],
              "34:10:f4:ff:fe:2f:3f:b6": [],
             }
    timeOff = {
               "b0:c7:de:ff:fe:52:ca:58": [],
               "34:10:f4:ff:fe:2f:3f:b6": [],
              }
    sunriseOnOffset = {
                      "b0:c7:de:ff:fe:52:ca:58": [],
                      "34:10:f4:ff:fe:2f:3f:b6": [],
                      }
    sunriseOffOffset = {
                       "b0:c7:de:ff:fe:52:ca:58": [],
                       "34:10:f4:ff:fe:2f:3f:b6": [],
                       }
    sunsetOnOffset = {
                      "b0:c7:de:ff:fe:52:ca:58": [0*3600+15*60],
                      "34:10:f4:ff:fe:2f:3f:b6": [0*3600+15*60],
                     }
    sunsetOffOffset = {
                       "b0:c7:de:ff:fe:52:ca:58": [1*3600+30*60],
                       "34:10:f4:ff:fe:2f:3f:b6": [],
                      }

```
The eight segment hex IDs are the IEEE Zigbee address for a device.  In this example, there are two devices. timeOn/timeOff are used to define times of day one wishes to turn on or off the device.  These times are UTC times second of the day.  So, for instance, 1*3600+30*60 would be 1:30 UTC.  This example has no devices that turn on or off by time of day.

The numbers in the other objects (sunriseOnOffset, sunriseOffOffset, sunsetOnOffset, and sunsetOffOffset) are offsets in seconds from the event time.  So, looking at sunsetOnOffset, one can see that there are two devices being turned on 15 minutes after sunset.  Looking at sunsetOffOffset, one can see that one of the two devices is being turned off 1 hour and 30 minutes after sunset.

One can have an arbitrary number of on or off commands.  Simply add to the array separating entries by commas.

## HTTP Page Customization

The index.txt file can and should be modified so that the canned names installed by bellows buildtools are meaningful.  If, for instance, name0 & name1 refer to a light in a office of your home, you might want to change them to office on and office off.  If name2 & name3 refer to a light in your master bedroom, you might want to change them to master bedroom on and master bedroom off.  Remember that this file needs to be renamed to index.html so that the HTTP server will use it for building the home page.
