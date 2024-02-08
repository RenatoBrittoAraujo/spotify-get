import requests
import json
import subprocess

BEARER = "Bearer ... ---------------- GET IT IN BROWSER NETWORK TAB"

global jqcount
jqcount = 3


def print_json(obj):
    print(json.dumps(obj, indent=4))


def jq(obj, query):
    global jqcount
    with open(f"res{jqcount}.json", "w") as f:
        f.write(json.dumps(obj, indent=4))
    data = subprocess.check_output(
        f"cat res{jqcount}.json | jq '{query}'",
        shell=True,
    )
    jqcount += 1
    return json.loads(data)


res = requests.get(
    "https://api-partner.spotify.com/pathfinder/v1/query",
    params={
        "operationName": "libraryV3",
        "variables": '{"filters":[],"order":null,"textFilter":"","features":["LIKED_SONGS","YOUR_EPISODES"],"limit":100000,"offset":0,"flatten":true,"expandedFolders":[],"folderUri":null,"includeFoldersWhenFlattening":true,"withCuration":false}',
        "extensions": '{"persistedQuery":{"version":1,"sha256Hash":"---------------- GET IT IN BROWSER NETWORK TAB"}}',
    },
    headers={
        "app-platform": "WebPlayer",
        "spotify-app-version": "1.2.31.0-unknown",
        "client-token": "... ---------------- GET IT IN BROWSER NETWORK TAB",
        "DNT": "1",
        "authorization": BEARER,
    },
)

if res.status_code != 200:
    print("[ERROR] failed to get playlists!")
    if res.status_code == 401:
        print(
            "The bearer token is invalid\nOpen https://open.spotify.com/ and get valid authorization token header"
        )
    else:
        print("unknown error in request. please fix")
    exit(1)

with open("res.json", "w") as f:
    f.write(res.text)

data = subprocess.check_output(
    "cat res.json | jq '[.data.me.libraryV3.items[].item.data]'", shell=True
)

playlists: list = json.loads(data)
items = []

for e in playlists:
    item = {"name": None, "uri": e.get("_uri") or e.get("uri")}
    if "name" in e:
        item["name"] = e["name"]
    else:
        if "profile" in e:
            if "name" in e["profile"]:
                item["name"] = e["profile"]["name"]
    items.append(item)

# print(json.dumps(items, indent=4))

spotify_data = []

for item in items:
    # get items in playlist
    uri = item["uri"]
    res = None

    offset = 0
    got = 0
    limit = 100

    res_list = []

    while got == 0 or got - offset == limit:
        print(f"MAKING REQ got={got} offset={offset} playlist='{item['name']}'")

        offset = got

        if "playlist" in uri:
            res = requests.get(
                "https://api-partner.spotify.com/pathfinder/v1/query",
                params={
                    "operationName": "fetchPlaylist",
                    "variables": '{{ "uri":"{}","offset":{},"limit":{}}}'.format(
                        item["uri"], offset, limit
                    ),
                    "extensions": '{"persistedQuery":{"version":1,"sha256Hash":"---------------- GET IT IN BROWSER NETWORK TAB"}}',
                },
                headers={
                    "app-platform": "WebPlayer",
                    "spotify-app-version": "1.2.31.0-unknown",
                    "client-token": "---------------- GET IT IN BROWSER NETWORK TAB",
                    "DNT": "1",
                    "authorization": BEARER,
                },
            )

        if "library" in uri:
            res = requests.get(
                "https://api-partner.spotify.com/pathfinder/v1/query",
                params={
                    "operationName": "fetchLibraryTracks",
                    "variables": '{{ "offset":{},"limit":{}}}'.format(offset, limit),
                    "extensions": '{"persistedQuery":{"version":1,"sha256Hash":"---------------- GET IT IN BROWSER NETWORK TAB"}}',
                },
                headers={
                    "app-platform": "WebPlayer",
                    "spotify-app-version": "1.2.31.0-unknown",
                    "client-token": "---------------- GET IT IN BROWSER NETWORK TAB",
                    "DNT": "1",
                    "authorization": BEARER,
                },
            )

        if res is None:
            break

        count_obj = json.loads(res.text)
        counter = jq(count_obj, "[.data.playlistV2.content.items[]]")
        pgot = got
        got += len(counter)
        res_list = res_list + counter
        if pgot == got:
            break

    if res is None:
        continue

    if res.status_code != 200:
        print(f"FAILED to fetch playlist '{item['name']}'")
        print(res, res.reason)
        print(res.text)
        exit(1)

    # with open("res2.json", "w") as f:
    #     res_obj = json.loads(res.text)
    #     f.write(json.dumps(res_obj))

    # # print(res_obj)
    res_obj = res_list

    addedAts = jq(res_obj, "[.[].addedAt.isoString]")

    names = jq(res_obj, "[.[].itemV2.data.name]")

    uris = jq(res_obj, "[.[].itemV2.data.uri]")

    durations = jq(
        res_obj,
        "[.[].itemV2.data.trackDuration.totalMilliseconds]",
    )

    playcounts = jq(res_obj, "[.[].itemV2.data.playcount]")

    artists = jq(
        res_obj,
        "[.[].itemV2.data.albumOfTrack.artists.items[0].profile.name]",
    )
    songs = []

    for i in range(len(addedAts)):
        song = {
            "addedAt": addedAts[i],
            "uri": uris[i],
            "playcount": playcounts[i],
            "duration": durations[i],
            "name": names[i],
            "artists": artists[i],
        }
        songs.append(song)

    spotify_data.append({"name": item["name"], "uri": item["uri"], "songs": songs})

    print(f"successfully got playlist '{item['name']}' with {len(songs)} tracks")

with open("out.json", "w") as f:
    f.write(json.dumps(spotify_data, indent=4))
