# WiihUb  
* Simple Media Server for the Wii U.  
* Requires Python 3.8 or higher.  
* Work in progress.  
# Features  
Flexible and simple plugin system. Currently support:  
* Streamlink calls to receive Twitch streams on your Wii U (Twitch is currently broken on the Wii U Browser).  
* Screenshot upload (for ease of use).  
* 4chan Thread search (The search doesn't work anymore on the Wii U Browser).  
* Twitter Browser (Twitter is now unusable on the Wii U Browser).  
* E-Pub reader (Support e-pub 2 and 3).  
* Mangadex Browser.  
* ExHentai Browser.  
* Pixiv Browser.  
* VLC Streaming (to watch videos from your PC using VLC to transcode to the proper format).  
* Notepad, to take notes.  
`pip install -r requirements.txt` to install all the modules. 
# Note  
* To disable a plugin, just remove the corresponding file from the `plugins` folder.  
* Some plugins might require additional setup, either at startup (in case of the twitter one) or after creating the config.json file.  
* I don't plan on actively supporting this project, I'm just putting it here for backup purpose.  
* No Javascript used, the python script generates pure HTML. I hate Javascript.    
# Plugin Development  
Making your own plugin is quite simple, as long as you know Python.  
Create a new file in the `plugins` folder.  
Here's a template:
```python
class Example():
    def __init__(self, server):
        self.server = server

    def stop(self):
        pass

    def process_get(self, handler, path):
        if path.startswith('/example?'):
            options = self.server.getOptions(path, 'example')
            handler.answer(200, {'Content-type': 'text/html'}, 'Hello, {}!'.format(options['name']).encode('utf-8'))
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        return '<form action="/example"><legend><b>Plugin Example</b></legend><label for="name">Input your name </label><input type="text" id="name" name="name" value=""><br><input type="submit" value="Send"></form>'

    def get_manual(self):
        return '<b>Plugin Example</b><br>This is an example.'
```
# Streamlink modification  
You must do a slight moditication to [Streamlink](https://github.com/streamlink/streamlink) to receive Twitch on your Wii U.  
Locate your Streamlink folder and then go into:  
`Streamlink/pkgs/streamlink_cli/utils`  
Open `http_server.py` and search for the line  
`conn.send(b"Content-Type: video/unknown\r\n")`  
Replace it with:  
`conn.send(b"Content-Type: video/mp4\r\n")`
Make sure to keep the indentation using spaces.  