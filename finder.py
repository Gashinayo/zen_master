import streamlit as st
import pandas as pd
import requests
import re
import os
import plotly.express as px
from datetime import datetime
from urllib.parse import urlparse, quote

# [0. Secrets 기반 설정 로드]
def get_config():
    return {
        "COUPANG": st.secrets.get("COUPANG_PARTNERS_ID", "NOT_SET"),
        "NAVER_BLOG": st.secrets.get("NAVER_AD_ID", "NOT_SET"),
        "LINKPRICE": st.secrets.get("LINKPRICE_AFF_ID", "NOT_SET"),
        "MIN_WAGE": 10030, # 2026년 최저임금 기준
        "ST_COLS": ['날짜', '유저ID', '쇼핑몰', '상품명', '결제금액', '아낀금액', '똑똑지수', '기다림비용', '암호', '암호힌트']
    }

CONFIG = get_config()
st.set_page_config(page_title="Zen Master v7.0", layout="wide")
LOG_FILE = 'zen_master_cloud_db.csv'

# [1. 인증 및 티어 엔진]
def get_zen_tier(savings):
    if savings >= 500000: return "🌈 Zen 4: 깨달음을 얻은 마스터", "rainbow"
    elif savings >= 150000: return "👁️ Zen 3: 통찰의 지혜", "violet"
    elif savings >= 50000: return "🌊 Zen 2: 평온한 수행자", "blue"
    else: return "🧘 Zen 1: 명상하는 초심자", "gray"

def verify_user(uid, upw):
    if not os.path.exists(LOG_FILE): return "NEW", pd.DataFrame(columns=CONFIG["ST_COLS"])
    df = pd.read_csv(LOG_FILE, on_bad_lines='skip', encoding='utf-8-sig')
    user_data = df[df['유저ID'] == uid]
    if user_data.empty: return "NEW", pd.DataFrame(columns=CONFIG["ST_COLS"])
    # 암호 일치 여부 확인
    if upw != "" and str(user_data.iloc[0]['암호']) == upw: return "SUCCESS", user_data
    return "FAIL", user_data

# [2. 사이드바: 0원부터 시작하는 시간 가치 및 상태 LED]
with st.sidebar:
    st.title("💎 Zen Master")
    uid = st.text_input("사용자 ID", value="이현우")
    upw = st.text_input("접근 암호", type="password")
    
    status, user_df = verify_user(uid, upw)
    
    # [피드백 반영] 로그인 상태 명확화
    if status == "SUCCESS":
        total_s = pd.to_numeric(user_df['아낀금액'], errors='coerce').sum()
        tier_name, t_color = get_zen_tier(total_s)
        st.success(f"🟢 **{uid}** 님 접속 중")
        st.markdown(f"현재 경지: :{t_color}[{tier_name}]")
        st.metric("누적 절약액", f"{int(total_s):,}원")
    elif status == "FAIL" and upw != "":
        st.error("🔴 암호가 틀립니다.")
    else:
        st.warning("🟡 로그인이 필요합니다.")

    st.divider()
    # [피드백 반영] 하한선 0원 시간 가치 슬라이더
    time_val = st.slider("나의 시간 가치 (원/시간)", 0, 200000, CONFIG["MIN_WAGE"], 500)
    wait_cost = int((15/60) * time_val + 3000)

# [3. 메인 분석 엔진]
tab1, tab2 = st.tabs(["🔍 퀀트 분석", "📊 Zen 대시보드"])

with tab1:
    with st.container(border=True):
        url_in = st.text_input("상품 URL (G마켓/옥션/쿠팡 등)")
        # 모델명 자동 감지
        m = re.search(r'([A-Z]+[0-9]+|[0-9]+[A-Z]+)[A-Z0-9]*', url_in.upper())
        c1, c2 = st.columns(2)
        name_in = c1.text_input("상품 식별명", value=m.group() if m else "")
        price_in = c2.number_input("현재 탐지 가격(원)", min_value=0, step=1000)

    if st.button("🚀 통찰 프로세스 시작", use_container_width=True):
        if name_in and price_in:
            with st.spinner('시장 데이터를 명상 중...'):
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
                
                # [피드백 반영] 이모지 차액 표시
                icon = "🔵" if diff <= 0 else "🔴"
                st.markdown(f"#### 후보 {i+1}: **{final_p:,}원** ({res['m']}) {icon} {diff:+,}원")
                st.caption(f"📝 {res['t']}") # [피드백 반영] 상세 상품명 작게 표기
                
                if net_benefit > 0:
                    st.success(f"🚀 **추천: 이 대안으로 구매하세요!** ({net_benefit:,}원 순이익)")
                else:
                    st.warning(f"🛒 **보류: 원래 상품을 유지하세요.** (기다림 비용 {wait_cost:,}원 제외 시 손해)")
                
                col_l, col_r = st.columns([2, 1])
                col_l.link_button("🌐 상품 상세 페이지로", res['l'], use_container_width=True)
                
                # [피드백 반영] 확정 버튼이 있는 힌트 입력 공정
                if status == "NEW":
                    with st.expander("✨ 신규 등록을 위해 암호 힌트를 설정하세요"):
                        hint_in = st.text_input("힌트 입력 (예: 졸업연도)", key=f"h_{i}")
                        if st.button("✅ 계정 생성 및 결과 기록", key=f"reg_{i}", use_container_width=True):
                            if upw != "" and hint_in != "":
                                new_row = [[datetime.now().strftime('%Y-%m-%d %H:%M'), uid, res['m'], res['t'], final_p, price_in-final_p, round((price_in-final_p)/price_in*100,1), wait_cost, upw, hint_in]]
                                pd.DataFrame(new_row, columns=CONFIG["ST_COLS"]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False, encoding='utf-8-sig')
                                st.balloons(); st.rerun()
                elif status == "SUCCESS":
                    if st.button(f"✅ {uid} 님 수행 기록 저장", key=f"save_{i}", use_container_width=True):
                        new_row = [[datetime.now().strftime('%Y-%m-%d %H:%M'), uid, res['m'], res['t'], final_p, price_in-final_p, round((price_in-final_p)/price_in*100,1), wait_cost, upw, user_df.iloc[0]['암호힌트']]]
                        pd.DataFrame(new_row, columns=CONFIG["ST_COLS"]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False, encoding='utf-8-sig')
                        st.balloons(); st.rerun()
