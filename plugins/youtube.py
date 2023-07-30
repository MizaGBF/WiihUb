import json
from urllib.parse import unquote
from threading import Lock

class Youtube():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.cookies = self.server.data.get("yt_cookie", {})
        self.thumb_cache = {}
        self.lock = Lock()
        if len(self.cookies.keys()) == 0:
            self.consentYoutube()

    def stop(self):
        self.server.data["yt_cookie"] = self.cookies

    def consentYoutube(self, headers={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["User-Agent"] = self.server.user_agent_common
        headers["Connection"] = "close"
        headers["Origin"] = "https://www.youtube.com"
        headers["Referer"] = "https://www.youtube.com/"
        rep = self.server.http_client.post("https://consent.youtube.com/save?continue=https://www.youtube.com/&gl=FR&m=0&pc=yt&x=5&src=2&hl=fr&bl=551504459&cm=2&set_eom=false&set_apyt=true&set_ytc=true", headers=headers)
        if rep.status_code >= 300 or rep.status_code < 200: raise Exception("HTTP Error {}".format(rep.status_code))
        self.updateCookie(rep.headers)

    def explore(self, d):
        if isinstance(d, list):
            videos = {}
            for v in d:
                videos = videos | self.explore(v)
            return videos
        elif isinstance(d, dict):
            if 'videoId' in d:
                try:
                    return {d['videoId'] : [d['thumbnail'], d.get('title', {}), d['publishedTimeText'], d['lengthText'], d['viewCountText'], d.get('ownerText', {})]}
                except:
                    return {}
            else:
                videos = {}
                for v in d.values():
                    videos = videos | self.explore(v)
                return videos
        return {}

    def searchYoutube(self, query, headers={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["User-Agent"] = self.server.user_agent_common
        headers["Connection"] = "close"
        headers["Origin"] = "https://www.youtube.com"
        headers["Referer"] = "https://www.youtube.com/"
        if query == "":
            rep = self.server.http_client.get("https://www.youtube.com/", headers=headers, follow_redirects=True)
        elif query.startswith("@"):
            rep = self.server.http_client.get("https://www.youtube.com/{}/videos".format(query), headers=headers, follow_redirects=True)
        else:
            rep = self.server.http_client.get("https://www.youtube.com/results", params={"search_query": query}, headers=headers, follow_redirects=True)
        if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
        self.updateCookie(rep.headers)
        t = rep.text
        a = t.find("var ytInitialData = {")
        if a == -1: raise Exception("Couldn't retrieve data (Step A)")
        a += len("var ytInitialData = {")
        b = t.find("};", a)
        if b == -1: raise Exception("Couldn't retrieve data (Step B)")
        data = json.loads(t[a-1:b+1])
        videos = self.explore(data)
        if 'metadata' in data:
            videos['metadata'] = data['metadata']
        return videos

    def updateCookie(self, headers):
        res = {}
        ck = headers.get('set-cookie', '').split('; ')
        for c in ck:
            s = c.split('=', 1)
            if len(s) != 2: continue
            res[s[0]] = s[1]
        self.cookies = {**self.cookies, **res}

    def buildCookie(self, c):
        return "; ".join([k+"="+c[k] for k in c])

    def loadImageFile(self, url, headers={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["User-Agent"] = self.server.user_agent_common
        headers["Connection"] = "close"
        headers["Origin"] = "https://www.youtube.com"
        headers["Referer"] = "https://www.youtube.com/"
        rep = self.server.http_client.get(url, headers=headers)
        if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
        return rep.content

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/youtubequery?'):
            options = self.server.getOptions(path, 'youtubequery')
            try:
                query = unquote(options.get('query', '').replace('+', ' '))
                videos = self.searchYoutube(query)

                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} .subelem {width: 305px;display: inline-block;}</style>'
                footer = '<div class="elem"><a href="/">Back</a><br><form action="/youtubequery"><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form></div>'
                html += footer
                html += '<div class="elem">'
                for k, v in videos.items():
                    if k == 'metadata': continue
                    html += '<div class="subelem">'
                    try:
                        thumb = '<img src="/youtubethumb?src={}" style="min-width:300px;max-width:300px;">'.format(v[0]["thumbnails"][0]["url"].split('?')[0])
                    except:
                        thumb = ""
                    try:
                        title = v[1]["runs"][0]["text"]
                    except:
                        title = "???"
                    try:
                        owner = '<br><a href="/youtubequery?query={}">{}</a>'.format(v[5]["runs"][0]["navigationEndpoint"]["browseEndpoint"]["canonicalBaseUrl"].replace('/', ''), v[5]["runs"][0]["text"])
                    except:
                        try:
                            owner = '<br><a href="/youtubequery?query=@{}">{}</a>'.format(videos["metadata"]["channelMetadataRenderer"]["vanityChannelUrl"].split('@')[1], videos["metadata"]["channelMetadataRenderer"]["title"])
                        except:
                            owner = ""
                    try:
                        bottomline = v[3]["simpleText"]
                    except:
                        bottomline = ""
                    try:
                        tmp = v[4]["simpleText"]
                        if bottomline != "": bottomline += " - " + tmp
                    except:
                        pass
                    try:
                        tmp = v[2]["simpleText"]
                        if bottomline != "": bottomline += " - " + tmp
                    except:
                        pass
                    html += '<a href="https://m.youtube.com/watch?v={}">{}<br>{}</a>{}<br>{}'.format(k, thumb, title, owner, bottomline)
                    html += '</div>'
                html += '</div>'
                html += footer
                html += "</body>"
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to search query:", query)
                self.server.printex(e)
                self.notification = 'Failed to search query {}, exception: {}'.format(query, e)
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/youtubethumb'):
            options = self.server.getOptions(path, 'youtubethumb')
            try:
                src = unquote(options.get('src', ''))
                ext = src.split('.')[-1]
                data = self.thumb_cache.get(src, None)
                if data is None:
                    data = self.loadImageFile(src)
                    if data is not None:
                        with self.lock:
                            self.thumb_cache[src]= data
                            if len(self.thumb_cache.keys()) > 60:
                                keys = set(list(self.thumb_cache.keys())[-60:])
                                self.thumb_cache = {k:v for k, v in self.thumb_cache.items() if k in keys}
                handler.answer(200, {'Content-type': 'image/' + ext}, data)
            except Exception as e:
                print('Failed to load thumbnail')
                self.server.printex(e)
                handler.answer(404)
            return True
        elif path.startswith('/youtubereset'):
            try:
                self.cookies = {}
                self.youtubeconsent()
                self.notification = "Cookies have been reset."
            except Exception as e:
                print("Failed to reset cookies.")
                self.server.printex(e)
                self.notification = 'Failed to reset cookies'
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False
        
    def get_interface(self):
        html = '<b>Youtube Browser</b><br><form action="/youtubequery"><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form><a href="/youtubereset">Reset Cookies</a>'
        if self.notification is not None:
            html += "<br>{}".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        html = '<b>Youtube Browser plugin</b><br>Let you lookup Youtube videos.'
        return html