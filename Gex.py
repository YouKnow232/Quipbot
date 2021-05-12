import discord
import io
import os
import sys
import random
import asyncio
import time

# in seconds
DEFAULT_QUIP_NUM = 645
DEFAULT_MESSAGE_RATE = 600
SOUNDS_DIR = '/home/gex/botfiles/sounds/'

BOT_TOKEN = 'ODI1NjQwMzU4MDMzMjI3Nzg2.YGA3gQ.GJhYOXYk1tmjw1V-iPXuBw_PWUk'

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
    print('quip_num: {0}'.format(quip_num))
    i = random.randrange(quip_num)
    print('quip selected {0}'.format(i)) #TODO remove
    try:
        source = discord.FFmpegOpusAudio(SOUNDS_DIR + '{:03d}'.format(i) + '.ogg', executable='/usr/bin/ffmpeg')
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
        guild_message_rates[vclient.guild.id] = DEFAULT_MESSAGE_RATE

    print('Using quip rate {0}'.format(guild_message_rates[vclient.guild.id])) #TODO remove
    print('members: {0}'.format([i.name for i in vclient.channel.members]))

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
            rate = DEFAULT_MESSAGE_RATE
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

@client.event
async def on_ready():
    print('logged in as {0.user.name}'.format(client))
    discord.opus.load_opus('/usr/lib/x86_64-linux-gnu/libopus.so.0.8.0')

    #TODO: look at how voice_clients are managed


def main():
    #Calculate number of files in sound file dir
    try:
        #Minus 1 to include the zero index
        global quip_num
        quip_num = len([f for f in os.listdir(SOUNDS_DIR) if f.endswith('.ogg')]) - 1
        print('total quips found {0}'.format(quip_num + 1)) #TODO remove
    except FileNotFoundError as e:
        print(e)
        quip_num = DEFAULT_QUIP_NUM

    asyncio.run(client.run(BOT_TOKEN))

if __name__ == '__main__':
    main()

