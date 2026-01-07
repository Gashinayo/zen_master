import streamlit as st
import pandas as pd
import requests
import re
import os
from datetime import datetime
from urllib.parse import urlparse, quote

# [1. 초기화 공정: AttributeError 및 세션 방어]
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = "이현우"

# [2. 환경 설정 및 Secrets 로드]
def get_config():
    return {
        "COUPANG": st.secrets.get("COUPANG_PARTNERS_ID", "AF1234567"),
        "NAVER_BLOG": st.secrets.get("NAVER_AD_ID", "yhw923"),
        "LINKPRICE": st.secrets.get("LINKPRICE_AFF_ID", "A100701775"),
        "MIN_WAGE": 10030, # 2026년 최저임금 기준
        "ST_COLS": ['날짜', '유저ID', '쇼핑몰', '상품명', '결제금액', '아낀금액', '똑똑지수', '기다림비용', '암호', '암호힌트']
    }

CONFIG = get_config()
st.set_page_config(page_title="Zen Master v7.5", layout="wide")
LOG_FILE = 'zen_master_v75_db.csv'

# [3. 데이터 및 인증 엔진]
def load_data():
    if not os.path.exists(LOG_FILE): return pd.DataFrame(columns=CONFIG["ST_COLS"])
    return pd.read_csv(LOG_FILE, on_bad_lines='skip', encoding='utf-8-sig')

def verify_user(uid, upw):
    df = load_data()
    user_data = df[df['유저ID'] == uid]
    if user_data.empty: return "NEW", pd.DataFrame(columns=CONFIG["ST_COLS"])
    if upw != "" and str(user_data.iloc[0]['암호']) == upw: return "SUCCESS", user_data
    return "FAIL", user_data

def save_all(df):
    df.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')
    st.rerun()

# [4. 사이드바: 상태 LED 및 유연한 가치 설정]
with st.sidebar:
    st.title("💎 Zen Master")
    uid = st.text_input("사용자 ID", value=st.session_state.user_id)
    upw = st.text_input("접근 암호", type="password")
    
    status, user_df = verify_user(uid, upw)
    
    if status == "SUCCESS":
        total_s = pd.to_numeric(user_df['아낀금액'], errors='coerce').sum()
        st.success(f"🟢 **{uid}** 님 접속 중")
        st.metric("누적 절약액", f"{int(total_s):,}원")
    elif status == "FAIL" and upw != "":
        st.error("🔴 암호가 일치하지 않습니다.")
    else:
        st.warning("🟡 로그인이 필요합니다.")

    st.divider()
    # [피드백 반영] 최저 하한선 0원 설정
    time_val = st.slider("나의 시간 가치 (원/시간)", 0, 200000, CONFIG["MIN_WAGE"], 500)
    wait_cost = int((15/60) * time_val + 3000)

# [5. 메인 UI: 세 개의 탭으로 구성]
tab1, tab2, tab3 = st.tabs(["🔍 퀀트 분석", "📊 Zen 대시보드", "📖 데이터 관리"])

with tab1:
    # [피드백 반영] 검색 입력란 복구
    with st.container(border=True):
        url_in = st.text_input("상품 URL (ID 자동추출)")
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
        st.subheader("📊 분석 리포트")
        for i, res in enumerate(st.session_state.search_results):
            with st.container(border=True):
                adj = st.number_input(f"최종 정산(±원) - 후보 {i+1}", step=1000, key=f"adj_{i}")
                final_p = res['p'] + adj
                diff = final_p - price_in
                net_benefit = (price_in - final_p) - wait_cost
                
                # [피드백 반영] 이모지 차액 표시
                icon = "🔵" if diff <= 0 else "🔴"
                st.markdown(f"#### 후보 {i+1}: **{final_p:,}원** ({res['m']}) {icon} {diff:+,}원")
                st.caption(f"📝 {res['t']}") # 상세 상품명 노출
                
                if net_benefit > 0:
                    st.success(f"🚀 **추천: 이 대안으로 전환하세요!** ({net_benefit:,}원 순이익)")
                else:
                    st.warning(f"🛒 **보류: 원래 상품을 유지하세요.** (기다림 비용 {wait_cost:,}원 제외 시 손해)")
                
                col_l, col_r = st.columns([2, 1])
                col_l.link_button("🌐 상품 페이지로 이동", res['l'], use_container_width=True)
                
                if status == "NEW":
                    with st.expander("✨ 신규 등록을 위해 암호 힌트를 설정하세요"):
                        hint_in = st.text_input("암호 힌트", key=f"h_{i}")
                        if st.button("✅ 계정 생성 및 결과 기록", key=f"reg_{i}", use_container_width=True):
                            if upw != "" and hint_in != "":
                                new_row = [[datetime.now().strftime('%Y-%m-%d %H:%M'), uid, res['m'], res['t'], final_p, price_in-final_p, round((price_in-final_p)/price_in*100,1), wait_cost, upw, hint_in]]
                                pd.DataFrame(new_row, columns=CONFIG["ST_COLS"]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False, encoding='utf-8-sig')
                                st.balloons(); st.rerun()
                elif status == "SUCCESS":
                    if st.button(f"✅ {uid} 님 기록 저장", key=f"save_{i}", use_container_width=True):
                        new_row = [[datetime.now().strftime('%Y-%m-%d %H:%M'), uid, res['m'], res['t'], final_p, price_in-final_p, round((price_in-final_p)/price_in*100,1), wait_cost, upw, user_df.iloc[0]['암호힌트']]]
                        pd.DataFrame(new_row, columns=CONFIG["ST_COLS"]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False, encoding='utf-8-sig')
                        st.balloons(); st.rerun()

with tab2:
    if status == "SUCCESS" and not user_df.empty:
        st.subheader("📊 통계적 통찰")
        # 요일별/누적 성장 그래프 로직 (v6.9 동일)
        user_df['날짜'] = pd.to_datetime(user_df['날짜'])
        st.plotly_chart(px.line(user_df.sort_values('날짜'), x='날짜', y=pd.to_numeric(user_df['아낀금액']).cumsum(), title='📈 자산 방어 성장 곡선'), use_container_width=True)
    else: st.info("데이터가 충분하지 않습니다.")

with tab3:
    if status == "SUCCESS" and not user_df.empty:
        st.subheader("⚙️ 데이터 교정 및 관리")
        # [피드백 반영] 데이터 수정 및 삭제 도구
        with st.expander("📝 오타 정정하기"):
            edit_df = user_df.copy()
            edit_df['식별자'] = edit_df['날짜'] + " | " + edit_df['상품명']
            target = st.selectbox("수정할 기록 선택", options=edit_df.index, format_func=lambda x: edit_df.loc[x, '식별자'])
            if target is not None:
                new_name = st.text_input("상품명 정정", value=edit_df.loc[target, '상품명'])
                new_saved = st.number_input("절약액 정정", value=int(edit_df.loc[target, '아낀금액']))
                if st.button("💾 수정 완료"):
                    all_data = load_data()
                    all_data.at[target, '상품명'] = new_name
                    all_data.at[target, '아낀금액'] = new_saved
                    save_all(all_data)
        
        if st.button("🚨 선택 항목 삭제", type="primary"):
            # multiselect를 통한 삭제 로직 추가 가능
            pass
        st.dataframe(user_df.sort_values(by='날짜', ascending=False), use_container_width=True)
