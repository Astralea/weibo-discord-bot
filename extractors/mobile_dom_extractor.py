from __future__ import annotations

import time
from typing import List, Dict, Any

from selenium import webdriver


def extract_mobile_dom_as_list(driver: webdriver.Remote, mobile_url: str, max_scrolls: int = 6) -> List[Dict[str, Any]]:
    driver.get(mobile_url)
    time.sleep(2)
    collected: List[Dict[str, Any]] = []
    for _ in range(max_scrolls):
        posts = driver.execute_script(
            """
            return (function(){
              function txt(el){return el? (el.innerText||el.textContent||'').trim():''}
              function strip(html){var d=document.createElement('div'); d.innerHTML=html||''; return (d.textContent||d.innerText||'').trim()}
              var cards = Array.from(document.querySelectorAll('.card')).filter(function(c){return c.querySelector('.weibo-text')});
              var out=[];
              cards.forEach(function(c,idx){
                try{
                  var tEl = c.querySelector('.weibo-text');
                  var textRaw = strip(tEl? tEl.innerHTML: '');
                  var timeEl = c.querySelector('time') || c.querySelector('.time');
                  var created = timeEl?(timeEl.getAttribute('datetime')||txt(timeEl)):'';
                  var srcEl = c.querySelector('.from') || c.querySelector('.weibo-footer');
                  var source = txt(srcEl)||'m.weibo.cn';
                  var id = null;
                  var linkEl = c.querySelector('a[href*="/detail/"]');
                  if (linkEl){ var m=(linkEl.getAttribute('href')||'').match(/\/detail\/(\d+)/); if(m){ id=parseInt(m[1]); } }
                  var imgs=[];
                  var media = c.querySelector('.weibo-media, .mwb-media-wrap, .mwb-media, .weibo-media-wrap');
                  var imgEls = media ? media.querySelectorAll('img') : [];
                  function isContentImage(img, src){
                    if (!src) return false;
                    if (src.indexOf('data:')===0) return false;
                    if (!/sinaimg\.cn/.test(src)) return false;
                    if (/\/(emoji|emoticon|face)\//i.test(src)) return false;
                    if (img.closest('.m-icon, .m-emoji, .m-card-head, .m-avatar-box, .badge, .weibo-top')) return false;
                    return true;
                  }
                  Array.prototype.forEach.call(imgEls, function(img){
                    var src = img.getAttribute('data-src') || img.getAttribute('src') || '';
                    if (!isContentImage(img, src)) return;
                    var u = src.replace(/\/\/wx\d+\./,'//wx4.').replace('/orj360/','/large/');
                    if (u.indexOf('/large/')===-1 && /\/bmiddle\//.test(u)===false) {
                      u = u.replace('/mw690/','/large/').replace('/mw1024/','/large/');
                    }
                    imgs.push(u);
                  });
                  var pic_infos={};
                  imgs.forEach(function(u,i){
                    var key='p'+i;
                    pic_infos[key]={ large: {url: u}, bmiddle: {url: u.replace('/large/','/bmiddle/')} };
                  });
                  var item={ id: id || (Date.now()/1000|0)*100000 + idx, text_raw: textRaw, created_at: created || new Date().toString(), source: source };
                  if (Object.keys(pic_infos).length){ item.pic_infos = pic_infos; }
                  out.push(item);
                }catch(e){}
              });
              return out;
            })();
            """
        )
        if isinstance(posts, list) and posts:
            # Unique by id
            seen = set()
            out = []
            for it in posts:
                i = it.get('id')
                if i in seen:
                    continue
                seen.add(i)
                out.append(it)
            if out:
                return out
        try:
            driver.execute_script('window.scrollBy(0, Math.min(1200, (document.body.scrollHeight||2000)));')
        except Exception:
            pass
        time.sleep(1)
    return collected



