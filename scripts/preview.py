"""Experimental Spine 3.8-ish JSON image preview. Not a full Spine runtime.
Dependencies: pillow numpy opencv-python. Keep original game assets local.
"""
import argparse, io, json, math, zipfile
import cv2
import numpy as np
from PIL import Image

def interpolate(keys,t,key,default):
    if not keys: return default
    before=keys[0]
    for after in keys[1:]:
        if after.get("time",0)>t:
            a=before.get(key,default); b=after.get(key,default)
            if before.get("curve")=="stepped": return a
            p=(t-before.get("time",0))/max(1e-9,after["time"]-before.get("time",0))
            return a+(b-a)*p
        before=after
    return before.get(key,default)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--character",default="char020701")
    ap.add_argument("--animation",default="idle")
    ap.add_argument("--frames",type=int,default=12)
    ap.add_argument("--out",default="preview.gif")
    args=ap.parse_args()
    with zipfile.ZipFile(args.zip) as z:
        if z.testzip(): raise ValueError("Corrupt ZIP")
        path=next((p for p in z.namelist() if p.endswith("/"+args.character+".json")),None)
        if path is None: raise ValueError("No matching exported JSON")
        base=path[:path.index(args.character+"/")+len(args.character)+1]
        data=json.loads(z.read(path))
        bones=data["bones"]; slots=data["slots"]; skin=data["skins"][0]["attachments"]
        anim=data["animations"][args.animation]
        ids={b["name"]:i for i,b in enumerate(bones)}
        files=set(z.namelist()); cache={}
        times=[]
        for group in anim.values():
            if not isinstance(group,dict):continue
            for channel in group.values():
                if not isinstance(channel,dict):continue
                for keys in channel.values():
                    if isinstance(keys,list):
                        times += [k.get("time",0) for k in keys if isinstance(k,dict)]
        duration=max(times,default=4) or 4
        def frame(t):
            matrices=[]
            for b in bones:
                channels=anim.get("bones",{}).get(b["name"],{})
                x=b.get("x",0)+interpolate(channels.get("translate",[]),t,"x",0)
                y=b.get("y",0)+interpolate(channels.get("translate",[]),t,"y",0)
                r=math.radians(b.get("rotation",0)+interpolate(channels.get("rotate",[]),t,"angle",0))
                sx=b.get("scaleX",1)*interpolate(channels.get("scale",[]),t,"x",1)
                sy=b.get("scaleY",1)*interpolate(channels.get("scale",[]),t,"y",1)
                m=np.array([[math.cos(r)*sx,-math.sin(r)*sy,x],[math.sin(r)*sx,math.cos(r)*sy,y],[0,0,1]])
                if b.get("parent"):m=matrices[ids[b["parent"]]]@m
                matrices.append(m)
            layers=[]
            for s in slots:
                name=s.get("attachment")
                for k in anim.get("slots",{}).get(s["name"],{}).get("attachment",[]):
                    if k.get("time",0)<=t:name=k.get("name")
                    else:break
                attachment=skin.get(s["name"],{}).get(name) if name else None
                if not attachment:continue
                p=base+"images/"+attachment.get("path",name)+".png"
                if p not in files:continue
                if p not in cache:cache[p]=np.asarray(Image.open(io.BytesIO(z.read(p))).convert("RGBA"))
                im=cache[p];h,w=im.shape[:2]
                if attachment.get("type")=="mesh":
                    uv=np.asarray(attachment["uvs"]).reshape(-1,2)
                    v=attachment["vertices"];count=len(uv)
                    if len(v)==2*count:
                        pts=np.asarray(v).reshape(-1,2)
                        m=matrices[ids[s["bone"]]]
                        pts=np.array([(m@np.array([x,y,1]))[:2] for x,y in pts])
                    else:
                        pts=[];j=0
                        for _ in range(count):
                            n=int(v[j]);j+=1;xy=np.zeros(2)
                            for _ in range(n):
                                bi=int(v[j]);x,y,weight=v[j+1:j+4];j+=4
                                xy+=(matrices[bi]@np.array([x,y,1]))[:2]*weight
                            pts.append(xy)
                        pts=np.array(pts)
                    tris=np.asarray(attachment["triangles"]).reshape(-1,3)
                else:
                    ww=attachment.get("width",w);hh=attachment.get("height",h)
                    x=attachment.get("x",0);y=attachment.get("y",0)
                    r=math.radians(attachment.get("rotation",0))
                    cs=math.cos(r);sn=math.sin(r)
                    pts=np.array([[-ww/2,-hh/2],[ww/2,-hh/2],[ww/2,hh/2],[-ww/2,hh/2]])
                    m=matrices[ids[s["bone"]]]
                    pts=np.array([(m@np.array([px*cs-py*sn+x,px*sn+py*cs+y,1]))[:2] for px,py in pts])
                    uv=np.array([[0,1],[1,1],[1,0],[0,0]])
                    tris=np.array([[0,1,2],[0,2,3]])
                layers.append((im,pts,uv,tris))
            W,H=520,750;out=np.zeros((H,W,4),dtype=np.uint8)
            origin=np.array([-430.,-600.]);scale=.55
            for im,pts,uv,tris in layers:
                h,w=im.shape[:2]
                src=uv*np.array([w-1,h-1])
                dst=(pts-origin)*scale;dst[:,1]=H-dst[:,1]
                for tri in tris:
                    ss=src[tri].astype(np.float32);dd=dst[tri].astype(np.float32)
                    x,y,bw,bh=cv2.boundingRect(dd)
                    x0=max(x,0);y0=max(y,0);x1=min(x+bw,W);y1=min(y+bh,H)
                    if x1<=x0 or y1<=y0:continue
                    offset=np.array([x0,y0],dtype=np.float32)
                    transform=cv2.getAffineTransform(ss,dd-offset)
                    patch=cv2.warpAffine(im,transform,(x1-x0,y1-y0),flags=cv2.INTER_LINEAR)
                    mask=np.zeros((y1-y0,x1-x0),np.uint8)
                    cv2.fillConvexPoly(mask,np.rint(dd-offset).astype(np.int32),255)
                    alpha=patch[:,:,3].astype(float)/255*mask/255
                    old=out[y0:y1,x0:x1];oa=old[:,:,3].astype(float)/255
                    na=alpha+oa*(1-alpha)
                    rgb=(patch[:,:,:3]*alpha[:,:,None]+old[:,:,:3]*oa[:,:,None]*(1-alpha[:,:,None]))/np.maximum(na[:,:,None],1e-5)
                    old[:,:,:3]=np.clip(rgb,0,255).astype(np.uint8)
                    old[:,:,3]=np.clip(na*255,0,255).astype(np.uint8)
            return Image.fromarray(out).convert("RGB")
        n=max(2,args.frames)
        frames=[frame(i*duration/n) for i in range(n)]
        frames[0].save(args.out,save_all=True,append_images=frames[1:],duration=int(duration*1000/n),loop=0,optimize=True)
        print("Saved",args.out,"duration",duration,"frames",n)

if __name__=="__main__":main()
