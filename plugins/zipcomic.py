import zipfile
import threading
from PIL import Image
from io import BytesIO
from os import listdir, unlink, makedirs, path, remove
from os.path import isfile, join, islink
import urllib.parse
import glob

class ZipComic():
    def __init__(self, server):
        self.server = server
        self.img_cache = {}
        self.list_cache = {}
        self.lock = threading.Lock()
        self.folder = self.server.data.get("comic_path", "comics")
        if not self.folder.endswith('\\'): self.folder += '\\'
        self.notification = None

    def stop(self):
        pass

    def update_list(self, archive):
        with self.lock:
            with zipfile.ZipFile(self.folder + archive, mode='r') as z:
                namelist = z.namelist()
                tab = {}
                for e in namelist:
                    tab[e.rjust(8)] = e
                keys = list(tab.keys())
                keys.sort()
                namelist = []
                for k in keys:
                    namelist.append(tab[k])
                self.list_cache[archive] = namelist

    def get_content(self, archive):
        if archive not in self.list_cache:
            self.update_list(archive)
        return self.list_cache[archive]

    def get_image(self, archive, id):
        if archive not in self.list_cache:
            self.update_list(archive)
        filename = self.list_cache[archive][id]
        key = archive + "@" + str(id)
        with self.lock:
            if key not in self.img_cache:
                with zipfile.ZipFile(self.folder + archive, mode='r') as z:
                    with z.open(filename) as f:
                        i = Image.open(f)
                        w, h = i.size
                        if w > 800:
                            tmp1 = i.resize((800, int(h * 800 / w)))
                            tmp2 = tmp1.convert('RGB')
                            tmp1.close()
                            i.close()
                            i = tmp2
                        with BytesIO() as out:
                            i.save(out, format='JPEG')
                            i.close()
                            if len(self.img_cache) > 100:
                                keys = list(self.img_cache.keys())[50:]
                                imdata = {}
                                for key in keys:
                                    imdata[key] = self.img_cache[key]
                                self.img_cache = imdata
                            self.img_cache[key] = out.getvalue()
            return self.img_cache[key]

    def get_zip_list(self):
        try: fs = glob.glob(self.folder + '/**/*', recursive=True)
        except: fs = []
        format = ['.zip']
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        for m in fs:
            for e in format:
                if m.endswith(e):
                    html += '<a href="/comicpage?archive={}">{}</a><br>'.format(urllib.parse.quote(m.replace(self.folder, "")), m.replace(self.folder, ""))
                    break
        if len(fs) == 0: html += "No files found in the '{}' folder".format(self.folder)
        html += '</div>'
        return html

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/comiclist'):
            try: handler.answer(200, {'Content-type': 'text/html'}, self.get_zip_list().encode('utf-8'))
            except Exception as e:
                print("Failed to open comic list")
                self.server.printex(e)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/comicpage?'):
            options = self.server.getOptions(path, 'comicpage')
            try:
                archive = urllib.parse.unquote(options['archive'])
                page = int(options.get('page', 0))
                content = self.get_content(archive)
                last = len(content) - 1
                
                pl = list(range(max(page-5, 0), min(page+6, last+1)))
                for px in range(0, 1 + last // 10):
                    if px * 10 not in pl: pl.append(px*10)
                if last not in pl: pl.append(last)
                pl.sort()
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size: 180%;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                
                # footer
                footer = '<div class="elem">'
                footer += f'<a href="/comiclist">Back</a>'
                footer += "<br><b>" + archive + "</b>"
                footer += "<br><b>" + content[page] + "</b>"
                footer += "<br>"
                for p in pl:
                    if p == page: footer += f"<b>{p+1}</b>"
                    else: footer += f'<a href="/comicpage?archive={urllib.parse.quote(archive)}&page={p}">{p+1}</a>'
                    if p != pl[-1]: footer += ' # '
                footer += '</div>'
                
                # body
                if page < last:
                    html += f'{footer}<div><a href="/comicpage?archive={urllib.parse.quote(archive)}&page={page+1}"><img src="/comicimg?archive={urllib.parse.quote(archive)}&page={page}"></a></div>{footer}</body>'
                else:
                    html += f'{footer}<div><img src="/comicimg?archive={urllib.parse.quote(archive)}&page={page}"></div>{footer}</body>'
                handler.answer(200, {'Content-type': 'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to open comic")
                self.server.printex(e)
                self.stop_vlc()
                self.notification = "Failed to open {}<br>{}".format(urllib.parse.unquote(options.get('archive', '')), e)
                handler.answer(303, {'Location':'http://{}/comiclist'.format(host_address)})
            return True
        elif path.startswith('/comicimg?'):
            options = self.server.getOptions(path, 'comicimg')
            try:
                archive = urllib.parse.unquote(options['archive'])
                page = int(options.get('page', 0))
                handler.answer(200, {'Content-type': 'image/jpg'}, self.get_image(archive, page))
                return True
            except Exception as e:
                print("Failed to open image")
                self.server.printex(e)
                handler.answer(404, {})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<b>Comic Browser</b><br><a href="/comiclist">Open folder</a>'
        if self.notification is not None:
            html += "<br>{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Comic Browser</b><br>Browse Zipped files containing images. Folder path must be set under "comic_path".'