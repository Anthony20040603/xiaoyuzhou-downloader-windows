import ctypes
import json
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from engine import resolve, fetch_feed, download

HOME = Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('小宇宙播客下载器 · 桌面版')
        self.geometry('1080x860'); self.minsize(880,720)
        self.configure(bg='#f4f6fb')
        self.events = queue.Queue(); self.stop = threading.Event(); self.busy = False
        self.episodes = []; self.podcast = ''; self.feed = ''; self.results = []; self.checked = set()
        self.settings_path = HOME / 'settings.json'
        try: settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
        except Exception: settings = {}
        self.folder = tk.StringVar(value=settings.get('folder',str(HOME/'downloads')))
        self.source = tk.StringVar(value=settings.get('source',''))
        self.status = tk.StringVar(value='输入播客名称、小宇宙节目页链接或 RSS 地址，然后获取节目。')
        style = ttk.Style(self); style.theme_use('clam')
        style.configure('.',font=('Microsoft YaHei UI',10))
        style.configure('TFrame',background='#f4f6fb')
        style.configure('TLabel',background='#f4f6fb',foreground='#23314b')
        style.configure('TButton',padding=(14,9),background='#e7edf8')
        style.configure('Primary.TButton',background='#316bea',foreground='white')
        style.map('Primary.TButton',background=[('active','#2454ba'),('disabled','#a3b7df')])
        style.configure('Treeview',rowheight=34,background='white',fieldbackground='white')
        style.configure('Treeview.Heading',padding=9,font=('Microsoft YaHei UI',10,'bold'))
        style.configure('Horizontal.TProgressbar',background='#316bea')
        outer = ttk.Frame(self,padding=24); outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='播客，保存到你的电脑',font=('Microsoft YaHei UI',23,'bold')).pack(anchor='w')
        ttk.Label(outer,text='小宇宙播客下载器  /  RSS 下载 · 勾选节目 · 暂停后继续',foreground='#69758c').pack(anchor='w',pady=(5,20))
        row = ttk.Frame(outer); row.pack(fill='x')
        self.entry = ttk.Entry(row,textvariable=self.source,font=('Microsoft YaHei UI',11)); self.entry.pack(side='left',fill='x',expand=True,ipady=8)
        self.fetch_button = ttk.Button(row,text='获取节目',style='Primary.TButton',command=self.load); self.fetch_button.pack(side='left',padx=(12,0))
        self.import_button = ttk.Button(row,text='导入 RSS',command=self.import_rss); self.import_button.pack(side='left',padx=(8,0))
        self.entry.bind('<Return>',lambda e:self.load())
        ttk.Label(outer,text='播客名称搜索会列出候选结果；小宇宙链接通过名称寻找公开 RSS。',foreground='#69758c').pack(anchor='w',pady=(8,12))
        choices = ttk.Frame(outer); choices.pack(fill='x')
        ttk.Label(choices,text='播客 / RSS').pack(side='left')
        self.combo = ttk.Combobox(choices,state='readonly'); self.combo.pack(side='left',fill='x',expand=True,padx=10)
        self.combo.bind('<<ComboboxSelected>>',lambda e:self.load_chosen())
        self.candidates = []
        self.feed_label = ttk.Label(outer,text='尚未加载节目',foreground='#69758c'); self.feed_label.pack(anchor='w',pady=(14,8))
        table = ttk.Frame(outer); table.pack(fill='both',expand=True)
        self.tree = ttk.Treeview(table,height=6,columns=('check','date','title','duration','status'),show='headings',selectmode='extended')
        for name,title,width in [('check','选择',55),('date','日期',110),('title','节目标题',480),('duration','时长',80),('status','状态',130)]:
            self.tree.heading(name,text=title); self.tree.column(name,width=width,stretch=name=='title')
        bar = ttk.Scrollbar(table,orient='vertical',command=self.tree.yview); self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side='left',fill='both',expand=True); bar.pack(side='right',fill='y')
        self.tree.bind('<Button-1>',self.toggle); self.tree.bind('<space>',self.toggle_selected)
        controls = ttk.Frame(outer); controls.pack(fill='x',pady=10)
        ttk.Button(controls,text='全选',command=lambda:self.check_all(True)).pack(side='left')
        ttk.Button(controls,text='清空勾选',command=lambda:self.check_all(False)).pack(side='left',padx=8)
        ttk.Button(controls,text='只选前 3 期',command=self.first_three).pack(side='left')
        self.start_button = ttk.Button(controls,text='下载勾选节目',style='Primary.TButton',command=self.start_download); self.start_button.pack(side='right')
        self.pause_button = ttk.Button(controls,text='暂停',command=self.stop.set,state='disabled'); self.pause_button.pack(side='right',padx=10)
        destination = ttk.Frame(outer); destination.pack(fill='x',pady=(3,10))
        ttk.Label(destination,text='保存位置').pack(side='left')
        self.folder_entry = ttk.Entry(destination,textvariable=self.folder); self.folder_entry.pack(side='left',fill='x',expand=True,padx=10)
        self.browse_button = ttk.Button(destination,text='选择文件夹',command=self.choose_folder); self.browse_button.pack(side='left')
        ttk.Button(destination,text='打开文件夹',command=self.open_folder).pack(side='left',padx=(8,0))
        self.progress = ttk.Progressbar(outer,maximum=100); self.progress.pack(fill='x',pady=(0,8))
        ttk.Label(outer,textvariable=self.status,wraplength=1000).pack(anchor='w')
        ttk.Label(outer,text='仅下载你有权保存的公开音频。下载完成后按年月归档；已有完整文件自动跳过。',foreground='#7b879b').pack(anchor='w',pady=(10,0))
        self.protocol('WM_DELETE_WINDOW',self.close); self.after(100,self.poll)

    def save_settings(self):
        try: self.settings_path.write_text(json.dumps({'source':self.source.get(),'folder':self.folder.get()},ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError: pass

    def set_busy(self,value):
        self.busy = value
        for widget in (self.fetch_button,self.import_button,self.start_button,self.browse_button,self.entry,self.folder_entry): widget.configure(state='disabled' if value else 'normal')
        self.combo.configure(state='disabled' if value else 'readonly')
        self.pause_button.configure(state='normal' if value else 'disabled')

    def job(self,fn):
        if self.busy: return
        self.stop.clear(); self.set_busy(True); self.save_settings()
        def work():
            try: fn()
            except Exception as e: self.events.put(('error',str(e)))
            finally: self.events.put(('idle',None))
        threading.Thread(target=work,daemon=True).start()

    def load(self):
        source = self.source.get().strip()
        if not source: return
        self.status.set('正在查找播客…')
        self.job(lambda:self.events.put(('candidates',resolve(source))))

    def load_chosen(self):
        if self.busy or self.combo.current()<0: return
        feed = self.candidates[self.combo.current()]['feedUrl']
        self.status.set('正在读取 RSS 节目列表…')
        self.job(lambda:self.events.put(('episodes',(feed,*fetch_feed(feed)))))

    def import_rss(self):
        if self.busy:return
        path=filedialog.askopenfilename(title='导入 RSS 文件',filetypes=[('RSS / XML','*.xml'),('所有文件','*.*')])
        if not path:return
        def work():
            from upstream import RSSParser
            parser=RSSParser(path);parser.fetch=lambda:Path(path).read_bytes()
            self.events.put(('episodes',(path,*parser.parse())))
        self.job(work)

    def show_episodes(self,feed,info,episodes):
        self.feed = feed; self.podcast = info.get('title') or '播客'; self.episodes = episodes; self.checked.clear()
        self.tree.delete(*self.tree.get_children())
        for i,ep in enumerate(episodes): self.tree.insert('', 'end',iid=str(i),values=('□',ep.pub_date,ep.title,ep.duration,'待下载'))
        self.feed_label.configure(text=f'{self.podcast}  ·  {len(episodes)} 期')
        self.status.set(f'已加载 {len(episodes)} 期。点击选择列勾选需要下载的节目。')

    def update_check(self,i): self.tree.set(str(i),'check','☑' if i in self.checked else '□')
    def toggle(self,e):
        if self.busy or self.tree.identify_column(e.x) != '#1': return
        row = self.tree.identify_row(e.y)
        if row:
            i=int(row); self.checked.symmetric_difference_update({i}); self.update_check(i)
    def toggle_selected(self,e):
        if not self.busy:
            for row in self.tree.selection():
                i=int(row); self.checked.symmetric_difference_update({i}); self.update_check(i)
        return 'break'
    def check_all(self,value):
        if self.busy:return
        self.checked = set(range(len(self.episodes))) if value else set()
        for i in range(len(self.episodes)): self.update_check(i)
    def first_three(self):
        if self.busy:return
        self.checked = set(range(min(3,len(self.episodes))))
        for i in range(len(self.episodes)): self.update_check(i)
    def choose_folder(self):
        folder=filedialog.askdirectory(initialdir=self.folder.get())
        if folder:self.folder.set(folder); self.save_settings()
    def open_folder(self):
        try: Path(self.folder.get()).mkdir(parents=True,exist_ok=True); os.startfile(self.folder.get())
        except OSError as e: messagebox.showerror('无法打开文件夹',str(e))

    def start_download(self):
        if not self.checked or self.busy:return
        indices=sorted(self.checked); folder=self.folder.get(); podcast=self.podcast
        self.status.set('准备下载…'); self.results=[]
        def work():
            ok=failed=0
            for position,i in enumerate(indices):
                if self.stop.is_set(): break
                self.events.put(('row',(i,'正在下载')))
                def progress(n,total): self.events.put(('progress',((position+(n/total if total else 0))/len(indices)*100,f'{position+1}/{len(indices)} · {self.episodes[i].title[:45]} · {n/1048576:.1f} MB' + (f' / {total/1048576:.1f} MB' if total else ''))))
                try:
                    result=download(folder,podcast,self.episodes[i],self.stop,progress)
                    self.results.append(result); self.events.put(('row',(i,result['status'])))
                    if result['status'] in ('完成','已存在'):ok+=1
                except Exception as e:
                    failed+=1; self.events.put(('row',(i,'失败'))); self.events.put(('status',f'下载失败：{e}'))
                if self.stop.is_set():break
            self.events.put(('status',f'{"已暂停，再次点击下载可继续" if self.stop.is_set() else "本次下载结束"} · 成功/已有 {ok} 期 · 失败 {failed} 期'))
            if not self.stop.is_set():self.events.put(('progress',(100,None)))
        self.job(work)

    def poll(self):
        auto=False
        try:
            while True:
                event,payload=self.events.get_nowait()
                if event=='idle':self.set_busy(False)
                elif event=='error':self.status.set('操作失败：'+payload); messagebox.showerror('操作失败',payload)
                elif event=='status':self.status.set(payload)
                elif event=='row':self.tree.set(str(payload[0]),'status',payload[1])
                elif event=='progress':
                    self.progress['value']=payload[0]
                    if payload[1]:self.status.set(payload[1])
                elif event=='episodes':self.show_episodes(*payload)
                elif event=='candidates':
                    self.candidates=payload
                    self.combo['values']=[x['collectionName'] for x in payload]
                    if payload:self.combo.current(0);auto=len(payload)==1;self.status.set('请选择匹配的播客，随后加载节目。')
                    else:self.status.set('未找到公开 RSS；请填写发布者提供的 RSS 地址。')
        except queue.Empty:pass
        if auto:self.load_chosen()
        self.after(100,self.poll)
    def close(self):
        self.save_settings();self.stop.set();self.destroy()

if __name__=='__main__':
    try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:pass
    App().mainloop()
