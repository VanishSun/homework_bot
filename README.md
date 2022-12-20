# homework_bot

Telegram-bot for checking a status of submitted homework to Yandex.Practikum by using API.

This bot sends a message to the user if the status changes to one of the following: "reviewing", "rejected" or "approved".

## Stack

* Python 3.8
* python-dotenv 0.19.0
* python-telegram-bot 13.7

## Install

Clone repo and go to the folder:
````
git clone https://github.com/VanishSun/homework_bot.git
cd homework_bot
````
Create and activate venv:
````
python3 -m venv venv
source venv/bin/activate
````
Install dependencies using requirements.txt:
````
python3 -m pip install --upgrade pip
pip install -r requirements.txt
````
Create env file with special variables:

* PRACTICUM_TOKEN - Your profile token for Yandex.Practikum
* TELEGRAM_TOKEN - Telegram-bot token
* TELEGRAM_CHAT_ID - Your Telegram ID

Run program:
````
python3 homework.py
````

## License:

MIT

## Author:

Ivan Verozub

## PS:

Relax and wait message!
