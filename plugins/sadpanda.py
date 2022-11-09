from urllib.parse import quote, unquote
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
        self.running = self.login()
        self.lock = threading.Lock()
        self.first_pages = {}
        self.page_cache = {}
        self.search_time = time.time()
        self.page_time = time.time()
        self.search_lock = threading.Lock()
        self.page_lock = threading.Lock()
        self.page_count = 0

    def stop(self):
        try: self.th.join(timeout=5)
        except: pass
        self.server.data["panda_cookie"] = self.cookies
        self.server.data["panda_login"] = self.credentials

    def requestPandaText(self, url, headers={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["User-Agent"] = self.server.user_agent_common
        headers["Connection"] = "close"
        rep = self.server.http_client.get(url, headers=headers)
        if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
        self.updateCookie(rep.headers)
        return rep.text

    def requestPandaRaw(self, url, headers={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["User-Agent"] = self.server.user_agent_common
        headers["Connection"] = "close"
        rep = self.server.http_client.get(url, headers=headers)
        if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
        self.updateCookie(rep.headers)
        return rep.content

    def login(self):
        try:
            page = self.requestPandaText("https://exhentai.org/?f_search=test")
            if page == "": raise Exception()
            return True
        except:
            try:
                rep = self.server.http_client.post('https://forums.e-hentai.org/index.php?act=Login&CODE=01', headers={'Referer': 'https://e-hentai.org/bounce_login.php?b=d&bt=1-1'}, data = {"CookieDate": "1","b": "d","bt": "1-1","UserName": self.credentials[0],"PassWord": self.credentials[1],"ipb_login_submit": "Login!"}, follow_redirects=True)
                if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
                self.updateCookie(rep.headers)
                if "ipb_member_id" not in self.cookies and "ipb_pass_hash" not in self.cookies: raise Exception("Invalid credentials")
                print("Successfully logged on sadpanda")
                return True
            except Exception as e:
                print("Failed to login on sadpanda")
                self.server.printex(e)
                return False

    def updateWatched(self, search, prev, next):
        self.requestPandaText("https://exhentai.org/mytags", {'Host': 'exhentai.org', 'Referer': 'https://exhentai.org/watched'})
        url = "https://exhentai.org/watched"
        if search is None and prev is None and next is None: data = self.requestPandaText(url)
        elif prev is None and next is None: data = self.requestPandaText(url + "?f_search={}".format(search))
        elif search is None:
            if next is not None: data = self.requestPandaText(url + "?next={}".format(next))
            elif prev is not None: data = self.requestPandaText(url + "?prev={}".format(prev))
            else: data = self.requestPandaText(url)
        else:
            if next is not None: data = self.requestPandaText(url + "?f_search={}&next={}".format(search, next))
            elif prev is not None: data = self.requestPandaText(url + "?f_search={}&prev={}".format(search, prev))
            else: data = self.requestPandaText(url + "?f_search={}".format(search))
        return data

    def loadList(self, search=None, prev=None, next=None, watched=False, popular=False):
        try:
            with self.search_lock:
                now = time.time()
                diff = now - self.search_time
                if diff < 30:
                    time.sleep(30 - diff + 0.1)
                self.search_time = now
            url = "https://exhentai.org/"
            if popular: url += "popular"
            elif watched: url += "watched"
            try:
                if search == "": search = None
                if popular: data = self.requestPandaText(url)
                elif search is None and prev is None and next is None: data = self.requestPandaText(url)
                elif prev is None and next is None: data = self.requestPandaText(url + "?f_search={}".format(search))
                elif search is None:
                    if next is not None: data = self.requestPandaText(url + "?next={}".format(next))
                    elif prev is not None: data = self.requestPandaText(url + "?prev={}".format(prev))
                    else: data = self.requestPandaText(url)
                else:
                    if next is not None: data = self.requestPandaText(url + "?f_search={}&next={}".format(search, next))
                    elif prev is not None: data = self.requestPandaText(url + "?f_search={}&prev={}".format(search, prev))
                    else: data = self.requestPandaText(url + "?f_search={}".format(search))
            except:
                data = self.updateWatched(search, prev, next)
            soup = BeautifulSoup(data, 'html.parser')
            td = soup.find_all("td", {'class':['gl3m', 'glname']})
            if len(td) == 0 and watched == True:
                data = self.updateWatched(search, prev, next)
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
            self.server.printex(e)
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
        if len(list(self.cache.keys())) > 400:
            keys = list(self.cache.keys())
            for i in range(0, 50):
                self.cache.pop(keys[i], None)
        ids = [[]]
        res = []
        for u, im in urls:
            i = self.urlToIds(u)
            if i is not None:
                if i[0] not in self.cache:
                    ids[-1].append(i)
                    if len(ids[-1]) >= 25: ids.append([])
                res.append(i[0])
        for il in ids:
            if len(il) > 0:
                try:
                    r = self.server.http_client.post('https://api.e-hentai.org/api.php', headers={'User-Agent':self.server.user_agent_common}, json={"method": "gdata","gidlist": il,"namespace": 1})
                    data = r.json()
                    print(data)
                    for m in data['gmetadata']:
                        if 'error' not in m:
                            self.cache[m['gid']] = m
                            self.cache[m['gid']]['pages'] = {}
                            self.cache[m['gid']]['thumbnail'] = self.cache[m['gid']].pop('thumb', None)
                            if dlThumb:
                                with self.lock:
                                    try:
                                        data = self.loadImageFile(self.cache[m['gid']]['thumbnail'])
                                        if data is not None:
                                            self.cache[m['gid']]['thumbnail'] = data
                                        time.sleep(0.3)
                                    except:
                                        pass
                except:
                    pass
                if il is not ids[-1] and not dlThumb:
                    time.sleep(1)
        return res

    def retrieveGallery(self, url, page = 0):
        ids = self.urlToIds(url)
        if ids[0] not in self.cache: self.loadGalleries([[url, None]])
        if ids[0] not in self.cache: raise Exception() # placeholder
        if self.page_count == 0 or str(1 + page * self.page_count) not in self.cache[ids[0]]['pages']:
            with self.page_lock:
                now = time.time()
                diff = now - self.page_time
                if diff < 5:
                    time.sleep(5 - diff + 0.1)
                self.page_time = now
            data = self.requestPandaText(url + '/?p={}'.format(page))
            soup = BeautifulSoup(data, 'html.parser')
            div = soup.find_all("div", class_="gdtm")
            res = []
            count = 0
            print(div)
            for e in div:
                a = e.findChildren("a", recursive=True)[0]
                l = a.attrs['href']
                pg = l.split('-')[-1]
                self.cache[ids[0]]['pages'][pg] = (0, l)
                count += 1
            self.page_count = max(self.page_count, count)
        return self.cache[ids[0]]

    def getPage(self, url, page_index):
        parts = url.split('-')
        if len(parts) != 2: raise Exception('Test') # placeholder
        ids = parts[0].split('/')[-2:]
        print("hi")
        m = self.cache[int(ids[1])]
        if str(page_index) not in m['pages'] or m['pages'][str(page_index)][0] == 0:
            with self.page_lock:
                now = time.time()
                diff = now - self.page_time
                if diff < 5:
                    time.sleep(5 - diff + 0.1)
                self.page_time = now
            data = self.requestPandaText(url)
            soup = BeautifulSoup(data, 'html.parser')
            div = soup.find_all("div", id="i3")[0]
            img = div.findChildren("img", recursive=True)[0]
            div = soup.find_all("div", id="i4")[0]
            a = div.findChildren("a", recursive=True)
            m['pages'][str(page_index)] = (1, img.attrs['src'])
        return m['pages'][str(page_index)][1]

    def updateCookie(self, headers):
        res = {}
        ck = headers.get('set-cookie', '').replace('domain=.e-hentai.org, ', '').replace('domain=forums.e-hentai.org, ', '').split('; ')
        for c in ck:
            s = c.split('=', 1)
            if s[0] in ['path', 'domain'] or len(s) != 2: continue
            res[s[0]] = s[1]
        self.cookies = {**self.cookies, **res}

    def buildCookie(self, c):
        s = ""
        for k in c:
            s += k + "=" + c[k] + "; "
        if len(s) > 0: s = s[:-2]
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
            res[k].append([v, quote(tt)])
        msg = ""
        for k in res:
            msg += k + ": "
            for v in res[k]:
                msg += '<a href="/panda?search={}">{}</a> '.format(v[1], v[0])
                if v is not res[k][-1]: msg += ", "
            msg += "<br>"
        return msg

    def loadImageFile(self, url, panda_headers={}):
        if url.startswith('https://exhentai.org/') or url.startswith('https://ehgt.org/'):
            data = self.requestPandaRaw(url, headers=panda_headers)
        else:
            rep = self.server.http_client.get(url, headers={'User-Agent':self.server.user_agent_common})
            if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
            self.updateCookie(rep.headers)
            data = rep.content
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

    def list2index(self, ll):
        try:
            prev = self.urlToIds(ll[0][0])[0]
            try: next = self.urlToIds(ll[-1][0])[0]
            except: next = None
        except:
            prev = None
            next = None
        return prev, next

    def process_get(self, handler, path):
        if not self.running: return False
        host_address = handler.headers.get('Host')
        if path.startswith('/panda?'):
            options = self.server.getOptions(path, 'panda')
            try:
                search = options.get('search', "")
                ll = self.loadList(search, options.get('prev', None), options.get('next', None), ('watched' in options), ('popular' in options))
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
                if 'popular' in options:
                    html += '<div class="elem"><a href="/">Back</a></div>'
                    footer = ""
                else:
                    html += '<div class="elem"><form action="/panda"><legend><b>Sadpanda Browser</b></legend>{}<label for="search">Search </label><input type="text" id="search" name="search" value="{}"><br><input type="submit" value="Search"></form>{}</div>'.format(hidden, "" if search is None else unquote(search.replace('+', ' ')).replace("'", '&#39;').replace('"', '&#34;'), back)

                    footer = ""
                    footer += '<div class="elem" style="font-size: 150%;">'
                    
                    prev, next = self.list2index(ll)
                    if 'prev' not in options and 'next' not in options:
                        self.first_pages[('watched' in options, search)] = prev
                    footer += '<a href="{}search={}">First</a>'.format(panda, search)
                    if ('prev' in options or 'next' in options) and prev is not None and self.first_pages.get(('watched' in options, search), None) != prev:
                        footer += ' # <a href="{}search={}&prev={}">Prev</a>'.format(panda, search, prev)
                    if next is not None:
                        footer += ' # <a href="{}search={}&next={}">Next</a>'.format(panda, search, next)
                        if next != "1": footer += ' # <a href="{}search={}&prev=1">Last</a>'.format(panda, search)
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
                self.server.printex(e)
                self.notification = 'Failed to access {}, prev token {}, next token {}'.format(options.get('search', ''), options.get('prev', 'undefined'), options.get('next', 'undefined'))
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
                self.server.printex(e)
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
                html += "<a href=/pandapage?gurl={}>Start reading</a>".format(path[len('/pandagallery/'):])
                html += '</div></body>'

                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open gallery")
                self.server.printex(e)
                self.notification = 'Failed to open gallery {}'.format(path)
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/pandapage'):
            try:
                options = self.server.getOptions(path, 'pandapage')
                path = path.split('?')[0]
                page_index = options.get('page', 1)
                gurl = options['gurl']
                page_index = int(page_index)
                m = self.retrieveGallery('https://exhentai.org/g/' + gurl, page_index // self.page_count)
                pdt = m['pages'][str(page_index)]
                if pdt[0] == 0: pic = self.getPage(pdt[1], page_index)
                else: pic = pdt[1]
                if page_index >= int(m['filecount']): next_p = -99
                else: next_p = page_index + 1
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;padding: 10px 10px 10px 10px;font-size: 150%;}</style>'
                html += '<div class="elem"><a href="/pandagallery/{}/{}">Back</a></div>'.format(m['gid'], m['token'])
                html += '<div class="elem">'
                html += '<b>' + m['title'] + '</b><br>'
                html += '<i>' + m['title_jpn'] + '</i><br>'
                html += "Page {} / {}<br>".format(page_index, m['filecount'])
                pl = list(range(max(page_index-5, 1), min(page_index+6, int(m['filecount'])+1)))
                if 1 not in pl: pl = [1] + pl
                for px in range(1, 1 + int(m['filecount']) // 10):
                    if px * 10 not in pl: pl = pl + [px*10]
                if int(m['filecount']) not in pl: pl = pl + [int(m['filecount'])]
                pl.sort()
                footer = ""
                for p in pl:
                    if p == page_index: footer += "<b>{}</b>".format(p)
                    else: footer += '<a href="/pandapage?page={}&gurl={}/{}">{}</a>'.format(p, m['gid'], m['token'], p)
                    if p != pl[-1]: footer += ' # '
                html += footer + "</div>"
                html += '<div>'
                if str(next_p) in m['pages']: html += '<a href="/pandapage?page={}&gurl={}/{}"><img src="/pandaimg?file={}"></a>'.format(page_index + 1, m['gid'], m['token'], pic)
                else: html += '<a href="/pandagallery/{}/{}"><img src="/pandaimg?file={}"></a>'.format(m['gid'], m['token'], pic)
                html += "</div>"
                html += '<div class="elem">'
                html += "Page {} / {}<br>".format(page_index, m['filecount'])
                html += footer + '</div></body>'

                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open page")
                self.server.printex(e)
                self.notification = 'Failed to open page {}'.format(path)
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/pandaimg?'):
            options = self.server.getOptions(path, 'pandaimg')
            try:
                url = unquote(options['file'])
                if url in self.page_cache:
                    data = self.page_cache[url]
                else:
                    if len(self.page_cache) >= 100:
                        keys = list(self.page_cache.keys())
                        for i in range(0, len(keys)):
                            self.page_cache.pop(keys[i], None)
                            if i >= 50: break
                    data = self.loadImageFile(url)
                    self.page_cache[url] = data
                ext = url.split('.')[-1]
                handler.answer(200, {'Content-type': 'image/' + ext}, data)
            except Exception as e:
                print("Failed to open image")
                self.server.printex(e)
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
                self.server.printex(e)
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
            html = '<b>Sadpanda Browser</b><br><a href="/panda?">Home</a><br><a href="/panda?watched=1">Watched</a><br><a href="/panda?popular=1">Popular</a><br><a href="/pandareset">Clear Cookies</a>'
            if self.notification is not None:
                html += "<br>{}".format(self.notification)
                self.notification = None
        return html

    def get_manual(self):
        html = '<b>Sadpanda Browser plugin</b><br>Lets you access exhentai.org. A valid account username and password must be set in config.json.'
        return html