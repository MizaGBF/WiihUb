from os import listdir, unlink, makedirs, path, remove
from os.path import isfile, join, islink
import urllib.parse
import glob

# to encode a video to the right format using ffmpeg
# bin\ffmpeg.exe -i input.whatever -filter:v "scale=-1:360:flags=lanczos" -c:v libx264 -c:a aac output.mp4

class N3DS():
    def __init__(self, server):
        self.server = server
        self.notification = None
        self.folder = self.server.data.get("3ds_folder", '')
        if self.folder == "": self.folder = "3ds"
        if self.folder[-1] == "/": self.folder = self.folder[:-1]
        self.stream = None
        self.current_file = ''

    def stop(self):
        self.server.data["3ds_folder"] = self.folder
        pass

    def get_media_list(self):
        try: fs = glob.glob(self.folder + '/**/*', recursive=True)
        except: fs = []
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        for m in fs:
            if m.endswith('.mp4'):
                html += '<a href="/3dsplay?file={}">{}</a><br>'.format(m, m[len(self.folder)+1:])
                break
        if len(fs) == 0: html += "No files found in the '{}' folder".format(self.folder)
        html += '</div>'
        return html

    def open(self, file):
        if self.current_file == file: return
        f = open(file, 'rb')
        if self.stream is not None: self.stream.close()
        self.stream = f
        self.current_file = file

    def read(self, file, pos, chunksize=8192):
        self.open(file)
        self.stream.seek(pos)
        return self.stream.read(), self.stream.tell()

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/3dsvideolist'):
            try: handler.answer(200, {'Content-type': 'text/html'}, self.get_media_list().encode('utf-8'))
            except Exception as e:
                print("Failed to open video list")
                print(e)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/3dsplay?'):
            options = self.server.getOptions(path, '3dsplay')
            try:
                self.open(urllib.parse.unquote(options['file']))
                handler.answer(200, {'Content-type': 'text/html'}, (self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div class="elem"><a href="/3dsvideolist">Back</a><br><br></div><div class="elem"><video width="400" controls="controls" type="video/mp4" src="' + 'http://{}/3dsstream?file={}"></video></div></body>'.format(host_address, options['file'])).encode('utf-8'))
            except Exception as e:
                print("Failed to open media")
                print(e)
                self.notification = "Failed to open {}<br>{}".format(urllib.parse.unquote(options.get('file', '')), e)
                handler.answer(303, {'Location':'http://{}/3dsvideolist'.format(host_address)})
            return True
        elif path.startswith('/3dsstream?'):
            options = self.server.getOptions(path, '3dsstream')
            try:
                file_range = handler.headers.get('Range')
                if file_range is None:
                    file_range = 0
                else:
                    file_range = int(file_range.split('=')[-1].split('-')[0])
                data, pos = self.read(urllib.parse.unquote(options['file']), file_range)
                content_range = 'bytes %s-%s/%s' % (file_range, pos, len(data))
                handler.answer(200, {'Content-type': 'video/mp4', 'Accept-Ranges': 'bytes', 'Content-Length':str(len(data)), 'Content-Range':content_range}, data)
            except Exception as e:
                print("Failed to stream media")
                print(e)
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