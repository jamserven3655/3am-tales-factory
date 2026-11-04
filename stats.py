# Free self-tuning: public YouTube stats -> stats.json (story id -> views/likes). Skips quietly without key.
import json,os,re,urllib.request,urllib.parse
K=os.environ.get("YOUTUBE_API_KEY")
if not K: print("no YOUTUBE_API_KEY, skipping"); raise SystemExit
def g(p,**q):
    q["key"]=K; return json.load(urllib.request.urlopen("https://www.googleapis.com/youtube/v3/"+p+"?"+urllib.parse.urlencode(q),timeout=30))
try:
    up=g("channels",part="contentDetails",forHandle="3amtales-v8q")["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids=[i["contentDetails"]["videoId"] for i in g("playlistItems",part="contentDetails",playlistId=up,maxResults=50)["items"]]
    vids=g("videos",part="snippet,statistics",id=",".join(ids))["items"] if ids else []
    norm=lambda s:re.sub(r"[^a-z0-9]","",s.lower().split("#")[0])
    stories={norm(s["title"]):s["id"] for s in json.load(open("stories.json"))}
    out={}
    for v in vids:
        sid=stories.get(norm(v["snippet"]["title"]))
        if sid: out[sid]={"views":int(v["statistics"].get("viewCount",0)),"likes":int(v["statistics"].get("likeCount",0))}
    json.dump(out,open("stats.json","w"),indent=1); print("stats for",len(out),"stories")
except Exception as e: print("stats skipped:",e)
