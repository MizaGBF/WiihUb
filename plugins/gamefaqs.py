import json
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup

class Gamefaqs():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.cookies = self.server.data.get("gamefaqs_cookie", {})
        self.games = {}
        self.loadGameDB()
        if len(self.games) == 0: self.getAllWiiUGames()

    def stop(self):
        self.server.data["gamefaqs_cookie"] = self.cookies

    def loadGameDB(self):
        try:
            with open('gamefaqs.json') as f:
                self.games = json.load(f)
            return True
        except Exception as e:
            print("loadGameDB() exception\n{}".format(self.server.printex(e)))
            return False

    def saveGameDB(self):
        try:
            with open('gamefaqs.json', 'w') as f:
                json.dump(self.games, f)
            return False
        except Exception as e:
            print("saveGameDB() exception\n{}".format(self.server.printex(e)))
            return True

    def updateCookie(self, headers):
        res = {}
        ck = headers.get('set-cookie', '').split('; ')
        for c in ck:
            s = c.split('=', 1)
            if s[0] in ['path', 'domain'] or len(s) != 2: continue
            res[s[0]] = s[1]
        self.cookies = {**self.cookies, **res}

    def buildCookie(self, c):
        s = ""
        for k in c:
            s += k + "=" + c[k] + "; "
        return s

    def requestGF(self, url, use_json=False):
        rep = self.server.http_client.get(url, headers={"User-Agent": self.server.user_agent_common, "Cookie": self.buildCookie(self.cookies)}, follow_redirects=True)
        if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
        self.updateCookie(rep.headers)
        if use_json: return rep.json()
        else: return rep.text

    def processAndStoreGame(self, game):
        if 'title' not in game:
            return False
        processed_game = {}
        processed_game['title'] = game['title'].text
        processed_game['url'] = game['title'].findChildren('a', recursive=False)[0].attrs['href']
        for k in game:
            if k not in processed_game:
                processed_game[k] = True
        self.games[processed_game['title'].lower()] = processed_game
        return True

    def getAllWiiUGames(self):
        endpoint = 'https://gamefaqs.gamespot.com/wii-u/category/999-all?page={}'
        sections = {'rtitle':'title', '/faqs':'faq', '/cheats':'cheat', '/answers':'answer', '/boards/':'board'}
        page = 0
        while True:
            try:
                html = self.requestGF(endpoint.format(page))
                soup = BeautifulSoup(html, "html.parser")
                results = soup.find_all('table')
                added = 0
                if len(results) == 0: raise Exception()
                for r in results:
                    trs = r.findChildren("tr", recursive=True)
                    for tr in trs:
                        game = {}
                        tds = tr.findChildren("td", recursive=False)
                        for td in tds:
                            if 'class' in td.attrs:
                                pass
                            for k in sections:
                                if k in str(td):
                                    game[sections[k]] = td
                                    break
                        if self.processAndStoreGame(game): added += 1
                page += 1
                if added == 0: break
            except:
                break
        self.saveGameDB()

    def getFaq(self, url):
        try:
            url = 'https://gamefaqs.gamespot.com' + url
            html = self.requestGF(url)
            soup = BeautifulSoup(html, "html.parser")
            results = soup.find_all('div', {"class": "faqtext", "id":"faqtext"})
            return results[0].text.replace('\n', '<br>')
        except Exception as e:
            self.server.printex(e)
            return None

    def getFaqList(self, title):
        try:
            game = self.games[title.lower()]
            if 'faq' not in game: raise Exception(title + " has no FAQs")
            url = 'https://gamefaqs.gamespot.com' + game['url'] + '/faqs'
            faqs = []
            html = self.requestGF(url)
            soup = BeautifulSoup(html, "html.parser")
            results = soup.find_all('div', {"class": ["pod", "faqs"]})
            for r in results:
                bodies = r.findChildren("div", class_="body", recursive=False)
                for b in bodies:
                    f = {}
                    try:
                        lis = b.findChildren("li", recursive=True)
                        for li in lis:
                            ref = li.findChildren("a", class_="bold", recursive=True)[0]
                            if game['url'] in ref.attrs['href']:
                                f['url'] = ref.attrs['href']
                                f['title'] = ref.text
                                faqs.append(f)
                    except:
                        pass
            return faqs
        except Exception as e:
            self.server.printex(e)
            return []

    def getCheatList(self, title):
        try:
            game = self.games[title.lower()]
            if 'faq' not in game: raise Exception(title + " has no Cheats")
            url = 'https://gamefaqs.gamespot.com' + game['url'] + '/cheats'
            cheats = []
            html = self.requestGF(url)
            soup = BeautifulSoup(html, "html.parser")
            results = soup.find_all('div', {"class": "content"})
            for r in results:
                subs = r.findChildren(['h4', 'p', 'table'], recursive=True)
                for s in subs:
                    if s.name == 'h4':
                        cheats.append('<b>' + s.text + '</b>') # title
                        try:
                            cheats.append('<i>' + r.findChildren('div', recursive=False)[0].text + '</i>')
                        except:
                            pass
                    elif s.name == 'table':
                        buf = '<table>'
                        trs = s.findChildren('tr', recursive=True)
                        for tr in trs:
                            buf += '<tr>'
                            tds = tr.findChildren(['th', 'td'], recursive=True)
                            for td in tds:
                                buf += '<th>' + td.text + "</th>"
                            buf += '</tr>'
                        cheats.append(buf + '</table>')
                    else:
                        cheats.append(s.text)
            return cheats
        except Exception as e:
            self.server.printex(e)
            return []

    def getAnswer(self, url):
        try:
            url = 'https://gamefaqs.gamespot.com' + url
            answers = []
            html = self.requestGF(url)
            soup = BeautifulSoup(html, "html.parser")
            results = soup.find_all('tbody')
            divs = soup.findChildren('div', class_='msg_text', recursive=True)
            for d in divs:
                answers.append(d.text)
            return answers
        except Exception as e:
            self.server.printex(e)
            return []

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/gamelist'):
            try:
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/">Back</a><br><form action="/gamesearch"><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form></div>'
                html += footer
                html += '<div class="elem">'
                for k in self.games:
                    html += '<b>{}</b> #&nbsp;'.format(self.games[k]['title'])
                    if 'faq' in self.games[k]: html += '<a href="/gamefaqs?title={}">Faqs</a>&nbsp;'.format(quote(k))
                    if 'cheat' in self.games[k]: html += '<a href="/gamecheats?title={}">Cheats</a>&nbsp;'.format(quote(k))
                    if 'answer' in self.games[k]: html += '<a href="/gameanswers?title={}">Answers</a>&nbsp;'.format(quote(k))
                    #if 'board' in self.games[k]: html += '<a href="/gameboards?title={}">Boards</a>&nbsp;'.format(quote(k))
                    html += '<br>'
                if len(self.games) == 0:
                    html += "No games loaded"
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open game list")
                self.server.printex(e)
                self.notification = 'Failed to open game list'
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
        elif path.startswith('/gamesearch?'):
            options = self.server.getOptions(path, 'gamesearch')
            try:
                search = unquote(options['query']).replace('+', ' ').lower()
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/">Back</a><br><form action="/gamesearch"><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form></div>'
                html += footer
                html += '<div class="elem">'
                html += "Searched: <b>{}</b><br><br>".format(search)
                count = 0
                for k in self.games:
                    if search in k:
                        html += '<b>{}</b> #&nbsp;'.format(self.games[k]['title'])
                        if 'faq' in self.games[k]: html += '<a href="/gamefaqs?title={}">Faqs</a>&nbsp;'.format(quote(k))
                        if 'cheat' in self.games[k]: html += '<a href="/gamecheats?title={}">Cheats</a>&nbsp;'.format(quote(k))
                        if 'answer' in self.games[k]: html += '<a href="/gameanswers?title={}">Answers</a>&nbsp;'.format(quote(k))
                        #if 'board' in self.games[k]: html += '<a href="/gameboards?title={}">Boards</a>&nbsp;'.format(quote(k))
                        html += '<br>'
                        count += 1
                if count == 0:
                    html += "No games found"
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open game list")
                self.server.printex(e)
                self.notification = 'Failed to open game list'
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/gamefaqs?'):
            options = self.server.getOptions(path, 'gamefaqs')
            try:
                title = unquote(options['title']).replace('+', ' ').lower()
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/gamelist">Back</a></div>'
                html += footer
                html += '<div class="elem">'
                html += "FAQs for: <b>{}</b><br><br>".format(title)
                fl = self.getFaqList(title)
                for faq in fl:
                    html += '<a href="/gamefaq?url={}">{}</a><br>'.format(faq['url'], faq['title'])
                if len(fl) == 0:
                    html += "No FAQs found"
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open game faq list")
                self.server.printex(e)
                self.notification = 'Failed to open game faq list for {}'.format(title)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/gamefaq?'):
            options = self.server.getOptions(path, 'gamefaq')
            try:
                url = unquote(options['url']).replace('+', ' ').lower()
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/">Back</a></div>'
                html += footer
                html += '<div class="elem">'
                faq = self.getFaq(url)
                if faq is None: raise Exception("faq not found")
                html += faq
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open game faq")
                self.server.printex(e)
                self.notification = 'Failed to open game faq at {}'.format(url)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/gamecheats?'):
            options = self.server.getOptions(path, 'gamecheats')
            try:
                title = unquote(options['title']).replace('+', ' ').lower()
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/gamelist">Back</a></div>'
                html += footer
                html += '<div class="elem">'
                html += "Cheats for: <b>{}</b><br><br>".format(title)
                cl = self.getCheatList(title)
                for cheat in cl:
                    html += cheat + '<br>'
                if len(cl) == 0:
                    html += "No Cheats found"
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open game cheat list")
                self.server.printex(e)
                self.notification = 'Failed to open game cheat list for {}'.format(title)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/gameanswers?'):
            options = self.server.getOptions(path, 'gameanswers')
            try:
                title = unquote(options['title']).replace('+', ' ').lower()
                if title not in self.games: raise Exception('Unknown game error')
                id = int(self.games[title]['url'].replace('/wii-u/', '').split('-')[0])
                search = unquote(options.get('query', '')).replace('+', ' ')
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/gamelist">Back</a></div>'
                html += footer
                html += '<div class="elem"><form action="/gameanswers"><legend><b>Search in Answers</b></legend><label for="query">Search </label><input id="title" name="title" type="hidden" value="{}"><input type="text" id="query" name="query" value="{}"><br><input type="submit" value="Send"></form>'.format(title, search)
                if search != "":
                    html += "Answers for: <b>{}</b><br><br>".format(search)
                    results = self.requestGF("https://gamefaqs.gamespot.com/ajax/gamespace_search?id={}&term=&group=answers&term={}".format(id, search), True)
                    if len(results) == 0:
                        html += 'No results'
                    for r in results:
                        if 'value' in r:
                            html += '<a href="/gameloadanswer?url={}">{}</a><br>'.format(r['value'], r['label'])
                html += '</div>'
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open answer search")
                self.server.printex(e)
                self.notification = 'Failed to open answer search:<br>' + str(e)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/gameloadanswer?'):
            options = self.server.getOptions(path, 'gameloadanswer')
            try:
                url = unquote(options['url'])
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                footer = '<div class="elem"><a href="/gamelist">Back</a></div>'
                html += footer
                answers = self.getAnswer(url)
                for a in answers:
                    html += '<div class="elem">{}</div>'.format(a)
                html += footer
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open answer")
                self.server.printex(e)
                self.notification = 'Failed to open answer {}'.format(url)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/gamerefresh'):
            self.getAllWiiUGames()
            self.notification = 'Game list refreshed'
            handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False
        
    def get_interface(self):
        html = '<form action="/gamesearch"><legend><b>Wii U Gamefaqs Browser</b></legend><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form><a href="/gamelist">Open List</a><br>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Wii U Gamefaqs Browser plugin</b><br>Only list the Wii U games.<br>Don\'t abuse but you can refresh the game list <a href="/gamerefresh">here</a><br>'