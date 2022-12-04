from urllib.parse import quote, unquote
import tweepy
import webbrowser
import datetime
import threading

class Twitter():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.bookmarks = self.server.data.get('twitter_bookmarks', [])
        self.client = None
        self.user_cache = {}
        self.token_cache = {}
        self.img_cache = {}
        self.lock = threading.Lock()
        self.bearer = self.server.data.get('twitter_bearer_token', None)
        try: self.client = tweepy.Client(bearer_token = self.bearer)
        except: pass

    def stop(self):
        self.server.data['twitter_bookmarks'] = self.bookmarks
        self.server.data['twitter_bearer_token'] = self.bearer

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if (path.startswith('/twitter') or path.startswith('/tweet')) and self.client is None:
            self.notification = "Twitter not enabled"
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        if path.startswith('/twitter?'):
            options = self.server.getOptions(path, 'twitter')
            try:
                handler.answer(200, {'Content-type': 'text/html'}, self.getTimeline(options['account'], options.get('token', None)).encode('utf-8'))
                return True
            except Exception as e:
                print("Twitter error")
                self.server.printex(e)
                self.notification += "Twitter Error\n" + str(e)
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/tweet?'):
            options = self.server.getOptions(path, 'tweet')
            try:
                handler.answer(200, {'Content-type': 'text/html'}, self.get_single_tweet(options['id']).encode('utf-8'))
                return True
            except Exception as e:
                print("Tweet error")
                self.server.printex(e)
                self.notification += "Tweet Error\n" + str(e)
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/twittersearch?'):
            options = self.server.getOptions(path, 'twittersearch')
            try:
                handler.answer(200, {'Content-type': 'text/html'}, self.getQuery(unquote(options['query'].replace('+', ' ')) + " -is:retweet", options.get('token', None)).encode('utf-8'))
                return True
            except Exception as e:
                print("Twitter search error")
                self.server.printex(e)
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
                self.server.printex(e)
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
                self.server.printex(e)
            if 'source' in options: loc = 'http://{}/twitter?account={}'.format(host_address, options['source'])
            else: loc = 'http://{}'.format(host_address)
            handler.answer(303, {'Location': loc})
            return True
        elif path.startswith('/twitterbookmark'):
            handler.answer(200, {'Content-type': 'text/html'}, self.get_bookmarks().encode('utf-8'))
            return True
        elif path.startswith('/twittersetup'):
            handler.answer(200, {'Content-type': 'text/html'}, self.get_setup().encode('utf-8'))
            return True
        elif path.startswith('/twitterkey?'):
            options = self.server.getOptions(path, 'twitterkey')
            try:
                self.bearer = unquote(options['key'])
                try: self.client = tweepy.Client(bearer_token = self.bearer)
                except: pass
                self.notification += "Key Set Successfully"
            except Exception as e:
                self.notification += "An error occured\n" + str(e)
                self.server.printex(e)
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        elif path.startswith('/twitterimg?'):
            options = self.server.getOptions(path, 'twitterimg')
            try:
                url = unquote(options['url'])
                if url in self.img_cache:
                    raw = self.img_cache[url]
                else:
                    rep = self.server.http_client.get(url, headers={'User-Agent':self.server.user_agent_common})
                    if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
                    raw = rep.content
                    with self.lock:
                        self.img_cache[url] = raw
                        if len(self.img_cache) > 50:
                            keys = list(self.img_cache.keys())[50:]
                            imdata = {}
                            for key in keys:
                                imdata[key] = self.img_cache[key]
                            self.img_cache = imdata
                handler.answer(200, {'Content-type': 'image/jpg'}, self.img_cache[url])
                return True
            except Exception as e:
                print("Failed to open image")
                self.server.printex(e)
                handler.answer(404, {})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_bookmarks(self):
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
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

    def get_setup(self):
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a><br><form action="/twitterkey"><label for="key">Set Token </label><input type="text" id="key" name="key" value=""><br><input type="submit" value="Send"></form></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
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

    def get_user(self, id):
        if id in self.user_cache:
            return self.user_cache[id]
        try:
            user = self.client.get_user(id=id, user_fields=['description', 'profile_image_url', 'pinned_tweet_id']).data
            if len(list(self.user_cache.keys())) > 100:
                self.user_cache = {}
            self.user_cache[id] = user
            return user
        except:
            return None

    def update_user(self, id, user):
        self.user_cache[id] = user

    def get_single_tweet(self, id):
        tweets = self.client.get_tweets(ids=[id], tweet_fields=['context_annotations', 'created_at', 'entities', 'public_metrics'], user_fields=['profile_image_url'], media_fields=['preview_image_url', 'url'], expansions=['author_id', 'attachments.media_keys', 'entities.mentions.username', 'referenced_tweets.id', 'referenced_tweets.id.author_id'])
        tweet = tweets.data[0]
        print("=========================", tweet.author_id)
        user = self.get_user(tweet.author_id)
        try: media = {m["media_key"]: m for m in tweets.includes['media']}
        except: media = {}
        for u in tweets.includes.get('users', []):
            self.update_user(u.id, u)
        try: references = {m.id: m for m in tweets.includes['tweets']}
        except: references = {}

        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} img{ max-width:400px; max-height:300px;}</style><div>'
        html += '<div class="elem">'+self.get_interface()+'<a href="/">Back</a><br>'
        if user.username in self.bookmarks: html += '<a href="/twitterdel?account={}&source={}">Remove from bookmarks</a>'.format(user.username, user.username)
        else: html += '<a href="/twitteradd?account={}&source={}">Add to bookmarks</a>'.format(user.username, user.username)
        html += '</div>'
        html += '<div class="elem">{}</div>'.format(self.tweetToHTML(tweet, media, references))
        html += '</div>'
        html += '</body>'
        return html

    def getTimeline(self, username, token):
        user = self.client.get_user(username=username, user_fields=['description', 'profile_image_url', 'pinned_tweet_id']).data
        self.update_user(user.id, user)
        if token is None:
            tweets = self.client.get_users_tweets(id=user.id, tweet_fields=['context_annotations', 'created_at', 'entities', 'public_metrics'], user_fields=['profile_image_url'], media_fields=['preview_image_url', 'url'], expansions=['author_id', 'attachments.media_keys', 'entities.mentions.username', 'referenced_tweets.id', 'referenced_tweets.id.author_id'], max_results=10)
        else:
            tweets = self.client.get_users_tweets(id=user.id, tweet_fields=['context_annotations', 'created_at', 'entities', 'public_metrics'], user_fields=['profile_image_url'], media_fields=['preview_image_url', 'url'], expansions=['author_id', 'attachments.media_keys', 'entities.mentions.username', 'referenced_tweets.id', 'referenced_tweets.id.author_id'], pagination_token=token, max_results=10)
        try: next_token = tweets.meta['next_token']
        except: next_token = None
        try: prev_token = tweets.meta['previous_token']
        except: prev_token = None
        try: media = {m["media_key"]: m for m in tweets.includes['media']}
        except: media = {}
        for u in tweets.includes.get('users', []):
            self.update_user(u.id, u)
        try: references = {m.id: m for m in tweets.includes['tweets']}
        except: references = {}

        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} img{ max-width:400px; max-height:300px;}</style><div>'
        html += '<div class="elem">'+self.get_interface()+'<a href="/">Back</a><br>'
        if username in self.bookmarks: html += '<a href="/twitterdel?account={}&source={}">Remove from bookmarks</a>'.format(username, username)
        else: html += '<a href="/twitteradd?account={}&source={}">Add to bookmarks</a>'.format(username, username)
        page_footer = ""
        if prev_token is not None and prev_token != "None":
            page_footer += '<a href="/twitter?account={}&token={}">Previous</a>'.format(username, prev_token)
        if next_token is not None and next_token != "None":
            if page_footer != "": page_footer += " # "
            page_footer += '<a href="/twitter?account={}&token={}">Next</a>'.format(username, next_token)
        page_footer = '<div style="font-size:30px">' + page_footer + '</div>'
        html += '<br>' + page_footer
        html += '</div>'
        html += '<div class="elem"><img height="50" src="{}" align="left" /><b><a href="/twitter?account={}">{}</a><br></b>{}</div>'.format(user.profile_image_url, user.username, user.name, user.description.replace('\n', '<br>'))

        for tweet in tweets.data:
            html += '<div class="elem">{}</div>'.format(self.tweetToHTML(tweet, media, references))
        html += '</div>'
        html += '<div class="elem">' + page_footer + '</div>'
        html += '</body>'
        return html

    def getQuery(self, query, token):
        if token is None:
            tweets = self.client.search_recent_tweets(query=query, tweet_fields=['context_annotations', 'created_at', 'entities', 'public_metrics'], user_fields=['profile_image_url'], media_fields=['preview_image_url', 'url'], expansions=['author_id', 'attachments.media_keys', 'entities.mentions.username', 'referenced_tweets.id', 'referenced_tweets.id.author_id'], max_results=10)
        else:
            tweets = self.client.search_recent_tweets(query=query, tweet_fields=['context_annotations', 'created_at', 'entities', 'public_metrics'], user_fields=['profile_image_url'], media_fields=['preview_image_url', 'url'], expansions=['author_id', 'attachments.media_keys', 'entities.mentions.username', 'referenced_tweets.id', 'referenced_tweets.id.author_id'], next_token=token, max_results=10)
        
        cache_size = 0
        for k in self.token_cache:
            cache_size += len(list(self.token_cache[k].keys()))
            if cache_size > 100:
                tmp = self.token_cache.get(query, {})
                self.token_cache = {query:tmp}
                break
        
        try:
            next_token = tweets.meta['next_token']
            if token is not None:
                if query not in self.token_cache:
                    self.token_cache[query] = {}
                if next_token not in self.token_cache[query]:
                    self.token_cache[query][next_token] = token
        except: next_token = None
        try: prev_token = self.token_cache[query][token]
        except: prev_token = None
        try: media = {m["media_key"]: m for m in tweets.includes['media']}
        except: media = {}
        for u in tweets.includes.get('users', []):
            self.update_user(u.id, u)
        try: references = {m.id: m for m in tweets.includes['tweets']}
        except: references = {}

        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;} img{ max-width:400px; max-height:300px;}</style><div>'
        html += '<div class="elem">'+self.get_interface()+'<a href="/">Back</a><br>'
        page_footer = ""
        if prev_token is None and token is not None:
            page_footer += '<a href="/twittersearch?query={}">Previous</a>'.format(quote(query))
        elif prev_token is not None:
            page_footer += '<a href="/twittersearch?query={}&token={}">Previous</a>'.format(quote(query), prev_token)
        if next_token is not None and next_token != "None":
            if page_footer != "": page_footer += " # "
            page_footer += '<a href="/twittersearch?query={}&token={}">Next</a>'.format(quote(query), next_token)
        page_footer = '<div style="font-size:30px">' + page_footer + '</div>'
        html += '<br>' + page_footer
        html += '</div>'

        if tweets.data is None:
            html += '<div class="elem">No results found</div>'
        else:
            for tweet in tweets.data:
                html += '<div class="elem">{}</div>'.format(self.tweetToHTML(tweet, media, references))
        html += '</div>'
        if page_footer != "":
            html += '<div class="elem">' + page_footer + '</div>'
        html += '</body>'
        return html

    def tweetTextFormat(self, status):
        text = status.text
        if status.entities and 'hashtags' in status.entities:
            for h in reversed(status.entities['hashtags']):
                text = text[:h['start']] + '<a href="/twittersearch?query=' + h['tag'] + '">#' + h['tag'] + '</a>&nbsp;' +  text[h['end']:]
        return text.replace('\n', '<br>')

    def tweetExtraFormat(self, tweet, status, media):
        try:
            attachments = status.data['attachments']
            media_keys = attachments['media_keys']
            first = True
            for k in media_keys:
                try:
                    if first:
                        tweet += '<br>'
                        first = False
                    if media[k].type == 'photo':
                        tweet += '<img src="/twitterimg?url={}">'.format(quote(media[k].url))
                    elif media[k].type == 'video':
                        tweet += '<img src="/twitterimg?url={}">'.format(quote(media[k].url))
                    else:
                        tweet += '<img src="/twitterimg?url={}">'.format(quote(media[k].preview_image_url))
                except:
                    pass
        except:
            pass
        if status.entities:
            if'urls' in status.entities:
                for m in status.entities['urls']:
                    if m['expanded_url'].startswith('https://twitter.com/') and ('/photo/' in m['expanded_url'] or '/video/' in m['expanded_url']):
                        tweet = tweet.replace(m['url'], '')
                    elif m['expanded_url'].startswith('https://twitter.com/'):
                        urltid = m['expanded_url'].split('/')
                        if len(urltid) > 0:
                            tweet = tweet.replace(m['url'], '<a href="/tweet?id={}">{}</a>&nbsp;'.format(urltid[-1], m['expanded_url']))
                    else:
                        tweet = tweet.replace(m['url'], '<a href="{}">{}</a>&nbsp;'.format(m['expanded_url'].replace('https://twitch.tv/', '/twitch?stream=').replace('http://twitch.tv/', '/twitch?stream=').replace('https://m.twitch.tv/', '/twitch?stream=').replace('http://m.twitch.tv/', '/twitch?stream=').replace('https://www.twitch.tv/', '/twitch?stream=').replace('http://www.twitch.tv/', '/twitch?stream=').replace('https://www.pixiv.net/en/artworks/', '/pixivpage?id=').replace('https://www.pixiv.net/artworks/', '/pixivpage?id='), m['expanded_url']))
            if 'mentions' in status.entities:
                for m in status.entities['mentions']:
                    tweet = tweet.replace('@'+m['username'], '<a href="/twitter?account={}">@{}</a>&nbsp;'.format(m['username'], m['username']))
        return tweet.replace('?s=20', '')


    def tweetToHTML(self, status, media, references, type=None):
        try:
            tweet = ""
            user = self.get_user(status.author_id)
            if type is None:
                tweet += '<img height="16" src="{}" align="left" />'.format(user.profile_image_url)
            else:
                tweet += '<br><br><img height="16" src="{}" align="left" />'.format(user.profile_image_url)
                if type == "retweeted": tweet += "<b>Retweeted</b>&nbsp;"
                elif type == "quoted": tweet += "<b>Quoted</b>&nbsp;"
                elif type == "replied_to": tweet += "<b>Replied to</b>&nbsp;"
            tweet += '<b><a href="/twitter?account={}">{}</a></b> {} ago # <a href="/tweet?id={}">Open</a><br>'.format(user.username, user.name, self.getTimedeltaStr(datetime.datetime.now(datetime.timezone.utc) - status.created_at), status.id)
            
            try:
                if type is not None: raise Exception()
                ref = status.referenced_tweets[0]
                r = references[ref.id]
                if r is not None:
                    if ref.type in ["retweeted", "quoted", "replied_to"]:
                        if ref.type != "retweeted":
                            if status.public_metrics:
                                tweet += '<div style="font-size:12px">{} Replies, {} RT, {} Quotes, {} Likes</div><br>'.format(status.public_metrics['reply_count'], status.public_metrics['retweet_count'], status.public_metrics['quote_count'], status.public_metrics['like_count'])
                            tweet += self.tweetTextFormat(status)
                            tweet = self.tweetExtraFormat(tweet, status, media)
                    
                        tweets = self.client.get_tweets(ids=[r.id], tweet_fields=['context_annotations', 'created_at', 'entities', 'public_metrics'], user_fields=['profile_image_url'], media_fields=['preview_image_url', 'url'], expansions=['author_id', 'attachments.media_keys', 'entities.mentions.username', 'referenced_tweets.id', 'referenced_tweets.id.author_id'])
                        r = tweets.data[0]
                        try: _media = {m["media_key"]: m for m in tweets.includes['media']}
                        except: _media = {}
                        for u in tweets.includes.get('users', []):
                            self.update_user(u.id, u)
                        try: _references = {m.id: m for m in tweets.includes['tweets']}
                        except: _references = {}
                        tweet += self.tweetToHTML(r, _media, _references, ref.type)
                        return tweet
                    else:
                        raise Exception()
                else:
                    raise Exception()
            except:
                if status.public_metrics:
                    tweet += '<div style="font-size:12px">{} Replies, {} RT, {} Quotes, {} Likes</div><br>'.format(status.public_metrics['reply_count'], status.public_metrics['retweet_count'], status.public_metrics['quote_count'], status.public_metrics['like_count'])
                tweet += self.tweetTextFormat(status)
                tweet = self.tweetExtraFormat(tweet, status, media)
        except Exception as e: 
            self.server.printex(e)
            return '<b>Tweet failed to load:</b><br>{}<br>{}<br>'.format(e, status)
        return tweet

    def get_interface(self):
        html = '<form action="/twittersearch"><legend><b>Twitter Browser</b></legend><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form>'
        html += '<a href="/twitterbookmark">Open Bookmarks</a><br>'
        html += '<br><a href="/twittersetup">Set Bearer Token</a><br>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Twitter Browser plugin</b><br>A Developer Twitter account is required to access the API and use this plugin.'