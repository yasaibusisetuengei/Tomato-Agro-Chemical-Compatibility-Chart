import os
import itertools
import re
import streamlit as st
import pandas as pd

# ----------------------------------------------------
# 1. ページ基本設定
# ----------------------------------------------------
st.set_page_config(
    page_title="トマト農薬混用事例検索アプリ",
    page_icon="🍅",
    layout="wide"
)

# ----------------------------------------------------
# 2. ログイン認証機能
# ----------------------------------------------------
def check_password():
    """指定のパスワードを入力しないとログインできないようにする認証関数"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🍅 トマト農薬混用事例検索アプリ - ログイン")
        st.warning("このアプリを利用するにはパスワードが必要です。")
        
        default_password = st.secrets.get("password", "tomato123")
        password = st.text_input("パスワードを入力してください", type="password")
        
        if st.button("ログイン"):
            if password == default_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("パスワードが間違っています。")
        return False
    return True

if not check_password():
    st.stop()

# ----------------------------------------------------
# 3. タイトル・説明
# ----------------------------------------------------
st.title("🍅 トマト農薬混用事例検索アプリ")
st.caption("混用表データから、混用事例を一括で確認できます。")

# ----------------------------------------------------
# 4. 50音変換・頭文字抽出ヘルパー関数
# ----------------------------------------------------
HIRAGANA_LIST = [
    "あ", "い", "う", "え", "お",
    "か", "き", "く", "け", "こ",
    "さ", "し", "す", "せ", "そ",
    "た", "ち", "つ", "て", "と",
    "な", "に", "ぬ", "ね", "の",
    "は", "ひ", "ふ", "へ", "ほ",
    "ま", "み", "む", "め", "も",
    "や", "ゆ", "よ",
    "ら", "り", "る", "れ", "ろ",
    "わ", "その他"
]

def get_initial_hiragana(text):
    if not text or not isinstance(text, str):
        return "その他"
    
    first_char = text[0]
    if 'ア' <= first_char <= 'ン':
        first_char = chr(ord(first_char) - 0x60)
    
    dakuon_map = str.maketrans(
        "ぁぃぅぇぉがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽゃゅょっ",
        "あいうえおかきくけこさしすせそたちつてとはひふへほはひふへほやゆよつ"
    )
    first_char = first_char.translate(dakuon_map)
    return first_char if first_char in HIRAGANA_LIST else "その他"

# ----------------------------------------------------
# 5. データ読み込み
# ----------------------------------------------------
CSV_FILENAME = "20261111tomato.csv"

@st.cache_data
def load_data():
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CSV_FILENAME)
    if not os.path.exists(file_path):
        return None
    try:
        try:
            return pd.read_csv(file_path, index_col=0, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, index_col=0, encoding="cp932")
    except Exception:
        return None

df_matrix = load_data()

if df_matrix is None or df_matrix.empty:
    st.error(f"⚠️ 混用表データ（{CSV_FILENAME}）の読み込みに失敗しました。ファイルがリポジトリ内に正しくアップロードされているか確認してください。")
    st.stop()

# ----------------------------------------------------
# 6. 検索する薬剤の選択 ＆ 影響日数・死亡率によるプルダウン絞り込み
# ----------------------------------------------------
st.subheader("💊 検索する薬剤の選択と絞り込み")

col_f1, col_f2 = st.columns(2)

BEE_OPTIONS = ["指定なし", "０日以下", "１日以下", "５日以下", "６日以上"]
TOBA_OPTIONS = ["指定なし", "低い（0〜30%）"]

with col_f1:
    selected_bee_cond = st.selectbox("マルハナバチへの影響日数で絞り込み", options=BEE_OPTIONS, index=0)

with col_f2:
    selected_toba_cond = st.selectbox("タバコカスミカメの死亡率（死虫率）で絞り込み", options=TOBA_OPTIONS, index=0)

# フィルタリング処理
filtered_medicines_set = []
bee_col = df_matrix.columns[0]
toba_col = df_matrix.columns[1]

for med in df_matrix.index:
    # マルハナバチ条件判定
    val_bee = df_matrix.loc[med, bee_col]
    bee_matched = True
    if selected_bee_cond != "指定なし":
        if pd.isna(val_bee) or str(val_bee).strip() in ["", "-", "nan"]:
            bee_matched = False
        else:
            nums = re.findall(r'\d+', str(val_bee))
            if nums:
                num = float(nums[0])
                if selected_bee_cond == "０日以下":
                    bee_matched = (num <= 0)
                elif selected_bee_cond == "１日以下":
                    bee_matched = (num <= 1)
                elif selected_bee_cond == "５日以下":
                    bee_matched = (num <= 5)
                elif selected_bee_cond == "６日以上":
                    bee_matched = (num >= 6)
            else:
                bee_matched = False

    # タバコカスミカメ条件判定
    val_toba = df_matrix.loc[med, toba_col]
    toba_matched = True
    if selected_toba_cond != "指定なし":
        if pd.isna(val_toba) or str(val_toba).strip() in ["", "-", "nan"]:
            toba_matched = False
        else:
            nums = re.findall(r'\d+', str(val_toba))
            if nums:
                num = float(nums[0])
                if selected_toba_cond == "低い（0〜30%）":
                    toba_matched = (num <= 30)
            else:
                toba_matched = False

    if bee_matched and toba_matched:
        filtered_medicines_set.append(med)

all_matrix_cols = df_matrix.columns[2:].tolist()
all_medicines = sorted(list(set(filtered_medicines_set + [c for c in all_matrix_cols if c in filtered_medicines_set])))

num_select = st.number_input("選択する薬剤の数を指定してください", min_value=1, max_value=4, value=2, step=1)

selected_medicines = []
cols = st.columns(num_select)

for i in range(num_select):
    with cols[i]:
        st.markdown(f"**【 薬剤 {i+1} 】**")
        selected_initial = st.selectbox("頭文字を選択", options=HIRAGANA_LIST, key=f"initial_{i}")
        filtered_list = [m for m in all_medicines if get_initial_hiragana(m) == selected_initial]
        
        if filtered_list:
            selected_med = st.selectbox("薬剤を選択", options=filtered_list, key=f"med_{i}")
            selected_medicines.append(selected_med)
        else:
            st.warning("該当する薬剤がありません。")

st.markdown("---")

# ----------------------------------------------------
# 7. 混用結果の照会および表示
# ----------------------------------------------------
if len(selected_medicines) == num_select and len(set(selected_medicines)) == num_select:
    st.subheader("🔍 混用可否 検索結果")
    pairs = list(itertools.combinations(selected_medicines, 2))
    
    if pairs:
        results = []
        has_ng = has_unknown = has_warning = False
        
        for med1, med2 in pairs:
            res = ""
            if med1 in df_matrix.index and med2 in df_matrix.columns:
                res = str(df_matrix.loc[med1, res_col if 'res_col' in locals() else med2]) # fix index/col check safely
            # Safe lookup
            if med1 in df_matrix.index and med2 in df_matrix.columns:
                res = str(df_matrix.loc[med1, med2])
            elif med2 in df_matrix.index and med1 in df_matrix.columns:
                res = str(df_matrix.loc[med2, med1])
            
            res = res.strip()
            
            if any(k in res for k in ["×", "▲", "△"]):
                if "×" in res:
                    status = "🔴 混用不可"
                elif "▲" in res:
                    status = "🔴 混用不可（薬害問題）"
                else:
                    status = "🔴 混用不可（物理性・効力低下等）"
                has_ng = True
            elif any(k in res for k in ["○", "〇", "◯", "◎"]):
                # 漢数字の「〇」や各種丸印に対応
                if any(k in res for k in ["○", "〇", "◯"]):
                    status = "⚠️条件付き（要攪拌）"
                else:
                    status = "⚠️条件付き（使用直前）"
                has_warning = True
            elif "●" in res:
                status = "✅ 混用可能"
            else:
                status = "⚪ 不明 / 知見乏しい"
                has_unknown = True
                
            results.append({
                "薬剤 1": med1,
                "薬剤 2": med2,
                "混用記号": res if res else "（空欄）",
                "判定": status
            })
        
        if has_ng:
            st.error("⚠️ **混用不可または問題のある組み合わせが含まれています！** 詳細をご確認ください。3剤以上の混用は推奨していません。")
        elif has_unknown:
            st.error("⚠️ **不明 / 知見乏しい組み合わせが含まれているため、混用をお勧めできない組み合わせがあります。** 3剤以上の混用は推奨していません。")
        elif has_warning:
            st.warning("⚠️ **注意が必要な条件付きの組み合わせが含まれています。** 攪拌や使用タイミングにご注意ください。3剤以上の混用は推奨していません。")
        else:
            st.success("✅ **選択されたすべての組み合わせで混用可能です。** 3剤以上の混用は推奨していません")
        
        st.table(pd.DataFrame(results))

elif len(set(selected_medicines)) < len(selected_medicines):
    st.error("※同じ薬剤が重複して選択されています。異なる薬剤を選択してください。")

# ----------------------------------------------------
# 8. 参照データプレビュー
# ----------------------------------------------------
with st.expander("📊 現在の混用表データ（令和8年7月10日 JA全農ふくれんトマト部会 令和8年7月10日の登録情報に基づくものです）"):
    st.markdown("**【 表内の記号の凡例 】**")
    st.markdown(
        """
        - **●** : 混用可能  
        - **○** : 条件付き（要攪拌）  
        - **◎** : 条件付き（使用直前）  
        - **×** : 混用不可  
        - **▲** : 混用不可（薬害問題）  
        - **△** : 混用不可（物理性・効力低下等）
        """
    )
    st.markdown("---")
    st.dataframe(df_matrix)

# ----------------------------------------------------
# 9. フッター
# ----------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #555555; font-size: 0.9em; padding: 10px;'>
        <p style='color: #d9534f; font-weight: bold;'>
            ※本アプリは農薬混用の目安を提供するものです。実際の使用にあたっては、必ず農薬ボトルのラベルおよび最新の指示事項をご確認ください。
            ※この表は、農薬メーカーによる試験結果に基づき取りまとめられたものです。栽培条件、気象条件等で反応が異なる場合があるので参考として活用して下さい。
            ※登録内容は追加・変更されることがありますので、常に最新の情報を登録情報等や農薬ラベルで必ずご確認下さい。
        <p style='font-size: 0.8em; color: #777777;'>
            This application uses open-source software libraries (Streamlit, Pandas, Python).
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
