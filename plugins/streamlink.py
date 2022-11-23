import subprocess
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
        self.quals = {"720p": "Wii U TV", "480p": "Wii U Gamepad", "360p": "N3DS", "160p": "Low Quality", "720p60": "Wii U TV (60 fps)", "1080p": "1080p", "1080p60": "1080p (60 fps)"}
        self.path = self.server.data.get("vlc_path", "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe")
        self.vlc_port = self.server.data.get("streamlink_port", 65313) + 1
        self.vlc = None

    def stop(self):
        self.server.data["streamlink_stream"] = self.last_stream
        self.server.data["streamlink_quality"] = self.last_quality
        self.server.data["streamlink_history"] = self.history
        self.server.data["streamlink_path"] = self.streamlink_path
        self.server.data["streamlink_port"] = self.streamlink_port
        self.server.data["vlc_folder"] = self.folder
        self.server.data["vlc_path"] = self.path
        self.streamlink_kill()

    def streamlink_kill(self):
        if self.kill_process(self.streamlink):
            print("Stopped the streamlink instance")
        if self.kill_process(self.vlc):
            print("Stopped the streamlink instance")
        self.streamlink = None
        self.vlc = None

    def kill_process(self, p):
        try:
            p.terminate()
            p.wait()
            return True
        except:
            return False

    def get_history(self):
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a><br>'
        if self.streamlink is not None:
            html += '<a href="{}">Watch {}</a>'.format(self.streamlink_url, self.streamlink_current)
            vlc_path = self.server.data.get("vlc_path", None)
            if vlc_path is not None:
                html += '<br><a href="/streamlinkads">Try to clear ads and watch</a>'
            html += '<br><form action="/kill"><input type="submit" value="Stop Streamlink"></form>'
        html += "</div>"
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem"><b>History</b><br>'
        for h in self.history:
            html += '<a href="/twitch?stream={}&qual={}">{} ({})</a><br>'.format(h[0], h[1], h[0], self.quals.get(h[1], h[1]))
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
        if len(self.history) > 100: self.history = self.history[:100]

    def start_process(self, params, qual = None):
        stlk = subprocess.Popen([self.streamlink_path] + params)
        if qual is None:
            size = "width=1280,height=720"
        else:
            match qual:
                case "720p": size = "width=1280,height=720"
                case "720p60": size = "width=1280,height=720"
                case "480p": size = "width=854,height=480"
                case "360p": size = "width=640,height=360"
                case "160p": size = "width=284,height=160"
                case "1080p": size = "width=1920,height=1080"
                case "1080p60": size = "width=1920,height=1080"
                case _: size = "width=1280,height=720"
        time.sleep(8)
        print("Checking if stream is available...")
        if stlk.poll() is None:
            self.streamlink_kill()
            self.streamlink = stlk
            self.vlc = subprocess.Popen([self.path, "http://127.0.0.1:{}/".format(self.streamlink_port), '--no-sout-all', '--sout=#transcode{' + size + ',fps=30,vcodec=h264,vb=1200,venc=x264{aud,profile=baseline,level=30,keyint=30,ref=1},acodec=aac,ab=128,channels=2,soverlay}:std{access=http{mime=video/mp4},mux=ts,dst=:' + str(self.vlc_port) + '/'])
            return True
        else:
            self.kill_process(stlk)
        return False

    def process_get(self, handler, path):
        if path.startswith('/twitch?'):
            host_address = handler.headers.get('Host')
            options = self.server.getOptions(path, 'twitch')
            try:
                if 'stream' not in options: raise Exception()
                if self.start_process(["--twitch-disable-ads", "--twitch-disable-hosting", "--stream-segment-threads", "2", "--player-continuous-http", "--player-external-http", "--player-external-http-port", str(self.streamlink_port), "twitch.tv/{}".format(options['stream']), options.get('qual', '720p60')], qual=options.get('qual', '720p60')):
                    time.sleep(8)
                    self.last_stream = options['stream']
                    self.last_quality = options.get('qual', self.last_quality)
                    self.streamlink_url = 'http://{}:{}'.format(host_address.split(":")[0], self.vlc_port)
                    self.streamlink_current = '{}'.format(options['stream'])
                    self.add_to_history(options['stream'], options.get('qual', self.last_quality))
                    handler.answer(303, {'Location': self.streamlink_url})
                else:
                    tmp = subprocess.Popen([self.streamlink_path, "--twitch-disable-ads", "--twitch-disable-hosting", "--stream-segment-threads", "2", "--player-external-http", "--player-external-http-port", str(self.streamlink_port), "twitch.tv/{}".format(options['stream'])], stdout=subprocess.PIPE)
                    lines = tmp.stdout.read().decode('utf-8').split('\n')
                    self.notification = ""
                    for i in range(len(lines)):
                        if lines[i].startswith('error: No playable streams found on this URL'):
                            self.notification = "The Stream is offline"
                            break
                        elif lines[i].startswith('Available streams: '):
                            self.notification = 'Available qualities:<br>' + lines[i][len('Available streams: '):]
                            break
                    if self.notification == "": self.notification = "Couldn't open the stream"
                    self.kill_process(tmp)
                    raise Exception()
                return True
            except Exception as e:
                print("Stream not found")
                self.server.printex(e)
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
            html += '<div class="elem"><form action="/twitch"><legend><b>Open a Twicth stream (manual quality input)</b></legend><label for="stream">Stream </label><input type="text" id="stream" name="stream" value="{}"><br><label for="qual">Quality </label><input type="text" id="qual" name="qual" value="{}"><br><input type="submit" value="Start"></form></div>'.format(self.last_stream, self.last_quality)
            html += '<div class="elem"><form action="/streamlinkcustom"><legend><b>Open any url. Results might vary.</b></legend><label for="url">Url </label><input type="text" id="url" name="url" value=""><br><label for="qual">Quality </label><input type="text" id="qual" name="qual" value="best"><br><label for="options">Options </label><input type="text" id="options" name="options" value=""><br><input type="submit" value="Start"></form>'
            handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            return True
        elif path.startswith('/streamlinkcustom?'):
            host_address = handler.headers.get('Host')
            options = self.server.getOptions(path, 'streamlinkcustom')
            try:
                if 'url' not in options: raise Exception()
                params = []
                o = urllib.parse.unquote(options.get('options', '').replace('+', ' '))
                if o != '': params += o.split(' ')
                params += ["--player-external-http", "--player-external-http-port", str(self.streamlink_port), "{}".format(urllib.parse.unquote(options['url'])), options.get('qual', 'best')]
                if self.start_process(params):
                    print("Stream started")
                    self.streamlink_url = 'http://{}:{}'.format(host_address.split(":")[0], self.vlc_port)
                    tmp = urllib.parse.unquote(options['url']).split('/')
                    for t in tmp:
                        if '.' in t:
                            self.streamlink_current = '.'.join(t.split('.')[-2:])
                            break
                    handler.answer(303, {'Location': self.streamlink_url})
                else:
                    if self.notification == "": self.notification = "Couldn't open the stream"
                    self.kill_process(tmp)
                    raise Exception()
                return True
            except Exception as e:
                print("Stream not found")
                self.server.printex(e)
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
        html = '<form action="/twitch"><legend><b>Twitch</b></legend><label for="stream">Stream </label><input type="text" id="stream" name="stream" value="{}"><br><label for="qual">Quality </label><select id="qual" name="qual">'.format(self.last_stream)
        for q in self.quals:
            html += f'<option value="{q}"'
            if q == self.last_quality: html += ' selected="selected"'
            html += f'>{self.quals[q]}</option>'
        if self.last_quality not in self.quals:
            f'<option value="{self.last_quality}" selected="selected">Last used: {self.last_quality}</option>'
        html += '</select><br><input type="submit" value="Start"></form><a href="streamlinkhistory">History</a><br><a href="streamlinkadvanced">Advanced</a><br>'
        if self.streamlink is not None:
            html += '<a href="{}">Watch {}</a>'.format(self.streamlink_url, self.streamlink_current)
            html += '<br><form action="/kill"><input type="submit" value="Stop Streamlink"></form>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Twitch plugin</b><br>If needed, Streamlink and VLC path must be defined in config.json, at "streamlink_path".<br>Currently, only one instance can run at once.<br>Using 60 fps on the Wii U isn\'t recommended.<br>Using higher than 360p on the New Nintendo 3DS isn\'t recommended.'