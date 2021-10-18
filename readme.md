# WiihUb  
* Simple Media Server for the Wii U.  
* Partially Compatible with the New 3DS and New 2DS.  
* Requires Python 3.9 or higher.  
* Work in progress.  
# Features  
Flexible and simple plugin system. Currently support:  
* Streamlink calls to receive Twitch streams on your Wii U (Twitch is currently broken on the Wii U/N3DS Browsers).  
* Screenshot upload (for ease of use).  
* 4chan Thread search (The search doesn't work anymore on the Wii U Browser).  
* Twitter Browser (Requires a Dev account).  
* E-Pub reader (Support e-pub 2 and 3).  
* Mangadex Browser.  
* ExHentai Browser.  
* VLC Streaming (to watch videos from your PC using VLC to transcode to the proper format) (Wii U Only).  
* Video Streaming for the 3DS (Video must be encoded to the right format, see below).  
* Notepad, to take notes.  
* Xenoblade X Companion (Allow you to search XCX-related items, etc...).  
`pip install -r requirements.txt` to install all the modules. 
# Note  
* To disable a plugin, just remove the corresponding file from the `plugins` folder.  
* Some plugins might require additional setup, either at startup (in case of the twitter one) or after creating the config.json file.  
* I don't plan on actively supporting this project, I'm just putting it here for backup purpose.  
* No Javascript used, the python script generates pure HTML. I hate Javascript.    
# Configuration  
Starts `WiihUb.py` once and press Ctrl-C to stop it once its started.  
A new file named `config.json` must be created (or the one available in this github will be initialized properly).  
You can then open it with a notepad, or similar, to change the settings of each plugin.  
One in particular you must touch is `"home_network"`, which is used to filter the incoming request.  
To keep it simple, if your local ip is something like `192.168.1.53` for example, just put `"home_network": "192.168.1"`.  
Be sure to escape any special character properly. For example, `"path": "C:\User\Example"` becomes `"path": "C:\\User\\Example"` or `"password": "a45*"$C"` becomes `"password": "a45*\"$C"`.  
Once you are done modifying `config.json`, save and close it, and starts `WiihUb.py`.  
Input the ip of your computer, followed by the port used, in an internet browser to test it's working (example: `http://192.168.1.11:8000`).  
If it works, just do the same on your Wii U or 3DS to access the content.  
Some plugins might need more configuration to be usable.  
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
  
Pre-roll ads make the Wii U unable to load the playlist, another modification is required as a result:
On Streamlink 2.0.0 and further, go to:
`Streamlink/pkgs/streamlink/plugins`  
Open `twitch.py` and search for the function  
`def access_token(self, is_live, channel_or_vod):`  
A bit lower, you'll find:
`"playerType": "embed"` or `"playerType="embed"`
Replace `embed` by `frontpage` and you are done.  
If you are still getting pre-roll ads, wait a few minutes before trying again.  
Alternatively, you can try `frontpage` or even keep the default, `embed`.  
# Using Twitter  
With the new Twitter API V2, it's now more complicated to use Twitter.  
1. Get a Twitter account.  
2. Apply for [Dev access](https://developer.twitter.com/en).  
3. On the dev portal, create a new project and then an application under it.  
4. Get and copy the **Bearer Token**.  
5. Either place the token in config.json with the key `twitter_bearer_token` if you know what you are doing OR start WiihUb and click `Set Twitter Key` under `Twitter`, then paste the token and send it.  
  
Sadly, the Twitter API V2 limits you to 500000 tweets per month, don't go too crazy with it and don't share your token.  
# 3DS Video Encoding  
I use [FFmpeg](https://ffmpeg.org/download.html) to encode my videos to the right format for the New 3DS.  
A simple example with a command line would be:
`bin\ffmpeg.exe -i input.whatever -filter:v "scale=-1:360:flags=lanczos, fps=24" -c:v libx264 -qscale:v 4 -c:a aac -b:a 128k output.mp4`  
`input.whatever` being the input file (for example: my_cat.mp4) and `output.mp4` whatever you want the resulting file to be named.  
The New 3DS/2DS internet browser only supports MP4 format (Video: H.264 - MPEG-4 AVC, Audio: AAC - ISO / IEC 14496-3 MPEG-4AAC, MP3), resolution lower than 480p and up to one hour.  
  
The plugin also have a simple playlist system to alleviate the one hour limit.  
You can put a `.txt` file in the folder, containing the name of one file per line, and loading it will put all the videos on the same page.  