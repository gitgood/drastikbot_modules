#!/usr/bin/env python3
# coding=utf-8

# YouTube Module for Drastikbot
#
# Search YouTube and return the resulting video.
# When a YouTube url is posted return the video's information.
#
# If you are planning to use the url module or a url bot, consider adding the
# following blacklist: ['youtu.be/', 'youtube.com/watch']
#
# Depends:
#   - requests      :: $ pip3 install requests
#   - beautifulsoup :: $ pip3 install beautifulsoup4

'''
Copyright (C) 2018 drastik.org

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import urllib.parse
import requests
import bs4


class Module:
    def __init__(self):
        self.commands = ['yt']
        self.helpmsg = [
            "Usage: .yt <Video Title>",
            " ",
            "Search YouTube and return the resulting video."]


# ----- Constants ----- #
parser = 'html.parser'
lang = "en-US"
# --------------------- #


def yt_vid_info(yt_id):
    '''Visit a video and get it's information.'''
    url = f'https://www.youtube.com/watch?v={yt_id}'
    short_url = f"https://youtu.be/{yt_id}"
    r = requests.get(url, headers={"Accept-Language": lang}, timeout=10)
    soup = bs4.BeautifulSoup(r.text, parser)
    date = soup.find(attrs={"itemprop": "datePublished"})['content']
    name = soup.find(attrs={"itemprop": "name"})['content']
    views = "{:,}".format(int(soup.find(
        attrs={"itemprop": "interactionCount"})['content']))
    genre = soup.find(attrs={"itemprop": "genre"})['content']
    channel = soup.find(attrs={"class": "yt-user-info"}).text.strip()
    likes = soup.find(attrs={"title": "I like this"}).text.strip()
    dislikes = soup.find(attrs={"title": "I dislike this"}).text.strip()
    duration = soup.find(attrs={"itemprop": "duration"})['content']
    duration = duration[2:][:-1].split('M')
    mins = int(duration[0])
    if mins > 59:
        mins = '{:02d}:{:02d}'.format(*divmod(mins, 60))  # wont do days
    if len(duration[1]) < 2:
        secs = f'0{duration[1]}'
    else:
        secs = duration[1]
    duration = f'{mins}:{secs}'
    return {
        'short_url': short_url, 'name': name, 'date': date, 'views': views,
        'genre': genre, 'channel': channel, 'likes': likes,
        'dislikes': dislikes, 'duration': duration, 'yt_id': yt_id
    }


def yt_search(query):
    '''
    Search YouTube for 'query' and get a video from the search results.
    It tries to visit the video found to ensure that it is valid.
    Returns:
        - 'yt_id' : The YouTube ID of the result video.
        - False   : If no video is found for 'query'.
    '''
    search = f'https://www.youtube.com/results?search_query={query}'
    r = requests.get(search, headers={"Accept-Language": lang}, timeout=10)
    soup = bs4.BeautifulSoup(r.text, parser)
    for s in soup.find_all('a', {'class': ['yt-uix-tile-link']}):
        yt_id = urllib.parse.urlparse(s.get('href')).query
        yt_id = urllib.parse.parse_qs(yt_id)
        try:
            yt_id = yt_id['v'][0]
        except KeyError:
            try:
                yt_id = yt_id['video_id'][0]
            except KeyError:
                continue
        yt_id = ''.join(yt_id.split())
        # Try to visit the url to make sure it's a valid one.
        try:
            u = f'https://www.youtube.com/watch?v={yt_id}'
            requests.get(u, timeout=10)
            break
        except Exception:
            pass
    else:
        return False
    return yt_id


def output(yt_url):
    '''Format the output message to be returned.'''
    # logo_yt = "\x0301,00You\x0300,04Tube\x0F"
    logo_yt = "\x0300,04 ► \x0F"
    i = yt_vid_info(yt_url)
    return (f"{logo_yt}: {i['short_url']} | "
            f"\x02{i['name']}\x0F ({i['duration']})"
            f" | \x02Views:\x0F {i['views']}"
            f" | \x02Channel\x0F: {i['channel']}"
            f" | \x02Date:\x0F {i['date']}"
            f" | \x02Genre:\x0F {i['genre']}"
            f" | \x0303+{i['likes']}\x0F"
            f" | \x0304-{i['dislikes']}\x0F |")


def main(i, irc):
    if i.cmd:
        query = urllib.parse.quote_plus(i.msg_nocmd)
        out = output(yt_search(query))
        irc.privmsg(i.channel, out)
