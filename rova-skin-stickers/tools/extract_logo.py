"""Pull the Rova mark, wordmark and sparkle out of the brand presentation PDF as clean SVG path data."""
import json, pymupdf
B="/root/.claude/uploads/e0f57f31-6e2d-53a9-92da-4c19438f9bc1/f3f3d4ac-Rova-Brand-Presentation.pdf"
doc=pymupdf.open(B)
BURG=(0.2353000044822693, 0.0706000030040741, 0.09799999743700027)
IVORY=(0.9373000264167786, 0.8744999766349792, 0.8156999945640564)

def near(a,b): return a is not None and b is not None and all(abs(x-y)<0.01 for x,y in zip(a,b))

def d_of(items):
    out=[]; cur=None
    f=lambda p:(round(p.x,3),round(p.y,3))
    for it in items:
        k=it[0]
        if k=='l':
            p1,p2=f(it[1]),f(it[2])
            if cur!=p1: out.append(f"M{p1[0]} {p1[1]}")
            out.append(f"L{p2[0]} {p2[1]}"); cur=p2
        elif k=='c':
            p1,p2,p3,p4=f(it[1]),f(it[2]),f(it[3]),f(it[4])
            if cur!=p1: out.append(f"M{p1[0]} {p1[1]}")
            out.append(f"C{p2[0]} {p2[1]} {p3[0]} {p3[1]} {p4[0]} {p4[1]}"); cur=p4
        elif k=='re':
            r=it[1]; out.append(f"M{round(r.x0,3)} {round(r.y0,3)}H{round(r.x1,3)}V{round(r.y1,3)}H{round(r.x0,3)}Z"); cur=None
        elif k=='qu':
            q=it[1]; pts=[f(q.ul),f(q.ur),f(q.lr),f(q.ll)]
            out.append("M%s %sL%s %sL%s %sL%s %sZ"%(pts[0]+pts[1]+pts[2]+pts[3])); cur=None
    return " ".join(out)

def grab(pno, ink, region, name):
    page=doc[pno]; sel=[]
    for d in page.get_drawings():
        r=d['rect']
        if not (r.x0>=region[0] and r.y0>=region[1] and r.x1<=region[2] and r.y1<=region[3]): continue
        is_ink = near(d.get('fill'),ink) or (d.get('fill') is None and near(d.get('color'),ink))
        if not is_ink: 
            print("  skip non-ink", name, d.get('fill'), d.get('color'), r); continue
        sel.append(d)
    x0=min(d['rect'].x0 for d in sel); y0=min(d['rect'].y0 for d in sel)
    x1=max(d['rect'].x1 for d in sel); y1=max(d['rect'].y1 for d in sel)
    paths=[]
    for d in sel:
        paths.append({
            "d": d_of(d['items']) + (" Z" if d.get('closePath') else ""),
            "fill": d.get('fill') is not None,
            "stroke": d.get('color') is not None,
            "width": round(d.get('width') or 0,3),
            "even_odd": bool(d.get('even_odd')),
        })
    print(f"{name}: {len(paths)} paths, bbox {x0:.1f},{y0:.1f} - {x1:.1f},{y1:.1f}  ({x1-x0:.1f} x {y1-y0:.1f})")
    return {"x0":x0,"y0":y0,"w":x1-x0,"h":y1-y0,"paths":paths}

out={}
# page 6 (index 5): the big mark, ivory on burgundy, left half
out["mark"]=grab(5, IVORY, (90,250,560,740), "mark")
# page 7 (index 6): wordmark ROVA + BEAUTY CLINIC on the white card (card spans ~ x 90-660, y 250-700)
page=doc[6]
for d in page.get_drawings():
    print("p7", d['rect'], d.get('fill'), d.get('color'), d.get('width'))
out["wordmark_all"]=grab(6, BURG, (95,255,655,695), "wordmark_all")
# page 12 (index 11): the vertical label badge (oval, stars, mark, ROVA, BEAUTY CLINIC) ivory on burgundy, right card
page=doc[11]
for d in page.get_drawings():
    r=d['rect']
    if r.x0>900: print("p12", r, d.get('fill'), d.get('color'), d.get('width'), d.get('even_odd'))
out["badge"]=grab(11, IVORY, (930,120,1350,690), "badge")
json.dump(out, open("logo_raw.json","w"))
