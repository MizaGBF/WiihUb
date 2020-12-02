import urllib.parse

class Notepad():
    def __init__(self, server):
        self.server = server
        self.notes = self.server.data.get("notepad_saved", [])

    def stop(self):
        self.server.data["notepad_saved"] = self.notes

    def get_notes(self):
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem"><a href="/">Back</a><br><a href="/newnote">New</a></div>'
        for i in range(len(self.notes)):
            html += '<div class="elem">'+self.notes[i]+'<br><br><a href="/editnote?id={}">Edit</a> # <a href="/delnote?id={}">Delete</a></div>'.format(i, i)
        return html

    def get_typing_ui(self, use_save=None):
        if use_save is None:
            default = ""
            hidden = ""
        else:
            if use_save < 0 or use_save >= len(self.notes):
                default = ""
                hidden = ""
            else:
                default = self.notes[use_save]
                hidden = '<input type="hidden" name="target" value="{}" />'.format(use_save)

        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        html += '<div class="elem"><form action="/savenote"><legend><b>Notepad</b></legend><textarea id="content" name="content" rows="20" cols="100">{}</textarea><br>{}<input type="submit" value="Save"></form></div>'.format(default, hidden)
        return html

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/newnote'):
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(self.get_typing_ui().encode('utf-8'))
            return True
        elif path.startswith('/listnote'):
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(self.get_notes().encode('utf-8'))
            return True
        elif path.startswith('/delnote?'):
            path_str = str(path)[len('/delnote?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                self.notes.pop(int(options['id']))
            except Exception as e:
                print("Failed to delete note")
                print(e)
            handler.send_response(303)
            handler.send_header('Location','http://{}/listnote'.format(host_address))
            handler.end_headers()
            return True
        elif path.startswith('/editnote?'):
            path_str = str(path)[len('/editnote?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write(self.get_typing_ui(int(options['id'])).encode('utf-8'))
            except Exception as e:
                print("Note not found")
                print(e)
                handler.send_response(303)
                handler.send_header('Location','http://{}/listnote'.format(host_address))
                handler.end_headers()
            return True
        elif path.startswith('/savenote?'):
            path_str = str(path)[len('/savenote?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                target = options.get('target', None)
                if 'target' in options: self.notes[int(options['target'])] = urllib.parse.unquote(options['content'].replace('+', ' '))
                else: self.notes.append(urllib.parse.unquote(options['content'].replace('+', ' ')))
            except Exception as e:
                print("Failed to save note")
                print(e)
            handler.send_response(303)
            handler.send_header('Location','http://{}/listnote'.format(host_address))
            handler.end_headers()
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        return '<b>Notepad</b><br><a href="/newnote">New</a><br><a href="/listnote">List</a>'

    def get_manual(self):
        return '<b>Notepad plugin</b><br>Allow you to take notes.'