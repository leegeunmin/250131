import json
import random, os, math
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from streamlit_option_menu import option_menu
from openai import OpenAI
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium  # pip install folium streamlit-folium

load_dotenv()

# 환경변수에서 API 키 가져오기
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("🚨 ERROR: 'OPENAI_API_KEY'를 찾을 수 없습니다! 경찰서 담당자에게 문의해주시기 바랍니다.")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=api_key)

def get_ai_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 자율방범대에게 순찰 시 필요한 사항을 안내해주는 안내자입니다."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0
    )
    return response.choices[0].message.content

# CSV 파일 경로
CSV_FILE_PATH = "patrol.csv"

# CSV 파일로 데이터 읽어오기
def load_patrol_locations_from_csv(file_path):
    df = pd.read_csv(file_path)
    required_columns = ["자율방범대", "순찰장소", "address", "description", "해당관서"]
    if not all(col in df.columns for col in required_columns):
        st.error(f"CSV 파일에 필수 열({', '.join(required_columns)})이 누락되었습니다.")
        return None
    patrol_data = {}
    for _, row in df.iterrows():
        team = row["자율방범대"]
        location = row["순찰장소"]
        if team not in patrol_data:
            patrol_data[team] = {}
        patrol_data[team][location] = {
            "address": row["address"],
            "description": row["description"],
            "해당관서": row["해당관서"]
        }
    return patrol_data

patrol_locations = load_patrol_locations_from_csv(CSV_FILE_PATH)
if not patrol_locations:
    st.error("CSV 파일을 로드하는 데 실패했습니다. 파일 형식 또는 경로를 확인하세요.")
    st.stop()

# 캐싱 처리 및 timeout 증가 (10초)로 지오코딩 함수 수정
@st.cache_data(show_spinner=False)
def geocode_address(address):
    geolocator = Nominatim(user_agent="geoapi", timeout=10)
    try:
        location = geolocator.geocode(address)
        if location:
            return {"lat": location.latitude, "lon": location.longitude}
        else:
            st.warning(f"주소를 찾을 수 없습니다: {address}")
            return None
    except Exception as e:
        st.error(f"지오코딩 중 오류 발생: {e}")
        return None

# 페이지 설정
st.set_page_config(
    page_title="고양경찰서 순찰추천 챗봇",
    page_icon="🚔",
    layout="centered"
)

# 앱 실행 시 기본 테마를 light 모드로 강제 (시스템 설정 무시)
# 다크모드 토글을 최상단에 배치하여 사용자가 변경할 수 있도록 함
dark_mode_toggle = st.checkbox("다크모드 전환", value=False)

if dark_mode_toggle:
    text_color = "white"
    bg_color = "#333333"
else:
    text_color = "black"
    bg_color = "white"

# 여백 제거 CSS
st.markdown(f"""
    <style>
    body {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}
    .main .block-container {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}
    /* st_folium 주변 여백 제거 */
    .element-container, .stFolio, .stBlock {{
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }}
    /* st_folium 내부 iframe 등에 대한 여백 제거 */
    iframe {{
        display: block;
        margin: 0 auto !important;
    }}
    #map_container {{
        margin: 0px !important;
        padding: 0px !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 헤더 및 설명 (dark mode 토글 이후에 렌더링되어 색상이 올바르게 적용됨)
st.markdown(
    f"""
    <div style="text-align: center; font-size: 26px; color: {text_color}; margin-top: 20px;">
        <b>👮Goyang Patrol APP GPA👮‍♂️</b>
    </div>
    """, unsafe_allow_html=True)

st.markdown(
    f"""
    <div style="text-align: center; font-size: 17px; color: {text_color}; margin-top: 20px;">
        <b>경찰서에서 순찰이 필요한 장소를 안내드립니다.</b><br>
        고양경찰서 치안에 도움을 주시는 방범대원분들의<br>
        노고에 감사드립니다.
    </div>
    """, unsafe_allow_html=True)
st.markdown("---")

# 첫 번째 선택 박스 (더미 옵션 추가)
dummy_select = st.selectbox("순찰 추천을 시작하려면 선택하세요", options=["-", "시작하기"], index=0)

if dummy_select == "시작하기":
    st.markdown(
        """
        <div style="text-align: center; font-size: 24px; margin-top: 5px;">
            <b>✅ 소속 자율방범대를 선택하세요</b>
        </div>
        """, unsafe_allow_html=True)
    
    team_option = ["-소속 자율방범대를 선택하세요-"] + list(patrol_locations.keys())
    selected_team = st.selectbox("-", options=patrol_locations.keys(), index=0)
    
    if selected_team != "-소속 자율방범대를 선택하세요-":
        locations = list(patrol_locations[selected_team].keys())
    else:
        locations = []
        
    if selected_team != "-소속 자율방범대를 선택하세요-":
        selected_location = st.selectbox("순찰 필요지역을 선택해주세요", options=locations)

        if selected_location:
            info = patrol_locations[selected_team][selected_location]
            st.markdown(f"<h3>🗺️순찰 필요 지역</h3>", unsafe_allow_html=True)
            
            # 주소 지오코딩 (캐시 사용, timeout 10초)
            coords = geocode_address(info['address'])
            if coords:
                # 지도 타일은 기본 밝은 OpenStreetMap 사용
                tile_provider = "OpenStreetMap"
                m = folium.Map(
                    location=[coords['lat'], coords['lon']], 
                    zoom_start=16, 
                    tiles=tile_provider
                )
                # 중심 마커 없이 300m 원만 추가 (원의 중심이 geocode 결과 좌표와 일치)
                folium.Circle(
                    location=[coords['lat'], coords['lon']],
                    radius=300,
                    color='red',
                    weight=2,
                    fill=True,
                    fill_opacity=0.2
                ).add_to(m)
                # 맵을 감싸는 DIV를 만들어 마진/패딩 최소화
                st.markdown("<div id='map_container'>", unsafe_allow_html=True)
                st_folium(m, width=700, height=400)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning("주소 지오코딩 실패로 지도 표시 불가.")
            
            # 아래로 공백 없이 곧바로 이어짐
            st.markdown(f"""
                <div style="text-align: left; font-size: 30px; color: {text_color}; margin-top: 10px;">
                    <b>📌 장소명</b>
                </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
                <div style="text-align: center; font-size: 26px; color: {text_color}; margin-top: 5px;">
                    <b>{selected_location}</b>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(
                f"""
                <div style="text-align: left; font-size: 30px; color: {text_color}; margin-top: 20px;">
                    <b>🌟 경찰서 범죄 분석 결과</b>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(info['description'])
            st.markdown(
                f"""
                <div style="text-align: left; font-size: 25px; color: {text_color}; margin-top: 20px;">
                    <b>🔍 순찰 시 주요 착안사항(AI) </b>
                </div>
                """, unsafe_allow_html=True)
            st.info("💡AI 활용으로 답변에 오류가 있을 수 있습니다")
            prompt = f"""
            [지시사항]
            당신은 자율방범대에게 순찰 시 필요한 사항을 안내해주는 안내자입니다.
            {selected_location}에서 자율방범대원이 순찰할 때 필요한 사항을 상세히 설명해주세요.
            지역적 특성 {info['description']}에 입력된 내용을 바탕으로 필요사항을 설명해주세요.
            순찰 시 범죄취약지역, 방범시설 부족지역을 발견하면 경찰서 CPO에게 통보하고, 긴급한 상황이 발생하면 112에 신고해야 합니다.
            경찰서 CPO에게는 신고하는 것이 아니라 범죄취약요인을 발견하게 되면 CPO에게 "통보"하는 것입니다.
            [제한사항]
            순찰노선을 정해주지 않고 자율적으로 순찰하도록 하는 것이 중요합니다. 
            순찰 시 유의사항을 5개까지만 추천해주고 눈에 들어오기 쉽게 짧게 작성해야합니다.
            """
            response = get_ai_response(prompt)
            st.info(response)

            st.markdown(
                f"""
                <div style="text-align: left; font-size: 30px; color: {text_color}; margin-top: 20px;">
                    <b>🏚️ 취약지역 통보 </b>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="text-align: center; font-size: 16px; color: {text_color}; margin-top: 20px;">
                    <b>아래의 링크를 통해 경찰서 범죄예방진단팀에게<br>
                    취약지역을 통보해주세요.<br>
                    <a href="https://open.kakao.com/o/scgaTwdh" target="_blank" style="color: blue; font-weight: bold;">🔗 고양경찰서 범죄예방진단팀</a>
                    </b>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="text-align: left; font-size: 30px; color: {text_color}; margin-top: 20px;">
                    <b>📑 기타 참고사항 </b>
                </div>
                """, unsafe_allow_html=True)
            if "해당관서" in info:
                st.markdown(
                    f"""
                    <div style="text-align: center; font-size: 16px; color: {text_color}; margin-top: 20px;">
                        <b>순찰활동 시 {selected_team}의<br>
                        해당 지역관서는 {info['해당관서']}입니다.</b>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="text-align: left; font-size: 30px; color: {text_color}; margin-top: 20px;">
                    <b>❓문의사항 </b>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="text-align: center; font-size: 16px; color: {text_color}; margin-top: 20px;">
                    <b>순찰활동 중 취약사항 발견 시<br>
                    고양경찰서 범죄예방대응과 담당자(031-930-5343)<br>
                    연락바랍니다.</b>
                </div>
                """, unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; font-size: 16px; color: {text_color}; margin-top: 20px;">
        <b> 위 순찰추천 장소는 고양경찰서 범죄예방대응과에서 제작한 어플입니다.<br>
        AI를 활용하여 답변에 오류가 발생할 수 있습니다.</b>
    </div>
    """, unsafe_allow_html=True)
