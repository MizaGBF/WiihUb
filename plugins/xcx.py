from urllib.parse import quote, unquote
import json
import requests
import os

class XCX():
    def __init__(self, server):
        self.server = server
        self.data = None
        self.notification = None
        if not self.load():
            self.update()
            self.load()

    def load(self):
        try:
            with open('assets/XCX.json', 'r', encoding="utf-8") as json_file:
                self.data = json.load(json_file)
            return True
        except:
            return False

    def clean(self, data):
        for t in ['thumbnail', 'image', 'tileLayers', 'minimap', 'center', 'defaultZoom', 'maxNativeZoom', 'hue', 'icon', 'q', 'r', 's', 'fa_icon', 'markerStyle']:
            try: data.pop(t)
            except: pass
        return data

    def formatName(self, et, en, ed):
        if et == "Segment":
            splitted = en.split(" (")
            en = splitted[0]
            coord = splitted[1][:-1]
            ed['grid_coordinate'] = coord
        return en, ed

    def update(self):
        try:
            rep = requests.get("https://frontiernav.jahed.dev/api/namespaces/xenoblade-chronicles-x/index.json", headers={'User-Agent':self.server.user_agent_common})
            hash = rep.json()['graph']['hash']
            size = rep.json()['graph']['size']
            rep = requests.get(f"https://frontiernav-static.jahed.dev/user-content/xenoblade-chronicles-x/{hash}.{size}.json", headers={'User-Agent':self.server.user_agent_common})
            data = rep.json()
            converted = {}
            ts = {}
            for e in data['entities']:
                et = data['entities'][e]['type']
                en = data['entities'][e]['data']['name']
                ed = data['entities'][e]['data']
                en, ed = self.formatName(et, en, ed)
                if et in ['Guide', 'Collectible Map', 'Game']: continue
                if et not in converted:
                    converted[et] = {}
                ts[e] = en
                converted[et][en] = self.clean(ed)
            for cat in converted:
                for e in converted[cat]:
                    for attrs in converted[cat][e]:
                        if isinstance(converted[cat][e][attrs], dict):
                            nd = {}
                            for k in converted[cat][e][attrs]:
                                elems = k.split('__')
                                for i in range(len(elems)):
                                    if elems[i] in ts:
                                        elems[i] = ts[elems[i]]
                                nd['__'.join(elems)] = converted[cat][e][attrs][k]
                            converted[cat][e][attrs] = nd

            try: os.makedirs('assets')
            except: pass
            with open('assets/XCX.json', 'w') as outfile:
                json.dump(converted, outfile)
            self.notification = "Database updated"
            return True
        except Exception as xe:
            self.notification = "Failed to update the database"
            self.server.printex(xe)
            return False

    def stop(self):
        pass

    def cmpStr(self, terms, target):
        for t in terms:
            if target.lower().find(t) != -1:
                return True
        return False

    def search(self, category, terms):
        terms = [terms.lower().replace('  ', ' ')]
        if len(terms) == 0: return []
        results = []
        for cat in self.data:
            if category != "" and category != "Category" and category != cat: continue
            if len(terms) == 1 and terms[0] == cat.lower():
                for e in self.data[cat]:
                    results.append([cat, e, self.data[cat][e]])
            else:
                catMatch = False
                if self.cmpStr(terms, cat):
                    results.append(['Category', cat, self.data[cat]])
                    catMatch = True
                if category == "Category": continue
                for e in self.data[cat]:
                    if catMatch or self.cmpStr(terms, e):
                        results.append([cat, e, self.data[cat][e]])
        return results

    def display_stat(self, ed, text, key, hasRange):
        try:
            if hasRange: return f"<b>{text}:</b> {ed[key]['minimum']} to {ed[key]['maximum']}<br>"
            else: return f"<b>{text}:</b> {ed[key]['minimum']}<br>"
        except:
            return ""

    def display_data(self, ed, text, key, format, index, *, mode=0):
        msg = ""
        if key in ed:
            msg += f"<b>{text}</b><br>"
            for e in ed[key]:
                text = e.replace(f'{format}', '__').split('__')[index]
                if mode == 1:
                    if text == "Enemies": text = "Enemy"
                    else: text = text[:-1]
                    msg += '<a href="/xcx?query={}">{}</a><br>'.format(quote(text).replace(' ', '+'), text)
                else:
                    msg += '<a href="/xcx?query={}">{}</a><br>'.format(quote(text).replace(' ', '+'), text)
        return msg

    def locate_in_region(self, lat, lng, boundaries):
        width = boundaries[1][0]-boundaries[0][0]
        height = boundaries[1][1]-boundaries[0][1]
        center = (width//2, height//2)
        msg = ""
        comma = False
        diff = abs(lat - center[0])
        if diff > (height / 10):
            if diff > height / 2: msg += "Far-"
            if lat < center[0]: msg += "North"
            else: msg += "South"
            comma = True
        diff = abs(lng - center[0])
        if diff > (width / 10):
            if comma: msg += ", "
            if diff > width / 2: msg += "Far-"
            if lng < center[0]: msg += "West"
            else: msg += "East"
        return msg

    def display_latLng(self, ed):
        regions = {'Primordia': [(-100, -50), (34, -90)], 'Noctilum': [(-176, 62), (-90, -73)], 'Oblivia': [(34, -57), (155, -85)], 'Sylvalum': [(-29, 62), (86, -33)], 'Cauldros': [(22, 90), (140, 40)], 'Mira': [(-210, 87), (232, -86)]}
        msg = ""
        
        try:
            for e in ed["MapMarker-MAP_LINK"]:
                l = self.data['Location'][e.replace(f'{format}', '__').split('__')[-1]]
                for r in l["Region-HAS-Location"]:
                    region = r.replace(f'{format}', '__').split('__')[0]
                    if region not in regions: return ""
                    break
                break
        except:
            return ""
        
        lat = ed['latLng']['lat']
        lng = ed['latLng']['lng']
        for n in regions:
            if lng >= regions[n][0][0] and lng <= regions[n][1][0] and lat <= regions[n][0][1] and lat >= regions[n][1][1]:
                msg += "<b>Estimated Position on {}:</b> {}<br>".format(n, self.locate_in_region(lat, lng, regions[n]))
                break
        return msg

    def display(self, elem):
        msg = '<div class="elem">'
        et = elem[0]
        en = elem[1]
        ed = elem[2]
        if et == 'Category':
            msg += '<b>Category</b>&nbsp;<a href="/xcx?query={}&category={}">{}</a><br>'.format(quote(en).replace(" ", "+"), quote(en).replace(" ", "+"), en)
        else:
            msg += '<a href="/xcx?query={}&category={}">{}</a><br>'.format(quote(en).replace(" ", "+"), quote(et), en)
            if et == 'FieldTreasureContainer':
                msg += self.display_data(ed, "Instances", 'FieldTreasure-FIELD_TREASURE_CONTAINER-FieldTreasureContainer', '__FieldTreasure__', 0)
            elif et == 'Enemy':
                for s in [("Level", "level_range"), ("XP", "experience_range"), ("Health", "health_range"), ("Melee Power", "melee_power_range"), ("Melee Accuracy", "melee_accuracy_range"), ("Ranged Power", "ranged_power_range"), ("Ranged Accuracy", "ranged_accuracy_range"), ("Potential", "potential_range"), ("Evasion", "evasion_range"), ("Physical Resistance", "physical_resistance"), ("Beam Resistance", "beam_resistance"), ("Thermal Resistance", "thermal_resistance"), ("Ether Resistance", "ether_resistance"), ("Gravity Resistance", "gravity_resistance")]:
                    msg += self.display_stat(ed, s[0], s[1], 'range' in s[1])
                for s in [("Drops", 'Enemy-DROPS', '__Enemy-DROPS__', -1), ("Species", 'Enemy-SUBCATEGORY', '__enemy-SUBCATEGORY__', -1), ("Type", 'Enemy-TYPE', '__enemy-TYPE__', -1), ("Weather", 'Enemy-WEATHER', '__enemy-WEATHER__', -1), ("Time", 'Enemy-TIME', '__Enemy-TIME__', -1), ("At", 'Enemy-HAS', '__Enemy-HAS__', -1)]:
                    msg += self.display_data(ed, s[0], s[1], s[2], s[3])
                msg += f"<b>Notes:</b> {ed['notes']}<br>"
            elif et == 'Pet':
                msg += f"<b>Description:</b> {ed['description']}<br>"
                msg += self.display_data(ed, "Species", "Pet-SPECIES", "__Pet-SPECIES__", -1)
            elif et == 'Material':
                msg += self.display_data(ed, "Enemy Drops", "Enemy-DROPS-Material", "__Enemy-DROPS__", 0)
            elif et == 'Item':
                msg += self.display_data(ed, "Treasure Drops", "FieldTreasure-DROPS-Item", "__FieldTreasure-DROPS__", 0)
            elif et == 'Region':
                msg += self.display_data(ed, "Containing", "Region-HAS", "__Region-HAS__", -1)
                msg += self.display_data(ed, "Map", "SegmentGrid-REGION-Region", "__SegmentGrid-REGION-Region__", 0)
            elif et == 'EnemySubcategory':
                msg += self.display_data(ed, "Species", "EnemySubcategory-CATEGORY", "__EnemySubcategory-CATEGORY__", -1)
                msg += self.display_data(ed, "Enemies", "Enemy-SUBCATEGORY-EnemySubcategory", "__Enemy-SUBCATEGORY-EnemySubcategory__", 0)
            elif et == 'AffinityMission':
                msg += self.display_data(ed, "Location", "Segment-GOAL-AffinityMission", "__Segment-GOAL__", 0)
            elif et == 'Time':
                msg += f"<b>Period:</b> {ed['period']}<br>"
                msg += self.display_data(ed, "Previous", "Time-NEXT-Time", "__Time-NEXT__", 0)
                msg += self.display_data(ed, "Next", "Time-NEXT", "__Time-NEXT__", -1)
                msg += self.display_data(ed, "Weathers", "Weather-TIME-Time", "__Weather-TIME-Time__", 0)
                msg += self.display_data(ed, "Enemies", "Enemy-TIME-Time", "__Enemy-TIME-Time__", 0)
            elif et == 'FieldSkill':
                msg += self.display_data(ed, "locations", "FieldTreasure-FIELD_SKILL-FieldSkill", "__FieldTreasure-FIELD_SKILL__", 0)
            elif et == 'BattleClass':
                msg += f"<b>Tier:</b> {ed['level']}<br>"
                msg += self.display_data(ed, "Characters", "Character-CLASS-BattleClass", "__Character-CLASS__", 0)
            elif et == 'FNSiteProbe':
                msg += f"<b>Type:</b> {ed['type']}<br>"
                msg += f"<b>Production Multiplier:</b> {ed['attributes']['production_multiplier']}<br>"
                msg += f"<b>Revenue Multiplier:</b> {ed['attributes']['revenue_multiplier']}<br>"
                msg += self.display_data(ed, "Dropped by", "FieldTreasure-DROPS-FNSiteProbe", "__FieldTreasure-DROPS__", 0)
            elif et == 'Weather':
                msg += self.display_data(ed, "Collectibles", "Collectible-WEATHER-Weather", "__Collectible-WEATHER__", 0)
                msg += self.display_data(ed, "Enemies", "Enemy-WEATHER-Weather", "__Enemy-WEATHER__", 0)
                msg += self.display_data(ed, "Time", "Weather-TIME", "__Weather-TIME__", -1)
                msg += self.display_data(ed, "Region", "Region-WEATHER-Weather", "__Region-WEATHER__", 0)
                msg += self.display_data(ed, "Prerequisite", "Weather-PREREQUISITE-Weather", "__Weather-PREREQUISITE__", -1)
            elif et == 'Map':
                msg += self.display_data(ed, "Containing", "Map-HAS", "__Map-HAS__", -1, mode=1)
                msg += self.display_data(ed, "Marker", "MapMarker-MAP_LINK-Map", "__MapMarker-MAP__", 0)
                msg += self.display_data(ed, "Area", "MapArea-MAP_LINK-Map", "__MapArea-MAP_LINK__", 0)
            elif et == 'MapMarker':
                msg += self.display_latLng(ed)
                msg += self.display_data(ed, "Map Link", "MapMarker-MAP_LINK", "__MapMarker-MAP_LINK__", -1)
                msg += self.display_data(ed, "Map Layer", "MapLayer-MARKED_WITH-MapMarker", "__MapLayer-MARKED_WITH__", 0)
            elif et == 'Location':
                msg += self.display_data(ed, "Fast Travel", "Location-FAST_TRAVEL", "__Location-FAST_TRAVEL__", -1)
                msg += self.display_data(ed, "Marker", "MapMarker-MAP_LINK-Location", "__MapMarker-MAP_LINK__", 0)
                msg += self.display_data(ed, "Region", "Region-HAS-Location", "__Region-HAS__", 0)
                msg += self.display_data(ed, "Type", "Location-TYPE", "__Location-TYPE__", -1)
            elif et == 'Species':
                if 'description' in ed: msg += f"<b>Description:</b> {ed['description']}<br>"
                msg += self.display_data(ed, "Pets", "Pet-SPECIES-Species", "__Pet-SPECIES__", 0)
                msg += self.display_data(ed, "Characters", "Character-SPECIES-Species", "__Character-SPECIES__", 0)
            elif et == 'Character':
                if 'age' in ed: msg += f"<b>Age:</b> {ed['age']}<br>"
                msg += self.display_data(ed, "Gender", "Character-GENDER", "__Character-GENDER__", -1)
                msg += self.display_data(ed, "Species", "Character-SPECIES", "__Character-SPECIES__", -1)
                msg += self.display_data(ed, "Class", "Character-CLASS", "__Character-CLASS__", -1)
                msg += self.display_data(ed, "Marker", "MapMarker-MAP_LINK-Character", "__MapMarker-MAP_LINK__", 0)
                msg += self.display_data(ed, "Location", "Segment-GOAL-Character", "__Segment-GOAL__", 0)
            elif et == 'EnemyCategory':
                msg += self.display_data(ed, "Subcategories", "EnemySubcategory-CATEGORY-EnemyCategory", "__EnemySubcategory-CATEGORY__", 0)
            elif et == 'Collectible':
                msg += f"<b>Description:</b> {ed['description']}<br>"
                msg += f"<b>Price:</b> {ed['price']}<br>"
                msg += self.display_data(ed, "Category", "Collectible-CATEGORY", "__Collectible-CATEGORY__", -1)
                msg += self.display_data(ed, "Rarity", "Collectible-RARITY", "__Collectible-RARITY__", -1)
                msg += self.display_data(ed, "Region", "Collectible-REGION", "__Collectible-REGION__", -1)
                msg += self.display_data(ed, "Area", "CollectibleArea-CONTAINS-Collectible", "__CollectibleArea-CONTAINS__", 0)
            elif et == 'CollectibleArea':
                msg += self.display_data(ed, "Collectible Areas", "CollectibleArea-CONTAINS", "__CollectibleArea-CONTAINS__", -1)
                msg += self.display_data(ed, "Area", "MapArea-MAP_LINK-CollectibleArea", "__MapArea-MAP_LINK__", 0)
                msg += self.display_data(ed, "Region", "Region-CONTAINS-CollectibleArea", "__Region-CONTAINS__", 0)
            elif et == 'Rarity':
                msg += self.display_data(ed, "Collectibles", "Collectible-RARITY-Rarity", "__Collectible-RARITY__", 0)
                msg += self.display_data(ed, "Precious Resources", "PreciousResource-RARITY-Rarity", "__PreciousResource-RARITY__", 0)
            elif et == 'Gender':
                msg += self.display_data(ed, "Characters", "Character-GENDER-Gender", "__Character-GENDER__", 0)
            elif et == 'MapLayer':
                if 'description' in ed: msg += f"<b>Description:</b> {ed['description']}<br>"
                msg += self.display_data(ed, "Markers", "MapLayer-MARKED_WITH", "MapLayer-MARKED_WITH", -1)
                msg += self.display_data(ed, "Part of", "Map-HAS-MapLayer", "Map-HAS", 0)
            elif et == 'Mission':
                msg += self.display_data(ed, "Location", "Segment-GOAL-Mission", "Segment-GOAL", 0)
            elif et == 'CollectibleCategory':
                msg += self.display_data(ed, "Collectibles", "Collectible-CATEGORY-CollectibleCategory", "Collectible-CATEGORY", 0)
            elif et == 'Segment':
                msg += "<b>Region Grid Coordinate:</b> {}<br>".format(','.join(ed['grid_coordinate'].split(',')[:-1]))
                msg += self.display_data(ed, "Part of", "SegmentGrid-HAS-Segment", "SegmentGrid-HAS", 0)
                msg += self.display_data(ed, "Linked to", "Segment-GOAL", "Segment-GOAL", -1)
            elif et == 'LocationType':
                msg += self.display_data(ed, "Locations", "Location-TYPE-LocationType", "Location-TYPE", 0)
            elif et == 'SegmentGrid':
                msg += self.display_data(ed, "Containing", "SegmentGrid-HAS", "SegmentGrid-HAS", -1)
                msg += self.display_data(ed, "Map Layers", "MapLayer-MARKED_WITH-SegmentGrid", "MapLayer-MARKED_WITH", 0, mode=1)
                msg += self.display_data(ed, "Region", "SegmentGrid-REGION", "SegmentGrid-REGION", -1)
            elif et == 'MapArea':
                msg += self.display_data(ed, "Containing", "MapLayer-MARKED_WITH-MapArea", "MapLayer-MARKED_WITH", 0)
                msg += self.display_data(ed, "Area of", "MapArea-MAP_LINK", "MapArea-MAP_LINK", -1)
            elif et == 'Treasure':
                if 'requirements' in ed:
                    if 'field_skill_level' in ed['requirements']:
                        msg += f"<b>Requirement:</b> {ed['requirements']['field_skill']} lvl {ed['requirements']['field_skill_level']}<br>"
                    else:
                        msg += f"<b>Requirement:</b> {ed['requirements']['field_skill']}<br>"
                msg += self.display_data(ed, "Location", "Segment-GOAL-Treasure", "Segment-GOAL", 0)
            elif et == 'EnemyType':
                msg += self.display_data(ed, "Enemies", "Enemy-TYPE-EnemyType", "Enemy-TYPE", 0)
            elif et == 'PreciousResource':
                msg += f"<b>Price:</b> {ed['price']}<br>"
                msg += self.display_data(ed, "Rarity", "PreciousResource-RARITY", "PreciousResource-RARITY", -1)
                msg += self.display_data(ed, "Location", "FNSite-PRECIOUS_RESOURCE-PreciousResource", "FNSite-PRECIOUS_RESOURCE", 0)
            elif et == 'FNSite':
                msg += f"<b>Production Rank:</b> {ed['production']}<br>"
                msg += f"<b>Revenue Rank:</b> {ed['revenue']}<br>"
                msg += f"<b>Support Rank:</b> {ed['combat_support']}<br>"
                msg += self.display_data(ed, "Location", "Segment-GOAL-FNSite", "Segment-GOAL", 0)
                msg += self.display_data(ed, "Sightseeing", "FNSite-SIGHTSEEING", "FNSite-SIGHTSEEING", -1)
                if 'sightseeing_spots' in ed: msg += f"<b>Sightseeing:</b> {ed['sightseeing_spots']}<br>"
                msg += self.display_data(ed, "Part of", "FNSiteGraph-HAS-FNSite", "FNSiteGraph-HAS", 0)
                msg += self.display_data(ed, "Linked to", "FNSite-HAS-FNSite", "FNSite-HAS", 0)
                msg += self.display_data(ed, "Field Skill", "FNSite-FIELD_SKILL", "FNSite-FIELD_SKILL", -1)
            elif et == 'FNSiteGraph':
                msg += self.display_data(ed, "Part of", "MapLayer-MARKED_WITH-FNSiteGraph", "MapLayer-MARKED_WITH", 0)
                msg += self.display_data(ed, "Contains", "FNSiteGraph-HAS", "FNSiteGraph-HAS", -1)
                msg += self.display_data(ed, "Starting Point", "FNSiteGraph-START", "FNSiteGraph-START", -1)
            elif et == 'FieldTreasure':
                if 'experience_points' in ed:  msg += f"<b>XP:</b> {ed['experience_points']}<br>"
                if 'credits' in ed:  msg += f"<b>Credits:</b> {ed['credits']}<br>"
                msg += self.display_data(ed, "Drops", "FieldTreasure-DROPS", "FieldTreasure-DROPS", -1)
                msg += self.display_data(ed, "Marker", "MapMarker-MAP_LINK-FieldTreasure", "MapMarker-MAP_LINK", 0)
                msg += self.display_data(ed, "Container", "FieldTreasure-FIELD_TREASURE_CONTAINER", "FieldTreasure-FIELD_TREASURE_CONTAINER", -1)
                msg += self.display_data(ed, "Field Skill", "FieldTreasure-FIELD_SKILL", "FieldTreasure-FIELD_SKILL", -1)
        msg += "</div>"
        return msg

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/xcx?'):
            options = self.server.getOptions(path, 'xcx')
            try:
                query = unquote(options.get('query', '').replace('+', ' '))
                category = unquote(options.get('category', ''))
                html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style>'
                if query == "" and category == "Category": footer = '<div class="elem"><a href="/">Back</a>'
                else: footer = '<div class="elem"><a href="/xcx?category=Category">Back</a>'
                footer += '<form action="/xcx"><label for="query">Search </label><input type="text" id="query" name="query" value="{}"><br><input type="submit" value="Send"></form>'.format(query)
                if self.notification is not None:
                    footer += "<br>{}".format(self.notification)
                    self.notification = None
                footer += '</div>'
                html += footer

                if category + query == "":
                    html += '<div class="elem">Please affine the search</div>'
                else:
                    results = self.search(category, query)
                    if len(results) == 0:
                        html += '<div class="elem">No results</div>'
                    else:
                        for r in results:
                            html += self.display(r)

                html += footer
                html += '</body>'
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
            except Exception as e:
                print("Failed to search the XCX DB")
                self.server.printex(e)
                handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        elif path.startswith('/xcxupdate'):
            self.update()
            handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<b>Xenoblade X Database</b><br><form action="/xcx"><label for="query">Search </label><input type="text" id="query" name="query" value=""><br><input type="submit" value="Send"></form><a href="/xcx?category=Category">Open</a><br><a href="/xcxupdate">Update</a>'
        if self.notification is not None:
            html += "<br>{}".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>Xenoblade X Database plugin</b><br>Search informations for the game Xenoblade Chronicles X using data from <a href="https://frontiernav.jahed.dev/">https://frontiernav.jahed.dev/</a>.<br>Region grid coordinates are centered at the center of each area.'