import tweepy
import webbrowser
import datetime

class Twitter():
    def __init__(self, server):
        self.server = server
        self.running = False
        self.notification = None

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
        pass

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if not self.running:
            handler.send_response(303)
            handler.send_header('Location','http://{}'.format(host_address))
            handler.end_headers()
            return True
        if path.startswith('/twitter?'):
            path_str = str(path)[len('/twitter?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                item = self.twitter_api.get_user(options['account'])
                if item is not None:
                    handler.send_response(200)
                    handler.send_header('Content-type', 'text/html')
                    handler.end_headers()
                    handler.wfile.write(self.get_twitter(item).encode('utf-8'))
                    return True
                
                print("name: " + item.name)
                print("screen_name: " + item.screen_name)
                print("description: " + item.description)
                print("statuses_count: " + str(item.statuses_count))
                print("friends_count: " + str(item.friends_count))
                print("followers_count: " + str(item.followers_count))
            except Exception as e:
                print("Twitter error")
                print(e)
            
            handler.send_response(303)
            handler.send_header('Location','http://{}'.format(host_address))
            handler.end_headers()
            return True
        return False

    def process_post(self, handler, path):
        return False

    def getTimedeltaStr(self, delta):
        d = delta.days
        h = delta.seconds // 3600
        m = (delta.seconds // 60) % 60
        s = delta.seconds % 60
        msg = ""
        if d > 0: msg += "{}d".format(d)
        if h > 0: msg += "{}h".format(h)
        if m > 0: msg += "{}m".format(m)
        if s > 0: msg += "{}s".format(s)
        return msg

    def get_twitter(self, item):
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} img{ max-width:400px; max-height:300px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem">'+self.get_interface()+'<a href="/">Back</a></div>'
        html += '<div class="elem"><b><a href="/twitter?account={}">{}</a><br></b>{}</div>'.format(item.screen_name, item.name, item.description)
        tweet_count = ""
        for status in tweepy.Cursor(self.twitter_api.user_timeline, id=item.screen_name, tweet_mode='extended').items(40):
            try:
                tweet = "<b>{}</b> {} ago<br>".format(item.name, self.getTimedeltaStr(datetime.datetime.utcnow() - status.created_at))
                tweet += status.full_text.replace('\n', '<br>')
                try:
                    tweet += '<br><img src="{}">'.format(status.entities['media'][0]['media_url'])
                    tweet = tweet.replace(status.entities['media'][0]['url'], '')
                except: pass
                for m in status.entities['urls']:
                    tweet = tweet.replace(m['url'], '<a href="{}">{}</a>'.format(m['expanded_url'].replace('https://twitch.tv/', '/twitch?stream='), m['expanded_url']))
                for m in status.entities['user_mentions']:
                    tweet = tweet.replace('@'+m['screen_name'], '<a href="/twitter?account={}">@{}</a>'.format(m['screen_name'], m['screen_name']))
                html += '<div class="elem">{}</div>'.format(tweet)
            except: pass
        html += '</div></body>'
        return html

    def get_interface(self):
        html = '<form action="/twitter"><legend><b>Twitter Browser</b></legend><label for="account">Account </label><input type="text" id="account" name="account" value=""><br><input type="submit" value="Search"></form>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Twitter Browser plugin</b><br>A Twitter account is required to access the API.'