import streamlit as st
import pandas as pd
import requests
import re
import os
import plotly.express as px
from datetime import datetime
from urllib.parse import urlparse, quote

# [0. 설정 및 개인 가치 산정]
CONFIG = {
    "COUPANG": "AF1234567",
    "NAVER_BLOG": "yhw923",
    "LINKPRICE": "A100701775",
    "MIN_WAGE": 10030,
    "ST_COLS": ['날짜', '유저ID', '쇼핑몰', '상품명', '결제금액', '아낀금액', '똑똑지수', '기다림비용', '암호', '암호힌트']
}

st.set_page_config(page_title="Zen Master v6.9", layout="wide")
LOG_FILE = 'zen_master_v69_db.csv'

if 'search_results' not in st.session_state: st.session_state.search_results = None

# [1. Zen 티어 및 요일 엔진]
def get_zen_tier(savings):
    if savings >= 500000: return "🌈 Zen 4: 깨달음을 얻은 마스터", "rainbow" # [해결] cyan 대신 rainbow 사용
    elif savings >= 150000: return "👁️ Zen 3: 통찰의 지혜", "violet"
    elif savings >= 50000: return "🌊 Zen 2: 평온한 수행자", "blue"
    else: return "🧘 Zen 1: 명상하는 초심자", "gray"

# [2. 인증 및 보안 센터]
def verify_user(uid, upw):
    if not os.path.exists(LOG_FILE): return "NEW", pd.DataFrame(columns=CONFIG["ST_COLS"])
    df = pd.read_csv(LOG_FILE, on_bad_lines='skip', encoding='utf-8-sig')
    user_data = df[df['유저ID'] == uid]
    if user_data.empty: return "NEW", pd.DataFrame(columns=CONFIG["ST_COLS"])
    if upw != "" and str(user_data.iloc[0]['암호']) == upw: return "SUCCESS", user_data
    return "FAIL", user_data

# [3. 사이드바: 통찰의 시작]
with st.sidebar:
    st.title("💎 Zen Master")
    uid = st.text_input("사용자 ID", value="이현우") #
    upw = st.text_input("접근 암호", type="password")
    
    status, user_df = verify_user(uid, upw)
    
    if status == "SUCCESS":
        total_s = pd.to_numeric(user_df['아낀금액'], errors='coerce').sum()
        tier_name, t_color = get_zen_tier(total_s)
        st.success(f"🟢 **{uid}** 님 접속 중")
        st.markdown(f"**현재 경지: :{t_color}[{tier_name}]**") #
        st.metric("총 누적 절약액", f"{int(total_s):,}원")
    elif status == "FAIL" and upw != "":
        st.error("🔴 암호 불일치")
    else:
        st.warning("🟡 로그인 대기 중")

    st.divider()
    time_val = st.slider("나의 시간 가치 (원/시간)", 0, 150000, CONFIG["MIN_WAGE"], 500) # 하한 0 설정
    wait_cost = int((15/60) * time_val + 3000)

# [4. 메인 분석 및 통계 탭]
tab1, tab2 = st.tabs(["🔍 퀀트 분석", "📊 Zen 통찰 대시보드"])

with tab1:
    with st.container(border=True):
        url_in = st.text_input("상품 URL (ID 자동추출 지원)")
        m = re.search(r'([A-Z]+[0-9]+|[0-9]+[A-Z]+)[A-Z0-9]*', url_in.upper())
        c1, c2 = st.columns(2)
        name_in = c1.text_input("상품 식별명", value=m.group() if m else "")
        price_in = c2.number_input("현재 탐지 가격(원)", min_value=0, step=1000)

    if st.button("🚀 통찰 프로세스 시작", use_container_width=True):
        if name_in and price_in:
            with st.spinner('데이터의 흐름을 명상 중...'):
                cid, csec = st.secrets["NAVER_CLIENT_ID"], st.secrets["NAVER_CLIENT_SECRET"]
                res = requests.get(f"https://openapi.naver.com/v1/search/shop.json?query={name_in}&display=15",
                                   headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec})
                if res.status_code == 200:
                    items = res.json().get('items', [])
                    valid = []
                    for i in items:
                        lp = int(i['lprice'])
                        if lp >= price_in * 0.3:
                            mall = "네이버" if any(x in i['link'] for x in ["smartstore", "brand.naver"]) else i['mallName']
                            valid.append({'p': lp, 't': i['title'].replace("<b>","").replace("</b>",""), 'l': i['link'], 'm': mall})
                    st.session_state.search_results = sorted(list({v['p']: v for v in valid}.values()), key=lambda x: x['p'])[:3]

    if st.session_state.search_results:
        for i, res in enumerate(st.session_state.search_results):
            with st.container(border=True):
                adj = st.number_input(f"최종 정산(±원) - 후보 {i+1}", step=1000, key=f"adj_{i}")
                final_p = res['p'] + adj
                diff = final_p - price_in
                net_benefit = (price_in - final_p) - wait_cost
                
                icon = "🔵" if diff <= 0 else "🔴"
                st.markdown(f"#### 후보 {i+1}: **{final_p:,}원** ({res['m']}) {icon} {diff:+,}원")
                st.caption(f"📝 {res['t']}")
                
                if net_benefit > 0:
                    st.success(f"🚀 **추천: 이 대안으로 전환하세요!** ({net_benefit:,}원 순이익)")
                else:
                    st.warning(f"🛒 **보류: 원래 상품을 유지하세요.** (기다림 비용 {wait_cost:,}원이 더 큼)")
                
                col_l, col_r = st.columns([2, 1])
                col_l.link_button("🌐 상품 페이지로 이동", res['l'], use_container_width=True)
                
                if status == "NEW":
                    with st.expander("✨ 첫 기록을 위한 암호 설정"):
                        hint_in = st.text_input("암호 힌트", key=f"h_{i}")
                        if st.button("✅ 계정 생성 및 저장", key=f"reg_{i}", use_container_width=True):
                            if upw != "" and hint_in != "":
                                new_row = [[datetime.now().strftime('%Y-%m-%d %H:%M'), uid, res['m'], res['t'], final_p, price_in-final_p, round((price_in-final_p)/price_in*100,1), wait_cost, upw, hint_in]]
                                pd.DataFrame(new_row, columns=CONFIG["ST_COLS"]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False, encoding='utf-8-sig')
                                st.balloons(); st.rerun()
                elif status == "SUCCESS":
                    if st.button(f"✅ {uid} 님 수행 기록 저장", key=f"save_{i}", use_container_width=True):
                        new_row = [[datetime.now().strftime('%Y-%m-%d %H:%M'), uid, res['m'], res['t'], final_p, price_in-final_p, round((price_in-final_p)/price_in*100,1), wait_cost, upw, user_df.iloc[0]['암호힌트']]]
                        pd.DataFrame(new_row, columns=CONFIG["ST_COLS"]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False, encoding='utf-8-sig')
                        st.balloons(); st.rerun()

with tab2:
    if status == "SUCCESS" and not user_df.empty:
        st.subheader(f"📊 {uid} 님의 Zen 통찰 대시보드")
        
        user_df['날짜'] = pd.to_datetime(user_df['날짜'])
        # [신규] 요일별 분석 로직
        user_df['요일'] = user_df['날짜'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # 1. 누적 성장 곡선
        st.plotly_chart(px.line(user_df.sort_values('날짜'), x='날짜', y=pd.to_numeric(user_df['아낀금액']).cumsum(), title='📈 자산 방어 성장 곡선'), use_container_width=True)

        c1, c2 = st.columns(2)
        # 2. [신규] 요일별 평균 똑똑지수 (통계적 통찰)
        with c1:
            day_stats = user_df.groupby('요일')['똑똑지수'].mean().reindex(day_order).reset_index()
            st.plotly_chart(px.bar(day_stats, x='요일', y='똑똑지수', title='📅 요일별 평균 쇼핑 효율(똑똑지수)', color='똑똑지수'), use_container_width=True)
        
        # 3. 쇼핑몰 기여도
        with c2:
            st.plotly_chart(px.pie(user_df, values='아낀금액', names='쇼핑몰', title='🏬 쇼핑몰별 절약 기여도', hole=0.4), use_container_width=True)

        st.divider()
        st.dataframe(user_df.sort_values(by='날짜', ascending=False), use_container_width=True)
    else: st.info("수행 기록을 남기면 통찰이 활성화됩니다.")