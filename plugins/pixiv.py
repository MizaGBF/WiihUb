from pixivpy3 import *
import pykakasi
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
        self.imgs = {}
        self.works = {}
        self.users = {}
        self.credentials = self.server.data.get("pixiv_login", ["login", "password"])
        self.token = self.server.data.get("pixiv_token", None)
        self.papi = None
        self.api = None
        self.kks = pykakasi.kakasi()

    def login(self, papi=True):
        if self.running == False: return
        try:
            if papi:
                self.papi = PixivAPI()
                if self.token is None:
                    self.token = self.papi.auth(self.credentials[0], self.credentials[1], None)
                else:
                    self.token = self.papi.auth(self.credentials[0], self.credentials[1], self.token)
                self.papi.require_auth()
                self.running = True
            else:
                self.api = AppPixivAPI()
                self.api.auth(self.credentials[0], self.credentials[1], None)
                self.api.require_auth()
        except Exception as e:
            print('Not logged on Pixiv,', papi)
            if papi:
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
        width, height = dt.size
        if width * height > 1024 * 1024:
            if width > height: ratio = 1024 / width
            else: ratio = 1024 / height
            dt = dt.resize((round(width*ratio), round(height*ratio)), Image.NEAREST)
        rgb_im = dt.convert('RGB')
        temp = BytesIO()
        rgb_im.save(temp, format="png")
        return temp.getbuffer()

    def retrieve(self, options={}):
         # clean up
        if len(self.imgs) > 500: self.imgs = {}
        if len(self.works) > 1000: self.works = {}
        
        mode = int(options.get('mode', 0))
        page = int(options.get('page', 1))
        if mode == 0:
            json_result = self.papi.me_following_works(page=page)
        elif mode == 1:
            json_result = self.papi.users_works(int(options['userid']), page=page)
        elif mode == 2:
            json_result = self.papi.search_works(urllib.parse.unquote(options['search'].replace('+', ' ')), page=page, mode='exact_tag')
        elif mode == 3:
            json_result = self.papi.ranking('illust', 'weekly', page)
            tmp = []
            for r in json_result.response:
                for w in r.works:
                    tmp.append(w.work)
            json_result.response = tmp
        elif mode == 4:
            json_result = self.papi.works(int(options['id']))
        else:
            raise Exception('Unknown mode')
        for work in json_result.response:
            self.users[work['user']['id']] = work['user']
            if work['id'] not in self.works:
                self.works[work['id']] = work
            self.add_to_img_cache(work['id'])
        return json_result.response

    def add_to_img_cache(self, id):
        if id in self.works:
            work = self.works[id]
            if work['id'] not in self.imgs:
                self.imgs[work['id']] = [[work.image_urls['large'], work.image_urls['px_128x128']]]
                for i in range(1, work['page_count']):
                    self.imgs[work['id']].append([work.image_urls['large'].replace('_p0', '_p'+str(i))])
        else:
            self.retrieve({'mode':4, 'id':id})

    def get_user(self, work):
        if work['user']['id'] not in self.users:
            self.users[work['user']['id']] = work['user']
        return self.users[work['user']['id']]

    def add_bookmark(self, id):
        try:
            self.api.illust_bookmark_add(id)
        except:
            self.login(False)
            self.api.illust_bookmark_add(id)

    def del_bookmark(self, id):
        try:
            self.api.illust_bookmark_delete(id)
        except:
            self.login(False)
            self.api.illust_bookmark_delete(id)

    def add_follow(self, id):
        self.papi.me_favorite_users_follow(id)

    def del_follow(self, id):
        self.papi.me_favorite_users_unfollow(id)

    def tagsToHTML(self, tags):
        html = ""
        for t in tags:
            html += '<a href="/pixiv?mode=2&search={}">{}</a>&nbsp;'.format(urllib.parse.quote(t), t)
            result = self.kks.convert(t)
            for item in result:
                html += "{}&nbsp;".format(item['hepburn'])
            if t is not tags[-1]:
                html += ", "
        return html

    def process_get(self, handler, path):
        if path.startswith('/pixiv') and self.running is None: self.login() # only login if used
        if not self.running: return False
        host_address = handler.headers.get('Host')
        if path.startswith('/pixiv?'):
            options = self.server.getOptions(path, 'pixiv')
            try:
                try:
                    works = self.retrieve(options)
                    if works is None: raise Exception()
                except:
                    self.login()
                    works = self.retrieve(options)
                mode = int(options.get('mode', 0))
                page = int(options.get('page', 1))

                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} .subelem {width: 200px;display: inline-block;}</style>'

                body = '<div class="elem">'
                if mode == 0:
                    body += '<b>Following illustrations</b><br>'
                    src = ''
                    pg = ''
                elif mode == 1:
                    body += '<b>{}\'s latest works</b><br>'.format(works[0].user.name)
                    src = '&src=' + base64.b64encode('&mode=1&userid={}'.format(works[0].user.id).encode('ascii')).decode('ascii')
                    pg = '&userid=' + options.get('userid', '')
                elif mode == 2:
                    body += '<b>Search: </b>{}<br>'.format(urllib.parse.unquote(options.get('search', '').replace('+', ' ')))
                    src = '&src=' + base64.b64encode('&mode=2&search={}'.format(urllib.parse.quote(options.get('search', ''))).encode('ascii')).decode('ascii')
                    pg = '&search=' + options.get('search', '')
                elif mode == 3:
                    body += '<b>Ranking:<br>'
                    src = '&src=' + base64.b64encode('&mode=3'.encode('ascii')).decode('ascii')
                    pg = ''
                if src == '' and 'src' in options: src = '&src=' + options['src']
                
                footer = '<div class="elem"><a href="/">Back</a><br><a href="/pixiv?">Following Works</a><br><a href="/pixiv?mode=3">Ranking</a><br>{}<br>'.format(self.get_search_form(urllib.parse.unquote(options.get('search', '').replace('+', ' '))))
                footer += '<div style="font-size:30px">'
                for i in range(max(1, int(page)-5), int(page)+5):
                    if i < page: footer += '<a href="/pixiv?mode={}&page={}{}{}">{}</a> # '.format(mode, i, pg, src, i)
                    elif i > page: footer += ' # <a href="/pixiv?mode={}&page={}{}{}">{}</a>'.format(mode, i, pg, src, i)
                    else: footer += "<b>{}</b>".format(page)
                footer += '</div></div>'
                html += footer
                html += body
                
                for work in works:
                    html += '<div class="subelem"><a href="/pixivpage?id={}{}"><img height="150" src="/pixivimg?id={}&qual=1" {} /></a><br><b>{}</b></div>'.format(work['id'], src, work['id'], ('style="border-style: solid;border-color: red"' if (work['favorite_id'] != 0 and work['favorite_id'] is not None) else '') , work['title'])
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
                if int(options['id']) in self.works:
                    work = self.works[int(options['id'])]
                else:
                    if 'mode' not in options: options['mode'] = 4
                    try:
                        works = self.retrieve(options)
                        if works is None: raise Exception()
                        work = works[0]
                    except:
                        self.login()
                        work = self.retrieve(options)[0]
                src = base64.b64decode(options.get('src', '')).decode('ascii')
                user = self.get_user(work)
                
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} </style>'
                footer = '<div class="elem"><a href="/pixiv?{}">Back</a><br><a href="/pixiv?">Following Works</a><br><a href="/pixiv?mode=3">Ranking</a><br>{}</div>'.format(src, self.get_search_form())
                html += footer
                for i in range(0, work['page_count']):
                    html += '<div class="elem"><img src="/pixivimg?id={}&qual=0&num={}" /></div>'.format(work['id'], i)
                html += '<div class="elem"><b>{}</b>&nbsp;{}<br><a href="/pixiv?mode=1&userid={}">{}</a>&nbsp;{}<br>{}<br>Tags:<br>{}<br>'.format(work.title, ('<a href="/pixivbookmark?id={}&add=1{}">Bookmarked</a>'.format(work['id'], ('' if src == '' else '&src={}'.format(src))) if (work['favorite_id'] != 0 and work['favorite_id'] is not None) else '<a href="/pixivbookmark?id={}&add=0{}">Not bookmarked</a>'.format(work['id'], ('' if src == '' else '&src={}'.format(src)))), user['id'], user['name'], ('<a href="/pixivfollow?id={}&userid={}&add=1{}">Followed</a>'.format(work['id'], user['id'], ('' if src == '' else '&src={}'.format(src))) if user['is_following'] else '<a href="/pixivfollow?id={}&userid={}&add=0{}">Not followed</a>'.format(work['id'], user['id'], ('' if src == '' else '&src={}'.format(src)))), work.caption, self.tagsToHTML(work['tags']))
                html += '</div>'
                
                html += footer
                html += "</div></body>"
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open page")
                print(e)
                self.notification = 'Failed to open page {}<br>{}'.format(options.get('id', ''), e)
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
                self.works.pop(id)
            except Exception as e:
                print("Failed to bookmark image")
                print(e)
            handler.answer(303, {'Location': 'http://{}/pixivpage?id={}{}'.format(host_address, id, ('' if src == '' else '&src={}'.format(src)))})
            return True
        elif path.startswith('/pixivfollow?'):
            options = self.server.getOptions(path, 'pixivfollow')
            try:
                id = int(options['id'])
                userid = int(options['userid'])
                add = int(options['add'])
                src = options.get('src', '')
                if add == 0: self.add_follow(userid)
                else: self.del_follow(userid)
                self.works.pop(id)
                self.users.pop(userid)
            except Exception as e:
                print("Failed to follow user")
                print(e)
            handler.answer(303, {'Location': 'http://{}/pixivpage?id={}{}'.format(host_address, id, ('' if src == '' else '&src={}'.format(src)))})
            return True
        elif path.startswith('/pixivimg?'):
            options = self.server.getOptions(path, 'pixivimg')
            try:
                id = int(options['id'])
                qual = int(options['qual'])
                num = int(options.get('num', 0))
                if id not in self.imgs:
                    self.add_to_img_cache(id)
                img = self.imgs[id][num][qual]
                if isinstance(img[0], str):
                    self.imgs[id][num][qual] = self.downloadImageAndConvert(img)
                    img = self.imgs[id][num][qual]
                handler.answer(200, {'Content-type': 'image/jpeg'}, img)
            except Exception as e:
                print("Failed to open image")
                print(e)
                handler.answer(200, {'Content-type': 'text/html'}, "Load failed".encode('utf-8'))
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
            html = '<b>Pixiv Browser</b><br><a href="/pixiv?">Following Works</a><br><a href="/pixiv?mode=3">Ranking</a>'
            if self.notification is not None:
                html += "<br>{}".format(self.notification)
                self.notification = None
        return html

    def get_manual(self):
        html = '<b>Pixiv Browser plugin</b><br>Lets you access pixiv.net.<br>A valid account username and password must be set in config.json.<br>Bookmarked works appear with a red border.'
        return html