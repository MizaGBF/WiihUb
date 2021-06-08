import requests
from urllib.parse import quote, unquote
import time
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
import threading

class Mangadex():
    def __init__(self, server):
        self.server = server
        self.api = "https://api.mangadex.org"
        self.cookies = self.server.data.get("mangadex_cookie", {})
        self.lang_filter = self.server.data.get("mangadex_languages", ['en'])
        self.cache = {}
        self.imgcache = {}
        self.lock = threading.Lock()
        self.notification = None
        self.page_limit = 40

    def stop(self):
        self.server.data["mangadex_cookie"] = self.cookies
        self.server.data["mangadex_bookmark"] = self.bookmarks
        self.server.data["mangadex_languages"] = self.lang_filter

    def updateCookie(self, headers):
        res = {}
        ck = headers.get('Set-Cookie', '').split('; ')
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

    def requestGet(self, url, headers={}, params={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["user-Agent"] = self.server.user_agent_common
        headers["Connection"] = "close"
        rep = requests.get(url, headers=headers, params=params)
        if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
        self.updateCookie(rep.headers)
        return rep

    def requestGetStream(self, url, headers={}):
        headers["Cookie"] = self.buildCookie(self.cookies)
        headers["user-Agent"] = self.server.user_agent_common
        headers["Connection"] = "close"
        headers["referer"] = "https://mangadex.org/"
        rep = requests.get(url, headers=headers, stream=True)
        if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
        self.updateCookie(rep.headers)
        raw = rep.raw.read()
        return raw

    def get_manga_cover(self, id):
        time.sleep(1)
        return self.requestGet(f"{self.api}/cover/{id}").json()

    def get_manga_covers(self, offset, ids):
        time.sleep(1)
        return self.requestGet(f"{self.api}/cover", params={"offset":offset, "limit":100, "ids[]":ids}).json()

    def get_manga_info(self, id):
        time.sleep(1)
        js = self.requestGet(f"{self.api}/manga/{id}").json()
        if js['result'] == 'error': return None
        if js['data']['id'] not in self.cache:
            self.cache[js['data']['id']] = js['data']
            self.cache[js['data']['id']]['chapter_list'] = None
            self.cache[js['data']['id']]['cover'] = None

            for r in js['relationships']:
                if r['type'] == 'cover_art':
                    covert_id = r['id']
            self.cache[js['data']['id']]['cover'] = self.get_manga_cover(covert_id)['data']['attributes']['fileName']
        return js

    def get_mangas(self, params={}):
        params['limit'] = self.page_limit
        params['order[updatedAt]'] = "desc"
        time.sleep(0.5)
        js = self.requestGet(f"{self.api}/manga", params=params).json()
        if js.get('result', None) is not None:
            return None
        covers = []
        for m in js['results']:
            self.cache[m['data']['id']] = m['data']
            self.cache[m['data']['id']]['chapter_list'] = None
            self.cache[m['data']['id']]['cover'] = None
            for r in m['relationships']:
                if r['type'] == 'cover_art':
                    covers.append(r['id'])
                    break
        if len(covers) > 0:
            offset = 0
            total = 1
            while offset < total:
                covers = self.get_manga_covers(offset, covers)
                total = covers['total']
                for c in covers['results']:
                    for r in c['relationships']:
                        if r['type'] == 'manga':
                            self.cache[r['id']]['cover'] = c['data']['attributes']['fileName']
                            break
                offset += len(covers['results'])

        return [m['data'] for m in js['results']], js['total']

    def get_chapters(self, id):
        if id not in self.cache:
            self.get_manga_info(id)
        if self.cache[id]['chapter_list'] is not None: return
        self.cache[id]['chapter_list'] = []
        offset = 0
        total = 1
        while offset < total:
            time.sleep(1)
            j = self.requestGet(f"{self.api}/manga/{id}/feed", params={"limit":500, "offset":offset}).json()
            if j.get('result', None) is not None: raise Exception(f"Failed to retrieve chapters for series {id}")
            for c in j['results']:
                if self.lang_filter is None or len(self.lang_filter) == 0 or c['data']["attributes"]["translatedLanguage"] in self.lang_filter:
                    issorted = False
                    for i in range(0, len(self.cache[id]['chapter_list'])):
                        if c['data']["attributes"]["volume"] is None:
                            if self.cache[id]['chapter_list'][i]["attributes"]["volume"] is None:
                                if float(c['data']["attributes"]["chapter"]) > float(self.cache[id]['chapter_list'][i]["attributes"]["chapter"]):
                                    self.cache[id]['chapter_list'].insert(i, c['data'])
                                    issorted = True
                                    break
                            else:
                                self.cache[id]['chapter_list'].insert(i, c['data'])
                                issorted = True
                                break
                        else:
                            if self.cache[id]['chapter_list'][i]["attributes"]["volume"] is not None:
                                if float(c['data']["attributes"]["volume"]) > float(self.cache[id]['chapter_list'][i]["attributes"]["volume"]):
                                    self.cache[id]['chapter_list'].insert(i, c['data'])
                                    issorted = True
                                    break
                                elif float(c['data']["attributes"]["volume"]) == float(self.cache[id]['chapter_list'][i]["attributes"]["volume"]) and float(c['data']["attributes"]["chapter"]) > float(self.cache[id]['chapter_list'][i]["attributes"]["chapter"]):
                                    self.cache[id]['chapter_list'].insert(i, c['data'])
                                    issorted = True
                                    break
                    if not issorted:
                        self.cache[id]['chapter_list'].append(c['data'])
            total = j['total']
            offset += len(j['results'])

    def get_pages(self, id, cid):
        if id not in self.cache:
            self.get_chapters(id)
        next = None
        for i in range(0, len(self.cache[id]['chapter_list'])):
            if cid == self.cache[id]['chapter_list'][i]['id']:
                return (None if (i >= len(self.cache[id]['chapter_list'])) else self.cache[id]['chapter_list'][i+1]), self.cache[id]['chapter_list'][i], next
            next = self.cache[id]['chapter_list'][i]
        return None, None, None

    def get_tags(self):
        time.sleep(1)
        return self.requestGet(f"{self.api}/manga/tag").json()['baseUrl']

    def compress(self, data):
        with BytesIO(data) as file:
            base = Image.open(file)
            conv = base.convert('RGB')
            base.close()
            with BytesIO() as out:
                conv.save(out, format='JPEG')
                conv.close()
                return out.getvalue()

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/manga'): # cache cleanup
            with self.lock:
                if len(self.cache) > 400:
                    keys = list(self.cache.keys())[200:]
                    data = {}
                    for key in keys:
                        data[key] = self.cache[key]
                    self.cache = data
        if path.startswith('/manga?'):
            options = self.server.getOptions(path, 'manga')
            try:
                query = unquote(options.get('query', '').replace('+', ' '))
                tag = options.get('tag', '')
                page = int(options.get('page', 0))
                name = unquote(options.get('name', '').replace('+', ' '))
                if name == '': name = query
                if tag != '':
                    mangas, total = self.get_mangas({'offset':page*self.page_limit, "includedTags[]":[tag]})
                    app = f"&tag={tag}"
                elif query != '':
                    mangas, total = self.get_mangas({'offset':page*self.page_limit, "title":query})
                    app = f"&query={quote(query).replace(' ', '+')}"
                else:
                    mangas, total = self.get_mangas({'offset':page*self.page_limit})
                    app = ""
                last = total // 20
                pl = list(range(max(page-10, 0), min(page+16, last+1)))
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} .subelem {width: 200px;display: inline-block;}</style>'

                # footer
                footer = '<div class="elem">'
                footer += '<a href="/">Back</a><br>'
                footer += f'<form action="/manga"><label for="query">Search </label><input type="text" id="query" name="query" value="{query}"><br><input type="submit" value="Send"></form><br>'
                if name != '': footer += f'Searched <b>{name}</b><br>'
                for p in pl:
                    if p == page: footer += f"<b>{p+1}</b>"
                    else: footer += f'<a href="/manga?page={p}{app}">{p+1}</a>'
                    if p != pl[-1]: footer += ' # '
                footer += '</div>'

                html += footer

                html += '<div class="elem">'
                for m in mangas:
                    html += f'<div class="subelem"><a href="mangaseries?id={m["id"]}"><img style="max-height:300px;max-width:auto;height:270px;width:auto;" src="/mangaimg?url=https://uploads.mangadex.org/covers/{m["id"]}/{m["cover"]}" /><br>{m["attributes"]["title"]["en"]}</a></div>'
                if len(mangas) == 0:
                    html += "No mangas found"
                html += '</div>'
                html += footer
                html += '</body>'
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open mangadex")
                self.server.printex(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', '')) # TODO
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mangaseries?'):
            options = self.server.getOptions(path, 'mangaseries')
            try:
                id = options['id']
                self.get_chapters(id)
                m = self.cache[id]
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/manga?">Back</a>'
                footer += '</div>'
                
                html += footer + '<div class="elem">'
                html += f'<img height="200" src="/mangaimg?url=https://uploads.mangadex.org/covers/{m["id"]}/{m["cover"]}" align="left" />'
                html += f'<b>{m["attributes"]["title"]["en"]}</b><br>'
                html += "tags:<br>"
                for t in m['attributes']['tags']:
                    html += f'<a href="/manga?tag={t["id"]}&name={quote("Tag: " + t["attributes"]["name"]["en"]).replace(" ", "+")}">{t["attributes"]["name"]["en"]}</a>'
                    if t is not m['attributes']['tags'][-1]: html += ", "
                html += "</div>"
                
                html += '<div class="elem">'
                for ch in m['chapter_list']:
                    html += f'<a href="/mangachapter?id={id}&chapter={ch["id"]}">Vol.{ch["attributes"]["volume"]} Chapter {ch["attributes"]["chapter"]} {ch["attributes"]["title"]}</a> ({ch["attributes"]["translatedLanguage"]})<br>'
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open manga")
                self.server.printex(e)
                self.notification = 'Failed to open series {}'.format(options.get('id', '')) # TODO
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mangachapter?'):
            options = self.server.getOptions(path, 'mangachapter')
            try:
                id = options['id']
                cid = options['chapter']
                page = int(options.get('page', 0))
                prev, ch, next = self.get_pages(id, cid)
                last = len(ch["attributes"]['data'])-1
                pl = list(range(max(page-5, 0), min(page+6, last+1)))
                for px in range(0, 1 + last // 10):
                    if px * 10 not in pl: pl.append(px*10)
                if last not in pl: pl.append(last)
                pl.sort()
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size: 180%;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                
                # footer
                footer = '<div class="elem">'
                if prev is not None: footer += f'<a href="/mangachapter?id={id}&chapter={prev["id"]}">Previous</a> # '
                footer += f'<a href="/mangaseries?id={id}">Back</a>'
                if next is not None: footer += f' # <a href="/mangachapter?id={id}&chapter={next["id"]}">Next</a>'
                if ch["attributes"]["title"] != "": footer += "<br><b>" + ch["attributes"]["title"] + "</b>"
                footer += "<br>"
                for p in pl:
                    if p == page: footer += f"<b>{p+1}</b>"
                    else: footer += f'<a href="/mangachapter?id={id}&chapter={cid}&page={p}">{p+1}</a>'
                    if p != pl[-1]: footer += ' # '
                footer += '</div>'
                
                # body
                imgurl = f"https://uploads.mangadex.org/data/{ch['attributes']['hash']}/{ch['attributes']['data'][page]}"
                if page < last:
                    html += f'{footer}<div><a href="/mangachapter?id={id}&chapter={cid}&page={page+1}"><img src="/mangaimg?url={imgurl}"></a></div>{footer}</body>'
                elif next is not None:
                    html += f'{footer}<div><a href="/mangachapter?id={id}&chapter={next["id"]}"><img src="/mangaimg?url={imgurl}"></a></div>{footer}</body>'
                else:
                    html += f'{footer}<div><a href="/mangaseries?id={id}"><img src="/mangaimg?url={imgurl}"></a></div>{footer}</body>'
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open chapter")
                self.server.printex(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', ''))
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mangatags'):
            try:
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} .subelem {width: 200px;display: inline-block;}</style>'
                html += '<div class="elem"><a href="/">Back</a><br></div>'
                html += '<div class="elem">'
                tags = self.get_tags()
                for t in tags:
                    html += f'<a href="/manga?tag={t["data"]["id"]}&name={quote("Tag: " + t["data"]["attributes"]["name"]["en"]).replace(" ", "+")}">{t["data"]["attributes"]["name"]["en"]}</a><br>'
                html += '</div>'
                html += '</body>'
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open chapter")
                self.server.printex(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', ''))
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/mangaimg?'):
            options = self.server.getOptions(path, 'mangaimg')
            try:
                url = unquote(options['url'])
                if url in self.imgcache:
                    ext = url.split('.')[-1]
                    raw = self.imgcache[url]
                else:
                    ext = url.split('.')[-1]
                    time.sleep(0.2)
                    raw = self.compress(self.requestGetStream(url))
                    with self.lock:
                        self.imgcache[url] = raw
                        if len(self.imgcache) > 200:
                            keys = list(self.imgcache.keys())[150:]
                            imdata = {}
                            for key in keys:
                                imdata[key] = self.imgcache[key]
                            self.imgcache = imdata
                handler.answer(200, {'Content-type': 'image/jpg'}, self.imgcache[url])
                return True
            except Exception as e:
                print("Failed to open image")
                self.server.printex(e)
                self.notification = 'Failed to open {}'.format(options.get('url', ''))
                handler.answer(404, {})
            return True
        return False

    def process_post(self, handler, path):
        return False
        
    def get_interface(self):
        html = '<b>Mangadex Browser</b><br><a href="/manga?">Home</a><br><a href="/mangatags">Tags</a><br><form action="/manga"><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form><br>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Mangadex Browser plugin</b><br>A cookie is saved in config.json.'