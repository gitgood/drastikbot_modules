#!/usr/bin/env python3
# coding=utf-8

# URL Module for Drastikbot
#
# Depends:
#   - requests      :: $ pip3 install requests
#   - beautifulsoup :: $ pip3 install beautifulsoup4

'''
Copyright (C) 2019 drastik.org

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import re
import math
import json
import urllib.parse
import requests
import bs4


class Module:
    def __init__(self):
        self.auto = True
        self.helpmsg = ["Visit posted urls and post their HTML <title> tag."]


# ----- Constants ----- #
parser = 'html.parser'
user_agent = "w3m/0.52"
accept_lang = "en-US"
nsfw_tag = "\x0304[NSFW]\x0F"
data_limit = 69120
# --------------------- #


def remove_formatting(msg):
    '''Remove IRC String formatting codes'''
    # - Regex -
    # Capture "x03N,M". Should be the first called:
    # (\\x03[0-9]{0,2},{1}[0-9]{1,2})
    # Capture "x03N". Catch all color codes.
    # (\\x03[0-9]{0,2})
    # Capture the other formatting codes
    line = re.sub(r'(\\x03[0-9]{0,2},{1}[0-9]{1,2})', '', msg)
    line = re.sub(r'(\\x03[0-9]{1,2})', '', line)
    line = line.replace("\\x03", "")
    line = line.replace("\\x02", "")
    line = line.replace("\\x1d", "")
    line = line.replace("\\x1D", "")
    line = line.replace("\\x1f", "")
    line = line.replace("\\x1F", "")
    line = line.replace("\\x16", "")
    line = line.replace("\\x0f", "")
    line = line.replace("\\x0F", "")
    return line


def convert_size(size_bytes):
    # https://stackoverflow.com/
    # questions/5194057/better-way-to-convert-file-sizes-in-python
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def get_url(msg):
    '''Search a string for urls and return a list of them.'''
    str_l = msg.split()
    req_l = ["http://", "https://"]  # add "." for parse urls without a scheme
    urls = [u for u in str_l if any(r in u for r in req_l)]
    # Avoid parsing IPv4s that are not complete (IPs like: 1.1):
    # Useful when a scheme is not required to parse a URL.
    # urls = [u for u in urls if u.count('.') == 3 or u.upper().isupper()]
    return urls


def default_parser(u):
    '''
    Visit each url and check if there is html content
    served. If there is try to get the <title></title>
    tag. If there is not try to read the http headers
    to find 'content-type' and 'content-length'.
    '''
    data = ""
    output = ""
    try:
        r = requests.get(u, stream=True,
                         headers={"user-agent": user_agent,
                                  "Accept-Language": accept_lang},
                         timeout=5)
    except Exception:
        return False
    for i in r.iter_content(chunk_size=512, decode_unicode=False):
        data += i.decode('utf-8', errors='ignore')
        if len(data) > data_limit or '</head>' in data.lower():
            break
    r.close()
    soup = bs4.BeautifulSoup(data, parser)
    try:
        output += soup.head.title.text.strip()
    except Exception:
        try:
            output += r.headers['content-type']
        except KeyError:
            pass
        try:
            h_length = convert_size(float(r.headers['content-length']))
            if output:
                output += f", Size: {h_length}"
            else:
                output += h_length
        except KeyError:
            pass
    try:
        if "RTA-5042-1996-1400-1577-RTA" in data:
            output = f"{nsfw_tag} {output}"
        elif r.headers["Rating"] == "RTA-5042-1996-1400-1577-RTA":
            output = f"{nsfw_tag} {output}"
    except KeyError:
        pass
    return output, data


#                                            #
# BEGIN: Website Handling Functions (by url) #
#                                            #
def youtube(url):
    '''Visit a video and get it's information.'''
    r = requests.get(url, headers={"Accept-Language": accept_lang}, timeout=10)
    soup = bs4.BeautifulSoup(r.text, parser)
    name = soup.find(attrs={"itemprop": "name"})['content']
    channel = soup.find(attrs={"class": "yt-user-info"}).text.strip()
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
    out = (f"\x0300,04 ► \x0F: {name} ({duration})"
           f" | \x02Channel:\x0F {channel}")
    return out


def lainchan(url):
    logo = "\x0309lainchan\x0F"
    if "/res/" in url:
        board = url.split("lainchan.org/")[1].split("/", 1)[0]
        board = urllib.parse.unquote(board)
        u = url.replace(".html", ".json")
        post_no = False
        if ".html#" in url:
            post_no = url.split("#")[1][1:]
        r = requests.get(u, timeout=10).json()
        try:
            title = r["posts"][0]["sub"]
        except KeyError:
            title = f'{r["posts"][0]["com"][:80]}...'
        replies = len(r["posts"]) - 1
        files = 0
        for i in r["posts"]:
            if "filename" in i:
                files += 1
            if "extra_files" in i:
                files += len(i["extra_files"])
        if post_no:
            for i in r["posts"]:
                if int(post_no) != i["no"]:
                    continue
                post_text = bs4.BeautifulSoup(i["com"], parser).get_text()[:50]
                return (f"{logo} \x0306/{board}/\x0F {title} "
                        f"\x02->\x0F \x0302{post_text}...\x0F | "
                        f"\x02Replies:\x0F {replies} - \x02Files:\x0F {files}")

        return (f"{logo} \x0306/{board}/\x0F {title} | "
                f"\x02Replies:\x0F {replies} - \x02Files:\x0F {files}")
    else:
        out = default_parser(url)[0]
        return f"{logo}: {out}"


def imgur(url):
    try:
        up = urllib.parse.urlparse(url)
        host = up.hostname
        path = up.path
        if host[:2] == "i.":
            host = host[2:]
            path = path.rsplit(".", 1)[0]
            u = f"https://{host}{path}"
        else:
            u = url

        r = requests.get(u, timeout=10)
        s = "widgetFactory.mergeConfig('gallery', "
        b = r.text.index(s) + len(s)
        e = r.text.index(");", b)
        t = r.text[b:e]

        s = "image               :"
        b = t.index(s) + len(s)
        e = t.index("},", b)
        t = t[b:e] + "}"

        j = json.loads(t)
        title = j["title"]
        mimetype = j["mimetype"]
        size = j["size"]
        width = j["width"]
        height = j["height"]
        nsfw = j["nsfw"]

        output = ""
        if nsfw:
            output += f"{nsfw_tag} "
        output += f"{title} - Imgur"
        output += f" | {mimetype}, Size: {convert_size(size)}"
        output += f", {width}x{height}"
        return output
    except Exception:
        return default_parser(url)[0]
#                                          #
# END: Website Handling Functions (by url) #
#                                          #


hosts_d = {
    "youtube.com": youtube,
    "youtu.be": youtube,
    "lainchan.org": lainchan,
    "i.imgur.com": imgur,
    "imgur.com": imgur
}


def get_title(u):
    host = urllib.parse.urlparse(u).hostname
    if host[:4] == "www.":
        host = host[4:]
    if host not in hosts_d:
        return default_parser(u)  # It's a tuple
    else:
        return hosts_d[host](u), False


#                                              #
# BEGIN: Website Handling Functions (by title) #
#                                              #
def pleroma(data):
    logo = "\x0308Pleroma\x0F"
    soup = bs4.BeautifulSoup(data, parser)
    t = soup.find(attrs={"property": "og:description"})['content']
    t = t.split(": ", 1)
    poster = t[0]
    post = t[1]
    return f"{logo}: \x0302{poster}\x0F {post}"
#                                            #
# END: Website Handling Functions (by title) #
#                                            #


titles_d = {
    "Pleroma": pleroma
}


def title_after_handler(title, data):
    '''
    Used to get data from the <head> when the <title> isn't very helpful
    '''
    if title in titles_d:
        return titles_d[title](data)
    else:
        return title


def main(i, irc):
    # - Raw undecoded message clean up.
    # Remove /r/n and whitespace
    msg = i.msg_raw.strip()
    # Convert the bytes to a string,
    # split the irc commands from the text message,
    # remove ' character from the end of the string.
    msg = str(msg).split(' :', 1)[1][:-1]
    # Remove all IRC formatting codes
    msg = remove_formatting(msg)
    # msg = info[2]

    urls = get_url(msg)
    prev_u = set()  # Already visited URLs, used to avoid spamming.
    for u in urls:
        if not (u.startswith('http://') or u.startswith('https://')):
            u = f'http://{u}'
        if u in prev_u:
            return
        title, data = get_title(u)
        if not title:
            continue
        if data:
            title = title_after_handler(title, data)
        irc.privmsg(i.channel, title)
        prev_u.add(u)
