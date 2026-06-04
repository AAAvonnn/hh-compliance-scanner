"""HH 合规扫描 v8 — HuggingFace 版"""
import os, json, subprocess, tempfile, time, re
import streamlit as st
import requests
import whisper

st.set_page_config(page_title="HH 扫描 v8", page_icon="⚡", layout="wide")
st.title("⚡ HH 视频合规扫描器 v8")
st.caption("Whisper+LLM后校正 · 首饰专域转录 · 精准时间轴 · OCR · 自定义词库")

# HF Secrets 中的 API Key
API_KEY = st.secrets.get("ARK_API_KEY", "")

def default_douyin():
    return {
        "极限词":["最","第一","唯一","全网最低","顶级","极致","绝对","永远","永久","万能","百分百","零风险","国家级","全球首发","独家"],
        "迷信词":["招财","保佑","祈福","开光","风水","转运","辟邪","护身","显灵","迷信","旺宅","逢凶化吉"],
        "虚假承诺":["包过","立马升值","稳赚","必涨","保底","绝对不起球","绝不掉色","永久保修"],
        "功效词":["根治","一盒见效","治疗","治愈","医疗级","处方","特效","神效","奇效","彻底清除","祛根"],
        "对比贬低":["吊打","碾压","完爆","秒杀同行"],
        "误导价格":["亏本","赔钱","不赚钱","倒闭","破产价","免费送"],
    }

def default_kuaishou():
    return {
        "材质承诺":["不掉色","不褪色","不脱色","永不褪色","保色","永久保色","防过敏","防敏","抗敏","水洗不掉色","水洗不用摘","睡觉不用摘","洗澡不用摘","戴着洗澡","戴着睡觉"],
        "极限词":["最","第一","唯一","全网最低","顶级","极致","绝对","永远","永久","万能","百分百","国家级","全球首发","独家"],
        "迷信词":["招财","保佑","祈福","开光","风水","转运","辟邪","护身","旺宅"],
        "虚假承诺":["包过","稳赚","必涨","保底","承诺","保证"],
        "功效词":["根治","治愈","治疗","神效","奇效","特效","立竿见影"],
        "对比贬低":["吊打","碾压","完爆","秒杀同行"],
        "价格误导":["亏本","赔钱","不赚钱","倒闭","破产价"],
    }

if 'douyin_dict' not in st.session_state:
    st.session_state.douyin_dict = default_douyin()
if 'kuaishou_dict' not in st.session_state:
    st.session_state.kuaishou_dict = default_kuaishou()

def flatten(d): return sorted(set(w for words in d.values() for w in words), key=len, reverse=True)

# 首饰领域词汇表 — 帮助 Whisper 精准转录
JEWELRY_VOCAB = (
    "以下是首饰珠宝类直播口播，请精准识别以下词汇："
    # 品类
    "耳钉 耳环 耳坠 耳扣 耳骨夹 项链 吊坠 手链 手镯 脚链 戒指 发簪 发夹 发卡 胸针 抓夹 头饰 头绳 发圈 发箍 项圈 锁骨链 脚镯 脚戒 指环 "
    # 元素造型
    "皇冠 铃铛 蝴蝶 花朵 花瓣 四叶草 爱心 星星 月亮 太阳 羽毛 翅膀 天使 恶魔 葫芦 福袋 小蛮腰 竹节 贝壳 珍珠 珠珠 小米珠 米珠 编织 镂空 流苏 麦穗 水钻 锆石 猫眼石 猫猫石 水晶 玛瑙 玉石 翡翠 钻石 宝石 碎钻 方糖 菱形 波点 条纹 豹纹 格子 圆环 方块 三角 水滴 扇子 扇贝 银杏 "
    # 材质工艺
    "银针 合金 镀金 镀银 包金 钛钢 纯银 铜镀金 电镀 烤漆 珐琅 滴釉 手工 手作 编织 编织绳 亚克力 树脂 陶瓷 琉璃 玻璃 锆石 贝母 天然石 "
    # 身体部位
    "锁骨 耳垂 耳骨 手腕 脚踝 脚脖 颈间 指尖 发间 耳边 胸前 胸口 手背 手掌 手指 大拇指 食指 中指 无名指 小拇指 脖子 耳朵 左脚 右脚 左手 右手 双腿 手臂 "
    # 修饰词
    "轻奢 高级感 气质 温柔 精致 优雅 时尚 百搭 显白 显瘦 显嫩 高级 甜美 可爱 复古 小众 法式 欧美 韩系 日系 简约 极简 中性 御姐 少女 森系 文艺 清新 暗黑 朋克 性感 "
    # 质感描述
    "不掉色 不褪色 不脱色 保色 防过敏 防敏 抗敏 不过敏 水洗不掉色 洗澡不用摘 睡觉不用摘 防水 防汗 耐磨 耐刮 不氧化 不生锈 不掉钻 不勾头发 不挂衣服 不夹肉 "
    # 营销话术
    "两位数 几十块 性价比 平替 复购 爆款 新款 热销 限时 优惠 活动价 直播间 下单 现货 福利 秒杀 宠粉 闭眼入 不踩雷 送闺密 送女友 送妈妈 自戴 礼物 生日礼物 纪念日 "
    # 颜色
    "奶白色 银色 金色 玫瑰金 锆石白 珍珠白 墨绿 湖蓝 樱花粉 奶茶色 黑色 白色 透明 酒红 宝蓝 香槟 紫罗兰 雾蓝 烟灰"
    # 穿戴方式
    "佩戴 戴上 摘下来 扣上 系上 别上 插上 卡上 套上 穿上 挂上 "
    # 穿搭场景
    "白衬衫 小黑裙 碎花裙 吊带裙 毛衣 卫衣 西装 大衣 风衣 旗袍 汉服 古装 婚纱 礼服 通勤 上班 约会 逛街 派对 晚宴 婚礼 日常 出街"
    # 常见口播句式
    "姐妹 女生 女人 女孩 仙女 小姐姐 太美了 特别好看 超好看 谁戴谁知道 真的绝 一眼就爱上 戴上就不想摘 回头率 精致感 氛围感 仪式感 小心机 点睛之笔"
)

# 风险提醒词（标黄）
RISK_WORDS = ["发黑","变黑","掉色","褪色","变色","氧化","生锈","褪镀","掉钻","脱胶","断裂",
              "过敏","红肿","发痒","沐浴露","洗发水","洗洁精","香皂","肥皂","热水",
              "洗澡","睡觉","游泳","运动","出汗","沾水","碰水","洗手","洗碗",
              "不用摘","不摘","不拿下来"]

@st.cache_resource
def load_whisper():
    return whisper.load_model('tiny')  # HF免费版用tiny，本地用small

whip = load_whisper()

# ===== Whisper转录后LLM校正 =====
def fix_transcription(raw_text):
    """用LLM根据首饰上下文修正Whisper的语音识别错误"""
    prompt = f"""你是首饰珠宝直播语音识别校对专家。下面是一段Whisper转录的首饰直播口播，因主播有口音导致识别错误。请根据上下文和首饰领域常识修正所有错误。

【必须修正的常见错误】
- 吊死/吊死 → 掉色
- 灵荡/零当/零铛 → 铃铛
- 黄瓜/黄光/惶光 → 皇冠
- 木鱼鹿/木鱼路 → 沐浴露
- 纽光/牛光/扭光 → 流光
- 起的吊脚/洗的吊脚 → 洗涤剂
- 发黑 → 发黑（正确，保持）
- 煮/主 → 洗（洗澡场景）
- 高温水煮 → 高温水洗
- 脚脸/角脸 → 脚链
- 手脸 → 手链
- 耳盯 → 耳钉
- 向脸 → 项链
- 借子 → 戒指
- 小公主/小工主/小公举 → 小公主
- 女王/女皇 → 女王
- 宠爱/重爱 → 宠爱
- 独立/读力 → 独立
- 强大/墙大 → 强大

【规则】
1. 只修正明显的语音识别错误，不通顺处保持原意
2. 修正后必须符合首饰/珠宝/配饰领域语境
3. 不要添加原文没有的信息
4. 保留所有数字、标点
5. 返回格式：{{"corrected": "修正后的完整文字"}}，只返回JSON

原文：{raw_text}"""
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
    return raw_text  # 失败返回原文

def llm_review(text, platform):
    prompt = f"""你是{platform}电商合规审核。判断违规，注意ASR可能有错别字。
规则：客观评价OK("最受欢迎")，绝对承诺违规("绝对不掉色")，迷信词必违规，材质承诺(不掉色/防敏/水洗不摘)在快手必违规。
返回JSON：{{"has_violation":true/false,"violations":[{{"text":"片段","reason":"理由","severity":"高/中/低","fix":"建议"}}],"summary":"总结"}}"""
    try:
        r = requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"},
            json={"model":"doubao-seed-1-6-250615","messages":[
                {"role":"system","content":prompt},
                {"role":"user","content":f"分析：{text}"}
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
    bad_words = flatten(st.session_state.douyin_dict if platform=="抖音" else st.session_state.kuaishou_dict)
    
    # Whisper转录（首饰领域词汇引导+词级时间戳）
    result = whip.transcribe(video_path, language='zh', fp16=False, 
                             initial_prompt=JEWELRY_VOCAB, word_timestamps=True)
    raw_text = result['text']
    segments = result.get('segments', [])
    
    # LLM后校正：修正口音导致的识别错误
    text = fix_transcription(raw_text)
    
    # 关键词扫描（使用词级时间戳，精准到秒）
    kw_hits = []
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
    
    # 风险词扫描（同样使用词级时间戳）
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
    
    # 判定
    llm_v = llm and llm.get('has_violation', False)
    has_ocr = any(any(bw in o.get('text','') for bw in bad_words) for o in ocr)
    status = "违规" if (kw_hits or llm_v or has_ocr) else "OK"
    
    return {"file":fname,"status":status,"elapsed":round(time.time()-t0,1),
            "text":text,"raw_text":raw_text,"kw_hits":kw_hits,"risk_hits":risk_hits,"llm":llm,"ocr":ocr}

# Sidebar
with st.sidebar:
    platform = st.selectbox("🎯 平台",["抖音","快手"])
    st.divider()
    st.markdown("### 📝 自定义词库")
    tab1,tab2 = st.tabs(["抖音词库","快手词库"])
    
    def dict_editor(tab, store):
        with tab:
            nc = st.text_input("新分类",key=f"cat_{store}")
            nw = st.text_input("新词(,分隔)",key=f"w_{store}")
            if nc and nw and st.button("添加",key=f"add_{store}"):
                for w in [x.strip() for x in nw.split(",") if x.strip()]:
                    if nc not in st.session_state[store]: st.session_state[store][nc]=[]
                    if w not in st.session_state[store][nc]: st.session_state[store][nc].append(w)
                st.rerun()
            for cat,words in st.session_state[store].items():
                with st.expander(f"{cat} ({len(words)}词)"):
                    st.caption(", ".join(words))
    
    dict_editor(tab1,'douyin_dict')
    dict_editor(tab2,'kuaishou_dict')
    total = sum(len(v) for v in st.session_state.douyin_dict.values()) + sum(len(v) for v in st.session_state.kuaishou_dict.values())
    st.metric("词库总计",f"{total}词")
    if st.button("🔄 恢复默认",use_container_width=True):
        st.session_state.douyin_dict=default_douyin()
        st.session_state.kuaishou_dict=default_kuaishou()
        st.rerun()

# Main
uploaded = st.file_uploader("📤 拖拽视频（mp4/mov/avi）",type=["mp4","mov","avi"],accept_multiple_files=True)

if uploaded and st.button("⚡ 开始扫描",type="primary",use_container_width=True):
    progress = st.progress(0)
    status_text = st.empty()
    results_area = st.container()
    
    bad_count = 0
    risk_count = 0
    
    for idx, uf in enumerate(uploaded):
        status_text.info(f"⚡ 扫描中 ({idx+1}/{len(uploaded)}) {uf.name} ...")
        
        tmp = tempfile.mktemp(suffix=os.path.splitext(uf.name)[1])
        with open(tmp,'wb') as f: f.write(uf.read())
        r = scan(tmp, uf.name, platform)
        os.remove(tmp)
        
        if r['status'] != 'OK': bad_count += 1
        elif r.get('risk_hits'): risk_count += 1
        
        # 边扫边出结果
        with results_area:
            if r['status'] == 'OK' and not r.get('risk_hits'):
                with st.expander(f"✅ {r['file']} — 安全 | {r['elapsed']}s"):
                    st.caption(f"口播: {r['text'][:200]}")
            elif r['status'] == 'OK' and r.get('risk_hits'):
                with st.expander(f"⚠️ {r['file']} — 有风险提示 | {r['elapsed']}s", expanded=True):
                    st.warning(f"🟡 风险提醒 ({len(r['risk_hits'])}处):")
                    for h in r['risk_hits']: st.write(f"  • `{h['word']}` @ {h['time']}")
                    if r['kw_hits']:
                        st.error(f"🔍 关键词 ({len(r['kw_hits'])}处):")
                        for h in r['kw_hits']: st.write(f"  • `{h['word']}` @ {h['time']}")
                    if r['llm']:
                        llm = r['llm']
                        if llm.get('has_violation'):
                            st.error(f"🧠 LLM: {llm.get('summary','')}")
                            for v in llm.get('violations',[]):
                                s = {"高":"🔴","中":"🟠","低":"🟡"}.get(v.get('severity',''),'')
                                st.write(f"  {s} `{v['text']}` — {v.get('reason','')}")
                                if v.get('fix'): st.caption(f"    💡 {v['fix']}")
                        else:
                            st.success("🧠 LLM: 语境正常")
                    if r['ocr']:
                        for o in r['ocr']: st.caption(f"📷 @{o['time']}s: {o['text'][:120]}")
                    st.caption(f"📝 转录: {r['text'][:300]}")
            else:
                with st.expander(f"❌ {r['file']} — 违规 | {r['elapsed']}s", expanded=True):
                    if r['kw_hits']:
                        st.error(f"🔍 关键词 ({len(r['kw_hits'])}处):")
                        for h in r['kw_hits']: st.write(f"  • `{h['word']}` @ {h['time']}")
                    if r.get('risk_hits'):
                        st.warning(f"🟡 风险提醒 ({len(r['risk_hits'])}处):")
                        for h in r['risk_hits']: st.write(f"  • `{h['word']}` @ {h['time']}")
                    if r['llm']:
                        llm = r['llm']
                        if llm.get('has_violation'):
                            st.error(f"🧠 LLM: {llm.get('summary','')}")
                            for v in llm.get('violations',[]):
                                s = {"高":"🔴","中":"🟠","低":"🟡"}.get(v.get('severity',''),'')
                                st.write(f"  {s} `{v['text']}` — {v.get('reason','')}")
                                if v.get('fix'): st.caption(f"    💡 {v['fix']}")
                        else:
                            st.success("🧠 LLM: 语境正常")
                    if r['ocr']:
                        for o in r['ocr']: st.caption(f"📷 @{o['time']}s: {o['text'][:120]}")
                    st.caption(f"📝 转录: {r['text'][:300]}")
        
        progress.progress((idx+1)/len(uploaded))
    
    progress.empty()
    status_text.empty()
    
    # 汇总
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("总计",len(uploaded))
    c2.metric("合格 ✅",len(uploaded)-bad_count-risk_count)
    c3.metric("风险 ⚠️",risk_count)
    c4.metric("违规 ❌",bad_count)

st.divider()
st.caption("HH v8 | Whisper+LLM后校正 | 词级时间戳 | 首饰专域 | 流式处理")

# ===== 智能剪辑 =====
st.divider()
st.header("✂️ 智能剪辑")
st.caption("勾选要删除的句子 → 一键生成干净视频")

edit_file = st.file_uploader("上传要剪辑的视频", type=["mp4","mov","avi"], key="editor_upload")

if edit_file:
    # 存到临时文件
    tmp_vid = tempfile.mktemp(suffix=os.path.splitext(edit_file.name)[1])
    with open(tmp_vid,'wb') as f: f.write(edit_file.read())
    
    if st.button("📝 识别口播", type="primary"):
        with st.spinner("Whisper转录中..."):
            result = whip.transcribe(tmp_vid, language='zh', fp16=False, initial_prompt=JEWELRY_VOCAB)
            segments = result.get('segments', [])
            text = result['text']
            
            st.session_state.edit_segments = segments
            st.session_state.edit_text = text
            st.session_state.edit_video = tmp_vid
            st.session_state.edit_fname = edit_file.name
            
            st.success(f"识别完成！{len(segments)} 个句子")
    
    if 'edit_segments' in st.session_state and st.session_state.edit_segments:
        segs = st.session_state.edit_segments
        
        # 违禁词检测并预选中
        bad_words = flatten(st.session_state.douyin_dict)
        risk_words = RISK_WORDS
        
        st.write("### 勾选要删除的句子：")
        
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
                label = f"🔴 {label}"
            elif has_risk:
                label = f"🟡 {label}"
            
            default_check = has_bad  # 默认勾选违规句子
            
            if st.checkbox(label, value=default_check, key=f"seg_{idx}"):
                cuts.append((start, end))
        
        if cuts and st.button("🔪 一键删除并生成视频", type="primary", use_container_width=True):
            with st.spinner("正在剪辑..."):
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
                    st.error("不能删除所有内容！")
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
                            st.download_button("⬇️ 下载剪辑后视频", f, 
                                file_name=f"clean_{st.session_state.edit_fname}",
                                mime="video/mp4")
                        st.success("剪辑完成！")
                    else:
                        st.error("剪辑失败，尝试用 re-encode 方式...")
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
                                st.download_button("⬇️ 下载剪辑后视频", f,
                                    file_name=f"clean_{st.session_state.edit_fname}",
                                    mime="video/mp4")
                            st.success("剪辑完成！")
                    
                    os.remove(concat_file)
        
        if st.button("🔄 重新识别"):
            for k in ['edit_segments','edit_text','edit_video','edit_fname']:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
