import socket, json, sys
def call(cmd, params=None, to=30):
    s = socket.create_connection(('127.0.0.1',55558), timeout=to)
    msg = json.dumps({'type':cmd, **({'params':params} if params else {})}).encode('utf-8')
    s.sendall(len(msg).to_bytes(4,'big')); s.sendall(msg); s.settimeout(to)
    hdr=b''
    while len(hdr)<4:
        c=s.recv(4-len(hdr)); 
        if not c: raise RuntimeError('closed')
        hdr+=c
    n=int.from_bytes(hdr,'big'); body=b''
    while len(body)<n:
        c=s.recv(n-len(body))
        if not c: raise RuntimeError('closed-body')
        body+=c
    s.close(); return json.loads(body.decode('utf-8'))
if __name__=='__main__':
    cmd=sys.argv[1]; params=json.loads(sys.argv[2]) if len(sys.argv)>2 else None
    print(json.dumps(call(cmd, params), ensure_ascii=False))
