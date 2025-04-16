# -*- coding: utf-8 -*-

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import os
import json
from urllib.parse import urlencode, quote, urlparse, parse_qsl
from urllib.request import urlopen, Request
import re
import datetime
from bs4 import BeautifulSoup
import requests
import unicodedata
import time
import hjson
import xbmcvfs
from typing import Optional

_url = sys.argv[0]
_handle = int(sys.argv[1])

_ADDON_ID = 'plugin.video.andriman.prehrajto'
addon = xbmcaddon.Addon(id=_ADDON_ID)
ls = addon.getSetting("ls")
download_path = addon.getSetting("download")
history_path = os.path.join(xbmcvfs.translatePath('special://home/addons/plugin.video.andriman.prehrajto'),'resources', 'history.txt')
subtitles_path = os.path.join(xbmcvfs.translatePath('special://home/addons/plugin.video.andriman.prehrajto'),'resources', 'subtitles.txt')
qr_path = os.path.join(xbmcvfs.translatePath('special://home/addons/plugin.video.andriman.prehrajto'),'resources', 'qr.png')
gid = {28: "Akční", 12: "Dobrodružný", 16: "Animovaný", 35: "Komedie", 80: "Krimi", 99: "Dokumentární", 18: "Drama", 10751: "Rodinný", 14: "Fantasy", 36: "Historický", 27: "Horor", 10402: "Hudební", 9648: "Mysteriózní", 10749: "Romantický", 878: "Vědeckofantastický", 10770: "Televizní film", 53: "Thriller", 10752: "Válečný", 37: "Western", 10759: "Action & Adventure", 10751: "Rodinný", 10762: "Kids", 9648: "Mysteriózní", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy", 10766: "Soap", 10767: "Talk", 10768: "War & Politics"}
headers = {'user-agent': 'kodi/prehraj.to'}
language = "en-US"


def encode(string):
    line = unicodedata.normalize('NFKD', string)
    output = ''
    for c in line:
        if not unicodedata.combining(c):
            output += c
    return output


def get_premium():
    if addon.getSetting("email") != '':
        login = {"password": addon.getSetting("password"),"email": addon.getSetting("email"), '_submit': 'Přihlásit+se', 'remember': 'on', '_do': 'login-loginForm-submit'}
        res = requests.post("https://prehraj.to/", login)
        soup = BeautifulSoup(res.content, "html.parser")
        title = soup.find('ul', {'class': 'header__links'})
        title = title.find('span' ,{'class': 'color-green'})
        if title == None:
            premium = 0
            cookies = res.cookies
            xbmcgui.Dialog().notification("Přehraj.to","Premium účet neaktivní", xbmcgui.NOTIFICATION_INFO, 4000, sound = False)
        else:
            premium = 1
            cookies = res.cookies
            xbmcgui.Dialog().notification("Přehraj.to","Premium: " + title.text, xbmcgui.NOTIFICATION_INFO, 4000, sound = False)
    else:
        premium = 0
        cookies = ''
    return premium, cookies


def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def convert_size(number_of_bytes):
    if number_of_bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")
    step_to_greater_unit = 1024.
    number_of_bytes = float(number_of_bytes)
    unit = 'bytes'
    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'KB'
    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'MB'
    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'GB'
    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'TB'
    precision = 1
    number_of_bytes = round(number_of_bytes, precision)
    return str(number_of_bytes) + ' ' + unit


def get_link(gl):
    soup = BeautifulSoup(gl, 'html.parser')
    pattern = re.compile('.*var sources = \[(.*?);.*', re.DOTALL)
    script = soup.find("script", string = pattern).string
    try:
        file = re.compile('.*file: "(.*?)".*', re.DOTALL)
        sources = re.compile('.*var sources = \[(.*?);.*', re.DOTALL)
        sources = sources.findall(script)
        for item in sources:
            file1 = file.findall(item)[0]
    except:
        src = re.compile('.*src: "(.*?)".*', re.DOTALL)
        file1 = src.findall(pattern.findall(script)[0])[0]
    try:
        pattern = re.compile('.*var tracks = (.*?);.*', re.DOTALL)
        script = soup.find("script", text=pattern).string
        data = hjson.loads(pattern.findall(script)[0])
        file2 = json.loads(json.dumps(data))[0]["src"]
    except:
        file2 = ""
    f = open(subtitles_path, "w", encoding="utf-8")
    f.write(file2)
    f.close()
    return file1, file2


def play_video_premium(link, cookies):
    link = "https://prehraj.to" + urlparse(link).path
    url = requests.get(link, cookies=cookies).content
    file, sub = get_link(url)
    res = requests.get(link + "?do=download", cookies = cookies, headers=headers, allow_redirects=False)
    file = res.headers['Location']
    listitem = xbmcgui.ListItem(path = file)
    if sub != "":
        subtitles = []
        subtitles.append(sub)
        listitem.setSubtitles(subtitles)
    xbmcplugin.setResolvedUrl(_handle, True, listitem)


def get_file_size_human_readable(file_path: str) -> Optional[str]:
    """
    Returns file size as a formatted string (e.g., "1.23 GB" or "456 MB").
    Returns None if size cannot be determined.
    """
    try:
        if file_path.startswith(('http://', 'https://')):
            # Remote file: Check Content-Length header
            response = requests.head(file_path, allow_redirects=True, timeout=5)
            size_bytes = int(response.headers.get('Content-Length', 0))
        else:
            # Local file
            size_bytes = os.path.getsize(file_path)

        # Convert to human-readable format
        if size_bytes >= 1024 ** 3:  # 1 GB or more
            return f"{size_bytes / (1024 ** 3):.2f} GB"
        else:
            return f"{size_bytes / (1024 ** 2):.2f} MB"

    except (requests.RequestException, OSError) as e:
        xbmc.log(f"Failed to get file size: {e}", xbmc.LOGWARNING)
        return None

def play_video(link):
    data = urlparse(link)

    url = requests.get("https://prehraj.to" + data.path, headers=headers).content
    file, sub = get_link(url)

    # Get formatted file size
    file_size_str = get_file_size_human_readable(file)
    if file_size_str:
        xbmcgui.Dialog().notification(
            heading="Přehraj.to",
            message=f"Velikost: {file_size_str}",
            icon=xbmcgui.NOTIFICATION_INFO,
            time=4000,
            sound=False
        )

    listitem = xbmcgui.ListItem(path = file)
    if sub != "":
        subtitles = []
        subtitles.append(sub)
        listitem.setSubtitles(subtitles)


    ############
    # video_info = listitem.getInfo('video')
    # video_info['plot'] = 'Stream size: '+file_size_str+'\r\n'+video_info.get('plot', '')
    # listitem.setInfo('video', video_info)

    xbmcplugin.setResolvedUrl(_handle, True, listitem)

def history():
    name_list = open(history_path, "r", encoding="utf-8").read().splitlines()
    for category in name_list:
        list_item = xbmcgui.ListItem(label=category)
        url = get_url(action='listing_search', name = category)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def search(name, params=None):
    if name == "None":
        kb = xbmc.Keyboard("", 'Zadejte název filmu nebo seriálu')
        kb.doModal()
        if not kb.isConfirmed():
            return
        q = kb.getText()
        if q == "":
            return
    else:
        q = encode(name)

    print(f'Search(): '+q)
    if os.path.exists(history_path):
        lh = open(history_path, "r").read().splitlines()
        if q not in lh:
            if len(lh) == 10:
                del lh[-1]
            lh.insert(0, q)
            f = open(history_path, "w")
            for item in lh:
                f.write("%s\n" % item)
            f.close()
    else:
        f = open(history_path, "w")
        f.write(q)
        f.close()
    p = 1
    videos = []
    premium = 0
    if addon.getSetting("email") and len(addon.getSetting("email")) > 0:
        premium, cookies = get_premium()
    while True:
        if premium == 1:
            html = requests.get('https://prehraj.to:443/hledej/' + quote(q) + '?vp-page=' + str(p), cookies=cookies).content
        else:
            html = requests.get('https://prehraj.to:443/hledej/' + quote(q) + '?vp-page=' + str(p)).content
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find_all('h3',attrs={'class': 'video__title'})
        size = soup.find_all('div',attrs={'class': 'video__tag--size'})
        time = soup.find_all('div',attrs={'class': 'video__tag--time'})
        link = soup.find_all('a',{'class': 'video--link'})
        next = soup.find_all('div',{'class': 'pagination-more'})
        for t,s,l,m in zip(title,size,link,time):
            videos.append((t.text , " (" + s.text + " - " + m.text + ")", 'https://prehraj.to:443' + l['href']))
        p = p + 1
        if next == [] or len(videos) > int(ls):
            break
    if not videos:
        xbmcgui.Dialog().notification("Přehraj.to","Nenalezeno:\r\n"+q, xbmcgui.NOTIFICATION_INFO, 4000, sound = False)
        return
    xbmcplugin.setContent(_handle, 'videos')

    print('search(): found: ' + str(len(videos)))
    for category in videos[:int(ls)]:
        print('search(): found item: ' + str(category))
        list_item = xbmcgui.ListItem(label=category[0] + category[1])

        if params is not None and len(params) > 0:
            art = params.get("art", None)
            if art is not None:
                art = json.loads(art)
                list_item.setArt(art)

            video_info = params.get("videoInfo", None)
            if video_info is not None:
                video_info = json.loads(video_info)
                video_info['title'] = category[0] + category[1]
                list_item.setInfo('video', video_info)

        list_item.setProperty('IsPlayable', 'true')
        list_item.addContextMenuItems([('Uložit do knihovny','RunPlugin({})'.format(get_url(action = "library", url = category[2]))), ('Stáhnout','RunPlugin({})'.format(get_url(action = "download", url = category[2]))), ('QR kód streamu','RunPlugin({})'.format(get_url(action = "qr", url = category[2])))])
        url = get_url(action='play', link = category[2])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle)


def tmdb_episodes(sname, params):
    type = params["type"]
    ses_num = params["ses_num"]
    fanart = params.get("fanart", "")
    thumb = params.get("thumb", "") ### Some series do not have thumb, ex: Secret Lives series

    print(f'sname(): ' + sname)

    html = urlopen('https://api.themoviedb.org/3/tv/' + type + '/season/' + ses_num + '?api_key=1f0150a5f78d4adc2407911989fdb66c').read()
    res = json.loads(html)
    print(f'tmdb_episodes(): '+str(res))

    for category in res['episodes']:
        if not category['name']: category['name'] = "Neznámo"
        if category['name'] != 'Speciály' and category['name'] != 'Specials':
            epNo = 'E' + str(category['episode_number'])
            list_item = xbmcgui.ListItem(label=epNo + ': ' + category['name'])

            plot = category['overview']
            if plot == "":
                plot = "~ empty ~"

            ####

            # Extract director(s)
            directors = [
                member['name'] for member in category.get('crew', [])
                if member.get('job') == 'Director'
            ]

            # Extract main cast (guest_stars + top-billed actors)
            main_cast = []
            # for actor in category.get('guest_stars', [])[:10]:  # Limit to top 10
            #     main_cast.append({
            #         'name': actor.get('name', ''),
            #         'role': actor.get('character', ''),
            #         'thumbnail': f"https://image.tmdb.org/t/p/original{actor.get('profile_path', '')}" if actor.get(
            #             'profile_path') else ''
            #     })

            # Create castandrole list (tuple of name,character)
            castandrole = [
                (star['name'], star['character'])
                for star in category.get('guest_stars', [])[:20]  # First 20 guest stars
                if star.get('name') and star.get('character')
            ]
            # Build extended plot with director info
            extended_plot = plot
            if directors:
                extended_plot += f"\n\nDirectors: {', '.join(directors)}"

            videoInfo = {
                'title': category['name'],
                # 'genre': genre,
                'plot': extended_plot,
                'plotoutline': plot,  # Keep original plot for brief view
                'year': category['air_date'],
                'rating': category["vote_average"],
                # 'director': directors,
                # 'cast': main_cast,
                'castandrole': castandrole,
                # Additional metadata
                # 'writer': [
                #     member['name'] for member in category.get('crew', [])
                #     if member.get('job') == 'Writer'
                # ],
                'premiered': category.get('air_date', ''),
                'episode': category.get('episode_number', 0),
                'status': category.get('status', 'Released')
            }


            # videoInfo = {
            #     'title': category['name'],
            #     'plot': plot,
            #     'plotoutline': plot,
            #     'year': category['air_date'],
            #     'rating': category["vote_average"],
            # }

            list_item.setInfo('video', videoInfo)

            print("tmdb_episodes(): "+str(category))
            print("tmdb_episodes(): "+str(videoInfo))

            # Set cast thumbnails if available
            # if main_cast:
            #     print("tmdb_episodes cast(): "+main_cast)
            #     list_item.setCast(main_cast)

            ###

            ####


            # videoInfo = {
            #     'title': category['name'],
            #     'plot': plot,
            #     'plotoutline': plot,
            #     'year': category['air_date'],
            #     'rating': category["vote_average"],
            # }
            #

            art = {'thumb':thumb, 'icon': thumb, 'fanart': fanart}

            list_item.setInfo('video', videoInfo)
            list_item.setArt(art)

            full_name = sname + ' S' + str(category['season_number']).zfill(2) + 'E' + str(category['episode_number']).zfill(2)
            url = get_url(action='listing_search', name = full_name, type = type, videoInfo = json.dumps(videoInfo), art = json.dumps(art))
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def tmdb_seasons(name, type):
    html = urlopen('https://api.themoviedb.org/3/tv/' + type + '?api_key=1f0150a5f78d4adc2407911989fdb66c&language=' + language).read()
    res = json.loads(html)
    print(f'tmdb_seasons(): '+str(res))
    try:
        fanart = "https://image.tmdb.org/t/p/w1280" + res["backdrop_path"]
    except:
        fanart = ""
    for category in res['seasons']:
        if category['name'] != 'Speciály' and category['name'] != 'Specials':
            list_item = xbmcgui.ListItem(label=category['name'])
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""
            list_item.setArt({'thumb':thumb , 'icon': thumb, 'fanart': fanart})

            plot = category['overview']
            if plot == "":
                plot = "~ empty ~"

            list_item.setInfo('video', {
                'title': category['name'],
                'plot': plot,
                'plotoutline': plot,
                'year': category['air_date'],
                'rating': category["vote_average"],
            })

            url = get_url(action='listing_episodes', name = name, type = type, ses_num = str(category['season_number']), fanart = fanart, thumb = thumb)
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    xbmcplugin.endOfDirectory(_handle)


def tmdb_serie(page, type):
    p = int(page)
    html = urlopen('https://api.themoviedb.org/3/tv/' + type + '?api_key=1f0150a5f78d4adc2407911989fdb66c&language=' + language + '&page=' + str(p)).read()
    res = json.loads(html)
    print(f'tmdb_serie(): '+str(res))

    res["results"].append({"name": "Další"})
    xbmcplugin.setContent(_handle, 'videos')
    for category in res['results']:
        list_item = xbmcgui.ListItem(label=category['name'])
        if category['name'] == "Další":
            url = get_url(action='listing_tmdb_serie', name = str(p + 1), type = type)
        else:
            gl = []
            for g in category["genre_ids"]:
                gl.append(gid[g])
            genre = " / ".join(gl)
            list_item.setInfo('video', {'mediatype' : 'movie', 'title': category['name'], "plot": category['overview'], "year": category['first_air_date'].split('-')[0], 'genre': genre, 'rating': str(category["vote_average"])[:3]})
            try:
                fanart = "https://image.tmdb.org/t/p/w1280" + category["backdrop_path"]
            except:
                fanart = ""
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""
            list_item.setArt({'thumb':thumb , 'icon': thumb, 'fanart': fanart})
            url = get_url(action='listing_seasons', name = category['name'], type = category["id"])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def tmdb_movie(page, type):
    print("tmdb_movie()")

    p = int(page)
    html = urlopen('https://api.themoviedb.org/3/movie/' + type + '?api_key=1f0150a5f78d4adc2407911989fdb66c&language=' + language + '&page=' + str(p)).read()
    res = json.loads(html)
    res["results"].append({"title": "Další"})
    res["results"].append({"title": "Domů"})
    xbmcplugin.setContent(_handle, 'videos')
    for category in res['results']:
        list_item = xbmcgui.ListItem(label=category['title'])
        if category['title'] == "Další":
            url = get_url(action='listing_tmdb_movie', name = str(p + 1), type = type)
        elif category['title'] == "Domů":
                url = get_url(action='home', name = str(p + 1), type = type)
        else:
            gl = []
            for g in category["genre_ids"]:
                gl.append(gid[g])
            genre = " / ".join(gl)
            try:
                year = category['release_date'].split('-')[0]
            except:
                year = ''


            ##########
            # plot = category['overview']
            # if plot == "":
            #     plot = "~ empty ~"
            #
            # videoInfo = {
            #     'mediatype': 'movie',
            #     'title': category['title'],
            #     'genre': genre,
            #     'plot': plot,
            #     'plotoutline': plot,
            #     'year': year,
            #     'rating': category["vote_average"],
            # }
            #
            # list_item.setInfo('video', videoInfo)

            ###

            plot = category['overview']
            if plot == "":
                plot = "~ empty ~"

            # Extract director(s)
            directors = [
                member['name'] for member in category.get('crew', [])
                if member.get('job') == 'Director'
            ]

            # Extract main cast (guest_stars + top-billed actors)
            main_cast = []
            for actor in category.get('guest_stars', [])[:10]:  # Limit to top 10
                main_cast.append({
                    'name': actor.get('name', ''),
                    'role': actor.get('character', ''),
                    'thumbnail': f"https://image.tmdb.org/t/p/original{actor.get('profile_path', '')}" if actor.get(
                        'profile_path') else ''
                })

            # Build extended plot with director info
            extended_plot = plot
            if directors:
                extended_plot += f"\n\nDirectors: {', '.join(directors)}"

            videoInfo = {
                'mediatype': 'movie',
                'title': category['title'],
                'genre': genre,
                'plot': extended_plot,
                'plotoutline': plot,  # Keep original plot for brief view
                'year': year,
                'rating': category["vote_average"],
                'director': directors,
                'cast': main_cast,
                # Additional metadata
                'writer': [
                    member['name'] for member in category.get('crew', [])
                    if member.get('job') == 'Writer'
                ],
                'premiered': category.get('air_date', ''),
                'episode': category.get('episode_number', 0),
                'status': category.get('status', 'Released')
            }

            list_item.setInfo('video', videoInfo)

            print("tmdb_movie(): "+str(category))
            print("tmdb_movie(): "+str(videoInfo))

            # Set cast thumbnails if available
            if main_cast:
                print("tmdb_movie cast(): "+main_cast)
                list_item.setCast(main_cast)

            ###

            try:
                fanart = "https://image.tmdb.org/t/p/w1280" + category["backdrop_path"]
            except:
                fanart = ""
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""

            art = {'thumb':thumb , 'icon': thumb, 'fanart': fanart}

            list_item.setArt(art)
            url = get_url(
                action='listing_search',
                name = category['title'] + " " + year,
                type = type,
                videoInfo = json.dumps(videoInfo),
                art = json.dumps(art)
            )
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def tmdb_serie_genre(page, type, id):
    p = int(page)
    html = urlopen('https://api.themoviedb.org/3/discover/' + type + '?api_key=1f0150a5f78d4adc2407911989fdb66c&with_genres=' + id + '&language=' + language + '&page=' + str(p)).read()
    res = json.loads(html)
    res["results"].append({"name": "Další"})
    res["results"].append({"name": "Domů"})
    xbmcplugin.setContent(_handle, 'videos')
    for category in res['results']:
        list_item = xbmcgui.ListItem(label=category['name'])
        if category['name'] == "Další":
            url = get_url(action='listing_genre', id = id, type = type, page = str(p + 1))
        elif category['name'] == "Domů":
            url = get_url(action='home', id = id, type = type, page = str(p + 1))
        else:
            gl = []
            for g in category["genre_ids"]:
                gl.append(gid[g])
            genre = " / ".join(gl)
            try:
                year = category['first_air_date'].split('-')[0]
            except:
                year = ''
            list_item.setInfo('video', {'mediatype' : 'movie', 'title': category['name'], "plot": category['overview'], "year": year, 'genre': genre, 'rating': str(category["vote_average"])[:3]})
            try:
                fanart = "https://image.tmdb.org/t/p/w1280" + category["backdrop_path"]
            except:
                fanart = ""
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""
            list_item.setArt({'thumb':thumb , 'icon': thumb, 'fanart': fanart})
            url = get_url(action='listing_seasons', name = category['name'], type = category["id"])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def tmdb_movie_genre(page, type, id):
    p = int(page)
    html = urlopen('https://api.themoviedb.org/3/discover/' + type + '?api_key=1f0150a5f78d4adc2407911989fdb66c&with_genres=' + id + '&language=' + language + '&page=' + str(p)).read()
    res = json.loads(html)
    res["results"].append({"title": "Další"})
    res["results"].append({"title": "Domů"})
    xbmcplugin.setContent(_handle, 'videos')
    for category in res['results']:
        list_item = xbmcgui.ListItem(label=category['title'])
        if category['title'] == "Další":
            url = get_url(action='listing_genre', id = id, type = type, page = str(p + 1))
        elif category['title'] == "Domů":
            url = get_url(action='home', id = id, type = type, page = str(p + 1))
        else:
            gl = []
            for g in category["genre_ids"]:
                gl.append(gid[g])
            genre = " / ".join(gl)
            try:
                year = category['release_date'].split('-')[0]
            except:
                year = ''

            plot = category['overview']
            if plot == "":
                plot = "~ empty ~"

            videoInfo = {
                'mediatype': 'movie',
                'title': category['title'],
                'genre': genre,
                'plot': plot,
                'plotoutline': plot,
                'year': year,
                'rating': category["vote_average"],
            }

            list_item.setInfo('video', videoInfo)

            try:
                fanart = "https://image.tmdb.org/t/p/w1280" + category["backdrop_path"]
            except:
                fanart = ""
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""

            art = {'thumb':thumb , 'icon': thumb, 'fanart': fanart}

            list_item.setArt(art)
            url = get_url(
                action='listing_search',
                name = category['title'] + " " + year,
                type = type,
                videoInfo = json.dumps(videoInfo),
                art = json.dumps(art)
            )

        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def genres_category(type):
    html = urlopen('https://api.themoviedb.org/3/genre/' + type + '/list?api_key=1f0150a5f78d4adc2407911989fdb66c&language=' + language).read()
    res = json.loads(html)
    for category in res['genres']:
        list_item = xbmcgui.ListItem(label=category['name'])
        url = get_url(action='listing_genre', id = str(category['id']), type = type, page = '1')
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def tmdb_year(page, type, id):
    if type == 'movie':
        title = 'title'
        rd = 'release_date'
        fy = 'primary_release_year'
    else:
        title = 'name'
        rd = 'first_air_date'
        fy = 'first_air_date_year'
    p = int(page)
    html = urlopen('https://api.themoviedb.org/3/discover/' + type + '?api_key=1f0150a5f78d4adc2407911989fdb66c&' + fy + '=' + id + '&language=' + language + '&page=' + str(p)).read()
    res = json.loads(html)
    res["results"].append({title: "Další"})
    xbmcplugin.setContent(_handle, 'videos')
    for category in res['results']:
        list_item = xbmcgui.ListItem(label=category[title])
        if category[title] == "Další":
            url = get_url(action='listing_year', id = id, type = type, page = str(p + 1))
        else:
            gl = []
            for g in category["genre_ids"]:
                gl.append(gid[g])
            genre = " / ".join(gl)
            try:
                year = category[rd].split('-')[0]
            except:
                year = ''

            plot = category['overview']
            if plot == "":
                plot = "~ empty ~"

            print("tmdb_year: "+str(category))
            videoInfo = {
                'mediatype': 'movie',
                'title': category.get('name', category.get('title', '#ERROR#')),
                'genre': genre,
                'plot': plot,
                'plotoutline': plot,
                'year': year,
                'rating': category["vote_average"],
            }
            list_item.setInfo('video', videoInfo)

            try:
                fanart = "https://image.tmdb.org/t/p/w1280" + category["backdrop_path"]
            except:
                fanart = ""
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""

            art = {'thumb':thumb , 'icon': thumb, 'fanart': fanart}
            list_item.setArt(art)

            if type == 'movie':
                url = get_url(
                    action='listing_search',
                    name=category['title'] + " " + year,
                    type=type,
                    videoInfo=json.dumps(videoInfo),
                    art=json.dumps(art)
                )
            else:
                url = get_url(action='listing_seasons', name = category[title], type = category["id"])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def years_category(type):
    year = datetime.datetime.today().year
    YEARS = [year - i for i in range(101)]
    for category in YEARS:
        list_item = xbmcgui.ListItem(label=str(category))
        url = get_url(action='listing_year', type = type, id = str(category), page = '1')
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def search_tmdb(name, type):
    if name == "movie":
        stitle = "filmu"
    else:
        stitle = "seriálu"
    kb = xbmc.Keyboard("", 'Zadejte název ' + stitle)
    kb.doModal()
    if not kb.isConfirmed():
        return
    q = kb.getText()
    if q == "":
        return
    url = 'https://api.themoviedb.org/3/search/' + name + '?api_key=1f0150a5f78d4adc2407911989fdb66c&language=' + language + '&page=1&include_adult=false&query=' + quote(q)
    html = urlopen(url).read()
    res = json.loads(html)
    xbmcplugin.setContent(_handle, 'videos')

    if name == "movie":
        for category in res['results']:
            list_item = xbmcgui.ListItem(label=category['title'])
            gl = []
            for g in category["genre_ids"]:
                gl.append(gid[g])
            genre = " / ".join(gl)
            try:
                year = category['release_date'].split('-')[0]
            except:
                year = ''
            list_item.setInfo('video', {'mediatype' : 'movie', 'title': category['title'], "plot": category['overview'], "year": year, 'genre': genre, 'rating': str(category["vote_average"])[:3]})
            try:
                fanart = "https://image.tmdb.org/t/p/w1280" + category["backdrop_path"]
            except:
                fanart = ""
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""
            list_item.setArt({'thumb':thumb , 'icon': thumb, 'fanart': fanart})
            url = get_url(action='listing_search', name = category['title'] + " " + year, type = type)
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    else:
        for category in res['results']:
            list_item = xbmcgui.ListItem(label=category['name'])
            gl = []
            for g in category["genre_ids"]:
                gl.append(gid[g])
            genre = " / ".join(gl)
            try:
                year = category['first_air_date'].split('-')[0]
            except:
                year = ''
            list_item.setInfo('video', {'mediatype' : 'movie', 'title': category['name'], "plot": category['overview'], "year": year, 'genre': genre, 'rating': str(category["vote_average"])[:3]})
            try:
                fanart = "https://image.tmdb.org/t/p/w1280" + category["backdrop_path"]
            except:
                fanart = ""
            try:
                thumb = "http://image.tmdb.org/t/p/w342" + category["poster_path"]
            except:
                thumb = ""
            list_item.setArt({'thumb':thumb , 'icon': thumb, 'fanart': fanart})
            url = get_url(action='listing_seasons', name = category['name'], type = category["id"])
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def movie_category():
    name_list = [("Nejlépe hodnocené", "listing_tmdb_movie", "1", "top_rated"), ("Oblíbené", "listing_tmdb_movie", "1", "popular"), ("Novinky", "listing_tmdb_movie", "1", "upcoming"), ("Žánry", "listing_genre_category", "movie", ""), ("Rok", "listing_year_category", "movie", ""), ("Hledat", "search_tmdb", "movie", "1")]
    for category in name_list:
        list_item = xbmcgui.ListItem(label=category[0])
        url = get_url(action=category[1], name = category[2], type = category[3])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def serie_category():
    name_list = [("Nejlépe hodnocené", "listing_tmdb_serie", "1", "top_rated"), ("Oblíbené", "listing_tmdb_serie", "1", "popular"), ("Vysílané", "listing_tmdb_serie", "1", "on_the_air"), ("Žánry", "listing_genre_category", "tv", ""),("Rok", "listing_year_category", "tv", ""), ("Hledat", "search_tmdb", "tv", "1")]
    for category in name_list:
        list_item = xbmcgui.ListItem(label=category[0])
        url = get_url(action=category[1], name = category[2], type = category[3])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def menu():
    if os.path.exists(history_path):
        name_list = [("Hledat", "listing_search", "None", ""), ("Historie hledání", "listing_history", "None", ""), ("Filmy", "listing_movie_category", "", ""), ("Seriály", "listing_serie_category", "", "")]
    else:
        name_list = [("Hledat", "listing_search", "None", ""), ("Filmy", "listing_movie_category", "", ""), ("Seriály", "listing_serie_category", "", "")]
    for category in name_list:
        list_item = xbmcgui.ListItem(label=category[0])
        url = get_url(action=category[1], name=category[2], type =category[3])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def home():
    xbmc.executebuiltin("Dialog.Close(all, true)")  # Zavře všechna okna/dialogy
    xbmc.executebuiltin(f"RunPlugin(plugin://{_ADDON_ID}/)")  # Spustí kořenovou stránku doplňku
    # xbmc.executebuiltin("ActivateWindow(Home)")  # Go to Kodi's main menu
    # xbmc.executebuiltin("Container.Update(plugin://plugin.video.andriman.prehrajto/, replace)")  # Go to root

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params["action"] == "home":
            home()
        if params["action"] == "listing_search":
            search(params["name"], params)
        elif params["action"] == "listing_history":
            history()
        elif params["action"] == "listing_episodes":
            tmdb_episodes(params["name"], params)
        elif params["action"] == "listing_seasons":
            tmdb_seasons(params["name"], params["type"])
        elif params["action"] == "listing_year":
            tmdb_year(params["page"], params["type"], params["id"])
        elif params["action"] == "listing_year_category":
            years_category(params["name"])
        elif params["action"] == "listing_movie_category":
            movie_category()
        elif params["action"] == "listing_serie_category":
            serie_category()
        elif params["action"] == "listing_genre_category":
            genres_category(params["name"])
        elif params["action"] == "listing_genre":
            if params["type"] == 'movie':
                tmdb_movie_genre(params["page"], params["type"], params["id"])
            else:
                tmdb_serie_genre(params["page"], params["type"], params["id"])
        elif params["action"] == "listing_tmdb_movie":
            tmdb_movie(params["name"], params["type"])
        elif params["action"] == "listing_tmdb_serie":
            tmdb_serie(params["name"], params["type"])
        elif params["action"] == "search_tmdb":
            search_tmdb(params["name"], params["type"])
        elif params["action"] == "play":
            premium, cookies = get_premium()
            if premium == 1:
                play_video_premium(params["link"], cookies)
            else:
                play_video(params["link"])
        elif params["action"] == "library":
            if addon.getSetting("library") == "":
                xbmcgui.Dialog().notification("Přehraj.to","Nastavte složku pro knihovnu", xbmcgui.NOTIFICATION_ERROR, 3000)
                return
            parsed1 = urlparse(params["url"]).path
            name = parsed1.split("/")[1]
            kb = xbmc.Keyboard(name.replace("-", " "), 'Zadejte název a rok filmu')
            kb.doModal()
            if not kb.isConfirmed():
                return
            q = kb.getText()
            if q == "":
                return
            f = open(addon.getSetting("library") + q +  ".strm", "w")
            f.write("plugin://plugin.video.andriman.prehrajto/?action=play&link=" + params["url"])
            f.close()
            xbmcgui.Dialog().notification("Přehraj.to","Uloženo", xbmcgui.NOTIFICATION_INFO, 3000, sound = False)
        elif params["action"] == "qr":
            u = requests.get(params["url"]).content
            file, sub = get_link(u)
            qr_link = "https://chart.googleapis.com/chart?chs=500x500&cht=qr&choe=UTF-8&chl=" + file.replace('&', '%26')
            xbmc.executebuiltin('ShowPicture('+qr_link+')')
        elif params["action"] == "download":
            if addon.getSetting("download") == "":
                xbmcgui.Dialog().notification("Přehraj.to","Nastavte složku pro stahování", xbmcgui.NOTIFICATION_ERROR, 4000)
                return
            u = requests.get(params["url"]).content
            file, sub = get_link(u)
            parsed1 = urlparse(params["url"]).path
            parsed2 = urlparse(file).path
            name = parsed1.split("/")[1] + "." + parsed2.split(".")[-1]
            if sub != "":
                name_subtitles = parsed1.split("/")[1] + ".srt"
                us = urlopen(sub).read()
                fs = open(download_path + name_subtitles, "wb")
                fs.write(us)
                fs.close()
            premium, cookies = get_premium()
            if premium == 1:
                res = requests.get(params["url"] + "?do=download", cookies = cookies, allow_redirects=False)
                file = res.headers['Location']
            dialog = xbmcgui.DialogProgress()
            u = urlopen(file)
            f = open(download_path + name, "wb")
            file_size = int(u.getheader("Content-Length"))
            dialog.create("Přehraj.to","Stahování...")
            start = time.time()
            file_size_dl = 0
            block_sz = 4096
            canceled = False
            while True:
                if dialog.iscanceled():
                    canceled = True
                    break
                buffer = u.read(block_sz)
                if not buffer: break
                file_size_dl += len(buffer)
                f.write(buffer)
                status = r"%3.2f%%" % (file_size_dl * 100. / file_size)
                status = status + chr(8)*(len(status)+1)
                done = int(50 * file_size_dl / file_size)
                speed = "%s" % round((file_size_dl//(time.time() - start) / 100000), 1)
                dialog.update(int(file_size_dl*100 /file_size), "Velikost:  " + convert_size(file_size) + "\n" + "Staženo:  " + status + "     Rychlost: " + speed + " Mb/s\n" + name)
            f.close()
            dialog.close()
            if canceled == False:
                dialog = xbmcgui.Dialog()
                dialog.ok('Přehraj.to', 'Soubor stažen\n' + name)
            else:
                os.remove(download_path + name)
                try:
                    os.remove(download_path + name_subtitles)
                except: pass
    else:
        menu()


if __name__ == '__main__':
    router(sys.argv[2][1:])
