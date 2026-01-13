import streamlit as st
import pandas as pd
import time
import difflib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import streamlit.components.v1 as components

# --- 페이지 설정 ---
st.set_page_config(page_title="100절 암송학교", layout="centered")

# --- CSS 스타일링 ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 10px; }
    .big-font { font-size: 20px !important; font-weight: bold; }
    .verse-text { font-size: 18px; line-height: 1.6; }
    .red-heart { color: red; font-size: 24px; cursor: pointer; }
    .gray-heart { color: gray; font-size: 24px; cursor: pointer; }
    .correct { color: green; font-weight: bold; font-size: 24px; text-align: center; }
    .incorrect { color: red; font-weight: bold; }
    .diff-red { color: red; font-weight: bold; text-decoration: underline; }
    .diff-green { color: green; font-weight: bold; }
    .login-box { padding: 20px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 20px; text-align: center; }
    
    /* 네비게이션 버튼 스타일 */
    .nav-buttons {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 구글 시트 연결 함수 ---
def get_google_sheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        return None

def load_user_data_from_sheet(nickname):
    client = get_google_sheet_client()
    if not client:
        return []

    try:
        sheet = client.open("bible_db").sheet1
        records = sheet.get_all_records()
        for row in records:
            if str(row.get('Nickname')) == nickname:
                saved_str = str(row.get('SavedVerses', ''))
                if saved_str:
                    return [int(x) for x in saved_str.split(',') if x.strip()]
                return []
        return []
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        return []

def save_user_data_to_sheet(nickname, verse_list):
    client = get_google_sheet_client()
    if not client:
        return

    try:
        sheet = client.open("bible_db").sheet1
        data_str = ",".join(map(str, verse_list))
        cell = sheet.find(nickname)
        if cell:
            sheet.update_cell(cell.row, 2, data_str)
        else:
            sheet.append_row([nickname, data_str])
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")

# --- 데이터 로드 ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("bible_verses_clean.csv")
        return df
    except:
        st.error("데이터 파일(bible_verses_clean.csv)을 찾을 수 없습니다.")
        return pd.DataFrame()

df = load_data()

# --- 세션 상태 초기화 ---
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'nickname' not in st.session_state: st.session_state.nickname = ""
if 'saved_verses' not in st.session_state: st.session_state.saved_verses = []

# 학습/암송 관련 상태
if 'study_idx' not in st.session_state: st.session_state.study_idx = 0 
if 'study_mode_hide' not in st.session_state: st.session_state.study_mode_hide = False 
if 'study_reveal_content' not in st.session_state: st.session_state.study_reveal_content = False 
if 'study_reveal_addr' not in st.session_state: st.session_state.study_reveal_addr = False 
if 'test_current_idx' not in st.session_state: st.session_state.test_current_idx = 0 
if 'test_answers' not in st.session_state: st.session_state.test_answers = [] 
if 'test_score' not in st.session_state: st.session_state.test_score = 0 
if 'test_hint_level' not in st.session_state: st.session_state.test_hint_level = 3 
if 'test_status' not in st.session_state: st.session_state.test_status = 'input' 
if 'input_key_suffix' not in st.session_state: st.session_state.input_key_suffix = 0 
if 'test_user_content' not in st.session_state: st.session_state.test_user_content = ""
if 'test_user_addr' not in st.session_state: st.session_state.test_user_addr = ""

# --- 도우미 함수 ---
def go_home():
    st.session_state.page = 'home'
    st.rerun()

def toggle_save(verse_id):
    verse_id = int(verse_id)
    if verse_id in st.session_state.saved_verses:
        st.session_state.saved_verses.remove(verse_id)
    else:
        st.session_state.saved_verses.append(verse_id)
    save_user_data_to_sheet(st.session_state.nickname, st.session_state.saved_verses)

def diff_strings(a, b):
    matcher = difflib.SequenceMatcher(None, a, b)
    html_output = []
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == 'equal':
            html_output.append(a[a0:a1])
        elif opcode == 'insert':
            pass 
        elif opcode == 'delete':
            html_output.append(f"<span class='diff-red'>{a[a0:a1]}</span>")
        elif opcode == 'replace':
            html_output.append(f"<span class='diff-red'>{a[a0:a1]}</span>")
    return "".join(html_output)

# --- 페이지 0: 로그인 ---
def page_login():
    st.title("📖 100절 암송학교")
    st.markdown("<div style='text-align: center; margin-top: 50px;'>", unsafe_allow_html=True)
    st.subheader("닉네임으로 시작하기")
    st.write("본인의 닉네임을 입력하면 저장된 말씀을 불러옵니다.")
    
    nickname_input = st.text_input("닉네임 입력", placeholder="예: 철수")
    
    if st.button("입장하기"):
        if nickname_input.strip():
            st.session_state.nickname = nickname_input.strip()
            with st.spinner("데이터를 불러오는 중..."):
                st.session_state.saved_verses = load_user_data_from_sheet(st.session_state.nickname)
            st.session_state.page = 'home'
            st.rerun()
        else:
            st.error("닉네임을 입력해주세요.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- 페이지 1: 홈 화면 ---
def page_home():
    st.title("📖 100절 암송학교")
    st.write(f"환영합니다, **{st.session_state.nickname}**님! 👋")
    
    saved_count = len(st.session_state.saved_verses)
    if saved_count > 0:
        st.caption(f"현재 {saved_count}개의 말씀이 저장되어 있습니다.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("말씀 학습"):
            st.session_state.page = 'study'
            st.rerun()
    with col2:
        if st.button("말씀 암송"):
            st.session_state.page = 'test_prep' 
            st.rerun()
    with col3:
        if st.button("저장된 말씀"):
            st.session_state.page = 'saved'
            st.rerun()
    
    st.markdown("---")
    if st.button("로그아웃"):
        st.session_state.nickname = ""
        st.session_state.saved_verses = []
        st.session_state.page = 'login'
        st.rerun()

# --- 페이지 2: 말씀 학습 ---
def page_study():
    st.header("말씀 학습")
    
    col_back, col_cat, col_toggle = st.columns([1, 2, 2])
    with col_back:
        if st.button("🏠 홈"):
            go_home()
    
    categories = ['전체보기'] + list(df['구분'].unique())
    with col_cat:
        selected_cat = st.selectbox("구분", categories)
    
    if selected_cat == '전체보기':
        filtered_df = df
    else:
        filtered_df = df[df['구분'] == selected_cat].reset_index(drop=True)
    
    if filtered_df.empty:
        st.write("해당하는 말씀이 없습니다.")
        return

    # 인덱스 범위 체크
    if st.session_state.study_idx >= len(filtered_df):
        st.session_state.study_idx = 0
    elif st.session_state.study_idx < 0:
        st.session_state.study_idx = len(filtered_df) - 1

    # --- 1. 상단 슬라이더 ---
    current_idx = st.session_state.study_idx + 1
    new_idx = st.slider(
        "순서 이동", 
        1, 
        len(filtered_df), 
        current_idx, 
        label_visibility="collapsed"
    )
    if new_idx != current_idx:
        st.session_state.study_idx = new_idx - 1
        st.rerun()

    row = filtered_df.iloc[st.session_state.study_idx]
    
    with col_toggle:
        if st.button("🙈 외워보기" if not st.session_state.study_mode_hide else "👁️ 다 보기"):
            st.session_state.study_mode_hide = not st.session_state.study_mode_hide
            st.session_state.study_reveal_content = False
            st.session_state.study_reveal_addr = False
            st.rerun()

    st.markdown("---")
    
    verse_id = int(row['번호'])
    is_saved = verse_id in st.session_state.saved_verses
    
    # 하트 및 내용 영역
    heart_col1, heart_col2 = st.columns([9, 1])
    with heart_col2:
        heart_label = "❤️" if is_saved else "🤍"
        if st.button(heart_label, key=f"heart_{verse_id}"):
            toggle_save(verse_id)
            st.rerun()
    
    st.caption(f"No. {verse_id} ({row['구분']})")
    
    container = st.container()
    
    with container:
        # 내용
        if st.session_state.study_mode_hide and not st.session_state.study_reveal_content:
            if st.button("👆 내용을 보려면 터치하세요", key="reveal_content"):
                st.session_state.study_reveal_content = True
                st.rerun()
        else:
            st.markdown(f"<div style='text-align: center; font-size: 22px; padding: 20px;'>{row['내용']}</div>", unsafe_allow_html=True)
            if st.session_state.study_mode_hide:
                 if st.button("다시 가리기", key="hide_content"):
                    st.session_state.study_reveal_content = False
                    st.rerun()

        st.write(" ") 

        # 장절
        if st.session_state.study_mode_hide and not st.session_state.study_reveal_addr:
            if st.button("👆 장절을 보려면 터치하세요", key="reveal_addr"):
                st.session_state.study_reveal_addr = True
                st.rerun()
        else:
            st.markdown(f"<div style='text-align: center; font-size: 18px; color: gray; font-weight: bold;'>{row['장절']}</div>", unsafe_allow_html=True)
            if st.session_state.study_mode_hide:
                 if st.button("다시 가리기", key="hide_addr"):
                    st.session_state.study_reveal_addr = False
                    st.rerun()

    st.markdown("---")
    
    # --- 2. 하단 네비게이션 버튼 (나란히 배치) ---
    col_prev, col_next = st.columns(2)
    
    with col_prev:
        if st.button("◀ 이전", use_container_width=True):
            st.session_state.study_idx -= 1
            st.rerun()
            
    with col_next:
        if st.button("다음 ▶", use_container_width=True):
            st.session_state.study_idx += 1
            st.rerun()


# --- 페이지 3: 저장된 말씀 ---
def page_saved():
    st.header("저장된 말씀 ❤️")
    if st.button("🏠 홈으로"):
        go_home()
    
    if not st.session_state.saved_verses:
        st.info("저장한 말씀이 없어요")
        return

    saved_df = df[df['번호'].isin(st.session_state.saved_verses)].copy()
    
    c1, c2, c3 = st.columns([2, 6, 2])
    c1.markdown("**장절**")
    c2.markdown("**말씀**")
    c3.markdown("**삭제**")
    st.markdown("---")
    
    for idx, row in saved_df.iterrows():
        c1, c2, c3 = st.columns([2, 6, 2])
        c1.write(row['장절'])
        c2.write(row['내용'])
        if c3.button("❤️(삭제)", key=f"del_{row['번호']}"):
            toggle_save(row['번호'])
            st.rerun()
        st.markdown("---")


# --- 페이지 4: 말씀 암송 ---
def init_test():
    st.session_state.test_current_idx = 0
    st.session_state.test_score = 0
    st.session_state.test_answers = [] 
    st.session_state.test_hint_level = 3
    st.session_state.test_status = 'input'
    st.session_state.input_key_suffix = 0 
    st.session_state.test_user_content = ""
    st.session_state.test_user_addr = ""
    st.session_state.page = 'test'

def page_test_prep():
    init_test()
    st.rerun()

def page_test():
    if st.session_state.test_current_idx >= len(df):
        finish_test() 
        return

    row = df.iloc[st.session_state.test_current_idx]
    verse_num = row['번호']
    
    c1, c2, c3 = st.columns([2, 6, 2])
    c1.subheader(f"{verse_num} / 100")
    
    with c2:
        hint_label = f"힌트 ({st.session_state.test_hint_level})"
        if st.session_state.test_hint_level == 0: 
            hint_label = "정답보기"
        
        if st.session_state.test_status == 'input':
            if st.button(hint_label):
                if st.session_state.test_hint_level == 0:
                    st.session_state.test_answers.append({
                        '번호': row['번호'],
                        '장절': row['장절'],
                        '내용': row['내용']
                    })
                    st.session_state.test_user_addr = "" 
                    st.session_state.test_user_content = ""
                    st.session_state.test_status = 'wrong'
                else:
                    st.session_state.test_hint_level -= 1
                st.rerun()
    
    with c3:
        if st.button("끝"):
            finish_test()
            return

    st.markdown("---")

    real_content = row['내용']
    real_addr = row['장절']
    
    try:
        base_addr = real_addr.split(':')[0]
    except:
        base_addr = real_addr 
    st.info(f"📖 문제 범위: **{base_addr}**")

    addr_hint_msg = ""
    content_hint_msgs = []
    
    # 힌트 2 (첫 단어)
    if st.session_state.test_hint_level <= 2:
        first_word = real_content.split()[0]
        content_hint_msgs.append(f"💡 첫 단어: **{first_word}**...")
    
    # 힌트 1 (장절)
    if st.session_state.test_hint_level <= 1:
        addr_hint_msg = f"💡 장절 힌트: **{real_addr}**"

    # 힌트 0 (마지막 단어)
    if st.session_state.test_hint_level == 0:
        last_word = real_content.split()[-1]
        content_hint_msgs.append(f"💡 마지막 단어: ...**{last_word}**")

    placeholder = st.empty()
    
    input_addr_key = f"input_addr_{st.session_state.test_current_idx}_{st.session_state.input_key_suffix}"
    input_content_key = f"input_content_{st.session_state.test_current_idx}_{st.session_state.input_key_suffix}"

    with placeholder.container():
        if st.session_state.test_status == 'input':
            
            st.write("장절을 입력하세요 (예: 창세기 1:26)")
            if addr_hint_msg:
                st.info(addr_hint_msg)
            
            u_addr = st.text_input("장절 입력", key=input_addr_key, label_visibility="collapsed")
            
            st.write(" ") 

            st.write("내용을 입력하세요:")
            if content_hint_msgs:
                st.info("\n\n".join(content_hint_msgs))
            
            u_content = st.text_area("내용 입력", height=100, key=input_content_key, label_visibility="collapsed")

            if st.button("완료"):
                check_answer(u_addr, u_content, real_addr, real_content, row)
                
        elif st.session_state.test_status == 'correct':
            st.markdown("""<div class='correct'>⭕ 정답입니다!</div>""", unsafe_allow_html=True)
            time.sleep(1) 
            next_question()
            
        elif st.session_state.test_status == 'wrong':
            st.error("틀린 부분이 있습니다. (정답 확인)")
            
            clean_u_addr = st.session_state.test_user_addr.strip().replace(" ", "")
            clean_r_addr = real_addr.strip().replace(" ", "")
            
            if clean_u_addr != clean_r_addr:
                if st.session_state.test_user_addr == "":
                     st.markdown(f"**내가 쓴 장절:** (입력 없음)", unsafe_allow_html=True)
                else:
                    st.markdown(f"**내가 쓴 장절:** <span style='color:red'>{st.session_state.test_user_addr}</span>", unsafe_allow_html=True)
                st.info(f"정답: {real_addr}")
            else:
                st.markdown(f"**장절:** {real_addr} (정답)")
            
            st.markdown("---")
            
            clean_u_content = st.session_state.test_user_content.strip() 
            diff_html = diff_strings(clean_u_content, real_content)
            
            st.markdown("**내가 쓴 내용 (틀린 부분 빨간색):**", unsafe_allow_html=True)
            if clean_u_content == "":
                st.write("(입력 없음)")
            else:
                st.markdown(f"<div style='background-color:#f0f0f0; padding:10px; border-radius:5px;'>{diff_html}</div>", unsafe_allow_html=True)
            
            st.info(f"**정답:**\n{real_content}")

            if st.button("다음"):
                next_question()

def check_answer(u_addr, u_content, r_addr, r_content, row_data):
    clean_u_addr = u_addr.strip().replace(" ", "")
    clean_r_addr = r_addr.strip().replace(" ", "")
    clean_u_content = u_content.strip().replace(" ", "")
    clean_r_content = r_content.strip().replace(" ", "")
    
    if clean_u_addr == clean_r_addr and clean_u_content == clean_r_content:
        st.session_state.test_score += 1
        st.session_state.test_status = 'correct'
        st.rerun()
    else:
        st.session_state.test_answers.append({
            '번호': row_data['번호'],
            '장절': row_data['장절'],
            '내용': row_data['내용']
        })
        st.session_state.test_user_addr = u_addr
        st.session_state.test_user_content = u_content
        st.session_state.test_status = 'wrong'
        st.rerun()

def next_question():
    st.session_state.test_current_idx += 1
    st.session_state.test_hint_level = 3 
    st.session_state.test_status = 'input'
    st.session_state.input_key_suffix += 1 
    st.rerun()

def finish_test():
    st.session_state.page = 'test_result'
    st.rerun()

# --- 페이지 5: 암송 결과 ---
def page_test_result():
    st.header("암송 결과")
    
    total = st.session_state.test_current_idx
    if st.session_state.test_status in ['correct', 'wrong']:
        total += 1
        
    if total == 0: total = 1 
    
    score = st.session_state.test_score
    
    st.markdown(f"<h1 style='text-align: center;'>{score} / {total}</h1>", unsafe_allow_html=True)
    
    if score == total and total > 0:
        st.success("오답이 없어요! 💯")
    else:
        st.markdown("### 틀린 문제")
        c1, c2, c3 = st.columns([3, 6, 1])
        c1.markdown("**장절**")
        c2.markdown("**말씀**")
        c3.markdown("**저장**")
        st.markdown("---")
        
        for item in st.session_state.test_answers:
            c1, c2, c3 = st.columns([3, 6, 1])
            c1.write(item['장절'])
            c2.write(item['내용'])
            
            verse_id = int(item['번호'])
            is_saved = verse_id in st.session_state.saved_verses
            heart_icon = "❤️" if is_saved else "🤍"
            
            if c3.button(heart_icon, key=f"result_save_{verse_id}"):
                toggle_save(verse_id)
                st.rerun()
                
            st.markdown("---")

    if st.button("홈으로 돌아가기"):
        go_home()


if st.session_state.page == 'login':
    page_login()
elif st.session_state.page == 'home':
    page_home()
elif st.session_state.page == 'study':
    page_study()
elif st.session_state.page == 'saved':
    page_saved()
elif st.session_state.page == 'test_prep':
    page_test_prep()
elif st.session_state.page == 'test':
    page_test()
elif st.session_state.page == 'test_result':
    page_test_result()
