import cgi
import os
import datetime;

class Screenshot():
    def __init__(self, server):
        self.server = server
        self.folder = self.server.data.get("screenshot_folder", "")
        if self.folder == "": self.folder = "screenshot"
        if self.folder[-1] == "/": self.folder = self.folder[:-1]
        self.notification = None

    def stop(self):
        self.server.data["screenshot_folder"] = self.folder

    def check_folder(self):
        if not os.path.exists(self.folder):
            print("Created", self.folder)
            os.makedirs(self.folder)

    def push_notification(self, msg):
        if self.notification is None: self.notification = ""
        self.notification += msg + "\n"

    def process_get(self, handler, path):
        return False

    def process_post(self, handler, path):
        if path.startswith('/screenshot'):
            form = cgi.FieldStorage(
                fp=handler.rfile,
                headers=handler.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':handler.headers['Content-Type'],
                         })
            filename = form['file'].filename
            data = form['file'].file.read()
            self.check_folder()
            try:
                open("{}/{}_{}".format(self.folder, int(datetime.datetime.now().timestamp()), filename), "wb").write(data)
                self.push_notification("Saved {}".format(filename))
            except Exception as e:
                print("Screenshot saving failed")
                self.server.printex(e)
                self.push_notification("Failed to save screenshot")

            host_address = handler.headers.get('Host')
            handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        return False

    def get_interface(self):
        html = '<form method="post" enctype="multipart/form-data" action="/screenshot"><legend><b>Screenshot Upload</b></legend><div><input type="file" id="file" name="file" accept="image/jpeg"></div><div><button>Send</button></div></form>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Screenshot Upload plugin</b><br>If needed, the output folder can be defined in config.json, at "screenshot_folder".'