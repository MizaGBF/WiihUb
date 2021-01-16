from pixivpy3 import *
from urllib.request import urlopen
from urllib import request
import urllib.parse
import base64
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO

class Pixiv():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.running = None
        self.cache = {}
        self.credentials = self.server.data.get("pixiv_login", ["login", "password"])
        self.token = self.server.data.get("pixiv_token", None)
        self.api = None

    def login(self):
        if self.running == False: return
        try:
            self.api = AppPixivAPI()
            if self.token is None:
                self.token = self.api.auth(self.credentials[0], self.credentials[1], None)
            else:
                self.token = self.api.auth(self.credentials[0], self.credentials[1], self.token)
            self.api.require_auth()
            self.running = True
        except Exception as e:
            print('Not logged on Pixiv')
            self.running = False

    def stop(self):
        self.server.data["pixiv_login"] = self.credentials
        self.server.data["pixiv_token"] = self.token

    def downloadImageAndConvert(self, url):
        req = request.Request(url, headers={'Referer': 'https://app-api.pixiv.net/'})
        url_handle = request.urlopen(req)
        data = url_handle.read()
        url_handle.close()
        file_data = BytesIO(data)
        dt = Image.open(file_data)
        rgb_im = dt.convert('RGB')
        temp = BytesIO()
        rgb_im.save(temp, format="png")
        return temp.getbuffer()

    def retrieve(self, options={}):
        if len(self.cache) > 400: self.cache = {}
        
        mode = int(options.get('mode', 0))
        if mode == 0:
            json_result = self.api.illust_follow()
        elif mode == 1:
            json_result = self.api.user_illusts(int(options['userid']))
        elif mode == 2:
            json_result = self.api.search_illust(urllib.parse.unquote(options['search'].replace('+', ' ')))
        elif mode == -1:
            json_result = self.api.illust_related(int(options['id']))
        elif mode == -2:
            json_result = self.api.illust_recommended(int(options['id']))
        else:
            raise Exception('Unknown mode')
        for illust in json_result.illusts:
            if illust.id not in self.cache:
                if illust.page_count > 1:
                    self.cache[illust.id] = []
                    for p in illust.meta_pages:
                        self.cache[illust.id].append([p.image_urls.medium, p.image_urls.square_medium])
                else:
                    self.cache[illust.id] = [[illust.image_urls.medium, illust.image_urls.square_medium]]
        return json_result.illusts

    def add_bookmark(self, id):
        self.api.illust_bookmark_add(id)

    def del_bookmark(self, id):
        self.api.illust_bookmark_delete(id)

    def tagsToHTML(self, tags):
        html = ""
        for t in tags:
            html += '<a href="/pixiv?mode=2&search={}">{}</a>&nbsp;'.format(urllib.parse.quote(t['name']), t['name'])
            if 'translated_name' in t and t['translated_name'] != '' and t['translated_name'] is not None:
                html += "{}&nbsp;".format(t['translated_name'])
            if t is not tags[-1]:
                html += ", "
        return html

    def process_get(self, handler, path):
        if path.startswith('/pixiv') and self.running is None: self.login() # only login if used
        if not self.running: return False
        host_address = handler.headers.get('Host')
        if path.startswith('/pixivlogin'): # debug, remove later
            try:
                self.login()
                self.notification = 'Login successful'
            except Exception as e:
                print("Failed to open list")
                print(e)
                self.notification = 'Failed to login, {}'.format(e)
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
        elif path.startswith('/pixiv?'):
            options = self.server.getOptions(path, 'pixiv')
            try:
                illusts = self.retrieve(options)
                if illusts is None:
                    self.login()
                    illusts = self.retrieve(options)
                mode = int(options.get('mode', 0))

                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} .subelem {width: 200px;display: inline-block;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                footer = '<div class="elem"><a href="/">Back</a><br>{}</div>'.format(self.get_search_form(urllib.parse.unquote(options.get('search', '').replace('+', ' '))))
                html += footer

                html += '<div class="elem">'
                if mode == 0:
                    html += '<b>Following illustrations</b><br>'
                    src = ''
                elif mode == 1:
                    html += '<b>{}\'s latest works</b><br>'.format(illusts[0].user.name)
                    src = '&src=' + base64.b64encode('&mode=1&userid={}'.format(illusts[0].user.id).encode('ascii')).decode('ascii')
                elif mode == 2:
                    html += '<b>Search: </b>{}<br>'.format(urllib.parse.unquote(options.get('search', '').replace('+', ' ')))
                    src = '&src=' + base64.b64encode('&mode=2&search={}'.format(urllib.parse.quote(options.get('search', ''))).encode('ascii')).decode('ascii')
                for i in illusts:
                    html += '<div class="subelem"><a href="/pixivpage?id={}{}"><img height="150" src="/pixivimg?id={}&qual=1" /></a><br><b>{}</b></div>'.format(i.id, src, i.id, i.title)
                html += '</div>'
                
                html += footer
                html += "</div></body>"
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open list")
                print(e)
                self.notification = 'Failed to access pixiv, mode {}'.format(options.get('mode', 0))
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/pixivpage?'):
            options = self.server.getOptions(path, 'pixivpage')
            try:
                illust = self.api.illust_detail(int(options['id']))['illust']
                src = base64.b64decode(options.get('src', '')).decode('ascii')
                
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} .subelem {display: inline-block;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                footer = '<div class="elem"><a href="/pixiv?{}">Back</a><br>{}</div>'.format(src, self.get_search_form())
                html += footer

                for i in range(0, illust['page_count']):
                    html += '<div class="elem"><img src="/pixivimg?id={}&qual=0&num={}" /></div>'.format(illust['id'], i)
                html += '<div class="elem"><b>{}</b>&nbsp;{}<br><a href="/pixiv?mode=1&userid={}">{}</a>&nbsp;{}<br>{}<br>Tags:<br>{}<br>'.format(illust['title'], ('<a href="/pixivbookmark?id={}&add=1{}">Bookmarked</a>'.format(illust['id'], ('' if src == '' else '&src={}'.format(src))) if illust['is_bookmarked'] else '<a href="/pixivbookmark?id={}&add=0{}">Not bookmarked</a>'.format(illust['id'], ('' if src == '' else '&src={}'.format(src)))), illust['user']['id'], illust['user']['name'], ('Followed' if illust['user']['is_followed'] else 'Not followed'), illust['caption'], self.tagsToHTML(illust['tags']))
                html += '</div>'
                
                html += '<div class="elem"><b>Related Works</b><br>'
                illusts = self.retrieve({'mode':-1, 'id':illust['id']})
                for i in illusts:
                    html += '<div class="subelem"><a href="/pixivpage?id={}"><img height="100" src="/pixivimg?id={}&qual=1" /></a></div>'.format(i.id, i.id)
                html += '</div>'
                html += '<div class="elem"><b>Recommended Works</b><br>'
                illusts = self.retrieve({'mode':-2, 'id':illust['id']})
                for i in illusts:
                    html += '<div class="subelem"><a href="/pixivpage?id={}"><img height="100" src="/pixivimg?id={}&qual=1" /></a></div>'.format(i.id, i.id)
                html += '</div>'
                
                html += footer
                html += "</div></body>"
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open page")
                print(e)
                self.notification = 'Failed to open page {}'.format(options.get('id', ''))
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/pixivbookmark?'):
            options = self.server.getOptions(path, 'pixivbookmark')
            try:
                id = int(options['id'])
                add = int(options['add'])
                src = options.get('src', '')
                if add == 0: self.add_bookmark(id)
                else: self.del_bookmark(id)
            except Exception as e:
                print("Failed to open image")
                print(e)
            handler.answer(303, {'Location': 'http://{}/pixivpage?id={}{}'.format(host_address, id, ('' if src == '' else '&src={}'.format(src)))})
            return True
        elif path.startswith('/pixivimg?'):
            options = self.server.getOptions(path, 'pixivimg')
            try:
                id = int(options['id'])
                qual = int(options['qual'])
                num = int(options.get('num', 0))
                img = self.cache[id][num][qual]
                if isinstance(img[0], str):
                    self.cache[id][num][qual] = self.downloadImageAndConvert(img)
                    img = self.cache[id][num][qual]
                handler.answer(200, {'Content-type': 'image/jpeg'}, img)
            except Exception as e:
                print("Failed to open image")
                print(e)
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_search_form(self, init=""):
        return '<form action="/pixiv"><label for="search">Search </label><input type="text" id="search" name="search" value="{}"><input type="hidden" name="mode" value="2" /><br><input type="submit" value="Send"></form>'.format(init)

    def get_interface(self):
        if self.running == False:
            html = '<b>Pixiv Browser</b><br>Not logged in'
        else:
            html = '<b>Pixiv Browser</b><br><a href="/pixiv?">Home</a>'
            if self.running == True:
                html += '<br><a href="/pixivlogin">Relogin</a>'
            if self.notification is not None:
                html += "<br>{}".format(self.notification)
                self.notification = None
        return html

    def get_manual(self):
        html = '<b>Pixiv Browser plugin</b><br>Lets you access pixiv.net. A valid account username and password must be set in config.json.'
        return html