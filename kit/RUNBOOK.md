# Quick News - 1日1分で社会がわかる（1本1ニュースのショート動画・1日3本）

**視聴者**：就活・試験勉強・ビジネスのために時事に詳しくなりたいが、ショート動画ばかり見てしまいニュースを読めていない人。
**トーン**：信頼できる、落ち着いた、簡潔。煽らない。キャラクターは出さない。
**形式**：1本の動画で1つのニュース。1日3本。1080x1920・30fps。**必ず61秒以上**（収益化の条件。上限の目安は89秒）。
**配信**：TikTok、YouTube ショート、Instagram リール（Metricool で予約投稿）。

制作キット（エンジン・準備スクリプト・台本見本・表紙ツール・公開スクリプト）は公開リポジトリの `kit/` にある：
https://github.com/shortnewschannel07-ux/QuickNews

---

## A. デザインの決まり（ユーザーの指示。すべて守る）

### ブランド
- チャンネル名「Quick News」、キャッチコピー「1日1分で社会がわかる」。
- ロゴは「Quick News」と大文字・小文字を混ぜて書く（全部大文字にしない）。「News」だけ青。ピリオドは付けない。ヘッダーのロゴは大きく目立たせる。
- 締めの呼びかけは「フォローして毎朝の習慣に」。「チャンネル登録」とは言わない。
- 書体は游ゴシック（なければ Zen Kaku Gothic New）。

### 色
- 白ベースに青のアクセント（信頼感）。紺は背景・文字、白は地。
- 足してよい色は1色まで。いまは橙（青の補色・注目／前向きな動き）を全体の1割ほど、上昇の線・矢印・ピン・ロゴ周りの点などにだけ使う。
- 危険・流出などは赤を使ってよい。
- カラフルなフラットイラストは安っぽく見えるので使わない。

### レイアウト・文字
- **余白**：ヘッダーと見出しの間、見出しと図の間、図と字幕の間を詰めない。エンジンが書き出しのたびに余白を自動調整する（見出しの下72px以上、字幕の上56px以上、空きは上1：下2）。書き出しの記録に `[layout] … 超過` が出たら、その場面の図や文言を減らして作り直す。
- **左端**：見出し・小見出し・数字・図の始点・カードの列は、すべての場面で同じ左端（96px）にそろえる。中央に置く図は本文の幅の中央にそろえる。
- **文字の配置**：見出しの大きさ・行間・字間は全場面で統一。画面上部の見出しは同じ高さから始める。
- **重なり**：線グラフと文字を重ねない。近くに置くときは色を分ける（数字は青、線は橙）。
- **一覧**：行の頭に線のアイコンを付ける。
- 背景やイラストは内容と関係のあるものだけ。意味のない海・円・四角などは置かない。
- 図解は、ぱっと見て論理が伝わる構成にする。用語の説明は意味のある図にする（例：G7 なら世界地図で加盟国が順に光り、国名チップが連動）。

### 動き
- 動きは多く、ダイナミックに（減らさない）。画面が次々と入れ替わるようにする。
- 地点から地点へ移動する感じ（カメラが追う、着地の衝撃、点線の軌跡、背景色の広がり）を付ける。
- 変形アニメーション（形がいったん円になって別の形に変わる）を、本文の中に1か所以上入れる（例：電力の話なら、地球儀が縮んで稲妻に変わる）。締めのロゴも変形で組み上げる。
- Kurzgesagt や TED-Ed のような説明的なアニメーションは、内容がわかりやすくなる場面で使う。ただし、アカウントの洗練された雰囲気に合わせる。

### ナレーション
- VOICEVOX:冥鳴ひまり（1.vvm、id 14、抑揚 1.15）。自然な日本語の抑揚で話す。
- 句点・読点の間は短く詰める（エンジンが前後の無音を削り、文と文の間を短くする）。
- 読み間違えやすい語（数字＋単位、G7、外相、上げ幅、AI など）は `reading` に読みを書く。

### 構成（離脱させない）
- **冒頭の要約は入れない**。いきなりそのニュースの大見出しから始める。
- **1コマ目**から、画面幅いっぱいの大見出し（ビジュアルフック）を出す。地図など、そのニュースの絵と組み合わせる。見出しは上下の余白のバランスがとれる位置に置き、下にナレーションの補足を1行添える。冒頭はそのニュースの事実そのもの（例「G7外相会合／パリで閉幕」）で始め、言い換えて煽らない。
- 3〜5秒ごとに画面を変える。
- 中盤に再フックを入れる（例「本題は *ここから*」「でも *期待は薄い？*」など、問いや転換の見出し）。
- 終盤に、持ち帰れる要約を置く（「ここだけ *押さえる*」で結論・次の焦点・見方の3行）。
- **無音でも追えるようにする**：全場面にナレーションの字幕を出す。例外は、見出しと補足でナレーションの内容がすべて画面にある冒頭の大見出しと、呼びかけがボタンとして画面にある締めだけ。
- コピーのような宣伝文句は動画の中に入れない。

---

## B. キャプションの型（この形を守る）

```
1日1分見るだけ、時事に詳しい人になる。

●{M/D}の重要ニュース
{何が起きたかの1行}
・{要点1}
・{要点2}
・{要点3}

●今日の用語
{用語}＝{一般に確立した定義}

フォローして毎朝の習慣を作ろう

出典：{媒体名、発表元}
音声：VOICEVOX:冥鳴ひまり

#時事 #ニュース #就活 #時事問題 #{話題のタグ1〜3} #QuickNews
```
- 冒頭の1行は、毎回この紹介文で固定する（アカウントの宣伝）。
- YouTube のタイトルは「{見出し}｜{要点}」の形で、末尾に「 #Shorts」を付ける。全体で60字前後まで。

## C. 表紙（サムネ）の決まり
- カードや色の帯は使わない。白地・紺の文字・強調は青1色。どぎつい配色にしない。
- 数字だけを大きくしない。何のニュースかが一読でわかる見出しを大きく出す。
- 構成：上にロゴと日付（小）→ ラベル（例「国際｜G7外相会合」）→ 大きな見出し3行（要点の句だけ青）→ 続きが気になる問いの補足2行（灰色）→ そのニュースの地図や図（任意）→ 下にキャッチコピー（小）。
- プロフィール一覧では中央の 3:4（上下240pxずつ切れる）しか見えないので、すべてその範囲に収める。
- 台本の `cover` に {label, title, sub, map?} を書き、`python3 tools/cover.py 台本.json 表紙.png` で作る。投稿用に JPEG に変換する。

---

## D. 毎日の手順（1回の実行で3本作り、予約する）

1. **準備**
   - current_time で日本時間の日付と曜日を確認する。
   - `git clone https://github.com/shortnewschannel07-ux/QuickNews 作業フォルダ/repo` でキットを取得する（公開なので認証は不要）。
   - `bash repo/kit/setup.sh 作業フォルダ/qn` を実行する。最後に表示される `VOICEVOX_DIR=… QN_FONT_DIR=…` を、以降の qn_short.py・cover.py・peek.py の実行に必ず付ける。
   - 動画を置くために、add_repo（owner: shortnewschannel07-ux、repo: QuickNews、access: push）でリポジトリへの書き込みを有効にする。
2. **ニュースを3本選ぶ**
   - 優先順位は 政治・国際 → 経済 → 社会。原則として各分野から1本ずつ選び、7:00 に政治・国際、12:00 に経済、20:00 に社会を出す。その分野に重要なニュースがない日は、政治・国際、次に経済から2本目を選ぶ。
   - `repo/media/posted.json`（投稿済みの話題の記録）を読み、3日以内に扱った話題と同じものは避ける。
   - WebSearch（mode: extended）で当日・前日のニュースを調べる。面接・試験・商談で話題になりやすいものを選ぶ。
   - 各ニュースは WebFetch で記事本文を開き、数字・固有名詞・日付・対象範囲を本文で確認する。可能なら2つ目の媒体や公式発表（省庁・企業）でも確認する。NHK、共同通信（地方紙の配信記事も可）、時事、日経、各社・各省の公式発表を優先する。
   - 本文で確認できない事実は書かない。続報待ちの速報は避ける。自殺・性犯罪・残虐な事件の詳細は扱わない。政治は事実だけを中立に書く。
   - 発言の引用は記事の要旨にとどめ、話し手の肩書きに「（要旨）」と添える。
3. **台本を書く**（1本ずつ。`kit/script_example.json` と同じ形）
   - 上位の項目：channel "Quick News"、tagline "1日1分で社会がわかる"、date_label（例 "2026.11.10 TUE"）、voice {file "1.vvm", id 14, name "冥鳴ひまり", intonation 1.15, pause 0.2}、speed 1.15、min_seconds 61、max_seconds 89、title、cover。
   - **構成の目安（合計62〜70秒）**
     1. 冒頭の大見出し（約4秒）：場所があるニュースは `globe`（mode zoom）に `hero: true, hero_size 140前後, map_h 600, hero_top 980, hero_sub（補足1行）, title_at -0.6`。場所がないニュースは `headline`（size 120前後）を使う。
     2. なぜ？・何が起きた？（約9秒）：`morph` の2ショットで、地点の移動と変形を見せる。
     3. 用語（約6秒）：`term`。加盟国などがあれば members で地図に光らせる。
     4. 背景・ほかの論点（約8秒）：`nodes`（3つ。ナレーションの1文ごとに1つずつ出る）。
     5. 本題・次の焦点（約9秒）：見出しで再フックする。
     6. 各国・各者の見方（約13秒）：`quotes`。
     7. ここだけ押さえる（約7秒）：`list` の3行。
     8. 締め（約4秒）：`morph` の logo（tagline「1日1分で社会がわかる」、cta「フォローして毎朝の習慣に」、ナレーション「フォローして、毎朝の習慣に。」）。
   - 内容が足りなくて61秒に届かないときは、間延びさせずに、事実の背景・関係者の発言・数字の比較などの中身を足す（エンジンは最後の手段として話す速さを落とし、締めを延ばす）。
   - 各場面に `story: 1`、`section`（例「国際｜外交」）、`source`（媒体名）を付ける。
   - 見出しは、青にする語を前後に半角スペースを入れて `*…*` で囲む（例 " *電力* を支え続ける"）。改行は `\n`。1行は8〜9文字まで。
   - 1場面のナレーション（beats）は1〜3文。ニュースの言葉で、です・ます調。
   - 図や数字は記事にあるものだけで作る。架空のグラフや推計値を描かない。報道写真・映像・企業ロゴは使わない。
   - 実在企業を名乗る詐欺の例は「◯◯を名乗るメール（例）」と書き、本物と誤認させない。
   - かなの「は」は「わ」と読まれないことがあるので、助詞の前の語は漢字のままにする。
4. **読みを確認する**：各 beat の reading（なければ say）を `pyopenjtalk.g2p(text, kana=True)` にかけ、誤読があれば reading を直す。
5. **見本フレームで確認する**：`python3 peek.py 台本.json 場面番号 秒,秒 出力.jpg` で、各場面の後半を見る。見出しの改行、はみ出し、重なり、余白、左端のずれを確かめ、問題があれば台本を直す。
6. **書き出す**：`python3 qn_short.py 台本.json news_YYYYMMDD_N.mp4`（1本10〜15分）。記録の `layout` 行に `[layout] … 超過` がないこと、`duration` が61秒以上であることを確かめる。
7. **確認する**：ffprobe で長さ（61秒以上）と解像度（1080x1920）を見る。1コマ目に大見出しが出ていること。数字・固有名詞を取材メモと照らし合わせる。
8. **表紙を作る**：`python3 tools/cover.py 台本.json cover.png` → JPEG（品質92）に変換する。
9. **置く**：`bash repo/kit/tools/publish.sh repo YYYY-MM-DD スラッグ 動画.mp4 表紙.jpg` で、動画と表紙を公開リポジトリに置く。表示された VIDEO_URL と COVER_URL を使う。`repo/media/posted.json` に {date, slot, title, topic} を追記して、同じスクリプトで一緒にコミットする。
10. **予約投稿**（Metricool）
    - getBrandSettings でブランド（Quick News、blogId 8023514、時間帯 Asia/Tokyo）を確認する。
    - createScheduledPost で予約する。
      - date/publicationDate：当日 07:00 / 12:00 / 20:00（日本時間）。すでに過ぎた時刻なら、その日の次の枠か、15分後にする。
      - providers：tiktok、youtube、instagram。media：[VIDEO_URL]。videoThumbnailUrl：COVER_URL。text：キャプション（B の型）。
      - youtubeData：{title, type "short", privacy "public", tags, category "NEWS_POLITICS", madeForKids false, isAiGeneratedContent false}
      - tiktokData：{privacyOption "PUBLIC_TO_EVERYONE", title（見出し）, isAigc true, disableComment false, disableDuet false, disableStitch false, autoAddMusic false}
      - instagramData：{type "REEL", showReelOnFeed true, isAiGenerated true}
      - draft false、autoPublish true。
    - VIDEO_THUMBNAIL_NOT_APPLICABLE で断られたら、videoThumbnailUrl を外して同じ内容で予約し直す。
    - 予約に失敗したら、理由を1行添えて、動画・表紙・キャプションを届ける（ユーザーが手で投稿できるように）。
11. **届ける**：3本分の mp4 と表紙を SendUserFile（status: proactive）で送る。SendUserMessage で、各本のタイトル・予約時刻・Metricool の plannerUrl・出典URL一覧を送る。

## E. テンプレート（scenes[].type）

共通：`beats: [{say, reading?, cap?, pad?}]`、`story`、`section`、`source`、`captions`（false で字幕を出さない）。

| type | 演出 | 主な項目 |
|---|---|---|
| globe（zoom） | 世界→地域→国→都市へ寄る地図＋ピン。hero で冒頭の大見出し | target [経度,緯度], hl [国番号], stages[4], pin, pin_sub, title, hero, hero_size, hero_top, hero_sub, map_h, title_at |
| globe（route） | 2地点を弧で結ぶ地球儀＋結果の帯 | title, from [名,補足], from_at, from_id, to, to_at, to_id, chip（"bolt"など）, result_key, result |
| morph | 地点から地点へ移動しながら形が変わる。背景色が着地点から広がる | shots[{bg: blue/navy/white, icon: globe/bolt/bubble/lock/card/chart/arrow/dot, icon2, icon2_at, visual: globe/ripple/spark/bars/records/cards/logo, kicker, big, number, prefix, unit, hl, pin, target}], anchor_offset |
| term | 今日の用語。members があれば世界地図で順に光り、国名チップと連動 | term, reading, members[{label,id,at}], extra{label,ids} |
| nodes | 3つの段が線でつながる（最後が青） | title, nodes[{key,value}] |
| quotes | 発言の引用（話し手・肩書き・発言） | title, quotes[{who, role, text}] |
| list | 行が順に入り、状態ラベルが付く（行頭に線アイコン） | title, rows[{label, state, neg, icon: person/home/phone/mail/key/card/calendar}] |
| headline | 左揃えの大見出し＋補足＋大きな数字 | eyebrow, text, sub, big, big_label, size |
| illus | 決まった図解（status_quo / market / breach） | illus, title |
| stat / wall / phone / zoom / flash / route | そのほかの表現 | qn_short.py の各関数を参照 |

## F. 離脱分析と改善提案（毎週の別タスク）
- 書き出すと、動画の隣に `*.timeline.json`（場面ごとの開始・終了秒、ナレーションの各文の開始秒）ができる。publish.sh が `media/日付/スラッグ.timeline.json` として一緒に置く。
- 秒単位の視聴維持率カーブは、Metricool・Windsor のどちらからも取れない。取れる指標で「どこで離れたか」を推定する。
  - Instagram リール：retention（平均視聴割合）、averageWatchTime、reelsSkipRate（最初の3秒で離れた割合）、reelsViewRate。
  - TikTok：fullVideoWatchedRate（完走率）、平均視聴時間（totalTimeWatched ÷ views）、流入元（おすすめ・フォロー・検索）。
  - YouTube（Windsor の youtube）：average_view_duration、average_view_percentage、views と engaged_views の比（冒頭で離れた割合の目安）。
  - 平均視聴時間を timeline.json に当てはめ、その秒数で流れている場面・文を「離脱の山」とみなす。本数が増えたら、場面の種類・順番・冒頭の見出しの型・ジャンル・投稿時刻ごとに比べる。
- 提案は採用されるまで、スキル・RUNBOOK・台本の型を書き換えない。
