"""Local link resolver. Share-page approach: yzfly/douyin-mcp-server (MIT).
No service keys, login cookies, or third-party parsing servers required for Douyin.
"""
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qs, unquote

import requests

MOBILE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1'
DOMAINS = ('douyin.com', 'iesdouyin.com', 'xiaohongshu.com', 'xhslink.com', 'xhslink.cn', 'youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com')
CACHE = Path.home() / 'Library/Caches/local.linkdrop.mac'


def allowed(url, domains=DOMAINS):
    p = urlsplit(url)
    return p.scheme in ('http', 'https') and not p.username and not p.password and any(p.hostname == d or (p.hostname or '').endswith('.' + d) for d in domains)


def find_item(obj, ident):
    if isinstance(obj, dict):
        if str(obj.get('aweme_id', '')) == ident and ('video' in obj or 'images' in obj):
            return obj
        for value in obj.values():
            found = find_item(value, ident)
            if found: return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_item(value, ident)
            if found: return found


def links(value):
    return [u for u in (value or []) if isinstance(u, str) and u.startswith(('https://', 'http://'))]


def session():
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(total=1, connect=1, read=1, backoff_factor=0.4, status_forcelist=[429,500,502,503,504]))
    s.mount('https://',adapter); s.mount('http://',adapter)
    return s


def find_note(obj, ident):
    if isinstance(obj,dict):
        if obj.get('noteId')==ident and ('imageList' in obj or 'video' in obj): return obj
        for v in obj.values():
            result=find_note(v,ident)
            if result: return result
    if isinstance(obj,list):
        for v in obj:
            result=find_note(v,ident)
            if result: return result


def douyin(url):
    s = session()
    s.headers.update({'User-Agent': MOBILE, 'Referer': 'https://www.douyin.com/', 'Accept-Language': 'zh-CN,zh;q=0.9'})
    s.get('https://www.iesdouyin.com/', timeout=15).raise_for_status()
    if urlsplit(url).hostname == 'v.douyin.com':
        r = s.get(url, timeout=20); r.raise_for_status(); url = r.url
    match = re.search(r'/(?:video|note|slides)/(\d+)', url) or re.search(r'[?&]modal_id=(\d+)', url)
    if not match: raise ValueError('未能识别抖音作品编号，请重新复制分享链接。')
    ident = match[1]
    item = None
    for route in ('video', 'slides'):
        for attempt in range(2):
            r = s.get(f'https://www.iesdouyin.com/share/{route}/{ident}/', timeout=20)
            r.raise_for_status()
            m = re.search(r'window\._ROUTER_DATA\s*=\s*(.*?)</script>', r.text, re.S)
            if m:
                item = find_item(json.loads(m[1]), ident)
                if item: break
        if item: break
    if not item: raise ValueError('抖音分享页未返回作品数据，可能需要登录或暂时限制访问，请稍后重试。')
    media = []
    pictures = item.get('images') or []
    if pictures:
        for picture in pictures:
            candidates = links(picture.get('url_list'))
            if not candidates: candidates = links((picture.get('display_image') or {}).get('url_list'))
            if candidates: media.append({'kind': 'image', 'urls': list(reversed(candidates))})
            video = picture.get('video') or {}
            if links((video.get('play_addr') or {}).get('url_list')):
                media.append({'kind': 'video', 'urls': links(video['play_addr']['url_list'])})
    else:
        candidates = links((item.get('video', {}).get('play_addr') or {}).get('url_list'))
        candidates = [u.replace('/playwm/', '/play/') for u in candidates]
        if candidates: media.append({'kind': 'video', 'urls': candidates})
    if not media: raise ValueError('已找到作品，但未找到可保存的媒体文件。')
    return {'id': ident, 'title': item.get('desc') or ident, 'uploader': item.get('author', {}).get('nickname', ''), 'duration': (item.get('video', {}).get('duration') or 0) / 1000, 'extractor': '抖音分享页', 'media': media, 'media_count': len(media), 'media_type': '图集' if pictures else '视频', 'quality_note': '分享页可用画质；未保证原片最高画质', 'referer': 'https://www.douyin.com/'}


def xhs(url):
    s = session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S9110) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36', 'Referer': 'https://www.xiaohongshu.com/'})
    r = s.get(url, timeout=25); r.raise_for_status()
    target=(parse_qs(urlsplit(r.url).query).get('redirectPath') or [''])[0]
    if target and allowed(target,('xiaohongshu.com',)):
        r=s.get(target.replace('http://','https://',1),timeout=25); r.raise_for_status()
    match = re.search(r'/(?:explore|discovery/item|note)/([a-f0-9]{24})', r.url)
    if not match: raise ValueError('小红书未返回笔记页面，请复制 App 内的完整分享链接（保留 xsec_token）。')
    ident = match[1]
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', r.text, re.S)
    if not m: raise ValueError('小红书页面需要登录或验证，请重新复制分享链接后重试。')
    state = json.loads(re.sub(r'"(?:\\.|[^"\\])*"|\bundefined\b', lambda v: 'null' if v[0]=='undefined' else v[0], m[1].strip().rstrip(';')))
    note = find_note(state,ident)
    if not note: raise ValueError('小红书未返回作品内容，分享 token 可能已失效，请重新复制完整链接。')
    media = []
    if note.get('type') == 'video':
        video = note.get('video') or {}
        streams = (video.get('media') or {}).get('stream') or {}
        candidates = []
        for variants in streams.values():
            if isinstance(variants, list):
                for v in variants:
                    if v.get('masterUrl'): candidates.append((v.get('avgBitrate') or 0, v['masterUrl']))
        urls = [u for _,u in sorted(candidates, reverse=True)]
        origin = (video.get('consumer') or {}).get('originVideoKey')
        if origin: urls.insert(0, 'https://sns-video-bd.xhscdn.com/' + origin)
        if urls: media.append({'kind': 'video', 'urls': urls})
    else:
        for pic in note.get('imageList') or []:
            urls = links([pic.get('urlDefault'), pic.get('url'), pic.get('urlPre')])
            file_id=pic.get('fileId','')
            if re.fullmatch(r'[A-Za-z0-9_/-]+',file_id):
                urls.insert(0,'https://ci.xiaohongshu.com/'+file_id+'?imageView2/2/w/0/format/jpg')
            urls += links([i.get('url') for i in pic.get('infoList') or []])
            if urls: media.append({'kind': 'image', 'urls': urls})
    if not media: raise ValueError('笔记内容已返回，但未找到媒体。此页面结构需要进一步适配。')
    return {'id': ident, 'title': note.get('title') or note.get('desc') or ident, 'uploader': note.get('user', {}).get('nickname') or note.get('user', {}).get('nickName',''), 'duration': (note.get('video',{}).get('capa') or {}).get('duration',0), 'extractor': '小红书分享页', 'media': media, 'media_count': len(media), 'media_type': '视频' if note.get('type') == 'video' else '图集', 'quality_note': '平台提供的可用媒体；水印及原画状态以实际文件为准', 'referer': 'https://www.xiaohongshu.com/'}


def parse(url):
    if not allowed(url): raise ValueError('不支持的链接域名。')
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache = CACHE / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    if cache.exists() and time.time() - cache.stat().st_mtime < 300:
        return json.loads(cache.read_text())
    d = douyin(url) if allowed(url, ('douyin.com','iesdouyin.com')) else xhs(url)
    temp = cache.with_suffix('.tmp')
    with temp.open('w') as f:
        os.chmod(temp, 0o600); json.dump(d, f, ensure_ascii=False)
    temp.replace(cache)
    return d


def variants(url):
    if url.startswith('http://'): url='https://'+url[7:]
    yield url
    p = urlsplit(url)
    if p.hostname in ('aweme.snssdk.com', 'www.iesdouyin.com', 'www.douyin.com') and p.path == '/aweme/v1/play/':
        for host in ('www.iesdouyin.com', 'www.douyin.com'):
            if p.hostname != host: yield urlunsplit((p.scheme,host,p.path,p.query,p.fragment))


def file_kind(first, content_type, expected):
    if expected == 'video' and (b'ftyp' in first[:32] or first.startswith(b'\x1aE\xdf\xa3')): return '.mp4' if b'ftyp' in first[:32] else '.webm'
    if expected == 'image':
        if first.startswith(b'\xff\xd8\xff'): return '.jpg'
        if first.startswith(b'\x89PNG'): return '.png'
        if first.startswith(b'RIFF') and first[8:12] == b'WEBP': return '.webp'
        if b'ftyp' in first[:32]: return '.heic'
    raise ValueError('服务器返回的不是预期媒体文件，未保存为成功结果。')


def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').digest()

def save(d, directory):
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', d['title'])[:65].strip(' .') or d['id']
    directory.mkdir(parents=True, exist_ok=True)
    group = directory / (stem + ' [' + d['id'] + ']')
    group.mkdir(exist_ok=True)
    saved=[]
    for i,media in enumerate(d['media'],1):
        errors=[]
        done=False
        for primary in media['urls']:
            for u in variants(primary):
                if urlsplit(u).scheme not in ('http','https'): continue
                part = group / f'{i:02d}.part'
                try:
                    with requests.get(u, headers={'User-Agent': MOBILE, 'Referer': d['referer']}, timeout=(12,30), stream=True) as r:
                        r.raise_for_status()
                        chunks=r.iter_content(256*1024); first=next(chunks, b'')
                        ext=file_kind(first,r.headers.get('content-type',''),media['kind'])
                        dest=group / (f'{i:02d}' + ext)
                        total=int(r.headers.get('content-length',0)); count=len(first); last=0
                        with part.open('wb') as f:
                            f.write(first)
                            for b in chunks:
                                f.write(b); count+=len(b)
                                if time.monotonic()-last>1:
                                    print(f'[{i}/{len(d["media"])}] {count/1048576:.1f} MB' + (f' / {total/1048576:.1f} MB' if total else ''), flush=True); last=time.monotonic()
                        if total and count!=total: raise ValueError('下载长度不完整')
                        # Keep a user's existing file intact. Identical existing downloads are reused.
                        if dest.exists():
                            if digest(dest)==digest(part): part.unlink()
                            else:
                                dest=group/(f'{i:02d}-{time.time_ns()}' + ext); part.replace(dest)
                        else: part.replace(dest)
                        saved.append(dest); done=True
                        print(f'已保存：{dest}',flush=True)
                    break
                except (requests.RequestException, ValueError, OSError) as e:
                    errors.append(str(e)); part.unlink(missing_ok=True)
            if done: break
        if not done: raise ValueError(f'第 {i} 个文件下载失败：' + '; '.join(errors)[-600:])
    if len(saved)>1 or d['media_type']=='图集':
        archive=group / ('图集-'+str(time.time_ns())+'.zip')
        with zipfile.ZipFile(archive,'w') as z:
            for f in saved: z.write(f,f.name)
        print(f'打包完成：{archive}',flush=True)
    return saved


def self_test():
    assert allowed('https://xhslink.cn/a/test')
    assert not allowed('https://douyin.com.evil.test/x')
    assert not allowed('https://user:pass@douyin.com/x')
    assert find_item({'x':[{'aweme_id':'123','images':[]}]},'123')['aweme_id']=='123'
    assert find_item({'aweme_id':'999','video':{}},'123') is None
    assert file_kind(b'\xff\xd8\xffabc','image/jpeg','image')=='.jpg'
    try: file_kind(b'<html>error','text/html','video'); assert False
    except ValueError: pass
    assert find_note({'noteData':{'data':{'noteData':{'noteId':'abc','imageList':[1]}}}},'abc')['imageList']==[1]
    print('PASS: allowed domains, exact item matching, mobile note schema, media signatures')


if __name__=='__main__':
    if '--self-test' in sys.argv: self_test(); sys.exit(0)
    args=sys.argv[1:]; url=args[-1]
    if not allowed(url): print('ERROR: 不支持的链接。',file=sys.stderr); sys.exit(1)
    if not allowed(url,('douyin.com','iesdouyin.com','xiaohongshu.com','xhslink.com','xhslink.cn')):
        import yt_dlp
        yt_dlp.main(args)
    else:
        try:
            d=parse(url)
            if '--dump-single-json' in args: print(json.dumps(d,ensure_ascii=False))
            else:
                dest=Path(args[args.index('-P')+1]) if '-P' in args else Path.home()/'Downloads/LinkDrop'
                save(d,dest)
        except Exception as e:
            print('ERROR: '+str(e),file=sys.stderr); sys.exit(1)
