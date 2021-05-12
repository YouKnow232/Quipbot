import discord
import io
import os
import sys
import random
import asyncio
import time
import configparser


CONFIG = configparser.ConfigParser()

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
    i = random.randrange(quip_num)
    try:
        source = discord.FFmpegOpusAudio(CONFIG['DIR']['SOUND'] + '{:03d}'.format(i) + '.ogg', executable=CONFIG['DIR']['FFMPEG'])
        if vclient.is_playing():
            vclient.stop()
        vclient.play(source)
    except FileNotFoundError as e:
        print(e, file=stderr)
    except discord.errors.ClientException as e:
        print(e, file=stderr)

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
        guild_message_rates[vclient.guild.id] = int(CONFIG['QUIPS']['DEFAULT_RATE'])


    try:
        while vclient.is_connected() and len(vclient.channel.members) > 0:
            play_random_quip(vclient)
            await asyncio.sleep(guild_message_rates[vclient.guild.id])
    except asyncio.CancelledError:
        return


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    elif message.content.startswith('$tailtime'):
        if not discord.opus.is_loaded():
            print('opus isn\'t loaded')
            return
        
        vchannel = message.author.voice.channel
        if (vchannel is not None and not is_bot_connected_to(vchannel)):
            await vchannel.connect()
            quip_timer_tasks[message.guild.id] = asyncio.create_task(quip_timer(vchannel))
        else:
            await message.channel.send('Join a voice channel before initiating Tail Time!')

    elif message.content.startswith('$shaddup'):
        vclient = get_voice_client_by_guild(message.guild)

        if vclient is not None and vclient.is_connected:
            await vclient.disconnect()

    elif message.content.startswith('$quipspeed'):
        tokens = message.content.split(' ')
        if len(tokens) > 1:
            rate = int(CONFIG['QUIPS']['DEFAULT_RATE'])
            try:
                rate = int(tokens[1])
                if (rate < 1):
                    raise ValueError
                guild_message_rates[message.guild.id] = rate

                #Reset quip timer if user is in same voice as Gex
                usrVC = message.author.voice.channel
                if usrVC is not None and get_voice_client_by_channel(usrVC) is not None and quip_timer_exists(message.guild):
                    reset_quip_timer(usrVC)
                
                await message.channel.send('Making a quip every {0} seconds'.format(rate))
            except ValueError:
                await message.channel.send('That ain\'t a real number.  Gimme a REAL number!')
        else:
            await message.channel.send('Gimme a number.')

    elif message.content.startswith('$quip'):
        await message.channel.send('It ain\'t tail time yet!')

    elif message.content.startswith('$gex'):
        await message.channel.send("""```
GEX BOT

commands:
$tailtime ... Joins voice
$shaddup .... Leaves voice
$quip ....... Make a quip right now! (not done yet)
$quipspeed .. Adjust quipping interval in seconds
$gex ........ This help dialog```""")
        #TODO: Move text out of source

@client.event
async def on_ready():
    print('logged in as {0.user.name}'.format(client))
    discord.opus.load_opus(CONFIG['DIR']['OPUS'])

    #TODO: look at how voice_clients are managed


def main():
    CONFIG.read('bot.ini')
    CONFIG.read('botsecrets.ini')

    #Calculate number of files in sound file dir
    global quip_num
    quip_num = len([f for f in os.listdir(CONFIG['DIR']['SOUND']) if f.endswith('.ogg')]) - 1
    print('total quips found {0}'.format(quip_num + 1))

    asyncio.run(client.run(CONFIG['SECRETS']['TOKEN']))

if __name__ == '__main__':
    main()

