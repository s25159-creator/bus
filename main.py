import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 페이지 기본 설정
st.set_page_config(
    page_title="제주 직통 버스 & 최단시간 경로 안내",
    page_icon="🚌",
    layout="centered"
)

# 데이터 불러오기 함수 (캐싱 적용)
@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        df['departure_time'] = df['departure_time'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"데이터 파일({file_path})을 읽는 중 오류가 발생했습니다: {e}")
        return None

# 시간 계산 헬퍼 함수
def get_time_difference_minutes(now_str, dep_str):
    """현재 시간(HH:MM)과 버스 출발 시간(HH:MM) 사이의 차이를 분 단위로 계산"""
    now = datetime.strptime(now_str, "%H:%M")
    dep = datetime.strptime(dep_str, "%H:%M")
    
    # 자정이 넘어가는 경우 처리
    if dep < now:
        dep += timedelta(days=1)
        
    diff = (dep - now).total_seconds() / 60
    return int(diff)

def main():
    st.title("🚌 제주 직통 버스 검색 서비스")
    st.caption("현재 정류장에서 도착 정류장까지 환승 없이 바로 가는 가장 빠른 버스를 찾아드립니다.")

    # 1. 데이터 로드
    data_file = "bus_schedule.csv"
    df = load_data(data_file)

    if df is None or df.empty:
        st.info("📌 `bus_schedule.csv` 파일이 정상적으로 로드되지 않았습니다. sample 데이터 형태로 등록 후 사용해 주세요.")
        return

    # 정류장 목록 수집
    all_stations = sorted(list(set(df['departure_station'].unique()).union(set(df['arrival_station'].unique()))))

    st.markdown("---")
    
    # 2. 정류장 및 출발 기준 시간 입력
    col1, col2 = st.columns(2)
    
    with col1:
        departure = st.selectbox("🚩 출발 정류장 선택", sorted(df['departure_station'].unique()))
    
    # 출발 정류장을 기준으로 도달 가능한 도착 정류장 필터링
    possible_arrivals = df[df['departure_station'] == departure]['arrival_station'].unique()
    
    with col2:
        arrival = st.selectbox("🏁 도착 정류장 선택", sorted(possible_arrivals) if len(possible_arrivals) > 0 else all_stations)

    # 기준 시간 선택 (기본값: 현재 시간)
    current_time_str = datetime.now().strftime("%H:%M")
    search_time = st.time_input("⏰ 출발 기준 시간", value=datetime.strptime(current_time_str, "%H:%M").time())
    search_time_str = search_time.strftime("%H:%M")

    # 3. 경로 조회 및 결과 표시
    if st.button("🚌 가장 빠른 직통 노선 찾기", use_container_width=True):
        if departure == arrival:
            st.warning("출발 정류장과 도착 정류장이 같습니다. 서로 다른 정류장을 선택해 주세요.")
            return

        # 조건에 맞는 직통 노선 필터링
        filtered_df = df[(df['departure_station'] == departure) & (df['arrival_station'] == arrival)].copy()

        if filtered_df.empty:
            st.error("❌ 현재 선택하신 구간을 환승 없이 직통으로 운행하는 버스 노선이 없습니다.")
            return

        # 대기 시간 및 도착 예정 시간 계산
        results = []
        for _, row in filtered_df.iterrows():
            wait_min = get_time_difference_minutes(search_time_str, row['departure_time'])
            
            # 기준 시간 기준 12시간 이내 출발 버스만 추출 (너무 먼 시간 제외)
            if 0 <= wait_min <= 720: 
                travel_min = int(row['travel_time_min'])
                total_min = wait_min + travel_min
                
                arr_dt = datetime.strptime(row['departure_time'], "%H:%M") + timedelta(minutes=travel_min)
                arr_time_str = arr_dt.strftime("%H:%M")

                results.append({
                    'route_id': row['route_id'],
                    'route_name': row['route_name'],
                    'departure_time': row['departure_time'],
                    'wait_min': wait_min,
                    'travel_time_min': travel_min,
                    'arrival_time': arr_time_str,
                    'total_duration': total_min
                })

        if not results:
            st.warning("⚠️ 선택하신 출발 시간 이후 해당 구간에 예정된 버스가 없습니다.")
            return

        # 소요 총 시간(대기시간 + 운행시간) 기준 최단 경로 정렬
        results_df = pd.DataFrame(results).sort_values(by='total_duration')

        # 추천 상위 노선 (가장 빨리 도착하는 경로)
        fastest = results_df.iloc[0]

        st.success("🎉 가장 빠르게 도착하는 직통 노선을 찾았습니다!")
        
        # 메인 추천 카드는 메트릭으로 시각화
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("추천 노선", f"{fastest['route_id']}번")
        m2.metric("정류장 출발", fastest['departure_time'])
        m3.metric("대기 시간", f"{fastest['wait_min']}분 후")
        m4.metric("목적지 도착 예정", fastest['arrival_time'])

        st.markdown("---")
        st.subheader("📋 이용 가능한 모든 직통 버스 운행 목록")

        # 테이블 표출을 위한 컬럼 정리 및 정렬
        display_df = results_df[['route_name', 'departure_time', 'wait_min', 'travel_time_min', 'arrival_time']].copy()
        display_df.columns = ['노선명', '출발 시간', '대기 시간(분)', '소요 시간(분)', '목적지 도착 예정']

        st.dataframe(
            display_df.reset_index(drop=True),
            use_container_width=True
        )

if __name__ == "__main__":
    main()
