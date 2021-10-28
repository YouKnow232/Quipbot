import discord
import os
import sys
import random
import asyncio
import configparser
import json
import enum

class Platform(enum.Enum):
    LINUX = 1,
    WINDOWS = 2,
    MAC = 3,

_SUPPORTED_FILETYPES = ('.ogg', '.wav')
_PLATFORM = None
_ERROROUT = None
_CONFIG = configparser.ConfigParser()
_LANG = None
# _PREFIX is a shorthand for = _LANG['commands']['prefix']
_PREFIX = None

# Dictionary containing quip timer async tasks.  Indexed by guild id.
quip_timer_tasks = {}
# Message Rate dictionary - tracks rates for each guild
guild_message_rates = {}
# Max number of sound fils in sound directory. Calculated in main.
quip_num = 0

client = discord.Client()


def get_voice_client_by_channel(voiceChannel):
    matches = [vc for vc in client.voice_clients if vc.channel == voiceChannel]
    if len(matches) > 0:
        return matches[0]
    else:
        return None

def get_voice_client_by_guild(guild):
    matches = [vc for vc in client.voice_clients if vc.guild.id == guild.id]
    if len(matches) > 0:
        return matches[0]
    else:
        return None

def is_bot_connected_to(voiceChannel):
    vClient = get_voice_client_by_channel(voiceChannel)
    return vClient is not None and vClient.is_connected()


def play_random_quip(vclient):
    quips = [f for f in os.listdir(_CONFIG['DIR']['SOUND']) if os.path.isfile(os.path.join(_CONFIG['DIR']['SOUND'], f))]
    quips = [q for q in quips if q.endswith(_SUPPORTED_FILETYPES)]
    quip = random.choice(quips)

    try:
        print('Playing quip: ' + quip)

        if quip.endswith('.ogg'):
            source = discord.FFmpegOpusAudio(_CONFIG['DIR']['SOUND'] + quip, executable=_CONFIG['DIR']['FFMPEG'])
        elif quip.endswith('.wav'):
            source = discord.FFmpegPCMAudio(_CONFIG['DIR']['SOUND'] + quip, executable=_CONFIG['DIR']['FFMPEG'])

        if vclient.is_playing():
            vclient.stop()
        vclient.play(source)

    except FileNotFoundError as e:
        print(e, file=_ERROROUT)
    except discord.errors.ClientException as e:
        print(e, file=_ERROROUT)
    except Exception as e:
        raise e

def quip_timer_exists(guild):
    try:
        return quip_timer_tasks[guild.id] is not None
    except KeyError:
        return False

def reset_quip_timer(vc):
    task = quip_timer_tasks[vc.guild.id]
    task.cancel()
    quip_timer_tasks[vc.guild.id] = asyncio.create_task(quip_timer(vc))

async def quip_timer(vc):
    vclient = get_voice_client_by_channel(vc)
    if vclient is None or not vclient.is_connected():
        return

    #Make sure guild_message_rate entry exists
    try:
        guild_message_rates[vclient.guild.id]
    except KeyError:
        guild_message_rates[vclient.guild.id] = int(_CONFIG['QUIPS']['DEFAULT_RATE'])


    try:
        print("current VC member count: " + len(vclient.channel.members))
        while vclient.is_connected() and len(vclient.channel.members) > 1:
            play_random_quip(vclient)
            await asyncio.sleep(guild_message_rates[vclient.guild.id])
    except asyncio.CancelledError:
        return


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # JOIN
    elif message.content.startswith(_PREFIX + _LANG['commands']['join']):
        if _PLATFORM == 'linux' and not discord.opus.is_loaded():
            print('opus isn\'t loaded', file=_ERROROUT)
            return
        
        vchannel = message.author.voice.channel
        if (vchannel is not None and not is_bot_connected_to(vchannel)):
            await vchannel.connect()
            quip_timer_tasks[message.guild.id] = asyncio.create_task(quip_timer(vchannel))
        else:
            await message.channel.send(_LANG['errors']['joinNotInVoice'])

    # LEAVE
    elif message.content.startswith(_PREFIX + _LANG['commands']['leave']):
        vclient = get_voice_client_by_guild(message.guild)

        if vclient is not None and vclient.is_connected:
            await vclient.disconnect()

    # FREQUENCY
    elif message.content.startswith(_PREFIX + _LANG['commands']['frequency']):
        tokens = message.content.split(' ')
        if len(tokens) > 1:
            rate = int(_CONFIG['QUIPS']['DEFAULT_RATE'])
            try:
                rate = int(tokens[1])
                if (rate < 1):
                    raise ValueError
                guild_message_rates[message.guild.id] = rate

                #Reset quip timer if user is in same voice as bot
                usrVC = message.author.voice.channel
                if usrVC is not None and get_voice_client_by_channel(usrVC) is not None and quip_timer_exists(message.guild):
                    reset_quip_timer(usrVC)
                
                await message.channel.send(_LANG['responses']['quip'].format(rate))
            except ValueError:
                await message.channel.send(_LANG['errors']['quipValErr'])
        else:
            await message.channel.send(_LANG['errors']['quipNoParam'])

    # QUIP
    elif message.content.startswith(_PREFIX + _LANG['commands']['quip']):
        vclient = get_voice_client_by_channel(message.author.voice.channel)
        source = discord.FFmpegPCMAudio(_CONFIG['DIR']['SOUND'] + "Neco_B2AA005.wav", executable=_CONFIG['DIR']['FFMPEG'])

        if vclient.is_playing():
            vclient.stop()
        vclient.play(source)

    # HELP
    elif message.content.startswith(_PREFIX + _LANG['commands']['help']):
        maxLen = len(max(_LANG['commands'].values()))
        formatStr = '{{0:<{0}}}{{1}}'.format(maxLen+3)

        rows = map(lambda c, d: formatStr.format(c, d), _LANG['commands'].values(), _LANG['commandDesc'].values())
        commands = '\n'.join(rows)

        await message.channel.send('```'+_LANG['help']+'\n'+commands+'```')


@client.event
async def on_ready():
    print('logged in as {0.user.name}'.format(client))
    if _PLATFORM == 'linux':
        discord.opus.load_opus(_CONFIG['DIR']['OPUS'])

    #TODO: look at how voice_clients are managed


def sysCheck():
    global _PLATFORM
    global _ERROROUT

    if sys.platform == 'linux' or sys.platform == 'linux2':
        _PLATFORM = Platform.LINUX
        _ERROROUT = stderr
        print('detected linux')
    elif sys.platform == 'win32' or sys.platform == 'win64':
        _PLATFORM = Platform.WINDOWS
        _ERROROUT = open(_CONFIG['DIR']['ERRLOG'], mode='a')
        print('detected windows')
    elif sys.platform == 'darwin':
        _PLATFORM = Platform.MAC
        print('detected mac')

def main():
    global _LANG
    global _PREFIX
    global quip_num

    _CONFIG.read('bot.ini')
    _CONFIG.read('botsecrets.ini')

    with open(_CONFIG['DIR']['LANG']) as f:
        _LANG = json.load(f)

    sysCheck()

    _PREFIX = _LANG['commandPrefix']

    # Calculate number of files in sound file dir
    quip_num = len([f for f in os.listdir(_CONFIG['DIR']['SOUND']) if f.endswith(_SUPPORTED_FILETYPES)]) - 1
    print('total quips found {0}'.format(quip_num + 1))

    asyncio.run(client.run(_CONFIG['SECRETS']['TOKEN']))


if __name__ == '__main__':
    main()
