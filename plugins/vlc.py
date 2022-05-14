import subprocess
from subprocess import DEVNULL
import time
from os import listdir, unlink, makedirs, path, remove
from os.path import isfile, join, islink
import urllib.parse
import glob

class VLC():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.folder = self.server.data.get("vlc_folder", "medias")
        self.path = self.server.data.get("vlc_path", "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe")
        if self.folder == "": self.folder = "videos"
        if not self.folder.endswith('/') and not self.folder.endswith('\\'): self.folder += '/'
        self.vlc = None
        self.current = ""

    def stop(self):
        self.server.data["vlc_folder"] = self.folder
        self.server.data["vlc_path"] = self.path
        self.stop_vlc()

    def stop_vlc(self):
        try:
            self.vlc.terminate()
            self.vlc.wait()
            self.vlc = None
            print("Stopped the VLC instance")
        except:
            self.vlc = None

    def get_media_list(self):
        try: fs = glob.glob(self.folder + '/**/*', recursive=True)
        except: fs = []
        format = ['.webm', '.mkv', '.flv', '.vob', '.gif', '.avi', '.rm', '.mpg', '.mp2', '.mpeg', '.mpe', '.mpv', '.mpg', '.mpeg', '.m2v', '.m4v', 'mp4']
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        for m in fs:
            for e in format:
                if m.endswith(e):
                    html += '<a href="/play?file={}">{}</a><br>'.format(m[len(self.folder):], m[len(self.folder):])
                    break
        if len(fs) == 0: html += "No files found in the '{}' folder".format(self.folder)
        html += '</div>'
        return html

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/medialist'):
            try: handler.answer(200, {'Content-type': 'text/html'}, self.get_media_list().encode('utf-8'))
            except Exception as e:
                print("Failed to open video list")
                self.server.printex(e)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/vlcstop'):
            self.stop_vlc()
            self.notification = "VLC has been stopped"
            handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/play?'):
            options = self.server.getOptions(path, 'play')
            try:
                mode = int(options.get('mode', 0))
                if self.current != options['file'] + str(mode):
                    self.stop_vlc()
                    if mode == 0: modestr = "width=1280,height=720"
                    elif mode == 1: modestr = "width=1280"
                    elif mode == 2: modestr = "height=720"
                    self.vlc = subprocess.Popen([self.path, self.folder + urllib.parse.unquote(options['file']), '--no-sout-all', '--sout=#transcode{' + modestr + ',fps=30,vcodec=h264,vb=1200,venc=x264{aud,profile=baseline,level=30,keyint=30,ref=1},acodec=aac,ab=128,channels=2,soverlay}:std{access=http{mime=video/mp4},mux=ts,dst=:8001/'])
                    time.sleep(1)
                    self.current = options['file'] + str(mode)
                issuefooter = '<div class="elem">Scaling Issue? Switch to another mode:<br>'
                if mode != 0: issuefooter += '<a href="/play?file={}&mode=0">Default (1280x720)</a><br>'.format(options['file'])
                if mode != 1: issuefooter += '<a href="/play?file={}&mode=1">Fixed Width (720p)</a><br>'.format(options['file'])
                if mode != 2: issuefooter += '<a href="/play?file={}&mode=2">Fixed Height (1280p)</a><br>'.format(options['file'])
                issuefooter += '</div>'
                handler.answer(200, {'Content-type': 'text/html'}, (self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div class="elem"><a href="/medialist">Back</a><br><br><form action="/vlcstop"><input type="submit" value="Stop VLC"></form></div><div class="elem"><video width="320" height="240" controls autoplay src="http://192.168.1.11:8001"></video></div>' + issuefooter +'</body>').encode('utf-8'))
            except Exception as e:
                print("Failed to open media")
                self.server.printex(e)
                self.stop_vlc()
                self.notification = "Failed to open {}<br>{}".format(urllib.parse.unquote(options.get('file', '')), e)
                handler.answer(303, {'Location':'http://{}/medialist'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<b>VLC Server</b><br><a href="/medialist">Open folder</a>'
        if self.vlc is not None:
            html += '<br><br><form action="/vlcstop"><input type="submit" value="Stop VLC"></form>'
        if self.notification is not None:
            html += "<br>{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>VLC Server plugin</b><br>Folder must be set in config.json, at "vlc_folder".'