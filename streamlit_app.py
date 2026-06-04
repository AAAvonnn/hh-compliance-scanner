"""HH 鍚堣鎵弿 v8 鈥?HuggingFace 鐗?""
import os, json, subprocess, tempfile, time, re
import streamlit as st
import requests
import whisper

st.set_page_config(page_title="HH 鎵弿 v8", page_icon="鈿?, layout="wide")
st.title("鈿?HH 瑙嗛鍚堣鎵弿鍣?v8")
st.caption("Whisper+LLM鍚庢牎姝?路 棣栭グ涓撳煙杞綍 路 绮惧噯鏃堕棿杞?路 OCR 路 鑷畾涔夎瘝搴?)

# HF Secrets 涓殑 API Key
API_KEY = st.secrets.get("ARK_API_KEY", "")

def default_douyin():
    return {
        "鏋侀檺璇?:["鏈€","绗竴","鍞竴","鍏ㄧ綉鏈€浣?,"椤剁骇","鏋佽嚧","缁濆","姘歌繙","姘镐箙","涓囪兘","鐧惧垎鐧?,"闆堕闄?,"鍥藉绾?,"鍏ㄧ悆棣栧彂","鐙"],
        "杩蜂俊璇?:["鎷涜储","淇濅綉","绁堢","寮€鍏?,"椋庢按","杞繍","杈熼偑","鎶よ韩","鏄剧伒","杩蜂俊","鏃哄畢","閫㈠嚩鍖栧悏"],
        "铏氬亣鎵胯":["鍖呰繃","绔嬮┈鍗囧€?,"绋宠禋","蹇呮定","淇濆簳","缁濆涓嶈捣鐞?,"缁濅笉鎺夎壊","姘镐箙淇濅慨"],
        "鍔熸晥璇?:["鏍规不","涓€鐩掕鏁?,"娌荤枟","娌绘剤","鍖荤枟绾?,"澶勬柟","鐗规晥","绁炴晥","濂囨晥","褰诲簳娓呴櫎","绁涙牴"],
        "瀵规瘮璐綆":["鍚婃墦","纰惧帇","瀹岀垎","绉掓潃鍚岃"],
        "璇浠锋牸":["浜忔湰","璧旈挶","涓嶈禋閽?,"鍊掗棴","鐮翠骇浠?,"鍏嶈垂閫?],
    }

def default_kuaishou():
    return {
        "鏉愯川鎵胯":["涓嶆帀鑹?,"涓嶈お鑹?,"涓嶈劚鑹?,"姘镐笉瑜壊","淇濊壊","姘镐箙淇濊壊","闃茶繃鏁?,"闃叉晱","鎶楁晱","姘存礂涓嶆帀鑹?,"姘存礂涓嶇敤鎽?,"鐫¤涓嶇敤鎽?,"娲楁尽涓嶇敤鎽?,"鎴寸潃娲楁尽","鎴寸潃鐫¤"],
        "鏋侀檺璇?:["鏈€","绗竴","鍞竴","鍏ㄧ綉鏈€浣?,"椤剁骇","鏋佽嚧","缁濆","姘歌繙","姘镐箙","涓囪兘","鐧惧垎鐧?,"鍥藉绾?,"鍏ㄧ悆棣栧彂","鐙"],
        "杩蜂俊璇?:["鎷涜储","淇濅綉","绁堢","寮€鍏?,"椋庢按","杞繍","杈熼偑","鎶よ韩","鏃哄畢"],
        "铏氬亣鎵胯":["鍖呰繃","绋宠禋","蹇呮定","淇濆簳","鎵胯","淇濊瘉"],
        "鍔熸晥璇?:["鏍规不","娌绘剤","娌荤枟","绁炴晥","濂囨晥","鐗规晥","绔嬬瑙佸奖"],
        "瀵规瘮璐綆":["鍚婃墦","纰惧帇","瀹岀垎","绉掓潃鍚岃"],
        "浠锋牸璇":["浜忔湰","璧旈挶","涓嶈禋閽?,"鍊掗棴","鐮翠骇浠?],
    }

if 'douyin_dict' not in st.session_state:
    st.session_state.douyin_dict = default_douyin()
if 'kuaishou_dict' not in st.session_state:
    st.session_state.kuaishou_dict = default_kuaishou()

def flatten(d): return sorted(set(w for words in d.values() for w in words), key=len, reverse=True)

# 棣栭グ棰嗗煙璇嶆眹琛?鈥?甯姪 Whisper 绮惧噯杞綍
JEWELRY_VOCAB = (
    "浠ヤ笅鏄楗扮彔瀹濈被鐩存挱鍙ｆ挱锛岃绮惧噯璇嗗埆浠ヤ笅璇嶆眹锛?
    # 鍝佺被
    "鑰抽拤 鑰崇幆 鑰冲潬 鑰虫墸 鑰抽澶?椤归摼 鍚婂潬 鎵嬮摼 鎵嬮暞 鑴氶摼 鎴掓寚 鍙戠蔼 鍙戝す 鍙戝崱 鑳搁拡 鎶撳す 澶撮グ 澶寸怀 鍙戝湀 鍙戠畭 椤瑰湀 閿侀閾?鑴氶暞 鑴氭垝 鎸囩幆 "
    # 鍏冪礌閫犲瀷
    "鐨囧啝 閾冮摏 铦磋澏 鑺辨湹 鑺辩摚 鍥涘彾鑽?鐖卞績 鏄熸槦 鏈堜寒 澶槼 缇芥瘺 缈呰唨 澶╀娇 鎭堕瓟 钁姦 绂忚 灏忚洰鑵?绔硅妭 璐濆３ 鐝嶇彔 鐝犵彔 灏忕背鐝?绫崇彔 缂栫粐 闀傜┖ 娴佽嫃 楹︾ 姘撮捇 閿嗙煶 鐚溂鐭?鐚尗鐭?姘存櫠 鐜涚憴 鐜夌煶 缈＄繝 閽荤煶 瀹濈煶 纰庨捇 鏂圭硸 鑿卞舰 娉㈢偣 鏉＄汗 璞圭汗 鏍煎瓙 鍦嗙幆 鏂瑰潡 涓夎 姘存淮 鎵囧瓙 鎵囪礉 閾舵潖 "
    # 鏉愯川宸ヨ壓
    "閾堕拡 鍚堥噾 闀€閲?闀€閾?鍖呴噾 閽涢挗 绾摱 閾滈晙閲?鐢甸晙 鐑ゆ紗 鐝愮悈 婊撮噳 鎵嬪伐 鎵嬩綔 缂栫粐 缂栫粐缁?浜氬厠鍔?鏍戣剛 闄剁摲 鐞夌拑 鐜荤拑 閿嗙煶 璐濇瘝 澶╃劧鐭?"
    # 韬綋閮ㄤ綅
    "閿侀 鑰冲瀭 鑰抽 鎵嬭厱 鑴氳笣 鑴氳剸 棰堥棿 鎸囧皷 鍙戦棿 鑰宠竟 鑳稿墠 鑳稿彛 鎵嬭儗 鎵嬫帉 鎵嬫寚 澶ф媷鎸?椋熸寚 涓寚 鏃犲悕鎸?灏忔媷鎸?鑴栧瓙 鑰虫湹 宸﹁剼 鍙宠剼 宸︽墜 鍙虫墜 鍙岃吙 鎵嬭噦 "
    # 淇グ璇?    "杞诲ア 楂樼骇鎰?姘旇川 娓╂煍 绮捐嚧 浼橀泤 鏃跺皻 鐧炬惌 鏄剧櫧 鏄剧槮 鏄惧 楂樼骇 鐢滅編 鍙埍 澶嶅彜 灏忎紬 娉曞紡 娆х編 闊╃郴 鏃ョ郴 绠€绾?鏋佺畝 涓€?寰″ 灏戝コ 妫郴 鏂囪壓 娓呮柊 鏆楅粦 鏈嬪厠 鎬ф劅 "
    # 璐ㄦ劅鎻忚堪
    "涓嶆帀鑹?涓嶈お鑹?涓嶈劚鑹?淇濊壊 闃茶繃鏁?闃叉晱 鎶楁晱 涓嶈繃鏁?姘存礂涓嶆帀鑹?娲楁尽涓嶇敤鎽?鐫¤涓嶇敤鎽?闃叉按 闃叉睏 鑰愮（ 鑰愬埉 涓嶆哀鍖?涓嶇敓閿?涓嶆帀閽?涓嶅嬀澶村彂 涓嶆寕琛ｆ湇 涓嶅す鑲?"
    # 钀ラ攢璇濇湳
    "涓や綅鏁?鍑犲崄鍧?鎬т环姣?骞虫浛 澶嶈喘 鐖嗘 鏂版 鐑攢 闄愭椂 浼樻儬 娲诲姩浠?鐩存挱闂?涓嬪崟 鐜拌揣 绂忓埄 绉掓潃 瀹犵矇 闂溂鍏?涓嶈俯闆?閫侀椇瀵?閫佸コ鍙?閫佸濡?鑷埓 绀肩墿 鐢熸棩绀肩墿 绾康鏃?"
    # 棰滆壊
    "濂剁櫧鑹?閾惰壊 閲戣壊 鐜懓閲?閿嗙煶鐧?鐝嶇彔鐧?澧ㄧ豢 婀栬摑 妯辫姳绮?濂惰尪鑹?榛戣壊 鐧借壊 閫忔槑 閰掔孩 瀹濊摑 棣欐 绱綏鍏?闆捐摑 鐑熺伆"
    # 绌挎埓鏂瑰紡
    "浣╂埓 鎴翠笂 鎽樹笅鏉?鎵ｄ笂 绯讳笂 鍒笂 鎻掍笂 鍗′笂 濂椾笂 绌夸笂 鎸備笂 "
    # 绌挎惌鍦烘櫙
    "鐧借‖琛?灏忛粦瑁?纰庤姳瑁?鍚婂甫瑁?姣涜。 鍗。 瑗胯 澶ц。 椋庤。 鏃楄 姹夋湇 鍙よ 濠氱罕 绀兼湇 閫氬嫟 涓婄彮 绾︿細 閫涜 娲惧 鏅氬 濠氱ぜ 鏃ュ父 鍑鸿"
    # 甯歌鍙ｆ挱鍙ュ紡
    "濮愬 濂崇敓 濂充汉 濂冲 浠欏コ 灏忓濮?澶編浜?鐗瑰埆濂界湅 瓒呭ソ鐪?璋佹埓璋佺煡閬?鐪熺殑缁?涓€鐪煎氨鐖变笂 鎴翠笂灏变笉鎯虫憳 鍥炲ご鐜?绮捐嚧鎰?姘涘洿鎰?浠紡鎰?灏忓績鏈?鐐圭潧涔嬬瑪"
)

# 椋庨櫓鎻愰啋璇嶏紙鏍囬粍锛?RISK_WORDS = ["鍙戦粦","鍙橀粦","鎺夎壊","瑜壊","鍙樿壊","姘у寲","鐢熼攬","瑜晙","鎺夐捇","鑴辫兌","鏂",
              "杩囨晱","绾㈣偪","鍙戠棐","娌愭荡闇?,"娲楀彂姘?,"娲楁磥绮?,"棣欑殏","鑲ョ殏","鐑按",
              "娲楁尽","鐫¤","娓告吵","杩愬姩","鍑烘睏","娌炬按","纰版按","娲楁墜","娲楃",
              "涓嶇敤鎽?,"涓嶆憳","涓嶆嬁涓嬫潵"]

@st.cache_resource
def load_whisper():
    return whisper.load_model('tiny')  # HF鍏嶈垂鐗堢敤tiny锛屾湰鍦扮敤small

whip = load_whisper()

# ===== Whisper杞綍鍚嶭LM鏍℃ =====
def fix_transcription(raw_text):
    """鐢↙LM鏍规嵁棣栭グ涓婁笅鏂囦慨姝hisper鐨勮闊宠瘑鍒敊璇?""
    prompt = f"""浣犳槸棣栭グ鐝犲疂鐩存挱璇煶璇嗗埆鏍″涓撳銆備笅闈㈡槸涓€娈礧hisper杞綍鐨勯楗扮洿鎾彛鎾紝鍥犱富鎾湁鍙ｉ煶瀵艰嚧璇嗗埆閿欒銆傝鏍规嵁涓婁笅鏂囧拰棣栭グ棰嗗煙甯歌瘑淇鎵€鏈夐敊璇€?
銆愬繀椤讳慨姝ｇ殑甯歌閿欒銆?- 鍚婃/鍚婃 鈫?鎺夎壊
- 鐏佃崱/闆跺綋/闆堕摏 鈫?閾冮摏
- 榛勭摐/榛勫厜/鎯跺厜 鈫?鐨囧啝
- 鏈ㄩ奔楣?鏈ㄩ奔璺?鈫?娌愭荡闇?- 绾藉厜/鐗涘厜/鎵厜 鈫?娴佸厜
- 璧风殑鍚婅剼/娲楃殑鍚婅剼 鈫?娲楁钉鍓?- 鍙戦粦 鈫?鍙戦粦锛堟纭紝淇濇寔锛?- 鐓?涓?鈫?娲楋紙娲楁尽鍦烘櫙锛?- 楂樻俯姘寸叜 鈫?楂樻俯姘存礂
- 鑴氳劯/瑙掕劯 鈫?鑴氶摼
- 鎵嬭劯 鈫?鎵嬮摼
- 鑰崇洴 鈫?鑰抽拤
- 鍚戣劯 鈫?椤归摼
- 鍊熷瓙 鈫?鎴掓寚
- 灏忓叕涓?灏忓伐涓?灏忓叕涓?鈫?灏忓叕涓?- 濂崇帇/濂崇殗 鈫?濂崇帇
- 瀹犵埍/閲嶇埍 鈫?瀹犵埍
- 鐙珛/璇诲姏 鈫?鐙珛
- 寮哄ぇ/澧欏ぇ 鈫?寮哄ぇ

銆愯鍒欍€?1. 鍙慨姝ｆ槑鏄剧殑璇煶璇嗗埆閿欒锛屼笉閫氶『澶勪繚鎸佸師鎰?2. 淇鍚庡繀椤荤鍚堥楗?鐝犲疂/閰嶉グ棰嗗煙璇
3. 涓嶈娣诲姞鍘熸枃娌℃湁鐨勪俊鎭?4. 淇濈暀鎵€鏈夋暟瀛椼€佹爣鐐?5. 杩斿洖鏍煎紡锛歿{"corrected": "淇鍚庣殑瀹屾暣鏂囧瓧"}}锛屽彧杩斿洖JSON

鍘熸枃锛歿raw_text}"""
    try:
        r = requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"},
            json={"model":"doubao-seed-1-6-250615","messages":[
                {"role":"system","content":prompt}
            ],"temperature":0,"max_tokens":1000},
            timeout=30)
        if r.status_code==200:
            raw = r.json()['choices'][0]['message']['content']
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                data = json.loads(m.group())
                if 'corrected' in data:
                    return data['corrected']
    except: pass
    return raw_text  # 澶辫触杩斿洖鍘熸枃

def llm_review(text, platform):
    prompt = f"""浣犳槸{platform}鐢靛晢鍚堣瀹℃牳銆傚垽鏂繚瑙勶紝娉ㄦ剰ASR鍙兘鏈夐敊鍒瓧銆?瑙勫垯锛氬瑙傝瘎浠稯K("鏈€鍙楁杩?)锛岀粷瀵规壙璇鸿繚瑙?"缁濆涓嶆帀鑹?)锛岃糠淇¤瘝蹇呰繚瑙勶紝鏉愯川鎵胯(涓嶆帀鑹?闃叉晱/姘存礂涓嶆憳)鍦ㄥ揩鎵嬪繀杩濊銆?杩斿洖JSON锛歿{"has_violation":true/false,"violations":[{{"text":"鐗囨","reason":"鐞嗙敱","severity":"楂?涓?浣?,"fix":"寤鸿"}}],"summary":"鎬荤粨"}}"""
    try:
        r = requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"},
            json={"model":"doubao-seed-1-6-250615","messages":[
                {"role":"system","content":prompt},
                {"role":"user","content":f"鍒嗘瀽锛歿text}"}
            ],"temperature":0,"max_tokens":400}, timeout=30)
        if r.status_code==200:
            raw = r.json()['choices'][0]['message']['content']
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m: return json.loads(m.group())
    except: pass
    return None

def quick_ocr(video_path):
    results = []
    try:
        dur = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',video_path],
            capture_output=True,text=True).stdout.strip() or 60)
        for t in [3, dur/2, dur-3]:
            if t<0 or t>dur: continue
            png = tempfile.mktemp(suffix='.png')
            subprocess.run(['ffmpeg','-y','-ss',str(int(t)),'-i',video_path,'-vframes','1','-vf','scale=360:-1',png],
                capture_output=True,timeout=5)
            if os.path.exists(png) and os.path.getsize(png)>500:
                txt = subprocess.run(['tesseract',png,'stdout','-l','chi_sim','--psm','6'],
                    capture_output=True,text=True,timeout=10).stdout.strip()
                if txt: results.append({"time":int(t),"text":txt[:200]})
            if os.path.exists(png): os.remove(png)
    except: pass
    return results

def scan(video_path, fname, platform):
    t0 = time.time()
    bad_words = flatten(st.session_state.douyin_dict if platform=="鎶栭煶" else st.session_state.kuaishou_dict)
    
    # Whisper杞綍锛堥楗伴鍩熻瘝姹囧紩瀵?璇嶇骇鏃堕棿鎴筹級
    result = whip.transcribe(video_path, language='zh', fp16=False, 
                             initial_prompt=JEWELRY_VOCAB, word_timestamps=True)
    raw_text = result['text']
    segments = result.get('segments', [])
    
    # LLM鍚庢牎姝ｏ細淇鍙ｉ煶瀵艰嚧鐨勮瘑鍒敊璇?    text = fix_transcription(raw_text)
    
    # 鍏抽敭璇嶆壂鎻忥紙浣跨敤璇嶇骇鏃堕棿鎴筹紝绮惧噯鍒扮锛?    kw_hits = []
    # Build word timeline from segments
    word_timeline = []
    for seg in segments:
        words_data = seg.get('words', [])
        if words_data:
            for w in words_data:
                word_timeline.append({"word": w['word'].strip(), "start": w['start'], "end": w['end']})
    
    # Scan for bad words in timeline
    if word_timeline:
        # Build full text from timeline
        tl_text = ''.join([w['word'] for w in word_timeline])
        i = 0
        while i < len(tl_text):
            for bw in bad_words:
                if i+len(bw) <= len(tl_text) and tl_text[i:i+len(bw)] == bw:
                    # Find timestamp from timeline
                    char_count = 0
                    ts_start = 0
                    for wt in word_timeline:
                        char_count += len(wt['word'])
                        if char_count >= i:
                            ts_start = wt['start']
                            break
                    m, s = divmod(int(ts_start), 60)
                    kw_hits.append({"word":bw, "time":f"{m:02d}:{s:02d}"})
                    i += len(bw)-1; break
            i += 1
    else:
        # Fallback: character-based estimation
        i = 0
        while i < len(text):
            for bw in bad_words:
                if i+len(bw) <= len(text) and text[i:i+len(bw)] == bw:
                    ts = (i/len(text))*segments[-1]['end'] if segments else 0
                    m, s = divmod(int(ts), 60)
                    kw_hits.append({"word":bw, "time":f"{m:02d}:{s:02d}"})
                    i += len(bw)-1; break
            i += 1
    
    # 椋庨櫓璇嶆壂鎻忥紙鍚屾牱浣跨敤璇嶇骇鏃堕棿鎴筹級
    risk_hits = []
    if word_timeline:
        tl_text = ''.join([w['word'] for w in word_timeline])
        i = 0
        while i < len(tl_text):
            for rw in RISK_WORDS:
                if i+len(rw) <= len(tl_text) and tl_text[i:i+len(rw)] == rw:
                    char_count = 0; ts_start = 0
                    for wt in word_timeline:
                        char_count += len(wt['word'])
                        if char_count >= i:
                            ts_start = wt['start']; break
                    m, s = divmod(int(ts_start), 60)
                    risk_hits.append({"word":rw, "time":f"{m:02d}:{s:02d}"})
                    i += len(rw)-1; break
            i += 1
    else:
        i = 0
        while i < len(text):
            for rw in RISK_WORDS:
                if i+len(rw) <= len(text) and text[i:i+len(rw)] == rw:
                    ts = (i/len(text))*segments[-1]['end'] if segments else 0
                    m, s = divmod(int(ts), 60)
                    risk_hits.append({"word":rw, "time":f"{m:02d}:{s:02d}"})
                    i += len(rw)-1; break
            i += 1
    
    # LLM
    llm = llm_review(text, platform) if (kw_hits or len(text)>20) else None
    
    # OCR
    ocr = quick_ocr(video_path)
    
    # 鍒ゅ畾
    llm_v = llm and llm.get('has_violation', False)
    has_ocr = any(any(bw in o.get('text','') for bw in bad_words) for o in ocr)
    status = "杩濊" if (kw_hits or llm_v or has_ocr) else "OK"
    
    return {"file":fname,"status":status,"elapsed":round(time.time()-t0,1),
            "text":text,"raw_text":raw_text,"kw_hits":kw_hits,"risk_hits":risk_hits,"llm":llm,"ocr":ocr}

# Sidebar
with st.sidebar:
    platform = st.selectbox("馃幆 骞冲彴",["鎶栭煶","蹇墜"])
    st.divider()
    st.markdown("### 馃摑 鑷畾涔夎瘝搴?)
    tab1,tab2 = st.tabs(["鎶栭煶璇嶅簱","蹇墜璇嶅簱"])
    
    def dict_editor(tab, store):
        with tab:
            nc = st.text_input("鏂板垎绫?,key=f"cat_{store}")
            nw = st.text_input("鏂拌瘝(,鍒嗛殧)",key=f"w_{store}")
            if nc and nw and st.button("娣诲姞",key=f"add_{store}"):
                for w in [x.strip() for x in nw.split(",") if x.strip()]:
                    if nc not in st.session_state[store]: st.session_state[store][nc]=[]
                    if w not in st.session_state[store][nc]: st.session_state[store][nc].append(w)
                st.rerun()
            for cat,words in st.session_state[store].items():
                with st.expander(f"{cat} ({len(words)}璇?"):
                    st.caption(", ".join(words))
    
    dict_editor(tab1,'douyin_dict')
    dict_editor(tab2,'kuaishou_dict')
    total = sum(len(v) for v in st.session_state.douyin_dict.values()) + sum(len(v) for v in st.session_state.kuaishou_dict.values())
    st.metric("璇嶅簱鎬昏",f"{total}璇?)
    if st.button("馃攧 鎭㈠榛樿",use_container_width=True):
        st.session_state.douyin_dict=default_douyin()
        st.session_state.kuaishou_dict=default_kuaishou()
        st.rerun()

# Main
uploaded = st.file_uploader("馃摛 鎷栨嫿瑙嗛锛坢p4/mov/avi锛?,type=["mp4","mov","avi"],accept_multiple_files=True)

if uploaded and st.button("鈿?寮€濮嬫壂鎻?,type="primary",use_container_width=True):
    progress = st.progress(0)
    status_text = st.empty()
    results_area = st.container()
    
    bad_count = 0
    risk_count = 0
    
    for idx, uf in enumerate(uploaded):
        status_text.info(f"鈿?鎵弿涓?({idx+1}/{len(uploaded)}) {uf.name} ...")
        
        tmp = tempfile.mktemp(suffix=os.path.splitext(uf.name)[1])
        with open(tmp,'wb') as f: f.write(uf.read())
        r = scan(tmp, uf.name, platform)
        os.remove(tmp)
        
        if r['status'] != 'OK': bad_count += 1
        elif r.get('risk_hits'): risk_count += 1
        
        # 杈规壂杈瑰嚭缁撴灉
        with results_area:
            if r['status'] == 'OK' and not r.get('risk_hits'):
                with st.expander(f"鉁?{r['file']} 鈥?瀹夊叏 | {r['elapsed']}s"):
                    st.caption(f"鍙ｆ挱: {r['text'][:200]}")
            elif r['status'] == 'OK' and r.get('risk_hits'):
                with st.expander(f"鈿狅笍 {r['file']} 鈥?鏈夐闄╂彁绀?| {r['elapsed']}s", expanded=True):
                    st.warning(f"馃煛 椋庨櫓鎻愰啋 ({len(r['risk_hits'])}澶?:")
                    for h in r['risk_hits']: st.write(f"  鈥?`{h['word']}` @ {h['time']}")
                    if r['kw_hits']:
                        st.error(f"馃攳 鍏抽敭璇?({len(r['kw_hits'])}澶?:")
                        for h in r['kw_hits']: st.write(f"  鈥?`{h['word']}` @ {h['time']}")
                    if r['llm']:
                        llm = r['llm']
                        if llm.get('has_violation'):
                            st.error(f"馃 LLM: {llm.get('summary','')}")
                            for v in llm.get('violations',[]):
                                s = {"楂?:"馃敶","涓?:"馃煚","浣?:"馃煛"}.get(v.get('severity',''),'')
                                st.write(f"  {s} `{v['text']}` 鈥?{v.get('reason','')}")
                                if v.get('fix'): st.caption(f"    馃挕 {v['fix']}")
                        else:
                            st.success("馃 LLM: 璇姝ｅ父")
                    if r['ocr']:
                        for o in r['ocr']: st.caption(f"馃摲 @{o['time']}s: {o['text'][:120]}")
                    st.caption(f"馃摑 杞綍: {r['text'][:300]}")
            else:
                with st.expander(f"鉂?{r['file']} 鈥?杩濊 | {r['elapsed']}s", expanded=True):
                    if r['kw_hits']:
                        st.error(f"馃攳 鍏抽敭璇?({len(r['kw_hits'])}澶?:")
                        for h in r['kw_hits']: st.write(f"  鈥?`{h['word']}` @ {h['time']}")
                    if r.get('risk_hits'):
                        st.warning(f"馃煛 椋庨櫓鎻愰啋 ({len(r['risk_hits'])}澶?:")
                        for h in r['risk_hits']: st.write(f"  鈥?`{h['word']}` @ {h['time']}")
                    if r['llm']:
                        llm = r['llm']
                        if llm.get('has_violation'):
                            st.error(f"馃 LLM: {llm.get('summary','')}")
                            for v in llm.get('violations',[]):
                                s = {"楂?:"馃敶","涓?:"馃煚","浣?:"馃煛"}.get(v.get('severity',''),'')
                                st.write(f"  {s} `{v['text']}` 鈥?{v.get('reason','')}")
                                if v.get('fix'): st.caption(f"    馃挕 {v['fix']}")
                        else:
                            st.success("馃 LLM: 璇姝ｅ父")
                    if r['ocr']:
                        for o in r['ocr']: st.caption(f"馃摲 @{o['time']}s: {o['text'][:120]}")
                    st.caption(f"馃摑 杞綍: {r['text'][:300]}")
        
        progress.progress((idx+1)/len(uploaded))
    
    progress.empty()
    status_text.empty()
    
    # 姹囨€?    c1,c2,c3,c4 = st.columns(4)
    c1.metric("鎬昏",len(uploaded))
    c2.metric("鍚堟牸 鉁?,len(uploaded)-bad_count-risk_count)
    c3.metric("椋庨櫓 鈿狅笍",risk_count)
    c4.metric("杩濊 鉂?,bad_count)

st.divider()
st.caption("HH v8 | Whisper+LLM鍚庢牎姝?| 璇嶇骇鏃堕棿鎴?| 棣栭グ涓撳煙 | 娴佸紡澶勭悊")

# ===== 鏅鸿兘鍓緫 =====
st.divider()
st.header("鉁傦笍 鏅鸿兘鍓緫")
st.caption("鍕鹃€夎鍒犻櫎鐨勫彞瀛?鈫?涓€閿敓鎴愬共鍑€瑙嗛")

edit_file = st.file_uploader("涓婁紶瑕佸壀杈戠殑瑙嗛", type=["mp4","mov","avi"], key="editor_upload")

if edit_file:
    # 瀛樺埌涓存椂鏂囦欢
    tmp_vid = tempfile.mktemp(suffix=os.path.splitext(edit_file.name)[1])
    with open(tmp_vid,'wb') as f: f.write(edit_file.read())
    
    if st.button("馃摑 璇嗗埆鍙ｆ挱", type="primary"):
        with st.spinner("Whisper杞綍涓?.."):
            result = whip.transcribe(tmp_vid, language='zh', fp16=False, initial_prompt=JEWELRY_VOCAB)
            segments = result.get('segments', [])
            text = result['text']
            
            st.session_state.edit_segments = segments
            st.session_state.edit_text = text
            st.session_state.edit_video = tmp_vid
            st.session_state.edit_fname = edit_file.name
            
            st.success(f"璇嗗埆瀹屾垚锛亄len(segments)} 涓彞瀛?)
    
    if 'edit_segments' in st.session_state and st.session_state.edit_segments:
        segs = st.session_state.edit_segments
        
        # 杩濈璇嶆娴嬪苟棰勯€変腑
        bad_words = flatten(st.session_state.douyin_dict)
        risk_words = RISK_WORDS
        
        st.write("### 鍕鹃€夎鍒犻櫎鐨勫彞瀛愶細")
        
        cuts = []  # time ranges to remove
        
        for idx, seg in enumerate(segs):
            txt = seg['text'].strip()
            if not txt: continue
            
            start = seg['start']
            end = seg['end']
            mm1, ss1 = divmod(int(start), 60)
            mm2, ss2 = divmod(int(end), 60)
            
            # Check for violations
            has_bad = any(bw in txt for bw in bad_words)
            has_risk = any(rw in txt for rw in risk_words)
            
            label = f"{txt}  [{mm1:02d}:{ss1:02d}-{mm2:02d}:{ss2:02d}]"
            if has_bad:
                label = f"馃敶 {label}"
            elif has_risk:
                label = f"馃煛 {label}"
            
            default_check = has_bad  # 榛樿鍕鹃€夎繚瑙勫彞瀛?            
            if st.checkbox(label, value=default_check, key=f"seg_{idx}"):
                cuts.append((start, end))
        
        if cuts and st.button("馃敧 涓€閿垹闄ゅ苟鐢熸垚瑙嗛", type="primary", use_container_width=True):
            with st.spinner("姝ｅ湪鍓緫..."):
                # Build ffmpeg filter to cut out selected segments
                # Keep parts: 0 to cut[0].start, cut[0].end to cut[1].start, etc.
                keep = []
                prev_end = 0.0
                for start, end in sorted(cuts):
                    if start > prev_end + 0.1:
                        keep.append((prev_end, start))
                    prev_end = max(prev_end, end)
                
                dur = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',st.session_state.edit_video],
                    capture_output=True,text=True).stdout.strip() or 60)
                if prev_end < dur - 0.1:
                    keep.append((prev_end, dur))
                
                if not keep:
                    st.error("涓嶈兘鍒犻櫎鎵€鏈夊唴瀹癸紒")
                else:
                    # Write concat list
                    concat_file = tempfile.mktemp(suffix='.txt')
                    with open(concat_file, 'w', encoding='utf-8') as f:
                        for s, e in keep:
                            f.write(f"file '{st.session_state.edit_video.replace(chr(92),chr(92)+chr(92))}'\n")
                            f.write(f"inpoint {s}\n")
                            f.write(f"outpoint {e}\n")
                    
                    out_vid = tempfile.mktemp(suffix='.mp4')
                    subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',concat_file,'-c','copy',out_vid],
                        capture_output=True, timeout=60)
                    
                    if os.path.exists(out_vid) and os.path.getsize(out_vid) > 1000:
                        with open(out_vid, 'rb') as f:
                            st.download_button("猬囷笍 涓嬭浇鍓緫鍚庤棰?, f, 
                                file_name=f"clean_{st.session_state.edit_fname}",
                                mime="video/mp4")
                        st.success("鍓緫瀹屾垚锛?)
                    else:
                        st.error("鍓緫澶辫触锛屽皾璇曠敤 re-encode 鏂瑰紡...")
                        # Fallback: re-encode with trim filters
                        filters = []
                        for s, e in keep:
                            filters.append(f"between(t,{s},{e})")
                        filter_str = '+'.join(filters)
                        out_vid2 = tempfile.mktemp(suffix='.mp4')
                        subprocess.run(['ffmpeg','-y','-i',st.session_state.edit_video,
                            '-vf',f"select='{filter_str}',setpts=N/FRAME_RATE/TB",
                            '-af',f"aselect='{filter_str}',asetpts=N/SR/TB",
                            '-c:v','libx264','-c:a','aac','-b:v','1500k','-b:a','64k',out_vid2],
                            capture_output=True, timeout=120)
                        if os.path.exists(out_vid2) and os.path.getsize(out_vid2) > 1000:
                            with open(out_vid2, 'rb') as f:
                                st.download_button("猬囷笍 涓嬭浇鍓緫鍚庤棰?, f,
                                    file_name=f"clean_{st.session_state.edit_fname}",
                                    mime="video/mp4")
                            st.success("鍓緫瀹屾垚锛?)
                    
                    os.remove(concat_file)
        
        if st.button("馃攧 閲嶆柊璇嗗埆"):
            for k in ['edit_segments','edit_text','edit_video','edit_fname']:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
