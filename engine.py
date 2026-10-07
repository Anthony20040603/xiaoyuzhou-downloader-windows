"""Desktop adapter for daruizi/xiaoyuzhou-downloader. No upstream download deletion paths are used."""
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
import requests
from upstream import RSSParser, Episode

HEADERS = {'User-Agent': 'PodcastDesktop/1.0', 'Accept-Encoding': 'identity'}

def safe(text):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text).strip(' .')[:65] or '未命名'
    if text.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        text = '_' + text
    return text

def fetch_feed(url):
    if urlparse(url).scheme not in ('http', 'https'):
        raise ValueError('请输入 http 或 https 的 RSS 地址')
    parser = RSSParser(url, HEADERS)
    info, episodes = parser.parse()
    return info, episodes

def resolve(source):
    source = source.strip()
    if 'xiaoyuzhoufm.com/' in source:
        r = requests.get(source, headers=HEADERS, timeout=(15,30)); r.raise_for_status()
        from xml.etree import ElementTree
        m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        if not m:
            raise ValueError('无法读取小宇宙页面；请改用播客名称搜索或直接填写 RSS 地址')
        data = json.loads(m.group(1))
        def find(obj):
            if isinstance(obj, dict):
                if isinstance(obj.get('podcast'), dict) and obj['podcast'].get('title'):
                    return obj['podcast']['title']
                for value in obj.values():
                    found = find(value)
                    if found: return found
            elif isinstance(obj, list):
                for value in obj:
                    found = find(value)
                    if found: return found
        source = find(data)
        if not source: raise ValueError('未找到播客名称；请直接填写名称或 RSS')
    elif source.startswith(('https://','http://')):
        return [{'collectionName':'直接使用 RSS 地址','feedUrl':source}]
    r = requests.get('https://itunes.apple.com/search', params={'term':source,'media':'podcast','entity':'podcast','limit':15}, headers=HEADERS, timeout=(15,30))
    r.raise_for_status()
    return [x for x in r.json().get('results',[]) if x.get('feedUrl')]

def digest(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def download(folder, podcast, ep, stop, progress=lambda *a:None):
    """Atomic completion, validated cache, HTTP Range and If-Range resume."""
    uid = hashlib.sha256((ep.guid or ep.audio_url).encode()).hexdigest()[:10]
    ext = Path(urlparse(ep.audio_url).path).suffix.lower()
    if ext not in ('.mp3','.m4a','.mp4','.ogg','.wav','.flac','.aac'): ext = '.mp3'
    date = ep.pub_date if re.fullmatch(r'\d{4}-\d{2}-\d{2}',ep.pub_date or '') else 'unknown'
    directory = Path(folder) / safe(podcast) / (date[:7] if date != 'unknown' else date)
    directory.mkdir(parents=True,exist_ok=True)
    dest = directory / f'{date}_{safe(ep.title)}_{uid}{ext}'
    record = dest.with_suffix(dest.suffix+'.json')
    if dest.exists() and record.exists():
        metadata = json.loads(record.read_text(encoding='utf-8'))
        if dest.stat().st_size == metadata['bytes'] and digest(dest) == metadata['sha256']:
            return {'status':'已存在','path':str(dest),**metadata}
    # Never overwrite an existing unverified user file.
    if dest.exists():
        dest = dest.with_name(dest.stem + '_' + str(time.time_ns()) + dest.suffix)
        record = dest.with_suffix(dest.suffix+'.json')
    part = dest.with_suffix(dest.suffix+'.part')
    state = part.with_suffix(part.suffix+'.json')
    for attempt in range(3):
        if stop.is_set(): return {'status':'已暂停'}
        try:
            offset = part.stat().st_size if part.exists() else 0
            prior = json.loads(state.read_text(encoding='utf-8')) if state.exists() else {}
            headers = dict(HEADERS)
            if offset and prior.get('validator'):
                headers.update({'Range':f'bytes={offset}-','If-Range':prior['validator']})
            else: offset = 0
            with requests.get(ep.audio_url, headers=headers, stream=True, timeout=(15,30)) as response:
                response.raise_for_status()
                if response.status_code == 206:
                    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                    if not match or int(match[1]) != offset: raise ValueError('服务器返回了无效的续传范围')
                    total = int(match[3])
                else:
                    offset = 0
                    total = int(response.headers.get('Content-Length',0))
                content_type = response.headers.get('Content-Type','').lower()
                if 'text/html' in content_type or 'application/json' in content_type:
                    raise ValueError('音频地址返回网页或错误信息')
                validator = response.headers.get('ETag') or response.headers.get('Last-Modified')
                state.write_text(json.dumps({'validator':validator}),encoding='utf-8')
                received = offset
                with open(part,'ab' if offset else 'wb') as f:
                    for chunk in response.iter_content(65536):
                        if stop.is_set(): return {'status':'已暂停'}
                        if chunk:
                            f.write(chunk); received += len(chunk); progress(received,total)
                if received == 0 or (total and received != total): raise ValueError('音频未下载完整')
            metadata = {'title':ep.title,'url':ep.audio_url,'bytes':received,'sha256':digest(part)}
            part.rename(dest)
            record.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
            return {'status':'完成','path':str(dest),**metadata}
        except Exception:
            if attempt == 2: raise
            if stop.wait(1): return {'status':'已暂停'}
