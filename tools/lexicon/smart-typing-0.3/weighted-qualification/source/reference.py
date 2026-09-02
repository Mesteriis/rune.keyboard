"""Independent policy and exhaustive-transposition-prefix oracle, no production imports."""
import itertools
import unicodedata as u
LANGS=('en','ru','es')
REASONS=['TOO_LONG','MALFORMED_UNICODE','PATH_OR_IDENTIFIER','MIXED_SCRIPT','UNSUPPORTED_SCRIPT','LETTERS_AND_DIGITS','MIXED_CASE','ALL_CAPS','TECHNICAL_HYPHEN','UNUSUAL_SYMBOL','NON_WORD']
ROWS={'en':('qwertyuiop','asdfghjkl','zxcvbnm'),'es':('qwertyuiop','asdfghjklñ','zxcvbnm'),'ru':('йцукенгшщзхъ','фывапролджэ','ячсмитьбю')}

def units(s):return len(s.encode('utf-16-le','surrogatepass'))//2
def bounded(s):return len(s)<=32 and units(s)<=64 and all(not 0xd800<=ord(c)<=0xdfff for c in s)
def folded(s):return u.normalize('NFC',u.normalize('NFC',s).lower())
def pattern(s):
 cased=[c for c in u.normalize('NFC',s) if c.islower() or c.isupper() or u.category(c)=='Lt']
 upper=[c.isupper() or u.category(c)=='Lt' for c in cased]
 if not cased:return 4
 if not any(upper):return 0
 if all(upper):return 2
 if upper[0] and sum(upper)==1:return 1
 return 3

def script(c):
 cp=ord(c);cat=u.category(c)
 if 'CYRILLIC' in u.name(c,''):return 'ru'
 if cat[0]=='M':return None
 if c.isalpha():
  if cp<0x0250 or 0x1e00<=cp<=0x1eff or 'LATIN' in u.name(c,''):return 'latin'
  return 'other'
 return None

def protection(token):
 if units(token)>64 or len(token)>32:return 0
 if not bounded(token):return 1
 text=u.normalize('NFC',token)
 if not bounded(text) or not bounded(folded(text)):return 0
 scripts={script(c) for c in text}-{None};letters=sum(c.isalpha() for c in text);digits=sum(c.isdecimal() for c in text)
 unusual=False;follows=False
 for i,c in enumerate(text):
  category=u.category(c)
  if c in '/\\@_':pass
  elif c.isalpha() or c.isdecimal():pass
  elif category[0]=='M':unusual |= not follows
  elif c=='-':pass
  elif c in "'’":unusual |= not follows or i+1==len(text) or not text[i+1].isalpha()
  else:unusual=True
  follows=c.isalpha() or (category[0]=='M' and follows)
 if len(scripts)>1:return 3
 if any(c in '/\\@_' for c in text):return 2
 if 'other' in scripts:return 4
 if letters and digits:return 5
 if unusual:return 9
 if '-' in text:return 8
 if not letters:return 10
 case=pattern(text)
 if case==3:return 6
 if letters>1 and case==2:return 7
 return -1

def routes(token,active):
 if protection(token)>=0:return []
 key=folded(token)
 if any(script(c)=='ru' for c in key):return [1]
 if any(c in 'ñáéíóúü' for c in key):return [2]
 return [2,0] if active==2 else [0,2]

def preserve(terminal,case):
 text=u.normalize('NFC',terminal).lower()
 if case==1:
  pos=next((i for i,c in enumerate(text) if c.islower() or c.isupper() or u.category(c)=='Lt'),None)
  if pos is None:return None
  text=text[:pos]+text[pos].title()+text[pos+1:]
 elif case==2:text=u.normalize('NFC',terminal).upper()
 elif case!=0:return None
 return u.normalize('NFC',text) if bounded(text) else None

def adjacent(a,b,lang):
 if a==b:return False
 positions={c:(2*x+y,y) for y,row in enumerate(ROWS[lang]) for x,c in enumerate(row)}
 if a not in positions or b not in positions:return False
 x,y=positions[a];xx,yy=positions[b];dx=abs(x-xx);dy=abs(y-yy)
 return (dy==0 and dx==2) or (dy==1 and dx<=1)

def distance(a,b,lang,weighted=True):
 """Enumerate ALL earlier matching transposition endpoints; no last-occurrence recurrence/state."""
 n,m=len(a),len(b);d=[[0]*(m+1) for _ in range(n+1)]
 for i in range(n+1):d[i][0]=4*i
 for j in range(m+1):d[0][j]=4*j
 for i in range(1,n+1):
  for j in range(1,m+1):
   sub=0 if a[i-1]==b[j-1] else 3 if weighted and adjacent(a[i-1],b[j-1],lang) else 4
   best=min(d[i-1][j]+4,d[i][j-1]+4,d[i-1][j-1]+sub)
   for ii in range(i-1):
    if a[ii]!=b[j-1]:continue
    for jj in range(j-1):
     if b[jj]==a[i-1]:best=min(best,d[ii][jj]+4*(i-ii-2)+4*(j-jj-2)+(5 if weighted else 4))
   d[i][j]=best
 return d[n][m]

def repeats(a,b):
 aa=[(c,len(list(g))) for c,g in itertools.groupby(a)];bb=[(c,len(list(g))) for c,g in itertools.groupby(b)]
 return sum(abs(x[1]-y[1]) for x,y in zip(aa,bb)) if [x[0] for x in aa]==[x[0] for x in bb] else 0

def order(c):return c['quarters'],-c['prior'],c['frequency'],c['key'],c['language'],c['terminal']
def select(candidates):
 # Group globally by folded display first, then independently merge primary + first two fallback.
 grouped={}
 for c in candidates:
  if not c['admitted']:continue
  k=c['key']
  if k not in grouped or order(c)<order(grouped[k]):grouped[k]=c
 primary=[c for c in grouped.values() if not c['fallback']]
 fallback=sorted((c for c in grouped.values() if c['fallback']),key=order)[:2]
 return sorted(primary+fallback,key=order)[:7]

def hex_units(text):
 b=text.encode('utf-16-le','surrogatepass')
 return ','.join(f'{int.from_bytes(b[i:i+2],"little"):04x}' for i in range(0,len(b),2)) or '-'
