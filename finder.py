import streamlit as st
import pandas as pd
import requests
import re
import os
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

# [0. 파트너스 설정 - 연구원님의 ID로 입력하세요]
MY_COUPANG_ID = "AF1234567" 
MY_NAVER_ID = "yhw923"

# [1. 초기 설정 및 세션 관리]
st.set_page_config(page_title="똑똑한 쇼핑 지킴이", layout="wide")
LOG_FILE = 'savings_log.csv'

if 'search_results' not in st.session_state:
    st.session_state.search_results = None

# [2. 필수 도우미 함수]
def convert_to_affiliate(url, mall_name):
    """링크를 파트너스 규격으로 치환합니다."""
    if "쿠팡" in mall_name:
        # 쿠팡 URL에서 상품 ID(숫자)를 정밀 추출합니다
        product_id_match = re.search(r'products/(\d+)', url)
        if product_id_match:
            pid = product_id_match.group(1)
            return f"https://link.coupang.com/re/AFFSDP?lptag={MY_COUPANG_ID}&subid=zen&pageKey={pid}"
        return url
    elif "네이버" in mall_name or "smartstore" in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}n_ad={MY_NAVER_ID}"
    return url

def get_optimized_top3(query, current_price):
    """배송비를 포함한 최적의 데이터 3개를 수집합니다."""
    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        min_threshold = current_price * 0.3
        
        url = f"https://openapi.naver.com/v1/search/shop.json?query={query}&display=50&sort=sim"
        headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            items = response.json().get('items', [])
            valid_items = []
            for item in items:
                price = int(item['lprice'])
                # 배송비 처리 (0 혹은 숫자로 변환)
                ship_fee = int(item.get('shipping', 0)) if item.get('shipping', '').isdigit() else 0
                
                item_url = item['link']
                mall = item.get('mallName', '일반쇼핑몰')
                if "smartstore" in item_url or "brand.naver" in item_url:
                    mall = "네이버"

                if price >= min_threshold:
                    valid_items.append({
                        'base_price': price,
                        'ship_fee': ship_fee,
                        'total_price': price + ship_fee,
                        'title': item['title'].replace("<b>", "").replace("</b>", ""),
                        'link': item_url,
                        'mall': mall
                    })
            # 총액 기준으로 중복 제거 및 정렬
            unique_items = list({v['total_price']: v for v in valid_items}.values())
            return sorted(unique_items, key=lambda x: x['total_price'])[:3]
    except Exception as e:
        st.error(f"분석 오류: {e}")
    return []

# [3. 사이드바 및 메뉴 구성]
with st.sidebar:
    st.title("💎 Zen Master")
    menu = st.radio("이동", ["🔍 지갑 지키기", "📖 절약 일기장", "📊 쇼핑 성적표"])
    st.divider()
    if st.button("🔄 검색 초기화"):
        st.session_state.search_results = None
        st.rerun()

# --- [메뉴 1: 지갑 지키기] ---
if menu == "🔍 지갑 지키기":
    st.title("🔍 실시간 최저가 탐지기")
    item_url = st.text_input("상품 주소를 입력하세요 (선택)", placeholder="https://...")
    
    suggested_name = ""
    if item_url:
        path = urlparse(item_url).path.upper()
        noise = ['HTTPS', 'WWW', 'COM', 'NAVER', 'BRAND', 'PRODUCTS', 'VIEW', 'SHOP']
        for w in noise: path = path.replace(w, '')
        model_match = re.search(r'([A-Z]+[0-9]+|[0-9]+[A-Z]+)[A-Z0-9]*', path)
        suggested_name = model_match.group() if model_match else ""

    col1, col2 = st.columns(2)
    with col1:
        item_input = st.text_input("상품명", value=suggested_name)
    with col2:
        current_price = st.number_input("현재 가격 (원)", min_value=0, step=100)

    if st.button("🔎 분석 시작"):
        if item_input and current_price > 0:
            with st.spinner('배송비 포함 최저가 분석 중...'):
                st.session_state.search_results = get_optimized_top3(item_input, current_price)
        else:
            st.warning("정보를 입력해주세요.")

    if st.session_state.search_results:
        st.subheader("📋 탐지된 최저가 후보 (배송비 포함)")
        for i, res in enumerate(st.session_state.search_results):
            with st.container(border=True):
                c_info, c_action = st.columns([3, 1])
                aff_link = convert_to_affiliate(res['link'], res['mall'])
                
                with c_info:
                    st.markdown(f"#### **[{res['mall']}] {res['total_price']:,}원** (배송비 {res['ship_fee']:,}원 포함)")
                    st.caption(res['title'])
                    extra_disc = st.number_input(f"쿠폰 등 추가 할인 (원)", min_value=0, step=1000, key=f"d_{i}")
                    
                    final_p = res['total_price'] - extra_disc
                    savings = current_price - final_p
                    score = round((savings / current_price) * 100, 1) if current_price > 0 else 0
                    st.write(f"👉 **최종 실구매가: {final_p:,}원** (똑똑 지수: {score}점)")
                
                with c_action:
                    st.link_button("🌐 이동", aff_link)
                    if st.button(f"✅ 기록", key=f"s_{i}"):
                        new_record = {
                            '날짜': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            '상품명': res['title'],
                            '결제금액': current_price,
                            '아낀금액': savings,
                            '똑똑지수': score,
                            '링크': aff_link
                        }
                        pd.DataFrame([new_record]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False, encoding='utf-8-sig')
                        st.balloons()
