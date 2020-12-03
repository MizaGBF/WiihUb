import subprocess
from subprocess import DEVNULL
import time

class Streamlink():
    def __init__(self, server):
        self.server = server
        self.last_stream = self.server.data.get("streamlink_stream", "")
        self.last_quality = self.server.data.get("streamlink_quality", "720p")
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
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem"><a href="/">Back</a><br>'
        if self.streamlink is not None:
            html += '<a href="{}">Watch {}</a><br><form action="/kill"><input type="submit" value="Stop Streamlink"></form>'.format(self.streamlink_url, self.streamlink_current, self.streamlink_current)
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += "</div>"
        for h in self.history:
            html += '<div class="elem"><a href="/twitch?stream={}&quality={}">{} ({})</a></div>'.format(h[0], h[1], h[0], h[1])
        if len(self.history) == 0:
            html += '<div class="elem">No streams in the memory</div>'
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
        if len(self.history) > 30: self.history = self.history[:30]

    def process_get(self, handler, path):
        if path.startswith('/twitch?'):
            path_str = str(path)[len('/twitch?'):]
            param_strs = path_str.split('&')
            options = {}
            host_address = handler.headers.get('Host')
            for s in param_strs:
                arg = s.split('=')
                if arg[0] == "stream" and arg[1] != "": options['stream'] = arg[1]
                elif arg[0] == "qual" and arg[1] != "": options['quality'] = arg[1]
            try:
                if 'stream' not in options: raise Exception()
                self.streamlink_kill()
                self.streamlink = subprocess.Popen([self.streamlink_path, "--twitch-disable-ads", "--twitch-disable-hosting", "--hls-live-edge", "1", "--hls-segment-threads", "2", "--player-external-http", "--player-external-http-port", str(self.streamlink_port), "twitch.tv/{}".format(options['stream']), options.get('quality', '720p')])
                time.sleep(8)
                print("Checking if stream is available...")
                self.last_stream = options['stream']
                self.last_quality = options.get('quality', self.last_quality)
                self.streamlink_url = 'http://{}:{}'.format(host_address.split(":")[0], self.streamlink_port)
                self.streamlink_current = '{}'.format(options['stream'])
                if self.streamlink.poll() is None:
                    print("Stream started")
                    self.add_to_history(options['stream'], options.get('quality', self.last_quality))
                    handler.send_response(303)
                    handler.send_header('Location', self.streamlink_url)
                    handler.end_headers()
                else:
                    raise Exception()
                return True
            except Exception as e:
                self.streamlink_kill()
                print("Stream not found")
                print(e)
                self.notification = "Stream not found"
                handler.send_response(303)
                handler.send_header('Location','http://{}'.format(host_address))
                handler.end_headers()
                return True
        elif path.startswith('/streamlinkhistory'):
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(self.get_history().encode('utf-8'))
            return True
        elif path.startswith('/kill'):
            self.streamlink_kill()
            host_address = handler.headers.get('Host')
            self.notification = "Streamlink Stopped"
            handler.send_response(303)
            handler.send_header('Location','http://{}'.format(host_address))
            handler.end_headers()
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<form action="/twitch"><legend><b>Twitch</b></legend><label for="stream">Stream </label><input type="text" id="stream" name="stream" value="{}"><br><label for="qual">Quality </label><input type="text" id="qual" name="qual" value="{}"><br><input type="submit" value="Start"></form><a href="streamlinkhistory">History</a>'.format(self.last_stream, self.last_quality)
        if self.streamlink is not None:
            html += '<a href="{}">Watch {}</a><br><form action="/kill"><input type="submit" value="Stop Streamlink"></form>'.format(self.streamlink_url, self.streamlink_current, self.streamlink_current)
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Twitch plugin</b><br>If needed, Streamlink path must be defined in config.json, at "streamlink_path".<br>Currently, only one instance can run at once.<br>Check <a href="https://www.neoseeker.com/members/Dynamite/blog/10285990-viewing-twitch-streams-on-wii-u-using-livestreamer/">this</a> on how to modify Livestream/Streamlink to make it compatible with the Wii U'