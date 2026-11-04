import json,sys,html
S=sys.argv[1]; V=json.load(open(f"{S}/videos.json"))
cards="".join(f"""<div class=c><video src="{v['file']}" controls playsinline preload=metadata></video>
<h2>{html.escape(v['title'])}</h2><small>{v['made'][:10]} · {v['duration']}s</small>
<a class=b href="{v['file']}" download>⬇ Download MP4</a>
<button onclick='cp(this,{json.dumps(v["title"])})'>Copy title</button>
<button onclick='cp(this,{json.dumps(v["description"])})'>Copy description</button>
<button onclick='cp(this,{json.dumps(v["hashtags"])})'>Copy hashtags</button></div>""" for v in V)
open(f"{S}/index.html","w").write(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>3AM Tales Factory</title>
<style>body{{background:#0b0d10;color:#e6e6e6;font-family:system-ui;margin:0;padding:14px}}h1{{font-size:20px;color:#ff3b3b}}.c{{background:#151a20;border:1px solid #222a33;border-radius:14px;padding:12px;margin:0 0 16px}}
video{{width:100%;max-height:70vh;border-radius:10px;background:#000}}h2{{font-size:16px;margin:8px 0 2px}}small{{color:#8a96a3}}
.b,button{{display:block;width:100%;box-sizing:border-box;margin-top:8px;padding:12px;border-radius:10px;border:0;font-size:15px;text-align:center;text-decoration:none;color:#fff;background:#2a323c}}.b{{background:#c62828}}</style>
<h1>🌙 3AM Tales Factory</h1><p><small>New Short every afternoon. Newest first. Post 7–10 PM ET.</small></p>{cards or '<p>No videos yet.</p>'}
<script>function cp(b,t){{navigator.clipboard.writeText(t).then(()=>{{let o=b.textContent;b.textContent='Copied ✓';setTimeout(()=>b.textContent=o,1200)}})}}</script>""")
