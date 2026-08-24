# -*- coding: utf-8 -*-
"""Leitor do Pal-WinGDK.pak (UnrealEngine PakFile versao 11) + Oodle via ctypes.

So o suficiente para extrair arquivos especificos (locres, datatables) sem
depender do FModel para cada exportacao. Usa o oodle-data-shared.dll que o
FModel baixou da fonte oficial.
"""
import os, struct, ctypes, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
MAGIC = 0x5A6F12E1

class R:
    def __init__(s, b, o=0): s.b=b; s.o=o
    def u32(s): v=struct.unpack_from("<I",s.b,s.o)[0]; s.o+=4; return v
    def i32(s): v=struct.unpack_from("<i",s.b,s.o)[0]; s.o+=4; return v
    def u64(s): v=struct.unpack_from("<Q",s.b,s.o)[0]; s.o+=8; return v
    def i64(s): v=struct.unpack_from("<q",s.b,s.o)[0]; s.o+=8; return v
    def raw(s,n): v=s.b[s.o:s.o+n]; s.o+=n; return v
    def fstr(s):
        n=s.i32()
        if n==0: return ""
        if n<0:
            n=-n; v=s.b[s.o:s.o+n*2-2].decode("utf-16-le","replace"); s.o+=n*2
        else:
            v=s.b[s.o:s.o+n-1].decode("utf-8","replace"); s.o+=n
        return v

def ler_footer(f, tam):
    f.seek(tam-221); foot=f.read(221)
    # acha o magic
    pos = foot.find(struct.pack("<I", MAGIC))
    if pos<0: raise ValueError("magic do pak nao encontrado")
    r=R(foot,pos+4)
    versao=r.u32(); ioff=r.i64(); isize=r.i64()
    return versao, ioff, isize

def carregar_indice():
    tam=os.path.getsize(paths.pak_file())
    f=open(paths.pak_file(),"rb")
    versao,ioff,isize=ler_footer(f,tam)
    f.seek(ioff); idx=f.read(isize)
    r=R(idx)
    mount=r.fstr(); nent=r.i32(); seed=r.u64()
    has_ph=r.i32()
    if has_ph: phoff=r.i64(); phsize=r.i64(); r.raw(20)
    has_fd=r.i32()
    if has_fd: fdoff=r.i64(); fdsize=r.i64(); r.raw(20)
    enc_sz=r.i32(); encoded=r.raw(enc_sz)
    print("versao=%d entradas=%d mount=%r has_fulldir=%d" % (versao,nent,mount,has_fd))
    # Full Directory Index
    f.seek(fdoff); fd=f.read(fdsize)
    r2=R(fd); ndir=r2.u32()
    arquivos={}
    for _ in range(ndir):
        d=r2.fstr(); nf=r2.u32()
        for _ in range(nf):
            nome=r2.fstr(); off=r2.i32()
            arquivos[(mount+d+nome)]=off
    return f, versao, encoded, arquivos, mount

if __name__=="__main__":
    f,versao,encoded,arquivos,mount=carregar_indice()
    print("total de arquivos no indice:", len(arquivos))
    alvos=[k for k in arquivos if "locres" in k.lower()]
    print("\n.locres encontrados:", len(alvos))
    for k in sorted(alvos):
        if "Game" in k: print("  ", k, "-> encoded_off", arquivos[k])


# ---------- decodificacao da entrada compacta + Oodle ----------
_ood=None
def _oodle():
    global _ood
    if _ood is None:
        _ood=ctypes.CDLL(paths.oodle_dll())
        _ood.OodleLZ_Decompress.restype=ctypes.c_longlong
        _ood.OodleLZ_Decompress.argtypes=[
            ctypes.c_char_p,ctypes.c_longlong,ctypes.c_char_p,ctypes.c_longlong,
            ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_longlong,
            ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_longlong,ctypes.c_int]
    return _ood

def oodle_dec(comp, unc_size):
    o=_oodle()
    out=ctypes.create_string_buffer(unc_size)
    n=o.OodleLZ_Decompress(comp,len(comp),out,unc_size,0,0,0,None,0,None,None,None,0,3)
    if n!=unc_size: raise RuntimeError("oodle devolveu %d, esperado %d" % (n,unc_size))
    return out.raw[:unc_size]

def compress_methods():
    tam=os.path.getsize(paths.pak_file()); f=open(paths.pak_file(),"rb"); f.seek(tam-221); foot=f.read(221); f.close()
    pos=foot.find(struct.pack("<I",MAGIC))
    names=foot[pos+4+4+8+8+20:]   # depois de magic,ver,ioff,isize,hash(20)
    out=["None"]
    for i in range(0,len(names),32):
        nm=names[i:i+32].split(b"\x00")[0].decode("ascii","replace")
        if nm: out.append(nm)
    return out

def decode_entry(encoded, off):
    r=R(encoded,off)
    val=r.u32()
    cmi=(val>>23)&0x3f
    off32=bool(val&0x80000000); unc32=bool(val&0x40000000); sz32=bool(val&0x20000000)
    enc=bool(val&0x400000); nblk=(val>>6)&0xffff
    low=val&0x3f
    cbs=r.u32() if low==0x3f else (low<<11)
    offset = r.u32() if off32 else r.u64()
    uncsize = r.u32() if unc32 else r.u64()
    if cmi!=0:
        size = r.u32() if sz32 else r.u64()
    else:
        size = uncsize
    blocks=[]
    if cmi!=0 and nblk>0:
        if nblk==1 and not enc and uncsize<=cbs:
            blocks=[(0,size)]   # bloco unico implicito (relativo ao fim do header)
        else:
            for _ in range(nblk):
                bs=r.u32(); blocks.append(bs)
    return dict(cmi=cmi,offset=offset,size=size,uncsize=uncsize,enc=enc,
                nblk=nblk,cbs=cbs,blocks=blocks)

def extrair(caminho_no_pak):
    f,versao,encoded,arquivos,mount=carregar_indice()
    if caminho_no_pak not in arquivos:
        raise KeyError(caminho_no_pak)
    ent=decode_entry(encoded, arquivos[caminho_no_pak])
    methods=compress_methods()
    print("entry:", ent, "| metodo:", methods[ent["cmi"]] if ent["cmi"]<len(methods) else ent["cmi"])
    # le o header inline em offset para achar os blocos reais
    f.seek(ent["offset"])
    h=f.read(200)
    hr=R(h)
    io=hr.i64(); isz=hr.i64(); iunc=hr.i64(); icmi=hr.u32(); hr.raw(20)
    print("inline header: off=%d size=%d unc=%d cmi=%d" % (io,isz,iunc,icmi))
    blocos=[]
    if icmi!=0:
        nb=hr.u32()
        for _ in range(nb):
            cs=hr.i64(); ce=hr.i64(); blocos.append((cs,ce))
    flags=hr.raw(1); cbs=hr.u32()
    header_size=hr.o
    print("blocos=%d cbs=%d header_size=%d" % (len(blocos), cbs, header_size))
    # dados
    metodo = methods[icmi] if icmi<len(methods) else "?"
    saida=b""
    if icmi==0:
        f.seek(ent["offset"]+header_size); saida=f.read(isz)
    else:
        for i,(cs,ce) in enumerate(blocos):
            # offsets podem ser relativos ao inicio do arquivo (ent.offset) ou ao payload
            base = ent["offset"]
            f.seek(base+cs); comp=f.read(ce-cs)
            unc = min(cbs, iunc-i*cbs)
            saida += oodle_dec(comp, unc)
    return saida, metodo

if __name__ in ("__main__","__mp_main__"):
    pass
