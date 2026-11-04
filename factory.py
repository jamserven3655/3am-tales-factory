# 3AM Tales factory: builds one Short from stories.json. Runs on ubuntu-latest.
import json,os,random,subprocess,sys,math,base64,urllib.request,re,datetime
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
SITE=sys.argv[1] if len(sys.argv)>1 else "site"; os.makedirs(f"{SITE}/videos",exist_ok=True)
W="work"; os.makedirs(W,exist_ok=True)
stories=json.load(open("stories.json"))
st=json.load(open(f"{SITE}/state.json")) if os.path.exists(f"{SITE}/state.json") else {"used":[]}
stats=json.load(open("stats.json")) if os.path.exists("stats.json") else {}
def run(c): subprocess.run(c,check=True)
# ---- pick: unused story, weighted toward best device types / lengths
pool=[s for s in stories if s["id"] not in st["used"]] or stories
if pool is stories: st["used"]=[]
dev={};ln={}
for s in stories:
    v=stats.get(s["id"])
    if v: dev.setdefault(s["device"],[]).append(v["views"]); ln.setdefault(len(s["lines"])>9,[]).append(v["views"])
allv=[x for l in dev.values() for x in l]; g=(sum(allv)/len(allv)) if allv else 0
def wt(s):
    if not g: return 1
    d=dev.get(s["device"]); l=ln.get(len(s["lines"])>9)
    return (0.5+(sum(d)/len(d))/g if d else 1)*(0.7+0.3*(sum(l)/len(l))/g if l else 1)
force=os.environ.get("STORY_ID")
S=next((s for s in stories if s["id"]==force),None) or random.choices(pool,[wt(s) for s in pool])[0]
print("STORY",S["id"],S["title"])
# ---- TTS
k=Kokoro("models/kokoro-v1.0.onnx","models/voices-v1.0.bin")
sr=24000;out=[np.zeros(int(sr*.25))];meta=[];t=.25;twist=None
lines=S["lines"]
for i,raw in enumerate(lines):
    red=(re.findall(r"\*(\w[\w']*)\*",raw) or [None])[0]; txt=raw.replace("*","")
    if txt.lower().startswith("it's me"): twist=i
    nxt=lines[i+1].replace("*","").lower() if i+1<len(lines) else ""
    p=1.1 if nxt.startswith("it's me") else (.6 if twist==i else .35)
    a,sr=k.create(txt,voice="am_michael",speed=.92,lang="en-us")
    meta.append([t,len(a)/sr,txt,red]); out+=[a,np.zeros(int(sr*p))]; t+=len(a)/sr+p
sf.write(f"{W}/vo.wav",np.concatenate(out),sr)
F=1/.95; T=[(s*F,(s+d)*F,x,r) for s,d,x,r in meta]; END=T[-1][1]+2.4
if twist is None: twist=len(T)//2
# ---- images: Cloudflare Workers AI (free), fallback to dark noise frames
acc,tok=os.environ.get("CF_ACCOUNT_ID"),os.environ.get("CF_API_TOKEN")
STYLE=", real amateur footage, grainy low light security camera or phone video still, night, muted colors, no faces, no text, photorealistic, vertical"
imgs=[]
AI_OK=[]
for j,p in enumerate(S["prompts"]):
    f=f"{W}/i{j}.jpg"; ok=False
    if acc and tok:
        try:
            rq=urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell",
              data=json.dumps({"prompt":p+STYLE,"steps":6}).encode(),
              headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"})
            r=json.load(urllib.request.urlopen(rq,timeout=90)); open(f,"wb").write(base64.b64decode(r["result"]["image"])); ok=True
        except Exception as e: print("image API failed:",e)
    if not ok:
        c=random.choice(["0x10161a","0x14140f","0x0d1410","0x161012"])
        run(["ffmpeg","-v","error","-y","-f","lavfi","-i",f"color=c={c}:s=1080x1920,noise=alls=40:allf=0,gblur=sigma=30,vignette=PI/3,noise=alls=12","-frames:v","1",f])
    imgs.append(f); AI_OK.append(ok)
# ---- shots: one per line, long lines split, black flash before twist
cut=[];n=len(imgs)
for i,(s,e,x,r) in enumerate(T):
    im=imgs[(i if i<twist else i+1)%n] if i!=twist else imgs[-1]
    if i==twist: cut.append((s-.25,"BLACK"))
    cut.append((s if i!=twist else s+.5,im))
    if e-s>2.4 and i!=twist: cut.append((s+(e-s)/2,imgs[(i+2)%n]))
cut[0]=(0,cut[0][1]); cut.append((T[-1][1],imgs[0]))  # loop back to opening shot
segs=[]
for i,(s,im) in enumerate(cut):
    e=cut[i+1][0] if i+1<len(cut) else END; d=max(e-s,.2); fr=max(1,round(d*30)); o=f"{W}/s{i:02d}.mp4"
    if im=="BLACK": c=["ffmpeg","-v","error","-y","-f","lavfi","-i",f"color=black:s=1080x1920:r=30:d={d}"]
    else:
        z0,z1=random.choice([(1.08,1.22),(1.22,1.10)]); cx,cy=random.uniform(.4,.6),random.uniform(.4,.6)
        zp=f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,scale=2160:-1,zoompan=z='{z0}+({z1}-{z0})*on/{fr}':x='iw*{cx}-iw/zoom/2+4*sin(on/3)':y='ih*{cy}-ih/zoom/2+4*cos(on/4)':d={fr}:s=1080x1920:fps=30"
        c=["ffmpeg","-v","error","-y","-loop","1","-i",im,"-vf",zp]
    run(c+["-frames:v",str(fr),"-pix_fmt","yuv420p","-c:v","libx264","-preset","veryfast","-crf","18",o]); segs.append(o)
open(f"{W}/segs.txt","w").write("".join(f"file '{os.path.basename(s)}'\n" for s in segs))
# ---- captions 1-3 words, red key word, CTA end card
def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
ev=[]
for li,(s,e,x,r) in enumerate(T):
    w=x.split();ch=[];i=0
    while i<len(w):
        kk=min(3,len(w)-i)
        if kk==3 and len(" ".join(w[i:i+3]))>16: kk=2
        ch.append(w[i:i+kk]); i+=kk
    tot=sum(len(" ".join(c)) for c in ch); t0=s
    for j,c in enumerate(ch):
        dd=(e-s)*len(" ".join(c))/tot; t1=t0+dd if j<len(ch)-1 else min(e+.35,(T[li+1][0] if li+1<len(T) else END-2))
        tx=" ".join("{\\c&H0000FF&}"+y+"{\\c&HFFFFFF&}" if r and y.strip(".,!?").lower()==r.lower() else y for y in c)
        ev.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},C,,0,0,0,,{tx.upper()}"); t0+=dd
ev.append(f"Dialogue: 1,{ts(END-2.1)},{ts(END)},E,,0,0,0,,{{\\fad(250,0)}}WHAT WOULD\\NYOU DO?")
open(f"{W}/cap.ass","w").write("""[Script Info]
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: C,DejaVu Sans,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,2,60,60,560,1
Style: E,DejaVu Sans,120,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,3,24,0,5,60,60,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""+"\n".join(ev)+"\n")
# ---- audio mix: voice (pitched down, reverb), brown noise + 55Hz drone, pings, sting at twist
S_ms=int(T[twist][0]*1000); P2=int(T[-1][0]*1000-300)
run(["ffmpeg","-v","error","-y","-f","concat","-i",f"{W}/segs.txt","-c","copy",f"{W}/v.mp4"])
run(["ffmpeg","-v","error","-y","-i",f"{W}/vo.wav","-f","lavfi","-i",f"anoisesrc=c=brown:a=0.03:d={END}","-f","lavfi","-i",f"sine=f=55:d={END}",
 "-f","lavfi","-i","sine=f=1318:d=0.12","-f","lavfi","-i","sine=f=1760:d=0.2","-f","lavfi","-i","anoisesrc=c=white:a=0.6:d=0.7","-f","lavfi","-i","sine=f=70:d=1.2","-filter_complex",
 f"[0:a]asetrate=24000*0.95,aresample=48000,aecho=0.8:0.5:45|80:0.22|0.12,volume=1.6,apad=whole_dur={END},asplit[vo][vk];"
 f"[3:a]adelay=0[c1];[4:a]adelay=130[c2];[c1][c2]amix=2:normalize=0,volume=0.35,aresample=48000,asplit[p1][p2b];[p2b]adelay={P2},aresample=48000[p2];"
 f"[5:a]highpass=f=800,afade=t=out:st=0.05:d=0.65[n];[6:a]afade=t=out:st=0.2:d=1.0,volume=0.9[l];[n][l]amix=2:normalize=0,adelay={S_ms},aresample=48000[st];"
 f"[2:a]volume=0.05[s];[1:a][s]amix=2:normalize=0,aresample=48000[bed];[bed][vk]sidechaincompress=threshold=0.02:ratio=8:release=400[bd];"
 f"[vo][bd][p1][p2][st]amix=5:duration=first:normalize=0,alimiter=limit=0.95[a]","-map","[a]","-t",str(END),"-ar","48000",f"{W}/mix.wav"])
today=datetime.date.today().strftime("%m/%d/%Y").replace("/","\\/"); cam=S.get("cam","CAM 01").replace(":","\\:")
mono="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
vid=datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")+"-"+S["id"]; outp=f"{SITE}/videos/{vid}.mp4"
run(["ffmpeg","-v","error","-y","-i",f"{W}/v.mp4","-i",f"{W}/mix.wav","-filter_complex",
 f"[0:v]hue=s=0.35,eq=contrast=1.08,rgbashift=rh=-3:bh=3,noise=alls=9:allf=t,vignette=PI/4.5,subtitles={W}/cap.ass,"
 f"drawtext=fontfile={mono}:text='{cam}  {today}  03\\:07\\:%{{eif\\:mod(t+12\\,60)\\:d\\:2}}':x=40:y=70:fontsize=36:fontcolor=white@0.8,"
 f"drawtext=fontfile={mono}:text='● REC':x=w-190:y=70:fontsize=36:fontcolor=red@0.9:enable='lt(mod(t\\,1)\\,0.6)'[v]",
 "-map","[v]","-map","1:a","-r","30","-c:v","libx264","-preset","medium","-b:v","6M","-maxrate","9M","-bufsize","16M","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",outp])
dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",outp]))
# ---- update site index (keep newest 14)
vj=f"{SITE}/videos.json"; V=json.load(open(vj)) if os.path.exists(vj) else []
V.insert(0,{"file":f"videos/{vid}.mp4","id":S["id"],"title":S["title"],"description":S["description"],"hashtags":S["hashtags"],"duration":round(dur,1),"made":datetime.datetime.utcnow().isoformat()+"Z","images":"ai" if AI_OK and all(AI_OK) else ("mixed" if any(AI_OK) else "fallback")})
for old in V[14:]:
    try: os.remove(f"{SITE}/{old['file']}")
    except OSError: pass
V=V[:14]; json.dump(V,open(vj,"w"),indent=1)
st["used"].append(S["id"]); json.dump(st,open(f"{SITE}/state.json","w"))
print("BUILT",outp,round(dur,1))
