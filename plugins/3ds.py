from os import listdir, unlink, makedirs, path, remove
from os.path import isfile, join, islink
import urllib.parse
import glob
import threading

# to encode a video to the right format using ffmpeg
# bin\ffmpeg.exe -i input.whatever -filter:v "scale=-1:360:flags=lanczos" -c:v libx264 -c:a aac output.mp4

class N3DS():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.folder = self.server.data.get("3ds_folder", '')
        if self.folder == "": self.folder = "3ds"
        if self.folder[-1] == "/": self.folder = self.folder[:-1]
        self.cache = {}
        self.lock = threading.Lock()

    def stop(self):
        self.server.data["3ds_folder"] = self.folder
        pass

    def load_playlist(self, file):
        with open(file, "r") as f:
            lines = f.readlines()
            for i in range(len(lines)):
                if not lines[i].startswith(self.folder):
                    lines[i] = self.folder + '/' + lines[i]
                if len(lines[i]) > 0 and lines[i][-1] == '\n':
                    lines[i] = lines[i][:-1]
            return lines

    def get_media_list(self):
        try: fs = glob.glob(self.folder + '/**/*', recursive=True)
        except: fs = []
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size:30px}</style><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        in_playlist = []
        for m in fs:
            if m.endswith('.txt'):
                try:
                    files = self.load_playlist(m)
                    for f in files: in_playlist.append(f.replace('\\', '/').split('/')[-1])
                    html += '<a href="/3dsplay?file={}">Playlist: {}</a><br>'.format(m, m[len(self.folder)+1:-4])
                except:
                    pass
        for m in fs:
            if m.endswith('.mp4') and m.replace('\\', '/').split('/')[-1] not in in_playlist:
                html += '<a href="/3dsplay?file={}">{}</a><br>'.format(m, m[len(self.folder)+1:])
        if len(fs) == 0: html += "No files found in the '{}' folder".format(self.folder)
        html += '</div>'
        return html

    def open(self, file):
        if file in self.cache: return self.cache[file]
        f = open(file, 'rb')
        with self.lock:
            self.cache[file] = [f, path.getsize(file)]
        return self.cache[file]

    def read(self, file, pos, chunksize=10485760):
        self.cache[file][0].seek(pos)
        return self.cache[file][0].read(chunksize), self.cache[file][0].tell()

    def close_all(self):
        with self.lock:
            for f in self.cache:
                self.cache[f][0].close()
            self.cache = {}

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/3dsvideolist'):
            try: 
                self.close_all()
                handler.answer(200, {'Content-type': 'text/html'}, self.get_media_list().encode('utf-8'))
            except Exception as e:
                print("Failed to open video list")
                self.server.printex(e)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/3dsplay?'):
            options = self.server.getOptions(path, '3dsplay')
            try:
                if options['file'].endswith('.txt'):
                    files = self.load_playlist(urllib.parse.unquote(options['file']))
                else:
                    files = [urllib.parse.unquote(options['file'])]
                
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size:30px}</style><div class="elem"><a href="/3dsvideolist">Back</a>' + '<br>{}</div>'.format(urllib.parse.unquote(options['file'])[len(self.folder)+1:])
                for f in files:
                    html += '<div class="elem"><video width="400" controls="controls" preload="metadata"><source src="http://{}/3dsstream?file={}" type="video/mp4" /></video></div>'.format(host_address, f)
                html += '</body>'
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open page")
                self.server.printex(e)
                self.notification = "Failed to open page {}<br>{}".format(urllib.parse.unquote(options.get('file', '')), e)
                handler.answer(303, {'Location':'http://{}/3dsvideolist'.format(host_address)})
            return True
        elif path.startswith('/3dsstream?'):
            options = self.server.getOptions(path, '3dsstream')
            try:
                fn = urllib.parse.unquote(options['file'])
                current_size = self.open(fn)[1]
                file_range = handler.headers.get('Range')
                if file_range is None:
                    range_start = 0
                    range_end = None
                else:
                    tmp = file_range.split('=')[-1].split('-')
                    range_start = int(tmp[0])
                    try: range_end = int(tmp[1]) + 1
                    except: range_end = current_size
                if (range_end is not None and range_end > current_size) or range_start >= current_size:
                    handler.answer(416)
                else:
                    if range_end is None:
                         data, pos = self.read(urllib.parse.unquote(options['file']), range_start)
                    else:
                        data, pos = self.read(urllib.parse.unquote(options['file']), range_start, range_end-range_start)
                    content_range = 'bytes %s-%s/%s' % (range_start, pos-1, current_size)
                    handler.answer((200 if (pos-range_start==current_size) else 206), {'Content-type': 'video/mp4' if fn.endswith('.mp4') else 'audio/mpeg', 'Accept-Ranges': 'bytes', 'Content-Length':str(len(data)), 'Content-Range':content_range}, data)
            except Exception as e:
                print("Failed to stream media")
                self.server.printex(e)
                self.notification = "Failed to stream {}<br>{}".format(urllib.parse.unquote(options.get('file', '')), e)
                handler.answer(303, {'Location':'http://{}/3dsvideolist'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<b>N3DS Video Player</b><br><a href="/3dsvideolist">Open folder</a>'
        if self.notification is not None:
            html += "<br>{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>N3DS Video Player</b><br>Folder must be set in config.json, at "3ds_folder".<br>The New 3DS/2DS only supports MP4 format ( H.264 - MPEG-4 AVC Video, AAC - ISO / IEC 14496-3 MPEG-4AAC, MP3) and resolution lower than 480p.'