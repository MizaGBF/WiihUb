import subprocess
from subprocess import DEVNULL
import time

class Streamlink():
    def __init__(self, server):
        self.server = server
        self.last_stream = self.server.data.get("streamlink_stream", "")
        self.last_quality = self.server.data.get("streamlink_quality", "720p")
        self.streamlink_path = self.server.data.get("streamlink_path", "streamlink")
        self.streamlink_port = self.server.data.get("streamlink_port", 65313)
        self.streamlink = None
        self.streamlink_url = None
        self.streamlink_current  = None
        self.notification = None

    def stop(self):
        self.server.data["streamlink_stream"] = self.last_stream
        self.server.data["streamlink_quality"] = self.last_quality
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
                self.streamlink = subprocess.Popen([self.streamlink_path, "--twitch-disable-ads", "--twitch-disable-hosting", "--hls-live-edge", "1", "--hls-segment-threads", "2", "--player-external-http", "--player-external-http-port", str(self.streamlink_port), "twitch.tv/{}".format(options['stream']), options.get('quality', '720p')]) # , stdout=DEVNULL, stderr=DEVNULL
                time.sleep(10)
                print("Checking if stream is available...")
                self.last_stream = options['stream']
                self.last_quality = options.get('quality', self.last_quality)
                self.streamlink_url = 'http://{}:{}'.format(host_address.split(":")[0], self.streamlink_port)
                self.streamlink_current = '{}'.format(options['stream'])
                if self.streamlink.poll() is None:
                    print("Stream started")
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
        html = '<form action="/twitch"><legend><b>Twitch</b></legend><label for="stream">Stream </label><input type="text" id="stream" name="stream" value="{}"><br><label for="qual">Quality </label><input type="text" id="qual" name="qual" value="{}"><br><input type="submit" value="Start"></form>'.format(self.last_stream, self.last_quality)
        if self.streamlink is not None:
            html += '<a href="{}">Watch {}</a><br><form action="/kill"><input type="submit" value="Stop Streamlink"></form>'.format(self.streamlink_url, self.streamlink_current )
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Twitch plugin</b><br>If needed, Streamlink path must be defined in config.json, at "streamlink_path".<br>Currently, only one instance can run at once.<br>Check <a href="https://www.neoseeker.com/members/Dynamite/blog/10285990-viewing-twitch-streams-on-wii-u-using-livestreamer/">this</a> on how to modify Livestream/Streamlink to make it compatible with the Wii U'