from pathlib import Path
import re, html, hashlib, json
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER,TA_JUSTIFY
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from reportlab.lib import textsplit
textsplit.ALL_CANNOT_START += '，。！？；：…）】》”’'

def chinese_split(word, widths, maxWidths):
 if not isinstance(maxWidths,(list,tuple)): maxWidths=[maxWidths]
 lines=[];start=0;size=len(word)
 closing=set(textsplit.ALL_CANNOT_START)
 opening=set('“‘（【《「『')
 while start<size:
  limit=maxWidths[min(len(lines),len(maxWidths)-1)];end=start;used=0
  while end<size and (used+widths[end]<=limit+0.001 or end==start):
   used+=widths[end];end+=1
  if end<size:
   cut=end
   while cut>start+1 and word[cut] in closing:cut-=1
   while cut>start+1 and word[cut-1] in opening:cut-=1
   if cut==end and word[end-1].isascii() and word[end-1].isalnum() and word[end].isascii() and word[end].isalnum():
    j=end
    while j>start and word[j-1].isascii() and word[j-1].isalnum():j-=1
    if j>start:cut=j
   end=cut
  lines.append([limit-sum(widths[start:end]),word[start:end].strip()]);start=end
 return lines
textsplit.dumbSplit=chinese_split
root=Path('/Users/dabao/Desktop/WorkBuddy/写作')
pdfmetrics.registerFont(TTFont('CN','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
W,H=152*mm,228*mm
out=root/'output/pdf/带着GPT重回高中_新版第1至51章.pdf'
body=ParagraphStyle('body',fontName='CN',fontSize=11,leading=19,firstLineIndent=22,spaceAfter=5,wordWrap='CJK',alignment=TA_JUSTIFY)
heading=ParagraphStyle('chapter',fontName='CN',fontSize=18,leading=28,spaceAfter=22,wordWrap='CJK',alignment=TA_CENTER)
center=ParagraphStyle('center',fontName='CN',fontSize=12,leading=23,alignment=TA_CENTER,wordWrap='CJK')
sep=ParagraphStyle('sep',parent=center,spaceBefore=8,spaceAfter=8)
class Book(BaseDocTemplate):
 def afterFlowable(self,f):
  if isinstance(f,Paragraph) and f.style.name=='chapter' and f.getPlainText().startswith('第'):
   key='chapter'+str(self.seq.nextf('chapter'))
   self.canv.bookmarkPage(key)
   self.canv.addOutlineEntry(f.getPlainText(),key,0,False)
   self.notify('TOCEntry',(0,f.getPlainText(),self.page,key))
def page(c,d):
 c.setFont('CN',8)
 if d.page>1:
  c.setFillColorRGB(.45,.45,.45);c.drawCentredString(W/2,9*mm,str(d.page))
doc=Book(str(out),pagesize=(W,H),leftMargin=17*mm,rightMargin=17*mm,topMargin=18*mm,bottomMargin=18*mm,title='带着GPT重回高中 · 新版第1至51章',author='')
doc.addPageTemplates(PageTemplate(id='book',frames=[Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=page))
story=[Spacer(1,42*mm),Paragraph('带着GPT重回高中',ParagraphStyle('cover',parent=heading,fontSize=25,leading=40)),Spacer(1,8*mm),Paragraph('新版第1至51章 · 高中篇',center),Spacer(1,40*mm),Paragraph('2026年10月19日导出',center),PageBreak(),Paragraph('目录',heading)]
toc=TableOfContents();toc.levelStyles=[ParagraphStyle('toc',fontName='CN',fontSize=10,leading=16,spaceBefore=2,wordWrap='CJK')];story += [toc,PageBreak()]
manifest=[];notes=[];texts=[]
for n in range(1,52):
 paths=list((root/'小说2004/正文_重写版').glob(f'第{n}章-*.md'));assert len(paths)==1
 p=paths[0];raw=p.read_text();lines=raw.splitlines();title=lines[0].lstrip('# ').strip();story.append(Paragraph(html.escape(title),heading));texts.append(title)
 for line in lines[1:]:
  line=line.strip()
  if not line:continue
  if line.startswith('#'):notes.append([p.name,line]);continue
  # Editorial inline annotations use #; omit only from this rendering.
  if '#' in line:
   line,note=line.split('#',1);notes.append([p.name,note]);line=line.rstrip()
  if not line:continue
  line=line.replace('**','');texts.append(line)
  story.append(Paragraph(html.escape(line),sep if line=='······' else body))
 if n<51:story.append(PageBreak())
 manifest.append({'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'title':title})
doc.multiBuild(story)
reader=PdfReader(str(out)); extracted='\n'.join(re.sub(r'^\d+\n', '', p.extract_text() or '') for p in reader.pages)
assert len(reader.outline)==51,len(reader.outline)
compact=lambda s:re.sub(r'\s+','',s)
clean=compact(extracted)
for t in texts:assert compact(t) in clean,repr(t[:90])
for item in manifest:assert hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()==item['sha256']
assert not any(note in extracted for _,note in notes)
(root/'tmp/pdfs/manifest.json').write_text(json.dumps({'sources':manifest,'omitted_notes':notes,'pages':len(reader.pages)},ensure_ascii=False,indent=2))
print('OUTPUT',out,'PAGES',len(reader.pages),'BOOKMARKS',len(reader.outline),'OMITTED_NOTES',len(notes),'ALL_TEXT_VERIFIED',len(texts))
print('CHAPTER_PAGE_SAMPLES',[(x['/Title'],reader.get_destination_page_number(x)+1) for x in reader.outline[::10]])
