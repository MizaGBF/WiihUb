from urllib.request import urlopen
from urllib import request
import urllib.parse
import json
import concurrent.futures

class Mangadex():
    def __init__(self, server):
        self.server = server
        self.chapter_id = None
        self.pages = []
        self.hash = None
        self.md_server = None
        self.notification = None

    def stop(self):
        pass

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
        req = request.Request(url)
        url_handle = request.urlopen(req)
        self.pages[index] = url_handle.read()
        return True

    def loadChapter(self, id):
        if id != self.chapter_id:
            try:
                req = request.Request("https://mangadex.org/api/?id={}&server=null&saver=1&type=chapter".format(id))
                url_handle = request.urlopen(req)
                data = json.loads(url_handle.read())
                self.md_server = data['server']
                self.hash = data['hash']
                self.pages = []
                while len(self.pages) < len(data['page_array']): self.pages.append(None)
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(data['page_array'])) as executor:
                    ft = {executor.submit(self.loadImage, "{}{}/{}".format(self.md_server, self.hash, data['page_array'][i]), i): i for i in range(0, len(data['page_array']))}
                    count = 0
                    for f in concurrent.futures.as_completed(ft):
                        if f: count += 1
                    print(count, "/", len(data['page_array']), "images loaded")
                self.chapter_id = id
                return True
            except:
                return False
        return True

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/mangadex?'):
            path_str = str(path)[len('/mangadex?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                id = self.urlToID(urllib.parse.unquote(options['url']))
                if id is None or not self.loadChapter(id): raise Exception()
                current = int(options.get('page', 0))
                last = len(self.pages)-1
                
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size: 180%;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                footer = '<div class="elem">'
                if current > 0: footer += '<a href="/mangadex?url={}&page={}">Previous</a> # '.format(options['url'], current-1)
                footer += '<a href="/">Back</a> # <a href="https://mangadex.org/chapter/{}">Link</a>'.format(id)
                if current < last: footer += ' # <a href="/mangadex?url={}&page={}">Next</a>'.format(options['url'], current+1)
                footer += '</div>'
                html += footer + '<div><img src="/mangaimg?id={}"</div>'.format(current) + footer + '</body>'
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write(html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open chapter")
                print(e)
                self.notification = 'Failed to open <a href="{}">{}</a><br>{}'.format(options.get('url', ''), options.get('url', ''))
                handler.send_response(303)
                handler.send_header('Location','http://{}'.format(host_address))
                handler.end_headers()
            return True
        elif path.startswith('/mangaimg?'):
            path_str = str(path)[len('/mangaimg?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                handler.send_response(200)
                handler.send_header('Content-type', 'image/jpg')
                handler.end_headers()
                handler.wfile.write(self.pages[int(options['id'])])
            except Exception as e:
                print("Can't access page", options.get('id', '?'))
                print(e)
                handler.send_response(404)
                handler.end_headers()
            return True
        return False

    def process_post(self, handler, path):
        return False
        
    def get_interface(self):
        html = '<form action="/mangadex"><legend><b>Mangadex Loader</b></legend><label for="url">URL </label><input type="text" id="url" name="url" value=""><br><input type="submit" value="Load"></form>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Mangadex Loader plugin</b><br>Input the url of a chapter to load it.'