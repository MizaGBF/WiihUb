import tweepy
import webbrowser
import datetime
import urllib.parse

class Twitter():
    def __init__(self, server):
        self.server = server
        self.running = False
        self.notification = None
        self.bookmarks = self.server.data.get('twitter_bookmarks', [])

        try: # test registered keys (if any)
            self.auth = tweepy.OAuthHandler(self.server.data['twitter_consumer_key'], self.server.data['twitter_consumer_secret'])
            self.auth.set_access_token(self.server.data['twitter_access_token'], self.server.data['twitter_access_token_secret'])
            self.twitter_api = tweepy.API(self.auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
            if self.twitter_api.verify_credentials() is None: raise Exception()
            self.running = True
        except: # ask for authentification
            print("Twitter authentification is required")
            self.auth = tweepy.OAuthHandler("b3yOKDCjF7fQhrNRRkHtvprIq", "Pk3po2cCfXHaKGPQuoleytbpHRxrPPTDy0s52NcK1AZvV3RIIv")
            try:
                redirect_url = self.auth.get_authorization_url()
                webbrowser.open(redirect_url, new=2)
                print("(Twitter) Please input the code PIN")
                code = input()
                self.auth.get_access_token(code)
                self.twitter_api = tweepy.API(self.auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
                if self.twitter_api.verify_credentials() is None: raise Exception()
                self.server.data['twitter_consumer_key'] = 'b3yOKDCjF7fQhrNRRkHtvprIq'
                self.server.data['twitter_consumer_secret'] = 'Pk3po2cCfXHaKGPQuoleytbpHRxrPPTDy0s52NcK1AZvV3RIIv'
                self.server.data['twitter_access_token'] = self.auth.access_token
                self.server.data['twitter_access_token_secret'] = self.auth.access_token_secret
                self.running = True
            except Exception as x:
                print("Authentification failed")
                print(x)

    def stop(self):
        self.server.data['twitter_bookmarks'] = self.bookmarks

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if not self.running:
            self.notification = "Twitter not enabled"
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        if path.startswith('/twitter?'):
            options = self.server.getOptions(path, 'twitter')
            try:
                item = self.twitter_api.get_user(options['account'])
                page = int(options.get('page', 1))
                if item is not None:
                    handler.answer(200, {'Content-type': 'text/html'}, self.get_twitter(item, page).encode('utf-8'))
                    return True
                else: raise Exception('Account not found')
            except Exception as e:
                print("Twitter error")
                print(e)
                self.notification += "Twitter Error\n" + str(e)
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/tweet?'):
            options = self.server.getOptions(path, 'tweet')
            try:
                item = self.twitter_api.get_status(options['id'], tweet_mode='extended')
                if item is not None:
                    handler.answer(200, {'Content-type': 'text/html'}, self.get_tweet(item).encode('utf-8'))
                    return True
                else: raise Exception('Tweet not found')
            except Exception as e:
                print("Tweet error")
                print(e)
                self.notification += "Tweet Error\n" + str(e)
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/twittersearch?'):
            options = self.server.getOptions(path, 'twittersearch')
            try:
                handler.answer(200, {'Content-type': 'text/html'}, self.get_search(urllib.parse.unquote(options['query']), int(options.get('page', 1))).encode('utf-8'))
                return True
            except Exception as e:
                print("Twitter search error")
                print(e)
                self.notification += "Twitter search Error\n" + str(e)
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/twitterdel?'):
            options = self.server.getOptions(path, 'twitterdel')
            try:
                i = 0
                while i < len(self.bookmarks):
                    if self.bookmarks[i] == options['account']:
                        self.bookmarks.pop(i)
                    else:
                        i += 1
            except Exception as e:
                print("Twitter Bookmark Del error")
                print(e)
            if 'source' in options: loc = 'http://{}/twitter?account={}'.format(host_address, options['source'])
            else: loc = 'http://{}'.format(host_address)
            handler.answer(303, {'Location': loc})
            return True
        elif path.startswith('/twitteradd?'):
            options = self.server.getOptions(path, 'twitteradd')
            try:
                self.bookmarks.append(options['account'])
            except Exception as e:
                print("Twitter Bookmark Add error")
                print(e)
            if 'source' in options: loc = 'http://{}/twitter?account={}'.format(host_address, options['source'])
            else: loc = 'http://{}'.format(host_address)
            print('GOTO', loc)
            handler.answer(303, {'Location': loc})
            return True
        elif path.startswith('/twitterbookmark'):
            handler.answer(200, {'Content-type': 'text/html'}, self.get_bookmarks().encode('utf-8'))
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_bookmarks(self):
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem"><a href="/">Back</a><br><form action="/twitter"><label for="account">Account </label><input type="text" id="account" name="account" value=""><br><input type="submit" value="Search User"></form></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        for b in self.bookmarks:
            html += '<a href="/twitter?account={}">@{}</a><br>'.format(b, b)
        if len(self.bookmarks) == 0: html += "No bookmarks found"
        html += '</div>'
        return html

    def getTimedeltaStr(self, delta):
        y = delta.days // 365
        d = delta.days % 365
        h = delta.seconds // 3600
        m = (delta.seconds // 60) % 60
        s = delta.seconds % 60
        msg = ""
        if y > 0: return "{}y".format(y)
        if d > 3: return "{}d".format(d)
        elif d > 0: msg += "{}d".format(d)
        if h > 0: msg += "{}h".format(h)
        if m > 0: msg += "{}m".format(m)
        if s > 0: msg += "{}s".format(s)
        return msg

    def get_tweet(self, item):
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} img{ max-width:400px; max-height:300px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem">'+self.get_interface()+'<a href="/">Back</a><br>'
        if item.user.screen_name in self.bookmarks: html += '<a href="/twitterdel?account={}&source={}">Remove from bookmarks</a>'.format(item.user.screen_name, item.user.screen_name)
        else: html += '<a href="/twitteradd?account={}&source={}">Add to bookmarks</a>'.format(item.user.screen_name, item.user.screen_name)
        html += '</div>'
        html += '<div class="elem"><img height="50" src="{}" align="left" /><b><a href="/twitter?account={}">{}</a><br></b>{}</div>'.format(item.user.profile_image_url, item.user.screen_name, item.user.name, item.user.description.replace('\n', '<br>'))
        
        html += '<div class="elem">{}</div>'.format(self.statusToHTML(item))
        html += '<div class="elem"><b>First Replies</b></div>'
        for r in tweepy.Cursor(self.twitter_api.search, q='to:{}'.format(item.user.name), since_id=item.id_str, tweet_mode='extended').items(30):
            if not hasattr(r, 'in_reply_to_status_id_str'):
                continue
            if r.in_reply_to_status_id_str == item.id_str:
                html += '<div class="elem">{}</div>'.format(self.statusToHTML(r))
        html += '</div>'
        html += '</body>'
        return html

    def get_twitter(self, item, page=1):
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} img{ max-width:400px; max-height:300px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem">'+self.get_interface()+'<a href="/">Back</a><br>'
        if item.screen_name in self.bookmarks: html += '<a href="/twitterdel?account={}&source={}">Remove from bookmarks</a>'.format(item.screen_name, item.screen_name)
        else: html += '<a href="/twitteradd?account={}&source={}">Add to bookmarks</a>'.format(item.screen_name, item.screen_name)
        page_footer = '<div style="font-size:30px">'
        for pi in range(max(1, page-5), max(1, page+5)):
            if pi < page:
                page_footer += '<a href="/twitter?account={}&page={}">{}</a> #'.format(item.screen_name, pi, pi)
            elif pi == page:
                page_footer += '<b>{}</b>'.format(pi)
            else:
                page_footer += '# <a href="/twitter?account={}&page={}">{}</a>'.format(item.screen_name, pi, pi)
        page_footer += '</div>'
        html += '<br>' + page_footer
        html += '</div>'
        html += '<div class="elem"><img height="50" src="{}" align="left" /><b><a href="/twitter?account={}">{}</a><br></b>{}</div>'.format(item.profile_image_url, item.screen_name, item.name, item.description.replace('\n', '<br>'))
        
        count = 1
        for pt in tweepy.Cursor(self.twitter_api.user_timeline, id=item.screen_name, tweet_mode='extended').pages():
            if count < page:
                count += 1
                continue
            count += 1
            for cst in pt:
                status = cst
                html += '<div class="elem">{}</div>'.format(self.statusToHTML(cst))
            break
        html += '</div>'
        html += '<div class="elem">' + page_footer + '</div>'
        html += '</body>'
        return html

    def get_search(self, query, page=1):
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} img{ max-width:400px; max-height:300px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem">'+self.get_interface()+'<a href="/">Back</a><br>'
        page_footer = '<div style="font-size:30px">'
        for pi in range(max(1, page-5), max(1, page+5)):
            if pi < page:
                page_footer += '<a href="/twittersearch?query={}&page={}">{}</a> #'.format(query, pi, pi)
            elif pi == page:
                page_footer += '<b>{}</b>'.format(pi)
            else:
                page_footer += '# <a href="/twittersearch?query={}&page={}">{}</a>'.format(query, pi, pi)
        page_footer += '</div>'
        html += '<br>' + page_footer
        html += '</div>'
        
        count = 1
        for pt in tweepy.Cursor(self.twitter_api.search, q='{} -filter:retweets'.format(query), tweet_mode='extended').pages():
            if count < page:
                count += 1
                continue
            count += 1
            for cst in pt:
                status = cst
                html += '<div class="elem">{}</div>'.format(self.statusToHTML(cst))
            break
        html += '</div>'
        html += '<div class="elem">' + page_footer + '</div>'
        html += '</body>'
        return html

    def formatTweetText(self, text):
        if len(text) > 0:
            text = text.replace('\n', '<br>')
            c = 0
            while True:
                tmp = text.find('#', c)
                if tmp == -1: break
                c = tmp
                while True:
                    tmp += 1
                    if not text[tmp].isalnum() or tmp == len(text):
                        break
                if c < tmp:
                    hashtag = text[c:tmp]
                    replaced = '<a href="/twittersearch?query={}">{}</a>&nbsp;'.format(urllib.parse.quote(hashtag), hashtag)
                    text = text[:c] + replaced + text[tmp:]
                    c += len(replaced)
        return text

    def statusToHTML(self, status):
        try:
            tweet = ""
            if status.full_text.startswith('RT @'):
                status = status.retweeted_status
                tweet += '<img height="16" src="{}" align="left" />'.format(status.user.profile_image_url)
                tweet += "<b>Retweet from</b>&nbsp;"
            else:
                tweet += '<img height="16" src="{}" align="left" />'.format(status.user.profile_image_url)
            tweet += '<b><a href="/twitter?account={}">{}</a></b> {} ago # <a href="/tweet?id={}">Open</a><br>'.format(status.user.screen_name, status.user.name, self.getTimedeltaStr(datetime.datetime.utcnow() - status.created_at), status.id_str)
            tweet += self.formatTweetText(status.full_text)
            try:
                tweet += '<br><img src="{}">'.format(status.entities['media'][0]['media_url'])
                tweet = tweet.replace(status.entities['media'][0]['url'], '')
            except: pass
            for m in status.entities['urls']:
                if m['expanded_url'].startswith('https://twitter.com/'):
                    urltid = m['expanded_url'].split('/')
                    if len(urltid) > 0:
                        tweet = tweet.replace(m['url'], '<a href="/tweet?id={}">{}</a>'.format(urltid[-1], m['expanded_url']))
                else:
                    tweet = tweet.replace(m['url'], '<a href="{}">{}</a>'.format(m['expanded_url'].replace('https://twitch.tv/', '/twitch?stream=').replace('http://twitch.tv/', '/twitch?stream='), m['expanded_url']))
            for m in status.entities['user_mentions']:
                tweet = tweet.replace('@'+m['screen_name'], '<a href="/twitter?account={}">@{}</a>'.format(m['screen_name'], m['screen_name']))
            tweet += '<br><div style="font-size:12px">{} RT, {} Likes</div>'.format(status.retweet_count, status.favorite_count)
        except Exception as e: 
            return 'Tweet failed to load:<br>{}'.format(e)
        return tweet

    def get_interface(self):
        html = '<form action="/twittersearch"><legend><b>Twitter Browser</b></legend><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form>'
        if len(self.bookmarks) > 0:
            html += '<a href="/twitterbookmark">Open Bookmarks</a><br>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Twitter Browser plugin</b><br>A Twitter account is required to access the API.'