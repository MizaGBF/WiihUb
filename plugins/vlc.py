import subprocess
from subprocess import DEVNULL
import time
from os import listdir, unlink, makedirs, path, remove
from os.path import isfile, join, islink
import urllib.parse

class VLC():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.folder = self.server.data.get("vlc_folder", "medias")
        self.path = self.server.data.get("vlc_path", "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe")
        if self.folder == "": self.folder = "books"
        if self.folder[-1] == "/": self.folder = self.folder[:-1]
        self.vlc = None

    def stop(self):
        self.server.data["vlc_folder"] = self.folder
        self.server.data["vlc_path"] = self.path
        self.stop_vlc()

    def delFile(self, file):
        remove(file)

    def stop_vlc(self):
        try:
            self.vlc.terminate()
            self.vlc.wait()
            self.vlc = None
            print("Stopped the VLC instance")
        except:
            self.vlc = None
        try: fs = [f for f in listdir() if isfile(f)]
        except: fs = []
        for f in fs:
            if f.startswith("stream"):
                self.delFile(f)
                print("Deleted", f)

    def get_media_list(self):
        try: fs = [f for f in listdir(self.folder) if isfile(join(self.folder, f))]
        except: fs = []
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        for m in fs:
            html += '<a href="/play?file={}">{}</a><br>'.format(m, m)
        if len(fs) == 0: html += "No files found in the '{}' folder".format(self.folder)
        html += '</div>'
        return html

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/medialist'):
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(self.get_media_list().encode('utf-8'))
            return True
        elif path.startswith('/play?'):
            path_str = str(path)[len('/play?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                self.stop_vlc()
                self.vlc = subprocess.Popen([self.path, self.folder + "/" + urllib.parse.unquote(options['file']), '--sout=#transcode{width=1280,height=720,fps=25,vcodec=h264,vb=256,venc=x264{aud,profile=baseline,level=30,keyint=30,ref=1},acodec=aac,ab=96,channels=2}:std{access=livehttp{seglen=3,delsegs=true,numsegs=1,index=stream.m3u8,index-url=/stream-########.ts},mux=ts{use-key-frames},dst=stream-########.ts}'])
                time.sleep(2)
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write('<html><meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div class="elem"><a href="/medialist">Back</a></div><div class="elem"><video width="320" height="240" controls autoplay src="/stream.m3u8"></video></div></body></html>'.encode('utf-8'))
            except Exception as e:
                print("Failed to open media")
                print(e)
                self.stop_vlc()
                self.notification = "Failed to open {}<br>{}".format(urllib.parse.unquote(options.get('file', '')), e)
                handler.send_response(303)
                handler.send_header('Location','http://{}/medialist'.format(host_address))
                handler.end_headers()
            return True
        elif path.startswith('/stream'):
            try:
                with open(path.split("/")[-1], "rb") as f:
                    handler.send_response(200)
                    handler.send_header('Content-type', 'application/x-mpegURL')
                    handler.end_headers()
                    handler.wfile.write(f.read())
                    print(path.split("/")[-1], 'sent')
            except Exception as e:
                print("Failed to send", path.split("/")[-1])
                print(e)
                self.notification = "Failed to open {}<br>{}".format(path.split("/")[-1], e)
                handler.send_response(404)
                handler.end_headers()
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<b>VLC Server</b><br><a href="/medialist">Open folder</a>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>VLC Server plugin</b><br>Folder must be set in config.json, at "vlc_folder".'