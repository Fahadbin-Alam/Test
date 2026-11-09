import io, sys, json, requests, concurrent.futures as cf, re
import pyarrow.parquet as pq, pyarrow as pa
BASE="https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/"
S=requests.Session()
class RangeFile(io.RawIOBase):
    def __init__(self,url):
        self.url=url; r=S.head(url,timeout=60); self.size=int(r.headers['Content-Length']); self.pos=0; self.cache={}
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self,off,wh=0):
        self.pos = off if wh==0 else (self.pos+off if wh==1 else self.size+off); return self.pos
    def read(self,n=-1):
        if n<0: n=self.size-self.pos
        if n==0: return b''
        end=min(self.size,self.pos+n)-1
        for a in range(4):
            try:
                r=S.get(self.url,headers={'Range':f'bytes={self.pos}-{end}'},timeout=120); r.raise_for_status(); break
            except Exception as e:
                if a==3: raise
        d=r.content; self.pos+=len(d); return d
    def readinto(self,b):
        d=self.read(len(b)); b[:len(d)]=d; return len(d)
def keys(typ, rel):
    out=[]; tok=None
    while True:
        u=BASE+f"?list-type=2&prefix=release/{rel}/{typ}/"+(f"&continuation-token={requests.utils.quote(tok)}" if tok else "")
        t=S.get(u,timeout=60).text; out+=re.findall(r"<Key>([^<]*)</Key>",t)
        m=re.search(r"<NextContinuationToken>([^<]*)</NextContinuationToken>",t)
        if not m: break
        tok=m.group(1)
    return [k for k in out if k.endswith('.parquet')]
def scan(key,bb):
    x0,y0,x1,y1=bb
    f=pq.ParquetFile(RangeFile(BASE+key)); md=f.metadata; sch=f.schema_arrow
    names=[md.schema.column(i).path for i in range(md.num_columns)]
    ix={n:i for i,n in enumerate(names)}
    hit=[]
    for g in range(md.num_row_groups):
        rg=md.row_group(g)
        def st(n): s=rg.column(ix[n]).statistics; return s.min,s.max
        try:
            a=st('bbox.xmin'); b=st('bbox.xmax'); c=st('bbox.ymin'); d=st('bbox.ymax')
        except Exception: hit.append(g); continue
        if b[1]>=x0 and a[0]<=x1 and d[1]>=y0 and c[0]<=y1: hit.append(g)
    rows=[]
    for g in hit:
        t=f.read_row_group(g)
        bx=t.column('bbox').combine_chunks()
        xmin=bx.field('xmin').to_numpy(); xmax=bx.field('xmax').to_numpy(); ymin=bx.field('ymin').to_numpy(); ymax=bx.field('ymax').to_numpy()
        import numpy as np
        m=(xmax>=x0)&(xmin<=x1)&(ymax>=y0)&(ymin<=y1)
        if m.any(): rows.append(t.filter(pa.array(m)))
    return key, rows, len(hit)
if __name__=='__main__':
    rel=sys.argv[1]; typ=sys.argv[2]; bb=tuple(map(float,sys.argv[3].split(','))); out=sys.argv[4]
    ks=keys(typ,rel); print(len(ks),'files'); tabs=[]
    with cf.ThreadPoolExecutor(24) as ex:
        for k,rows,nh in ex.map(lambda k: scan(k,bb), ks):
            if rows: print(k.split('/')[-1], sum(r.num_rows for r in rows), 'rows', nh,'rg'); tabs+=rows
    if tabs:
        t=pa.concat_tables(tabs, promote_options='permissive'); pq.write_table(t,out); print('wrote',t.num_rows)
