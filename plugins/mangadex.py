from urllib.request import urlopen
from urllib import request
import urllib.parse
import json
from bs4 import BeautifulSoup
import concurrent.futures

class Mangadex():
    def __init__(self, server):
        self.server = server
        self.cookies = self.server.data.get("mangadex_cookie", {})
        self.chapter_id = None
        self.pages = []
        self.hash = None
        self.md_server = None
        self.title = ""
        self.cache = {}
        self.langs = {"1": "<b>English</b>", "6": "Italian", "7": "Russian", "8": "German", "10": "French", "16": "Portugese (Br)", "21": "Chinese", "26": "Turkish", "27": "Indonesian", "29": "Spanish (LATAM)", "32": "Thai"}
        self.notification = None

        self.know_tags = {k: v for k, v in sorted({1: '4-Koma', 2: 'Action', 3: 'Adventure', 4: 'Award Winning', 5: 'Comedy', 6: 'Cooking', 7: 'Doujinshi', 8: 'Drama', 9: 'Ecchi', 10: 'Fantasy', 11: 'Gyaru', 12: 'Harem', 13: 'Historical', 14: 'Horror', 16: 'Martial Arts', 17: 'Mecha', 18: 'Medical', 19: 'Music', 20: 'Mystery', 21: 'Oneshot', 22: 'Psychological', 23: 'Romance', 24: 'School Life', 25: 'Sci-Fi', 28: 'Shoujo Ai', 30: 'Shounen Ai', 31: 'Slice of Life', 32: 'Smut', 33: 'Sports', 34: 'Supernatural', 35: 'Tragedy', 36: 'Long Strip', 37: 'Yaoi', 38: 'Yuri', 40: 'Video Games', 41: 'Isekai', 42: 'Adaptation', 43: 'Anthology', 44: 'Web Comic', 45: 'Full Color', 46: 'User Created', 47: 'Official Colored', 48: 'Fan Colored', 49: 'Gore', 50: 'Sexual Violence', 51: 'Crime', 52: 'Magical Girls', 53: 'Philosophical', 54: 'Superhero', 55: 'Thriller', 56: 'Wuxia', 57: 'Aliens', 58: 'Animals', 59: 'Crossdressing', 60: 'Demons', 61: 'Delinquents', 62: 'Genderswap', 63: 'Ghosts', 64: 'Monster Girls', 65: 'Loli', 66: 'Magic', 67: 'Military', 68: 'Monsters', 69: 'Ninja', 70: 'Office Workers', 71: 'Police', 72: 'Post-Apocalyptic', 73: 'Reincarnation', 74: 'Reverse Harem', 75: 'Samurai', 76: 'Shota', 77: 'Survival', 78: 'Time Travel', 79: 'Vampires', 80: 'Traditional Games', 81: 'Virtual Reality', 82: 'Zombies', 83: 'Incest', 84: 'Mafia', 85: 'Villainess'}.items(), key=lambda item: item[1])}
        
        if len(self.cookies) == 0:
            req = request.Request("https://mangadex.org", headers={"User-Agent": self.server.user_agent_common})
            url_handle = request.urlopen(req)
            self.updateCookie(url_handle.getheaders())

    def stop(self):
        self.server.data["mangadex_cookie"] = self.cookies

    def updateCookie(self, headers):
        res = {}
        for t in headers:
            if t[0] != 'Set-Cookie': continue
            ck = t[1].split('; ')
            for c in ck:
                s = c.split('=')
                if len(s) <= 1: continue
                res[s[0]] = s[1]
        self.cookies = {**self.cookies, **res}

    def buildCookie(self, c):
        s = ""
        for k in c:
            s += k + "=" + c[k] + "; "
        return s

    def urlToID(self, ch_url):
        sch = ch_url.split('/')
        id = None
        for i in sch:
            try:
                id = int(i)
                break
            except:
                pass
        return id

    def loadImage(self, url, index):
        err = 0
        while err < 3:
            try:
                req = request.Request(url, headers={'User-Agent': self.server.user_agent_common})
                url_handle = request.urlopen(req, timeout=10)
                self.pages[index] = url_handle.read()
                return True
            except:
                self.pages[index] = url
                err += 1
        return False

    def loadChapter(self, id):
        if id != self.chapter_id:
            try:
                req = request.Request("https://mangadex.org/api/?id={}&server=null&saver=1&type=chapter".format(id), headers={"User-Agent": self.server.user_agent_common, "Cookie": self.buildCookie(self.cookies)})
                url_handle = request.urlopen(req)
                self.updateCookie(url_handle.getheaders())
                data = json.loads(url_handle.read())
                self.md_server = data['server']
                self.hash = data['hash']
                self.pages = []
                self.title = data['title']
                while len(self.pages) < len(data['page_array']): self.pages.append(None)
                if len(data['page_array']) > 0:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(data['page_array'])) as executor:
                        ft = {executor.submit(self.loadImage, "{}{}/{}".format(self.md_server, self.hash, data['page_array'][i]), i): i for i in range(0, len(data['page_array']))}
                        count = 0
                        for f in concurrent.futures.as_completed(ft):
                            if f: count += 1
                self.chapter_id = id
                return True
            except Exception as e:
                print(e)
                return False
        return True

    def requestMD(self, url, use_json=False):
        req = request.Request(url, headers={"User-Agent": self.server.user_agent_common, "Cookie": self.buildCookie(self.cookies)})
        url_handle = request.urlopen(req, timeout=10)
        self.updateCookie(url_handle.getheaders())
        if use_json: return json.loads(url_handle.read())
        else: return url_handle.read()

    def getSeries(self, url):
        sid = str(self.urlToID(url))
        suffix = ""
        nid = 1
        if sid not in self.cache:
            self.cache[sid] = {'thumbnail':None, 'title':None, 'tags':None, 'len':None, 'chapters':[]}
        else:
            self.cache[sid]['len'] = None
            self.cache[sid]['chapters'] = []
        while True:
            soup = BeautifulSoup(self.requestMD(url + suffix), 'html.parser')

            if self.cache[sid]['len'] is None:
                li = soup.find_all('li', class_='list-inline-item')
                for l in li:
                    if len(l.findChildren("span", {'class':['far', 'fa-file', 'fa-fw'], 'title':'Total chapters'}, recursive=True)) > 0:
                        try:
                            self.cache[sid]['len'] = int(l.text)
                        except:
                            pass
            
            if self.cache[sid]['thumbnail'] is None:
                try:
                    div = soup.find_all("div", {'class':['card-body', 'p-0']})
                    self.cache[sid]['thumbnail'] = self.requestMD(div[0].findChildren("img", class_="rounded", recursive=True)[0].attrs['src'])
                except:
                    pass

            if self.cache[sid]['title'] is None:
                try:
                    h6 = soup.find_all("h6", class_='card-header')
                    self.cache[sid]['title'] = h6[0].findChildren("span", class_="mx-1", recursive=True)[0].text
                except:
                    pass

            if self.cache[sid]['tags'] is None:
                self.cache[sid]['tags'] = []
                a = soup.find_all("a", class_='badge')
                for aa in a:
                    if aa.attrs['href'].startswith('/genre/'):
                        self.cache[sid]['tags'].append([aa.attrs['href'], aa.text])
            
            div = soup.find_all("div", {'class':['row', 'no-gutters']})
            for d in div:
                try:
                    if str(d).find('data-chapter') != -1:
                        ch = d.findChildren("div", class_="chapter-row", recursive=True)[0]
                        chap = ch.attrs['data-chapter']
                        vol = ch.attrs['data-volume']
                        lang = ch.attrs['data-lang']
                        id = ch.attrs['data-id']
                        self.cache[sid]['chapters'].append([id, vol, chap, lang])
                except:
                    pass
            
            if self.cache[sid]['len'] is None or nid * 100 >= self.cache[sid]['len']:
                break
            nid += 1
            suffix = "/chapters/{}/".format(nid)
        return self.cache[sid]

    def getCategory(self, url):
        soup = BeautifulSoup(self.requestMD(url), 'html.parser')
        a = soup.find_all("a", {'class':['ml-1', 'manga_title']})
        l = []
        for aa in a:
            url = aa.attrs['href']
            id = str(self.urlToID(url))
            if id not in self.cache:
                self.cache[id] = {'thumbnail':'https://mangadex.org/images/manga/{}.large.jpg'.format(self.urlToID(url)), 'title':None, 'tags':None, 'len':None, 'chapters':[]}
            l.append([url, aa.text])
        return l

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/mdgenres'):
            html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;">'
            html += '<div class="elem"><a href="/">Back</a></div>'
            html += '<div class="elem">'
            for id in self.know_tags:
                html += '<a href="/md?url=https://mangadex.org/genre/{}">{}</a><br>'.format(id, self.know_tags[id])
            html += '</div>'
            html += '<div class="elem"><a href="/">Back</a></div>'
            html += '</body>'
            handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
        elif path.startswith('/md?'):
            options = self.server.getOptions(path, 'md')
            try:
                url = urllib.parse.unquote(options.get('url', 'https://mangadex.org/'))
                l = self.getCategory(url)
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                footer = '<div class="elem"><a href="/">Back</a><br><a href="/mdgenres">Genres</a></div>'
                html += footer
                for m in l:
                    html += '<div class="elem"><a href="/mdseries?url=https://mangadex.org{}"><img height="150" src="/mdthumb?id={}" align="left" />{}</a></div>'.format(m[0], self.urlToID(m[0]), m[1])
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open mangadex")
                print(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', '')) # TODO
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mdthumb?'):
            options = self.server.getOptions(path, 'mdthumb')
            try:
                id = options['id']
                if isinstance(self.cache[id]['thumbnail'], str):
                    self.cache[id]['thumbnail'] = self.requestMD(self.cache[id]['thumbnail'])
                handler.answer(200, {}, self.cache[id]['thumbnail'])
            except Exception as e:
                print("Failed to open thumbnail")
                print(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', '')) # TODO
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mdseries?'):
            options = self.server.getOptions(path, 'mdseries')
            try:
                url = urllib.parse.unquote(options['url'])
                m = self.getSeries(url)
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                footer = '<div class="elem"><a href="/md?">Back</a></div>'
                
                html += footer + '<div class="elem">'
                if m['thumbnail'] is not None: html += '<img height="200" src="/mdthumb?id={}" align="left" />'.format(self.urlToID(url))
                html += '<b>' + m['title'] + '</b><br>'
                html += "tags:<br>"
                for t in m['tags']:
                    html += '<a href="/md?url=https://mangadex.org{}">{}</a>'.format(t[0], t[1])
                    if t is not m['tags'][-1]: html += ", "
                html += "</div>"
                
                html += '<div class="elem">'
                for ch in m['chapters']:
                    html += '<a href="/mdchapter?url={}&src={}">Vol.{} Chapter {}</a> ({})<br>'.format(ch[0], url, ch[1], ch[2], self.langs.get(ch[3], "Unknown Language {}".format(ch[3])))
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open manga")
                print(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', '')) # TODO
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mdchapter?'):
            options = self.server.getOptions(path, 'mdchapter')
            try:
                id = self.urlToID(urllib.parse.unquote(options['url']))
                if id is None or not self.loadChapter(id): raise Exception()
                current = int(options.get('page', 0))
                last = len(self.pages)-1
                
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size: 180%;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                
                if last >= 0:
                    # pages
                    pl = list(range(max(current-5, 0), min(current+6, last+1)))
                    if 1 not in pl: pl = [1] + pl
                    for px in range(0, 1 + last // 10):
                        if px * 10 not in pl: pl = pl + [px*10]
                    if last not in pl: pl = pl + [last]
                    pl.sort()
                    
                    # prev/next chapter
                    next = None
                    prev = None
                    try:
                        srcid = str(self.urlToID(options['src']))
                        m = self.cache[srcid]['chapters']
                        state = 0
                        print("searching")
                        for ch in m:
                            if state == 0 and ch[0] == str(id):
                                state = 1
                                lg = ch[3]
                            elif state == 1 and ch[3] == lg:
                                prev = ch[0]
                                break
                        state = 0
                        for ch in reversed(m):
                            if state == 0 and ch[0] == str(id): state = 1
                            elif state == 1 and ch[3] == lg:
                                next = ch[0]
                                break
                    except:
                        pass
                else:
                    next = None
                    prev = None
                    pl = []
                
                # footer
                footer = '<div class="elem">'
                if 'src' not in options: back = '/'
                else: back = '/mdseries?url={}'.format(options['src'])
                if prev is not None: footer += '<a href="/mdchapter?url={}&src={}">Previous</a> # '.format(prev, options['src'])
                footer += '<a href="{}">Back</a>'.format(back)
                if next is not None: footer += ' # <a href="/mdchapter?url={}&src={}">Next</a>'.format(next, options['src'])
                if self.title != "": footer += "<br><b>" + self.title + "</b>"
                footer += "<br>"
                for p in pl:
                    if p == current: footer += "<b>{}</b>".format(p+1)
                    else: footer += '<a href="/mdchapter?url={}&page={}{}">{}</a>'.format(options['url'], p, ('&src={}'.format(options['src']) if 'src' in options else ''), p+1)
                    if p != pl[-1]: footer += ' # '
                footer += '</div>'
                
                # body
                if last < 0:
                    html += footer + '<div class="elem">Chapter unavailable</div>' + footer
                elif current < last:
                    html += footer + '<div><a href="/mdchapter?url={}&page={}{}"><img src="/mdimg?id={}"></a></div>'.format(options['url'], current+1, ('&src={}'.format(options['src']) if 'src' in options else ''), current) + footer + '</body>'
                elif next is not None:
                    html += footer + '<div><a href="/mdchapter?url={}&src={}"><img src="/mdimg?id={}"></a></div>'.format(next, options['src'], current) + footer + '</body>'
                else:
                    html += footer + '<div><img src="/mdimg?id={}"></div>'.format(current) + footer + '</body>'
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open chapter")
                print(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', ''))
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mdimg?'):
            options = self.server.getOptions(path, 'mdimg')
            try:
                img = self.pages[int(options['id'])]
                if isinstance(img, str):
                    if self.loadImage(img, int(options['id'])):
                        img = self.pages[int(options['id'])]
                    else:
                        raise Exception('Loading failed')
                handler.answer(200, {'Content-type': 'image/jpg'}, img)
            except Exception as e:
                print("Can't access page", options.get('id', '?'))
                print(e)
                handler.answer(404)
            return True
        return False

    def process_post(self, handler, path):
        return False
        
    def get_interface(self):
        html = '<b>Mangadex Browser</b><br><a href="/md?">Home</a><br><a href="/mdgenres">Genres</a>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Mangadex Browser plugin</b><br>A cookie is saved in config.json.'