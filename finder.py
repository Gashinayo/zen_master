import streamlit as st
import pandas as pd
import requests
import re
import os
from datetime import datetime
from urllib.parse import urlparse, quote

# [1. 초기화 및 세션 상태 관리]
if 'search_results' not in st.session_state: st.session_state.search_results = None
if 'user_id' not in st.session_state: st.session_state.user_id = "이현우"

def get_config():
    # Streamlit Cloud의 Secrets에서 보안 정보를 호출합니다.
    return {
        "COUPANG": st.secrets.get("COUPANG_PARTNERS_ID", "AF1234567"),
        "NAVER_BLOG": st.secrets.get("NAVER_AD_ID", "yhw923"),
        "LINKPRICE": st.secrets.get("LINKPRICE_AFF_ID", "A100701775"),
        "MIN_WAGE": 10030,
        "ST_COLS": ['날짜', '유저ID', '쇼핑몰', '상품명', '결제금액', '아낀금액', '똑똑지수', '기다림비용', '암호', '암호힌트']
    }

CONFIG = get_config()
st.set_page_config(page_title="Zen Master v7.4", layout="wide")
LOG_FILE = 'zen_master_v74_db.csv'

# [2. 데이터 엔진: 로드, 보안, 수정, 삭제]
def load_data():
    if not os.path.exists(LOG_FILE): return pd.DataFrame(columns=CONFIG["ST_COLS"])
    return pd.read_csv(LOG_FILE, on_bad_lines='skip', encoding='utf-8-sig')

def verify_user(uid, upw):
    df = load_data()
    user_data = df[df['유저ID'] == uid]
    if user_data.empty: return "NEW", pd.DataFrame(columns=CONFIG["ST_COLS"])
    if upw != "" and str(user_data.iloc[0]['암호']) == upw: return "SUCCESS", user_data
    return "FAIL", user_data

def save_all_data(df):
    df.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')
    st.rerun()

# [3. 사이드바: 0원부터 조절하는 가치와 티어]
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
    
    st.divider()
    time_val = st.slider("나의 시간 가치 (원/시간)", 0, 200000, CONFIG["MIN_WAGE"], 500)
    wait_cost = int((15/60) * time_val + 3000)

# [4. 메인 UI 분석 및 일기장 편집]
tab1, tab2 = st.tabs(["🔍 퀀트 분석", "📖 절약 일기장 & 데이터 교정"])

with tab1:
    # ... (기존 v7.2와 동일한 1+3 분석 및 기록 로직 위치)
    st.info("여기에 기존의 분석 및 기록 로직이 들어갑니다.")

with tab2:
    if status == "SUCCESS" and not user_df.empty:
        st.subheader(f"📖 {uid} 님의 데이터 정정 센터")
        
        # [신규] 데이터 수정(Edit) 기능
        with st.expander("📝 기록 수정하기 (오타 정정)"):
            edit_df = user_df.copy()
            edit_df['식별자'] = edit_df['날짜'] + " | " + edit_df['상품명']
            target_idx = st.selectbox("수정할 기록을 선택하세요", options=edit_df.index, format_func=lambda x: edit_df.loc[x, '식별자'])
            
            if target_idx is not None:
                row = edit_df.loc[target_idx]
                col_e1, col_e2 = st.columns(2)
                new_name = col_e1.text_input("상품명 수정", value=row['상품명'])
                new_price = col_e2.number_input("결제금액 수정", value=int(row['결제금액']), step=1000)
                new_saved = col_e1.number_input("절약액 수정", value=int(row['아낀금액']), step=1000)
                
                if st.button("💾 수정 사항 적용"):
                    all_df = load_data()
                    all_df.at[target_idx, '상품명'] = new_name
                    all_df.at[target_idx, '결제금액'] = new_price
                    all_df.at[target_idx, '아낀금액'] = new_saved
                    # 똑똑지수 재계산
                    all_df.at[target_idx, '똑똑지수'] = round((new_saved / (new_price + new_saved)) * 100, 1)
                    save_all_data(all_df)
                    st.success("데이터가 성공적으로 정정되었습니다.")

        # [기존] 부분 삭제 기능
        with st.expander("🗑️ 기록 삭제하기"):
            selected_items = st.multiselect("삭제할 항목 선택", options=edit_df.index, format_func=lambda x: edit_df.loc[x, '식별자'])
            if st.button("🚨 선택 삭제", type="primary"):
                all_df = load_data()
                all_df = all_df.drop(selected_items)
                save_all_data(all_df)

        st.divider()
        st.dataframe(user_df.sort_values(by='날짜', ascending=False), use_container_width=True)
    else:
        st.info("데이터가 없거나 로그인이 필요합니다.")
