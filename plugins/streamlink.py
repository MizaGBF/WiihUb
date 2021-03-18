import subprocess
from subprocess import DEVNULL
import time
import urllib.parse

class Streamlink():
    def __init__(self, server):
        self.server = server
        self.last_stream = self.server.data.get("streamlink_stream", "")
        self.last_quality = self.server.data.get("streamlink_quality", "720p60")
        self.history = self.server.data.get("streamlink_history", [])
        self.streamlink_path = self.server.data.get("streamlink_path", "streamlink")
        self.streamlink_port = self.server.data.get("streamlink_port", 65313)
        self.streamlink = None
        self.streamlink_url = None
        self.streamlink_current  = None
        self.notification = None

    def stop(self):
        self.server.data["streamlink_stream"] = self.last_stream
        self.server.data["streamlink_quality"] = self.last_quality
        self.server.data["streamlink_history"] = self.history
        self.server.data["streamlink_path"] = self.streamlink_path
        self.server.data["streamlink_port"] = self.streamlink_port
        self.streamlink_kill()

    def streamlink_kill(self):
        try:
            self.streamlink.terminate()
            self.streamlink.wait()
            self.streamlink = None
            print("Stopped the streamlink instance")
        except:
            self.streamlink = None

    def get_history(self):
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a><br>'
        if self.streamlink is not None:
            html += '<a href="{}">Watch {}</a><br><form action="/kill"><input type="submit" value="Stop Streamlink"></form>'.format(self.streamlink_url, self.streamlink_current, self.streamlink_current)
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += "</div>"
        html += '<div class="elem">'
        for h in self.history:
            html += '<a href="/twitch?stream={}&qual={}">{} ({})</a><br>'.format(h[0], h[1], h[0], h[1])
        if len(self.history) == 0:
            html += 'No streams in the memory'
        html += "</div>"
        return html

    def remove_from_history(self, user):
        i = 0
        while i < len(self.history):
            if self.history[i][0] == user:
                self.history.pop(i)
            else:
                i += 1

    def add_to_history(self, user, qual):
        self.remove_from_history(user)
        self.history = [[user, qual]] + self.history
        if len(self.history) > 50: self.history = self.history[:50]

    def process_get(self, handler, path):
        if path.startswith('/twitch?'):
            host_address = handler.headers.get('Host')
            options = self.server.getOptions(path, 'twitch')
            try:
                if 'stream' not in options: raise Exception()
                if options.get('qual', '') == '720p': options['qual'] = '720p60' # force 60 fps, twitch removed 30
                tmp = subprocess.Popen([self.streamlink_path, "--twitch-disable-ads", "--twitch-disable-hosting", "--hls-live-edge", "1", "--hls-segment-threads", "2", "--player-external-http", "--player-external-http-port", str(self.streamlink_port), "twitch.tv/{}".format(options['stream']), options.get('qual', '720p60')])
                time.sleep(8)
                print("Checking if stream is available...")
                if tmp.poll() is None:
                    print("Stream started")
                    self.streamlink_kill()
                    self.streamlink = tmp
                    self.last_stream = options['stream']
                    self.last_quality = options.get('qual', self.last_quality)
                    self.streamlink_url = 'http://{}:{}'.format(host_address.split(":")[0], self.streamlink_port)
                    self.streamlink_current = '{}'.format(options['stream'])
                    self.add_to_history(options['stream'], options.get('qual', self.last_quality))
                    handler.answer(303, {'Location': self.streamlink_url})
                else:
                    try:
                        tmp.terminate()
                        tmp.wait()
                    except:
                        pass
                    raise Exception()
                return True
            except Exception as e:
                print("Stream not found")
                print(e)
                self.notification = "Stream not found"
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
                return True
        elif path.startswith('/streamlinkhistory'):
            handler.answer(200, {'Content-type': 'text/html'}, self.get_history().encode('utf-8'))
            return True
        elif path.startswith('/streamlinkadvanced'):
            html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
            html += '<div class="elem"><a href="/">Back</a><br>'
            if self.notification is not None:
                html += "{}<br>".format(self.notification)
                self.notification = None
            html += '</div>'
            html += '<div class="elem">Open any url using Streamlink. Results might vary.<br><form action="/streamlinkcustom"><label for="url">Url </label><input type="text" id="url" name="url" value=""><br><label for="qual">Quality </label><input type="text" id="qual" name="qual" value="best"><br><label for="options">Options </label><input type="text" id="options" name="options" value=""><br><input type="submit" value="Start"></form>'
            handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            return True
        elif path.startswith('/streamlinkcustom?'):
            host_address = handler.headers.get('Host')
            options = self.server.getOptions(path, 'streamlinkcustom')
            try:
                if 'url' not in options: raise Exception()
                params = [self.streamlink_path]
                o = urllib.parse.unquote(options.get('options', '').replace('+', ' '))
                if o != '': params += o.split(' ')
                params += ["--hls-live-edge", "1", "--hls-segment-threads", "2", "--player-external-http", "--player-external-http-port", str(self.streamlink_port), "{}".format(urllib.parse.unquote(options['url'])), options.get('qual', 'best')]
                tmp = subprocess.Popen(params)
                time.sleep(8)
                print("Checking if stream is available...")
                if tmp.poll() is None:
                    print("Stream started")
                    self.streamlink_kill()
                    self.streamlink = tmp
                    self.streamlink_url = 'http://{}:{}'.format(host_address.split(":")[0], self.streamlink_port)
                    tmp = urllib.parse.unquote(options['url']).split('/')
                    for t in tmp:
                        if '.' in t:
                            self.streamlink_current = '.'.join(t.split('.')[-2:])
                            break
                    handler.answer(303, {'Location': self.streamlink_url})
                else:
                    try:
                        tmp.terminate()
                        tmp.wait()
                    except:
                        pass
                    raise Exception()
                return True
            except Exception as e:
                print("Stream not found")
                print(e)
                self.notification = "Stream not found"
                handler.answer(303, {'Location': 'http://{}'.format(host_address)})
                return True
        elif path.startswith('/kill'):
            self.streamlink_kill()
            host_address = handler.headers.get('Host')
            self.notification = "Streamlink Stopped"
            handler.answer(303, {'Location': 'http://{}'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<form action="/twitch"><legend><b>Twitch</b></legend><label for="stream">Stream </label><input type="text" id="stream" name="stream" value="{}"><br><label for="qual">Quality </label><input type="text" id="qual" name="qual" value="{}"><br><input type="submit" value="Start"></form><a href="streamlinkhistory">History</a><br><a href="streamlinkadvanced">Advanced</a><br>'.format(self.last_stream, self.last_quality)
        if self.streamlink is not None:
            html += '<a href="{}">Watch {}</a><br><form action="/kill"><input type="submit" value="Stop Streamlink"></form>'.format(self.streamlink_url, self.streamlink_current, self.streamlink_current)
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Twitch plugin</b><br>If needed, Streamlink path must be defined in config.json, at "streamlink_path".<br>Currently, only one instance can run at once.<br>Check <a href="https://www.neoseeker.com/members/Dynamite/blog/10285990-viewing-twitch-streams-on-wii-u-using-livestreamer/">this</a> on how to modify Livestream/Streamlink to make it compatible with the Wii U'