# bellows plus

This repository was cloned from https://github.com/zigpy/bellows

See that repository for bellows documentation.

I have added a bellows gateway command, which starts a websocket server on port 8126 and accepts zcl like commands from clients.  gateway translates these commands to to bellows zcl commands and executes them.  Updated status information is sent back to the websock clients (all attached).

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
  