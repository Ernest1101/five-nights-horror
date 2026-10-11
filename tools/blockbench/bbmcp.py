import json, sys, urllib.request, os
URL = "http://localhost:3000/bb-mcp"
SF = os.path.join(os.path.dirname(__file__), ".session")
def _post(body, sid=None):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if sid: h["mcp-session-id"] = sid
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=h)
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read().decode("utf-8")
        sid2 = r.headers.get("mcp-session-id")
    if raw.startswith("event:") or raw.startswith("data:"):
        datas = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = datas[-1] if datas else "{}"
    return (json.loads(raw) if raw.strip() else {}), sid2
def session():
    if os.path.exists(SF):
        return open(SF).read().strip()
    res, sid = _post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"claude","version":"1"}}})
    _post({"jsonrpc":"2.0","method":"notifications/initialized"}, sid)
    open(SF,"w").write(sid); return sid
_id = [10]
def rpc(method, params=None):
    sid = session(); _id[0]+=1
    try:
        res, _ = _post({"jsonrpc":"2.0","id":_id[0],"method":method,"params":params or {}}, sid)
    except urllib.error.HTTPError as e:
        if e.code in (400,404) and os.path.exists(SF):
            os.remove(SF); return rpc(method, params)
        raise
    return res
def call(name, args=None):
    r = rpc("tools/call", {"name": name, "arguments": args or {}})
    if "error" in r: raise RuntimeError(json.dumps(r["error"]))
    res = r["result"]
    if res.get("isError"):
        raise RuntimeError(name + ": " + " ".join(c.get("text", "") for c in res.get("content", [])))
    return res
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        for t in rpc("tools/list")["result"]["tools"]:
            print(t["name"], "-", (t.get("description") or "")[:110].replace("\n"," "))
    elif cmd == "schema":
        for t in rpc("tools/list")["result"]["tools"]:
            if t["name"] in sys.argv[2:]: print(json.dumps(t, indent=1)[:4000])
    elif cmd == "call":
        r = call(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv)>3 else {})
        for c in r.get("content",[]):
            if c["type"]=="text": print(c["text"][:5000])
            else: print("[", c["type"], "]")
