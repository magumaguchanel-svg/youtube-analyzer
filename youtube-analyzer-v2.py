import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib import font_manager
from wordcloud import WordCloud
from datetime import datetime, timedelta

# --- ページ設定 ---
st.set_page_config(
    page_title="YouTube 動画分析ダッシュボード",
    page_icon="📊",
    layout="wide"
)

# --- 日本語フォントの設定 (豆腐文字対策) ---
def set_japanese_font():
    font_paths = [
        "C:\\Windows\\Fonts\\msgothic.ttc",  # Windows MS Gothic
        "C:\\Windows\\Fonts\\YuGothM.ttc",   # Windows Yu Gothic
        "/System/Library/Fonts/ipaexg.ttf",  # Mac IPA Gothic
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf" # Linux
    ]
    font_path = None
    for path in font_paths:
        if os.path.exists(path):
            font_path = path
            break
    if font_path:
        prop = font_manager.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = prop.get_name()
        # マイナス記号の文字化け対策
        plt.rcParams['axes.unicode_minus'] = False
        return font_path
    return None

font_path = set_japanese_font()

# --- タイトル ---
st.title("📊 YouTube 動画詳細検索 ＆ 拡散分析アプリ")
st.markdown("YouTube Data APIを利用して、指定したキーワードに関する動画の「タイトル」「説明」「タグ」などの詳細情報を取得・分析します。")

# --- セッションステートの初期化 ---
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None
if 'searched_keyword' not in st.session_state:
    st.session_state.searched_keyword = ""

# --- サイドバー設定 ---
st.sidebar.header("🔑 API設定 & 検索条件")

# デモモード
use_demo = st.sidebar.checkbox("デモモードを使用する (APIキー不要)", value=True)

# APIキー入力
api_key = ""
if not use_demo:
    api_key = st.sidebar.text_input("YouTube Data API キーを入力してください", type="password")
    if not api_key:
        st.sidebar.warning("🔑 APIキーを入力するか、デモモードをONにしてください。")

# 検索ワード
keyword = st.sidebar.text_input("検索キーワード", value="Python プログラミング" if use_demo else "")

# 取得件数
max_results = st.sidebar.slider("最大取得件数", min_value=5, max_value=50, value=20, step=5)

# --- 絞り込みフィルター（サイドバー下部） ---
st.sidebar.markdown("---")
st.sidebar.header("🔍 データの絞り込み (フィルター)")

# 1. 公開時期フィルター
time_filter = st.sidebar.selectbox(
    "📆 公開時期",
    options=["指定なし", "1か月以内", "1年以内"],
    index=0
)

# 2. 視聴回数（星）フィルター
view_stars_options = {
    "☆1 (100 ~ 1,000回)": "☆1",
    "☆2 (1,000 ~ 10,000回)": "☆2",
    "☆3 (10,000 ~ 100,000回)": "☆3",
    "☆4 (100,000回以上)": "☆4",
    "その他 (100回未満)": "その他"
}
selected_stars = st.sidebar.multiselect(
    "⭐ 視聴回数星ランク",
    options=list(view_stars_options.keys()),
    default=list(view_stars_options.keys())
)

# 3. 拡散率フィルター
spread_options = {
    "1未満 (低拡散)": "1未満",
    "1倍台 (1~2未満)": "1倍台",
    "2倍台 (2~3未満)": "2倍台",
    "3倍台 (3~4未満)": "3倍台",
    "4倍台 (4~5未満)": "4倍台",
    "5倍以上 (高拡散)": "5倍以上"
}
selected_spreads = st.sidebar.multiselect(
    "📈 拡散率 (再生数 ÷ 登録者数)",
    options=list(spread_options.keys()),
    default=list(spread_options.keys())
)

# --- データ取得・シミュレーション関数 ---
def get_youtube_data(query, limit):
    # デモ用のダミーデータを生成
    if use_demo:
        now = datetime.now()
        dummy_titles = [
            "Python超入門コース！30分でプログラミング基礎を完全攻略",
            "【初心者向け】YouTube APIの使い方とデータ分析実践ガイド",
            "2026年最新AIトレンド徹底解説！AI時代の生き残り戦略",
            "プロの料理人が教える！世界一美味しい至高のパラパラ炒飯の作り方",
            "10分で学べるExcel仕事術！今日から使える圧倒的時短ワザ10選",
            "【解説】新時代の資産形成！新NISAの超効率的活用ロードマップ",
            "初心者必見！一眼レフカメラでシネマティック動画を撮影する3つのコツ",
            "【VLOG】週末ソロキャンプ。大自然で焚き火と極厚ステーキ肉を堪能する夜",
            "最新スマホ徹底比較！最強の1台はどれ？カメラ・電池性能をガチ検証",
            "【ASMR】深夜の優しい雨の音と暖炉の薪がはぜる音（睡眠用・勉強用BGM）",
            "【超大作】古代ローマ帝国の栄華と衰退の歴史を1時間で完全理解する",
            "【筋トレ】自宅でできる10分間限界HIITトレーニング！脂肪燃焼効果MAX",
            "【ルームツアー】30代一人暮らしミニマリスト。こだわり抜いた愛用品と収納術",
            "英語がスラスラ話せるようになる！毎日15分のシャドーイング練習法",
            "【DIY】総制作費3000円！100均グッズで作るおしゃれなディスプレイ棚",
            "世界一分かりやすい「量子力学」入門！二重スリット実験の謎を解き明かす",
            "【超簡単】おうちで作る本格スパイスカレー！黄金比スパイス3つだけ",
            "ゲーム実況：史上最恐ホラーゲームを初見プレイしたら絶叫が止まらなかった件",
            "【保存版】プレゼン資料デザイン術！1ランク上のスライドを作るデザインのルール",
            "【旅VLOG】死ぬまでに行きたい絶景。ウユニ塩湖の鏡張りに感動の涙"
        ]
        
        dummy_channels = [
            "AI・プログラミングLab", "Techアカデミー", "未来予測チャンネル", "クッキング極み",
            "オフィスHack", "マネーリテラシー向上委員会", "シネマライフレシピ", "野遊びキャンパー",
            "ガジェット最前線", "Sound Therapy", "歴史ロマン紀行", "おうちフィットネス",
            "シンプリストの暮らし", "英会話スピードアップ", "DIYクリエイターズ", "サイエンス・アイ",
            "スパイス研究所", "絶叫ゲーム実況", "デザインプロの技", "世界の絶景を往く"
        ]
        
        dummy_tags = [
            ["Python", "プログラミング", "初心者", "プログラミング入門", "エンジニア"],
            ["YouTube", "API", "データ分析", "Python", "スクレイピング", "自動化"],
            ["AI", "ChatGPT", "トレンド", "未来予測", "テクノロジー", "仕事"],
            ["料理", "レシピ", "炒飯", "中華", "男飯", "クッキング"],
            ["Excel", "エクセル", "効率化", "仕事術", "時短", "ビジネススキル"],
            ["投資", "NISA", "資産形成", "お金", "ライフプラン", "株"],
            ["カメラ", "一眼レフ", "撮影技術", "動画編集", "映像制作"],
            ["キャンプ", "ソロキャンプ", "焚き火", "ステーキ", "アウトドア", "VLOG"],
            ["スマホ", "ガジェット", "比較", "iPhone", "Android", "レビュー"],
            ["ASMR", "睡眠用", "勉強用BGM", "雨の音", "暖炉", "癒し"],
            ["歴史", "世界史", "古代ローマ", "教養", "ドキュメンタリー"],
            ["筋トレ", "ダイエット", "HIIT", "フィットネス", "トレーニング"],
            ["ミニマリスト", "ルームツアー", "インテリア", "持たない暮らし", "収納"],
            ["英語", "英会話", "学習法", "シャドーイング", "リスニング"],
            ["DIY", "100均", "模様替え", "ハンドメイド", "インテリア"],
            ["量子力学", "物理", "科学", "宇宙", "教養"],
            ["カレー", "スパイス", "料理", "レシピ", "本格カレー"],
            ["ゲーム実況", "ホラーゲーム", "絶叫", "実況プレイ", "ゲーム"],
            ["プレゼン", "パワーポイント", "デザイン", "スライド", "資料作成"],
            ["旅行", "VLOG", "ウユニ塩湖", "観光", "絶景", "ボリビア"]
        ]

        data_list = []
        for i in range(min(limit, len(dummy_titles))):
            # 再生回数と登録者数のバリエーションを作成して面白い拡散率を作る
            sub_choices = [500, 1500, 12000, 50000, 150000, 800000]
            subs = sub_choices[i % len(sub_choices)]
            
            # 再生数をランダムに設定（拡散率が1未満〜8倍程度になるように）
            multiplier = np.random.choice([0.15, 0.4, 0.9, 1.2, 2.5, 4.8, 7.5])
            views = int(subs * multiplier)
            if views < 100:
                views = np.random.randint(100, 1200)
            
            likes = int(views * np.random.uniform(0.02, 0.08))
            
            # 公開日
            days_ago = np.random.choice([5, 15, 45, 120, 400, 600])
            pub_date = now - timedelta(days=int(days_ago))
            
            data_list.append({
                "動画ID": f"dummy_id_{i}",
                "タイトル": dummy_titles[i],
                "チャンネル名": dummy_channels[i],
                "チャンネル登録者数": subs,
                "再生回数": views,
                "いいね数": likes,
                "公開日": pub_date,
                "動画URL": f"https://www.youtube.com/watch?v=dummy_id_{i}",
                "説明": f"これは「{dummy_titles[i]}」のテスト用説明文です。チャンネル登録よろしくお願いします！",
                "タグ": dummy_tags[i]
            })
        return pd.DataFrame(data_list)
        
    else:
        # 実際のYouTube APIから取得
        from googleapiclient.discovery import build
        try:
            youtube = build("youtube", "v3", developerKey=api_key)
            
            # 1. 検索実行
            search_response = youtube.search().list(
                q=query,
                part="id,snippet",
                maxResults=limit,
                type="video"
            ).execute()
            
            video_ids = []
            channel_ids = []
            search_items = search_response.get("items", [])
            
            for item in search_items:
                video_ids.append(item["id"]["videoId"])
                channel_ids.append(item["snippet"]["channelId"])
                
            if not video_ids:
                return pd.DataFrame()
                
            # 2. 動画詳細の取得
            video_response = youtube.videos().list(
                part="snippet,statistics",
                id=",".join(video_ids)
            ).execute()
            
            # 3. チャンネル情報の取得 (登録者数)
            channel_response = youtube.channels().list(
                part="statistics",
                id=",".join(list(set(channel_ids)))
            ).execute()
            
            # チャンネル登録者数のマッピング作成
            channel_subs = {}
            for ch in channel_response.get("items", []):
                channel_subs[ch["id"]] = int(ch["statistics"].get("subscriberCount", 0))
                
            # 動画詳細データのパース
            data_list = []
            for video in video_response.get("items", []):
                snippet = video["snippet"]
                stats = video.get("statistics", {})
                ch_id = snippet["channelId"]
                
                # タグの取得
                tags = snippet.get("tags", [])
                
                # 日時パース
                pub_date_str = snippet["publishedAt"]
                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%SZ")
                
                data_list.append({
                    "動画ID": video["id"],
                    "タイトル": snippet["title"],
                    "チャンネル名": snippet["channelTitle"],
                    "チャンネル登録者数": channel_subs.get(ch_id, 0),
                    "再生回数": int(stats.get("viewCount", 0)),
                    "いいね数": int(stats.get("likeCount", 0)),
                    "公開日": pub_date,
                    "動画URL": f"https://www.youtube.com/watch?v={video['id']}",
                    "説明": snippet["description"],
                    "タグ": tags
                })
            return pd.DataFrame(data_list)
        except Exception as e:
            st.error(f"⚠️ エラーが発生しました: {str(e)}")
            return pd.DataFrame()

# --- 検索実行ボタン ---
if st.sidebar.button("🔍 検索・分析を実行", use_container_width=True):
    if not use_demo and not api_key:
        st.error("APIキーを入力してください。または「デモモード」にチェックを入れてください。")
    elif not keyword:
        st.error("検索キーワードを入力してください。")
    else:
        with st.spinner("データを取得中..."):
            df_raw = get_youtube_data(keyword, max_results)
            if not df_raw.empty:
                st.session_state.raw_data = df_raw
                st.session_state.searched_keyword = keyword
                st.success(f"データ取得完了！（取得件数: {len(df_raw)}件）")
            else:
                st.warning("動画データが見つかりませんでした。")

# --- データ分析と表示 ---
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data.copy()
    
    # タイムゾーンを排除して比較可能にする
    df['公開日'] = pd.to_datetime(df['公開日']).dt.tz_localize(None)
    
    # --- 指標計算の追加 ---
    # 拡散率 (再生数 ÷ チャンネル登録者数)
    df['拡散率'] = df['再生回数'] / df['チャンネル登録者数'].replace(0, 1)
    df['拡散率'] = df['拡散率'].round(2)
    
    # 視聴回数星ランクの判定
    def get_star_rank(views):
        if 100 <= views < 1000:
            return "☆1"
        elif 1000 <= views < 10000:
            return "☆2"
        elif 10000 <= views < 100000:
            return "☆3"
        elif views >= 100000:
            return "☆4"
        else:
            return "その他"
            
    df['視聴星ランク'] = df['再生回数'].apply(get_star_rank)
    
    # 拡散率分類の判定
    def get_spread_class(rate):
        if rate < 1:
            return "1未満"
        elif rate < 2:
            return "1倍台"
        elif rate < 3:
            return "2倍台"
        elif rate < 4:
            return "3倍台"
        elif rate < 5:
            return "4倍台"
        else:
            return "5倍以上"
            
    df['拡散率分類'] = df['拡散率'].apply(get_spread_class)
    
    # --- フィルターの適用 ---
    now = datetime.now()
    
    # 1. 公開時期フィルターの適用
    if time_filter == "1か月以内":
        df = df[df['公開日'] >= (now - timedelta(days=30))]
    elif time_filter == "1年以内":
        df = df[df['公開日'] >= (now - timedelta(days=365))]
        
    # 2. 視聴回数（星）フィルターの適用
    selected_star_codes = [view_stars_options[item] for item in selected_stars]
    df = df[df['視聴星ランク'].isin(selected_star_codes)]
    
    # 3. 拡散率フィルターの適用
    selected_spread_codes = [spread_options[item] for item in selected_spreads]
    df = df[df['拡散率分類'].isin(selected_spread_codes)]
    
    # フィルター適用後の結果数チェック
    if df.empty:
        st.warning("⚠️ 選択したフィルター条件に合致する動画がありません。サイドバーのフィルター設定を変更してください。")
    else:
        # メインメトリクスの表示
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("分析対象動画数", f"{len(df)} 件")
        m2.metric("平均再生回数", f"{int(df['再生回数'].mean()):,} 回")
        m3.metric("最大拡散率", f"{df['拡散率'].max():.2f} 倍")
        m4.metric("平均いいね数", f"{int(df['いいね数'].mean()):,} 件")
        
        # タブの作成
        tab1, tab2, tab3 = st.tabs(["📋 動画データ一覧", "📈 統計・可視化", "🏷️ タグ分析（ワードクラウド）"])
        
        # --- TAB1: データ一覧 ---
        with tab1:
            st.subheader(f"🔍 「{st.session_state.searched_keyword}」の動画詳細データ一覧")
            
            # テーブル用に並び替え、リネーム
            display_df = df[[
                "タイトル", "チャンネル名", "視聴星ランク", "再生回数", "チャンネル登録者数", "拡散率", "拡散率分類", "いいね数", "公開日", "動画URL"
            ]].copy()
            
            # 日付フォーマット変更
            display_df['公開日'] = display_df['公開日'].dt.strftime('%Y-%m-%d')
            
            # データフレームの表示
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "動画URL": st.column_config.LinkColumn("YouTubeリンク"),
                    "再生回数": st.column_config.NumberColumn(format="%d 回"),
                    "チャンネル登録者数": st.column_config.NumberColumn(format="%d 人"),
                    "いいね数": st.column_config.NumberColumn(format="%d"),
                    "拡散率": st.column_config.NumberColumn(format="%.2f 倍"),
                },
                hide_index=True
            )
            
            # CSVのダウンロード
            csv = display_df.to_csv(index=False).encode('utf-8_sig')
            st.download_button(
                label="📥 フィルタリング済みデータをCSVとしてダウンロード",
                data=csv,
                file_name=f"youtube_search_{st.session_state.searched_keyword}.csv",
                mime="text/csv"
            )
            
        # --- TAB2: 統計・可視化 ---
        with tab2:
            st.subheader("📊 視聴データ＆拡散の可視化")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 散布図：登録者数 vs 再生数
                st.write("📈 **チャンネル登録者数 と 再生回数 の関係**")
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.scatter(df["チャンネル登録者数"], df["再生回数"], alpha=0.7, color="crimson", edgecolors="black")
                
                # 1対1の線（拡散率 = 1の目安ライン）
                max_val = max(df["チャンネル登録者数"].max(), df["再生回数"].max())
                ax.plot([0, max_val], [0, max_val], linestyle="--", color="gray", label="拡散率 = 1.0 (目安)")
                
                ax.set_xlabel("チャンネル登録者数")
                ax.set_ylabel("再生回数")
                ax.grid(True, linestyle=":", alpha=0.6)
                ax.legend()
                st.pyplot(fig)
                plt.close()
                st.caption("※点線より上にある動画は、チャンネル登録者数よりも多く再生されている「高拡散」動画です。")
                
            with col2:
                # 拡散率の分布棒グラフ
                st.write("📊 **拡散率の分布状況**")
                spread_counts = df['拡散率分類'].value_counts().reindex(["1未満", "1倍台", "2倍台", "3倍台", "4倍台", "5倍以上"]).fillna(0)
                
                fig, ax = plt.subplots(figsize=(6, 4))
                bars = ax.bar(spread_counts.index, spread_counts.values, color="skyblue", edgecolor="black")
                ax.set_ylabel("動画件数")
                ax.set_xlabel("拡散率（再生数 ÷ チャンネル登録者数）")
                ax.grid(axis='y', linestyle=":", alpha=0.6)
                
                # 値を棒の上に表示
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.annotate(f'{int(height)}',
                                    xy=(bar.get_x() + bar.get_width() / 2, height),
                                    xytext=(0, 3),  
                                    textcoords="offset points",
                                    ha='center', va='bottom')
                                    
                st.pyplot(fig)
                plt.close()
                st.caption("※チャンネル登録者数に対して、どれだけの効率で動画が広がったかを示します。")
                
            # 投稿時期別トレンド
            st.write("📆 **投稿日別の再生回数トレンド**")
            trend_df = df.sort_values("公開日")
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(trend_df["公開日"], trend_df["再生回数"], marker="o", color="orange", linewidth=2)
            ax.set_ylabel("再生回数")
            ax.set_xlabel("投稿日")
            ax.grid(True, linestyle=":", alpha=0.6)
            plt.xticks(rotation=15)
            st.pyplot(fig)
            plt.close()
            
        # --- TAB3: タグ分析 ---
        with tab3:
            st.subheader("🏷️ 設定されているタグの傾向")
            
            # タグデータのフラット化
            all_tags = []
            for tags_list in df['タグ']:
                if isinstance(tags_list, list):
                    all_tags.extend(tags_list)
                    
            if not all_tags:
                st.info("この動画リストのタグ情報は見つかりませんでした。")
            else:
                # 頻出タグの集計
                tag_counts = pd.Series(all_tags).value_counts()
                
                col_left, col_right = st.columns([1.2, 0.8])
                
                with col_left:
                    st.write("☁️ **タグのワードクラウド (WordCloud)**")
                    # 単語頻度のディクショナリ
                    word_freq = tag_counts.to_dict()
                    
                    try:
                        # ワードクラウドの生成
                        if font_path:
                            wc = WordCloud(font_path=font_path, width=800, height=450, background_color='white', colormap='tab10').generate_from_frequencies(word_freq)
                        else:
                            wc = WordCloud(width=800, height=450, background_color='white', colormap='tab10').generate_from_frequencies(word_freq)
                            
                        fig, ax = plt.subplots(figsize=(8, 4.5))
                        ax.imshow(wc, interpolation='bilinear')
                        ax.axis("off")
                        st.pyplot(fig)
                        plt.close()
                    except Exception as wc_err:
                        st.error(f"ワードクラウドの描画でエラーが発生しました: {str(wc_err)}")
                        
                with col_right:
                    st.write("📊 **頻出タグ TOP 10**")
                    top_tags = tag_counts.head(10)
                    
                    fig, ax = plt.subplots(figsize=(5, 5))
                    ax.barh(top_tags.index[::-1], top_tags.values[::-1], color="lightgreen", edgecolor="black")
                    ax.set_xlabel("出現回数")
                    ax.grid(axis='x', linestyle=":", alpha=0.6)
                    st.pyplot(fig)
                    plt.close()

else:
    # 検索がまだ行われていない時の初期画面
    st.info("👈 左側のサイドバーから条件を設定し、「検索・分析を実行」をクリックしてください。")
    
    # 仕組みの簡単な解説カード
    st.subheader("💡 拡散率とは？")
    st.markdown("""
    **拡散率 = 再生回数 ÷ チャンネル登録者数**
    
    YouTubeにおいて「登録者数の割に爆発的に再生されたバズ動画」を炙り出すための指標です。
    * **拡散率 1.0 未満**：主に既存の登録者に視聴されている標準的な動画
    * **拡散率 1.0 〜 3.0**：おすすめや関連動画に載り、順調に外部へ拡散している動画
    * **拡散率 5.0 以上**：登録者数を大幅に超える視聴を獲得している、トレンド入りした超人気（バズ）動画
    """)
