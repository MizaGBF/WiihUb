from urllib.request import urlopen
from urllib import request
import urllib.parse
import json
from bs4 import BeautifulSoup
import time
import threading

class Sadpanda():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.running = False
        self.cache = {}
        self.cookies = self.server.data.get("panda_cookie", {})
        self.credentials = self.server.data.get("panda_login", ["login", "password"])
        self.enable_preload = self.server.data.get("panda_enable_preload", False)
        self.running = self.login()
        self.lock = threading.Lock()
        self.page_cache = {}
        self.stop_preload = False
        self.th = threading.Thread(target=self.preload)
        if self.running and self.enable_preload:
            self.th.setDaemon(True)
            self.th.start()

    def stop(self):
        self.stop_preload = False
        try: self.th.join(timeout=5)
        except: pass
        self.server.data["panda_cookie"] = self.cookies
        self.server.data["panda_login"] = self.credentials
        self.server.data["panda_enable_preload"] = self.enable_preload

    def preload(self):
        if self.stop_preload or not self.server.is_running: return
        time.sleep(60)
        for i in range(0, 10):
            if self.stop_preload or not self.server.is_running: return
            x = i % 3
            y = i // 3
            if y == 0:
                search = None
                watched = False
            elif y == 1:
                search = "English"
                watched = False
            elif y == 2:
                search = None
                watched = True
            else:
                continue
            ll = self.loadList(search, str(x), watched)
            self.loadGalleries(ll, True)
        for gid in self.cache:
            if self.stop_preload or not self.server.is_running: return
            self.loadThumbnail(gid)

    def requestPanda(self, url, headers={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["user-Agent"] = self.server.user_agent_common
        req = request.Request(url, headers=headers)
        url_handle = request.urlopen(req)
        self.updateCookie(url_handle.getheaders())
        return url_handle.read()

    def login(self):
        try:
            self.requestPanda("https://exhentai.org/?f_search=test")
            return True
        except:
            try:
                req = request.Request('https://forums.e-hentai.org/index.php?act=Login&CODE=01', headers={'Referer': 'https://e-hentai.org/bounce_login.php?b=d&bt=1-1'}, data=urllib.parse.urlencode({"CookieDate": "1","b": "d","bt": "1-1","UserName": self.credentials[0],"PassWord": self.credentials[1],"ipb_login_submit": "Login!"}).encode('ascii'))
                url_handle = request.urlopen(req)
                self.updateCookie(url_handle.getheaders())
                if "ipb_member_id" not in self.cookies and "ipb_pass_hash" not in self.cookies: raise Exception("Invalid credentials")
                print("Successfully logged on sadpanda")
                return True
            except Exception as e:
                print("Failed to login on sadpanda")
                print(e)
                return False

    def updateWatched(self, search, page):
        self.requestPanda("https://exhentai.org/mytags", {'Host': 'exhentai.org', 'Referer': 'https://exhentai.org/watched'})
        url = "https://exhentai.org/watched"
        if search is None and page is None: data = self.requestPanda(url)
        elif page is None: data = self.requestPanda(url + "?f_search={}".format(search))
        elif search is None: data = self.requestPanda(url + "?page={}".format(page))
        else: data = self.requestPanda(url + "?page={}&f_search={}".format(page, search))
        return data

    def loadList(self, search=None, page=None, watched=False):
        try:
            url = "https://exhentai.org/"
            if watched: url += "watched"
            if search is None and page is None: data = self.requestPanda(url)
            elif page is None: data = self.requestPanda(url + "?f_search={}".format(search))
            elif search is None: data = self.requestPanda(url + "?page={}".format(page))
            else: data = self.requestPanda(url + "?page={}&f_search={}".format(page, search))
            soup = BeautifulSoup(data, 'html.parser')
            td = soup.find_all("td", {'class':['gl3m', 'glname']})
            if len(td) == 0 and watched == True:
                data = self.updateWatched(search, page)
                soup = BeautifulSoup(data, 'html.parser')
                td = soup.find_all("td", {'class':['gl3m', 'glname']})
            res = []
            for e in td:
                href = e.findChildren("a", recursive=True)
                for h in href:
                    name = h.findChildren("div", class_="glink", recursive=False)[0].text
                    res.append([h.attrs['href'], None])
            div = soup.find_all("div", {'class':['glthumb']})
            for i in range(len(div)):
                img = div[i].findChildren("img", recursive=True)
                try: res[i][1] = img[0].attrs['data-src']
                except:
                    try: res[i][1] = img[0].attrs['src']
                    except: pass
            return res
        except Exception as e:
            print(e)
            return None

    def urlToIds(self, url):
        if url.endswith("/"): tmp = url[:-1]
        else: tmp = url
        tmp = tmp.split("/")
        try:
            return [int(tmp[-2]), str(tmp[-1])]
        except:
            return None

    def loadGalleries(self, urls, dlThumb=False):
        if len(self.cache) > 200:
            keys = list(self.cache.keys())
            for i in range(0, 150):
                self.cache.pop(keys[i])
        ids = []
        imgs = {}
        res = []
        for u, im in urls:
            i = self.urlToIds(u)
            if i is not None:
                if i[0] not in self.cache:
                    ids.append(i)
                    imgs[i[0]] = im
                elif not isinstance(self.cache[i[0]].get('thumbnail', None), bytes):
                    self.cache[i[0]]['thumbnail'] = im
                res.append(i[0])
        if len(ids) > 0:
            try:
                req = request.Request("https://api.e-hentai.org/api.php", data=json.dumps({"method": "gdata","gidlist": ids,"namespace": 1}).encode('utf-8'))
                url_handle = request.urlopen(req)
                data = json.loads(url_handle.read())
                url_handle.close()
                for m in data['gmetadata']:
                    if 'error' not in m:
                        self.cache[m['gid']] = m
                        self.cache[m['gid']]['pages'] = {}
                        if dlThumb:
                            with self.lock:
                                try:
                                    data = self.loadImageFile(imgs[m['gid']])
                                    if data is not None:
                                        self.cache[m['gid']]['thumbnail'] = data
                                    else:
                                        self.cache[m['gid']]['thumbnail'] = imgs[m['gid']]
                                    time.sleep(0.1)
                                except:
                                    self.cache[m['gid']]['thumbnail'] = imgs[m['gid']]
                        else:
                            self.cache[m['gid']]['thumbnail'] = imgs[m['gid']]
            except:
                pass
        return res

    def retrieveGallery(self, url):
        ids = self.urlToIds(url)
        if ids[0] not in self.cache: self.loadGalleries([[url, None]])
        if ids[0] not in self.cache: raise Exception() # placeholder
        pi = 0
        while True:
            data = self.requestPanda(url + '/?p={}'.format(pi))
            soup = BeautifulSoup(data, 'html.parser')
            div = soup.find_all("div", class_="gdtm")
            res = []
            for e in div:
                a = e.findChildren("a", recursive=True)[0]
                l = a.attrs['href']
                page = l.split('-')[-1]
                self.cache[ids[0]]['pages'][page] = l
            pi += 1
            if len(self.cache[ids[0]]['pages']) >= int(self.cache[ids[0]]['filecount']):
                break

    def getPage(self, url):
        parts = url.split('-')
        if len(parts) != 2: raise Exception('Test') # placeholder
        ids = parts[0].split('/')[-2:]
        m = self.cache[int(ids[1])]
        data = self.requestPanda(url)
        soup = BeautifulSoup(data, 'html.parser')
        div = soup.find_all("div", id="i3")[0]
        img = div.findChildren("img", recursive=True)[0]
        div = soup.find_all("div", id="i4")[0]
        a = div.findChildren("a", recursive=True)
        return img.attrs['src']

    def updateCookie(self, headers):
        res = {}
        for t in headers:
            if t[0] != 'Set-Cookie': continue
            ck = t[1].split('; ')
            for c in ck:
                s = c.split('=')
                if s[0] in ['path', 'domain']: continue
                res[s[0]] = s[1]
        self.cookies = {**self.cookies, **res}

    def buildCookie(self, c):
        s = ""
        for k in c:
            s += k + "=" + c[k] + "; "
        return s

    def formatTags(self, tags):
        res = {}
        for t in tags:
            s = t.split(':')
            if len(s) > 1:
                k = s[0]
                v = ':'.join(s[1:])
                tt = k + ':"' + v + '$"'
            else:
                k = 'misc'
                v = t
                tt = t
            if k not in res: res[k] = []
            res[k].append([v, urllib.parse.quote(tt)])
        msg = ""
        for k in res:
            msg += k + ": "
            for v in res[k]:
                msg += '<a href="/panda?search={}">{}</a> '.format(v[1], v[0])
                if v is not res[k][-1]: msg += ", "
            msg += "<br>"
        return msg

    def loadImageFile(self, url, panda_headers={}):
        if url.startswith('https://exhentai.org/'):
            data = self.requestPanda(url, headers=panda_headers)
        else:
            req = request.Request(url)
            url_handle = request.urlopen(req)
            data = url_handle.read()
            url_handle.close()
        return data

    def loadThumbnail(self, gid):
        m = self.cache[gid]
        if isinstance(m['thumbnail'], str):
            data = self.loadImageFile(m['thumbnail'], {'Host': 'exhentai.org', 'Referer': 'https://exhentai.org/'})
            if data is None: raise Exception('Failed to load thumbnail')
            with self.lock:
                self.cache[gid]['thumbnail'] = data
                m = self.cache[gid]
        return m

    def process_get(self, handler, path):
        if not self.running: return False
        if not self.stop_preload and path.startswith('/panda'): self.stop_preload = True
        host_address = handler.headers.get('Host')
        if path.startswith('/panda?'):
            options = self.server.getOptions(path, 'panda')
            try:
                search = options.get('search', None)
                if search == "": search = None
                page = options.get('page', None)
                ll = self.loadList(search, page, ('watched' in options))
                l = self.loadGalleries(ll)

                if 'watched' in options:
                    back = '<a href="/">Back</a><br>'
                    panda = '/panda?watched=1&'
                    hidden = '<input type="hidden" name="watched" value="1" />'
                else:
                    back = '<a href="/">Back</a><br><a href="/panda?watched=1">Watched</a>'
                    panda = '/panda?'
                    hidden = ''

                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                html += '<div class="elem"><form action="/panda"><legend><b>Sadpanda Browser</b></legend>{}<label for="search">Search </label><input type="text" id="search" name="search" value="{}"><br><input type="submit" value="Search"></form>{}</div>'.format(hidden, "" if search is None else urllib.parse.unquote(search.replace('+', ' ')).replace("'", '&#39;').replace('"', '&#34;'), back)

                if page is None: page = "0"
                if search is None: search = ""
                page_list = [0]
                for i in range(max(0, int(page)-5), int(page)+5):
                    if i not in page_list: page_list.append(i)
                footer = ""
                footer += '<div class="elem" style="font-size: 150%;">'
                for p in page_list:
                    if p == int(page): footer += '<b>{}</b>'.format(page)
                    else: footer += '<a href="{}search={}&page={}">{}</a>'.format(panda, search, p, p)
                    if p is not page_list[-1]: footer += " # "
                footer += '</div>'

                html += footer
                for id in l:
                    m = self.cache[id]
                    html += '<div class="elem">'
                    if m['thumbnail'] is not None: html += '<img height="150" src="/pandathumb/{}/{}" align="left" />'.format(id, m['token'])
                    html += '<a href="/pandagallery/{}/{}">{}</a><br>'.format(id, m['token'], m['title'])
                    html += '<br>' + self.formatTags(m['tags'])
                    html += '</div>'
                
                html += footer
                
                html += "</body>"
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open list")
                print(e)
                self.notification = 'Failed to access {}, page {}'.format(options.get('search', ''), options.get('page', 'unknown'))
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/pandathumb/'):
            try:
                gid = self.urlToIds(path)[0]
                m = self.loadThumbnail(gid)
                if not isinstance(m['thumbnail'], bytes): raise Exception('Thumbnail not loaded')
                handler.answer(200, {}, m['thumbnail'])
            except Exception as e:
                print('Failed to load thumbnail')
                print(e)
                handler.answer(404)
            return True
        elif path.startswith('/pandagallery/'):
            try:
                self.retrieveGallery('https://exhentai.org/g/' + path[len('/pandagallery/'):])
                m = self.cache[self.urlToIds(path)[0]]
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                html += '<div class="elem"><a href="/panda?">Back</a></div>'
                html += '<div class="elem">'
                if m['thumbnail'] is not None: html += '<img src="/pandathumb/{}" align="left" />'.format(path[len('/pandagallery/'):])
                html += '<b>' + m['title'] + '</b><br>'
                html += '<i>' + m['title_jpn'] + '</i><br>'
                html += "tags:<br>"
                html += self.formatTags(m['tags'])
                html += "</div>"
                
                html += '<div class="elem">'
                html += '<i>{} images</i><br>'.format(m['filecount'])
                tk = m['pages']['1'].split('/')
                html += "<a href=/pandapage/{}/{}>Start reading</a>".format(tk[-2], tk[-1])
                html += '</div></body>'

                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open gallery")
                print(e)
                self.notification = 'Failed to open gallery {}'.format(path)
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/pandapage/'):
            try:
                pic = self.getPage('https://exhentai.org/s/' + path[len('/pandapage/'):])
                current = int(path.split('-')[-1])
                tk = path.split('/')
                m = self.cache[int(tk[-1].split('-')[0])]
                if current >= int(m['filecount']): next_p = int(m['filecount'])
                else: next_p = current + 1
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;padding: 10px 10px 10px 10px;font-size: 150%;}</style>'
                html += '<div class="elem"><a href="/pandagallery/{}/{}">Back</a></div>'.format(m['gid'], m['token'])
                html += '<div class="elem">'
                html += '<b>' + m['title'] + '</b><br>'
                html += '<i>' + m['title_jpn'] + '</i><br>'
                html += "Page {} / {}<br>".format(current, m['filecount'])
                pl = list(range(max(current-5, 1), min(current+6, int(m['filecount'])+1)))
                if 1 not in pl: pl = [1] + pl
                for px in range(1, 1 + int(m['filecount']) // 10):
                    if px * 10 not in pl: pl = pl + [px*10]
                if int(m['filecount']) not in pl: pl = pl + [int(m['filecount'])]
                pl.sort()
                for p in pl:
                    if p == current: html += "<b>{}</b>".format(p)
                    else: html += '<a href="/pandapage/{}">{}</a>'.format('/'.join(m['pages'][str(p)].split('/')[-2:]), p)
                    if p != pl[-1]: html += ' # '
                html += "</div>"
                html += '<div>'
                if str(next_p) in m['pages']: html += '<a href="/pandapage/{}"><img src="/pandaimg?file={}"></a>'.format('/'.join(m['pages'][str(next_p)].split('/')[-2:]), pic)
                else: html += '<a href="/pandagallery/{}/{}"><img src="/pandaimg?file={}"></a>'.format(m['gid'], m['token'], pic)
                html += "</div>"
                html += '<div class="elem">'
                html += "Page {} / {}<br>".format(current, m['filecount'])
                for p in pl:
                    if p == current: html += "<b>{}</b>".format(p)
                    else: html += "<a href=/pandapage/{}>{}</a>".format('/'.join(m['pages'][str(p)].split('/')[-2:]), p)
                    if p != pl[-1]: html += ' # '
                html += '</div></body>'

                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open page")
                print(e)
                self.notification = 'Failed to open page {}'.format(path)
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/pandaimg?'):
            options = self.server.getOptions(path, 'pandaimg')
            try:
                url = urllib.parse.unquote(options['file'])
                if url in self.page_cache:
                    data = self.page_cache[url]
                else:
                    data = self.loadImageFile(url)
                    if len(self.page_cache) >= 15:
                        keys = list(self.page_cache.keys())
                        for i in range(0, 9):
                            self.page_cache.pop(keys[i])
                    self.page_cache[url] = data
                ext = url.split('.')[-1]
                handler.answer(200, {'Content-type': 'image/' + ext}, data)
            except Exception as e:
                print("Failed to open image")
                print(e)
                self.notification = 'Failed to open image {}'.format(options.get('file', ''))
                handler.answer(404)
            return True
        elif path.startswith('/pandareset'):
            options = self.server.getOptions(path, 'pandareset')
            try:
                self.cookies = {}
                res = self.login()
                if res:
                    self.running = True
                    self.notification = 'Successfully cleared the cookies and logged in'
                else:
                    self.running = False
                    self.notification = "Can't login, check your credentials"
            except Exception as e:
                print("Failed to clear sadpanda cookies")
                print(e)
                self.notification = 'Failed to '.format(options.get('file', ''))
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False
        
    def get_interface(self):
        if not self.running:
            html = '<b>Sadpanda Browser</b><br>Not logged in<br><a href="/pandareset">Login</a>'
        else:
            html = '<b>Sadpanda Browser</b><br><a href="/panda?">Home</a><br><a href="/panda?watched=1">Watched</a><br><a href="/pandareset">Clear Cookies</a>'
            if self.notification is not None:
                html += "<br>{}".format(self.notification)
                self.notification = None
        return html

    def get_manual(self):
        html = '<b>Sadpanda Browser plugin</b><br>Lets you access exhentai.org. A valid account username and password must be set in config.json.'
        return html