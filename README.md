# Quipbot
A Discord bot that will make perodic quips in your voice channel


# Requirements
- A Discord bot account
- Python 3 (developed on v3.8.6)
- Linux or Windows environment
- A folder of ogg sound files, named from 000.ogg up to 999.ogg
- ffmpeg codec
- opus codec (Linux only)


# Installation
- `pip install configparser`
- `pip install asyncio`
- `pip install discord.py`
- If running on Windows `pip install discord.py[voice]`
- Configure audio codec directories in `bot.ini`
- Paste bot token into `botsecrets.ini`
- Launch with `python3 QuipBot.py` or `python QuipBot.py` depending on your python setup
