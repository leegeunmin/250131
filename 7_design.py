import json
import random, os
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from streamlit_option_menu import option_menu
import pydeck as pdk
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# 환경변수에서 API 키 가져오기
api_key = os.getenv("OPENAI_API_KEY")

# 🔥 [🚨 오류 방지] API 키가 없으면 경고 메시지 출력
if not api_key:
    raise ValueError("🚨 ERROR: 환경변수에서 'OPENAI_API_KEY'를 찾을 수 없습니다! .env 파일을 확인하세요.")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=api_key)


def get_ai_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "당신은 자율방범대에게 순찰 시 필요한 사항을 안내해주는 안내자입니다."},
                  {"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0
    )
    return response.choices[0].message.content

# CSV 파일 경로
CSV_FILE_PATH = "patrol.csv"

# CSV 파일로 데이터 읽어오기
def load_patrol_locations_from_csv(file_path):
    # CSV 파일 읽기
    df = pd.read_csv(file_path)
    # 데이터 확인
    if not all(col in df.columns for col in ["자율방범대", "순찰장소", "address", "description", "해당관서"]):
        st.error("CSV 파일에 필수 열(자율방범대, 순찰장소, address, description, 해당관서)이 누락되었습니다.")
        return None
    # DataFrame에서 딕셔너리로 변환
    patrol_data = {}
    for _, row in df.iterrows():
        team = row["자율방범대"]
        location = row["순찰장소"]
        if team not in patrol_data:
            patrol_data[team] = {}
        patrol_data[team][location] = {
            "address": row["address"],
            "description": row["description"],
            "해당관서" : row["해당관서"]
        }
    return patrol_data

# 데이터 로드
patrol_locations = load_patrol_locations_from_csv(CSV_FILE_PATH)
if not patrol_locations:
    st.error("CSV 파일을 로드하는 데 실패했습니다. 파일 형식 또는 경로를 확인하세요.")
    st.stop()

# 지오코딩 함수
def geocode_address(address):
    geolocator = Nominatim(user_agent="geoapi")
    try:
        location = geolocator.geocode(address)
        if location:
            # 반환된 좌표 출력 (디버깅용)
            # st.write(f"Geocoded Address: {address}, Coordinates: {location.latitude}, {location.longitude}")
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

# 사이드바
st.sidebar.markdown("#### 고양경찰서 순찰 추천 앱")
with st.sidebar:
    menu = option_menu("", ["기동순찰대", "자율방범대", "지역관서"],
    icons=["chat-dots", "lightbulb","patch-question","telephone-forward"],
    default_index=1)


# 기본 제목 설정
st.markdown(
    """
    <div style="text-align: center; font-size: 26px; color: black; margin-top: 20px;">
        <b>👮Goyang Patrol APP GPA👮‍♂️</b>
    </div>
    """,
    unsafe_allow_html=True)

st.markdown(
    """
    <div style="text-align: center; font-size: 17px; color: black; margin-top: 20px;">
        <b>경찰서에서 순찰이 필요한 장소를 안내드립니다. </b> <br>
        고양경찰서 치안에 도움을 주시는 방범대원분들의<br>
        노고에 감사드립니다.
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("---")

# 순찰 장소 추천 인터페이스
if patrol_locations:
    st.markdown(    """
    <div style="text-align: center; font-size: 24px; color: black; margin-top: 5px;">
        <b>✅ 소속 자율방범대를 선택하세요</b>
    </div>
    """,
    unsafe_allow_html=True)
    team_option = ["-소속 자율방범대를 선택하세요-"] + list(patrol_locations.keys())
    selected_team = st.selectbox(" ", options=team_option, index=0)
    if selected_team != "-소속 자율방범대를 선택하세요-":
        locations = list(patrol_locations[selected_team].keys())
        # 순찰 장소 선택박스에 기본값 추가
        location_option = ["-순찰 장소를 선택하세요-"] + locations

    # 기본값 선택 시 아무 동작도 하지 않고 기본 화면 유지
    if selected_team == "-소속 자율방범대를 선택하세요-":
        pass
    else:
        locations = list(patrol_locations[selected_team].keys())
        location_option = ["-소속 자율방범대를 선택하세요-"] + locations
        selected_location = st.selectbox("순찰 필요지역을 선택해주세요", options=locations)

        if selected_location:
            info = patrol_locations[selected_team][selected_location]
            st.markdown(f"### 🗺️순찰 필요 지역")
            # 지오코딩 처리
            coords = geocode_address(info['address'])
            if coords:
                # 지도 데이터프레임 생성
                map_df = pd.DataFrame([{"lat": coords["lat"], "lon": coords["lon"]}])
                
                # 지도 데이터 확인 후 표시
                if not map_df.empty:
                    st.map(map_df)  # 지도 표시
                else:
                    st.warning("맵 데이터가 비어 있어 지도를 표시할 수 없습니다.")
            else:
                st.warning("주소를 지오코딩할 수 없어 지도를 표시할 수 없습니다.")
            st.markdown(
                """
                <div style="text-align: left; font-size: 30px; color: black; margin-top: 20px;">
                    <b>📌 장소명</b>
                </div>
                """,
                unsafe_allow_html=True
                )
            st.markdown(selected_location)
            st.markdown(
                """
                <div style="text-align: left; font-size: 30px; color: black; margin-top: 20px;">
                    <b>🌟 지역적 특성</b>
                </div>
                """,
                unsafe_allow_html=True
                )
            st.markdown(info['description'])
            st.markdown(
                """
                <div style="text-align: left; font-size: 30px; color: black; margin-top: 20px;">
                    <b>🔍 순찰 시 주요 착안사항 </b>
                </div>
                """,
                unsafe_allow_html=True
                )
            st.info("💡AI 활용으로 답변에 오류가 있을 수 있습니다")
            # ChatGPT API를 활용하여 순찰 시 주요 착안사항을 생성
            prompt = f"""
            [지시사항]
            당신은 자율방범대에게 순찰 시 필요한 사항을 안내해주는 안내자입니다.
            {selected_location}에서 자율방범대원이 순찰할 때 필요한 사항을 상세히 설명해주세요.
            지역적 특성: {info['description']}
            순찰 시 범죄취약지역, 방범시설 부족지역을 발견하면 경찰서 CPO에게 통보하고, 긴급한 상황이 발생하면 112에 신고해야 합니다.
            경찰서 CPO에게는 신고하는것이 아니라 범죄취약요인을 발견하게 되면 CPO에게 "통보"하는 것입니다.
            [제한사항]
            순찰노선을 정해주지 않고 자율적으로 순찰하도록 하는 것이 중요합니다. 
            순찰 시 유의사항을 5개까지만 추천해주고 눈에 들어오기 쉽게 짧게 작성해야합니다.
            """
            response = get_ai_response(prompt)
            st.info(response)
            
            st.markdown(
                """
                <div style="text-align: left; font-size: 30px; color: black; margin-top: 20px;">
                    <b>📑 기타 참고사항 </b>
                </div>
                """,
                unsafe_allow_html=True
                )
            if "해당관서" in info:
                st.markdown(f"""
                <div style="text-align: center; font-size: 16px; color: black; margin-top: 20px;">
                    <b>순찰활동 시 {selected_team}의<br>
                해당 지역관서는 {info['해당관서']}입니다.</b>
                </div>
                """,
                unsafe_allow_html=True)
            #문의사항 제목 title
            st.markdown(
                """
                <div style="text-align: left; font-size: 30px; color: black; margin-top: 20px;">
                    <b>❓문의사항 </b>
                </div>
                """,
                unsafe_allow_html=True
                )

            st.markdown(
                """
                <div style="text-align: center; font-size: 16px; color: black; margin-top: 20px;">
                    <b>순찰활동 중 취약사항 발견 시<br>
                    고양경찰서 범죄예방대응과 담당자(031-930-5343)<br>
                    연락바랍니다.</b>
                </div>
                """,
                unsafe_allow_html=True
            )

# 수평선 추가
st.markdown("---")

# 주의사항 - 마크다운 가운데 정렬
st.markdown(
    """
    <div style="text-align: center; font-size: 16px; color: gray; margin-top: 20px;">
        <b> 위 순찰추천 장소는 고양경찰서 범죄예방대응과에서 제작한 어플입니다.<br>
        AI를 활용하여 답변에 오류가 발생할 수 있습니다.</b>
    </div>
    """,
    unsafe_allow_html=True
)
