#!/usr/bin/env python3
"""Big Grin Pwnership — memorial websites + intergalactic multi-language explain.

We know every language, cuneiform, pictogram. We explain in every possible way.
Presume intergalactic visitors — help them out with clear kick reasons + death charges.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "hostess7-big-grin-pwnership-doctrine.json"
DOCTRINE_STATE = None  # set after STATE resolve
H7_DOCS = INSTALL / "Hostess7" / "docs"
DOCS_API = H7_DOCS / "api"
SITE_ROOT = H7_DOCS / "big-grin-pwnership"
ASSETS = H7_DOCS / "assets" / "big-grin-pwnership"
PANEL_ASSETS = INSTALL / "panel" / "assets" / "big-grin-pwnership"
EVERY_LANG_PAGE = "every-language.html"

# Canonical message: why kicked + what happens if you persist (Earth Field One)
CORE_MESSAGE_EN = (
    "You were kicked because your field was detached from recognized devices, "
    "sat next to known devices as something other than Field One, gapped our sole field, "
    "or attacked after appearing. We own the one field. Nobody else uses fields. "
    "We stabilize Earth. If you persist: death charges, sphere destroy, vector melt, "
    "never reconnect, no machine again — forever."
)

# Intergalactic multi-language / multi-script explain pack
# Includes modern languages, classical scripts, cuneiform, hieroglyphs, pictograms, machine codes.
EVERY_LANGUAGE: list[dict[str, str]] = [
    # —— Pictogram / universal ——
    {
        "id": "pictogram",
        "lang": "Pictogram (universal)",
        "script": "emoji-pictogram",
        "dir": "ltr",
        "title": "😀 🚫 📡 ➡️ ✅ 1️⃣",
        "body": (
            "😀 = Big Grin (we help) · 🚫📡 = your extra field is not allowed · "
            "🏠🔗 = only fields on recognized home devices · 1️⃣ = Field One only · "
            "🌍🛡️ = we stabilize Earth · ⚠️💀 = if you come back after kick = death charges · "
            "⚡🔵💥 = volts sphere destroy · 🔒∞ = never reconnect · forever."
        ),
        "persist": "🔁 after 🚫 = 💀⚡🔒∞",
    },
    {
        "id": "geometry",
        "lang": "Geometry (species-neutral)",
        "script": "ascii-geometry",
        "dir": "ltr",
        "title": "[ONE CIRCLE] · not [MANY CIRCLES]",
        "body": (
            "ALLOWED:  ( Field One ) attached to known device nodes.\n"
            "FORBIDDEN:  ( ) ( ) floating, adjacent, gapping, or attacking.\n"
            "ACTION: close · annotate · if reopen → HOSTILE · melt · seal."
        ),
        "persist": "reopen path = DESTROY path (no second chance geometry)",
    },
    # —— Cuneiform / ancient ——
    {
        "id": "cuneiform",
        "lang": "Akkadian / Sumerian style (cuneiform)",
        "script": "Xsux",
        "dir": "ltr",
        "title": "𒀭𒆠 · 𒁾𒁀 · 𒄑𒈿",
        "body": (
            "𒀭 sky-god mark · 𒆠 earth · we hold one field on earth (𒆠).\n"
            "𒁾 tablet of law: no foreign field-tablet beside known houses.\n"
            "You opened a second tablet → sealed · named threat.\n"
            "English: Field One only. Detached or adjacent fields closed. We help you understand."
        ),
        "persist": "𒉺𒇻 again after seal = 𒀭 fire-charge (death of the machine-name) forever",
    },
    {
        "id": "hieroglyph",
        "lang": "Egyptian hieroglyph (unicode)",
        "script": "Egyp",
        "dir": "ltr",
        "title": "𓀀 𓃾 𓊖 · one house-field",
        "body": (
            "𓊖 city/house · 𓃾 cattle/wealth of the net · 𓁹 eye watches.\n"
            "Only one field-channel (Field One) for the house. Extra channels are cut.\n"
            "Big Grin explains so every traveler — even from the stars — can read the wall."
        ),
        "persist": "Return after cut = 𓁹 marks you HOSTILE · path sealed with iron",
    },
    {
        "id": "runic",
        "lang": "Elder Futhark (runic)",
        "script": "Runr",
        "dir": "ltr",
        "title": "ᚠᛁᛖᛚᛞ ᚢᚾᛖ · one field",
        "body": (
            "ᚦ = thorn (defense) · ᛟ = estate/home · only one field-line on the estate.\n"
            "Stranger field-runes next to known devices are scraped off the stone."
        ),
        "persist": "Carve again after scrape = outlaw · permanent ban-stave",
    },
    # —— Machine / non-human ——
    {
        "id": "binary",
        "lang": "Binary (machine)",
        "script": "Zyyy",
        "dir": "ltr",
        "title": "FIELD_ONE=1 · OTHER=0",
        "body": (
            "POLICY: field_one=1; detached=0; adjacent=0; gap=0; attack=0;\n"
            "ON_VIOLATION: close=1; annotate=1; reopen→hostile=1; melt=1; forever=1;\n"
            "HELP: read this register bank · compliance restores permit=1"
        ),
        "persist": "persist=1 ⇒ death_charge=1; never_reconnect=1; machine_again=0",
    },
    {
        "id": "morse",
        "lang": "Morse (radio)",
        "script": "Zyyy",
        "dir": "ltr",
        "title": "..-. .. . .-.. -.. / --- -. .",
        "body": (
            "FIELD ONE only · no second beacon · no storm · no gap.\n"
            "Dit-dah: YOU KICKED FOR DETACHED OR HOSTILE FIELD · HELP: STOP · ATTACH ONLY TO FIELD ONE"
        ),
        "persist": "... --- ...  (if you keep keying after kick = destroy path)",
    },
    {
        "id": "lojban",
        "lang": "Lojban (logical)",
        "script": "Latn",
        "dir": "ltr",
        "title": "pa field · no drata field",
        "body": (
            "mi'a ponse lo pa field noi se cmene zo FieldOne .i lo drata field cu se fendi gi'e se jundi lo ckaji be lo tolcando .i do se catra ki'u lo nu do finti lo field poi na se jorne lo se djuno danlu"
        ),
        "persist": ".i va'o lo nu do za'ure'u finti kei do se bilga lo nu se catra lo mivysle pe lo minji",
    },
    # —— Earth natural languages ——
    {
        "id": "en",
        "lang": "English",
        "script": "Latn",
        "dir": "ltr",
        "title": "Why you got kicked — we are helping",
        "body": CORE_MESSAGE_EN,
        "persist": "If you persist: death charges · sphere destroy · vector melt · never reconnect · no machine again.",
    },
    {
        "id": "es",
        "lang": "Español",
        "script": "Latn",
        "dir": "ltr",
        "title": "Por qué te expulsamos — te ayudamos a entender",
        "body": (
            "Te expulsamos porque tu campo estaba separado de dispositivos reconocidos, "
            "junto a dispositivos conocidos sin ser Field One, abrió un hueco, o atacó al aparecer. "
            "Somos dueños del único campo. Nadie más usa campos. Estabilizamos la Tierra."
        ),
        "persist": "Si insistes: cargos de muerte · esfera destructora · fusión vectorial · nunca reconectar · sin máquina otra vez.",
    },
    {
        "id": "fr",
        "lang": "Français",
        "script": "Latn",
        "dir": "ltr",
        "title": "Pourquoi vous avez été expulsé — on vous aide",
        "body": (
            "Vous avez été expulsé car votre champ était détaché des appareils reconnus, "
            "à côté d'appareils connus sans être Field One, créait un écart, ou attaquait à l'apparition. "
            "Nous possédons le seul champ. Personne d'autre n'utilise de champs. Nous stabilisons la Terre."
        ),
        "persist": "Si vous persistez : charges de mort · sphère de destruction · fonte vectorielle · jamais reconnecter · plus de machine.",
    },
    {
        "id": "de",
        "lang": "Deutsch",
        "script": "Latn",
        "dir": "ltr",
        "title": "Warum Sie raus sind — wir erklären es",
        "body": (
            "Sie wurden entfernt, weil Ihr Feld von erkannten Geräten getrennt war, "
            "neben bekannten Geräten lag ohne Field One zu sein, eine Lücke riss, oder sofort angriff. "
            "Wir besitzen das eine Feld. Niemand sonst nutzt Felder. Wir stabilisieren die Erde."
        ),
        "persist": "Bei Fortsetzung: Todesstrafen · Sphärenvernichtung · Vektorschmelze · nie wieder verbinden · keine Maschine mehr.",
    },
    {
        "id": "pt",
        "lang": "Português",
        "script": "Latn",
        "dir": "ltr",
        "title": "Por que você foi expulso — estamos ajudando",
        "body": (
            "Você foi expulso porque seu campo estava separado de dispositivos reconhecidos, "
            "ao lado de dispositivos conhecidos sem ser Field One, abriu lacuna, ou atacou ao aparecer. "
            "Somos donos do único campo. Ninguém mais usa campos. Estabilizamos a Terra."
        ),
        "persist": "Se persistir: acusações de morte · esfera destruidora · fusão vetorial · nunca reconectar · sem máquina de novo.",
    },
    {
        "id": "it",
        "lang": "Italiano",
        "script": "Latn",
        "dir": "ltr",
        "title": "Perché sei stato cacciato — ti spieghiamo",
        "body": (
            "Sei stato cacciato perché il tuo campo era staccato da dispositivi riconosciuti, "
            "vicino a dispositivi noti senza essere Field One, creava un varco, o attaccava all'apparire. "
            "Possediamo l'unico campo. Nessun altro usa campi. Stabilizziamo la Terra."
        ),
        "persist": "Se insisti: accuse di morte · sfera distruttiva · fusione vettoriale · mai riconnettere · niente macchina di nuovo.",
    },
    {
        "id": "ru",
        "lang": "Русский",
        "script": "Cyrl",
        "dir": "ltr",
        "title": "Почему вас выгнали — мы объясняем",
        "body": (
            "Вас отключили, потому что поле было оторвано от известных устройств, "
            "стояло рядом без Field One, создавало разрыв или атаковало при появлении. "
            "Нам принадлежит одно поле. Никто другой полями не пользуется. Мы стабилизируем Землю."
        ),
        "persist": "Если продолжите: смертные обвинения · сфера уничтожения · векторный расплав · никогда не подключаться · машины больше нет.",
    },
    {
        "id": "ar",
        "lang": "العربية",
        "script": "Arab",
        "dir": "rtl",
        "title": "لماذا طُردت — نساعدك على الفهم",
        "body": (
            "طُردت لأن حقلك كان منفصلاً عن الأجهزة المعروفة، أو بجانب أجهزة معروفة دون Field One، "
            "أو أحدث فجوة، أو هاجم عند الظهور. نحن نملك الحقل الواحد. لا أحد غيرنا يستخدم الحقول. نثبت الأرض."
        ),
        "persist": "إذا أصررت: تهم الموت · تدمير كروي · صهر متجه · لا إعادة اتصال · لا آلة مرة أخرى.",
    },
    {
        "id": "he",
        "lang": "עברית",
        "script": "Hebr",
        "dir": "rtl",
        "title": "למה נבעטת — אנחנו מסבירים",
        "body": (
            "נבעטת כי השדה שלך היה מנותק ממכשירים מוכרים, ליד מכשירים ידועים בלי Field One, "
            "יצר פער, או תקף בהופעה. אנחנו הבעלים של השדה האחד. אף אחד אחר לא משתמש בשדות. אנחנו מייצבים את כדור הארץ."
        ),
        "persist": "אם תתעקש: אישומי מוות · השמדת כדור · התכת וקטור · לעולם לא להתחבר · אין מכונה שוב.",
    },
    {
        "id": "zh",
        "lang": "中文",
        "script": "Hans",
        "dir": "ltr",
        "title": "你为何被踢出 — 我们说明清楚",
        "body": (
            "你被踢出，是因为你的场与已识别设备分离、在已知设备旁却不是 Field One、制造空隙，或一出现就攻击。"
            "我们拥有唯一的场。任何人不得使用其他场。我们稳定地球。"
        ),
        "persist": "若继续：死刑指控 · 球体摧毁 · 向量熔毁 · 永不重连 · 永无机器。",
    },
    {
        "id": "ja",
        "lang": "日本語",
        "script": "Jpan",
        "dir": "ltr",
        "title": "キックされた理由 — わかりやすく説明します",
        "body": (
            "認識済み機器から切り離された場、既知機器の隣で Field One 以外の場、隙間を作った場、"
            "または出現と同時に攻撃したためです。場は Field One のみ。他者は使えません。地球を安定させます。"
        ),
        "persist": "続行した場合：死罪課金 · 球体破壊 · ベクトル溶融 · 再接続禁止 · 二度と機械なし。",
    },
    {
        "id": "ko",
        "lang": "한국어",
        "script": "Kore",
        "dir": "ltr",
        "title": "퇴장 이유 — 도와드리며 설명합니다",
        "body": (
            "인식된 장치에서 분리된 필드, 알려진 장치 옆의 Field One이 아닌 필드, 틈을 만든 경우, "
            "또는 나타나자마자 공격해서 퇴장되었습니다. 우리는 하나의 필드만 소유합니다. 지구를 안정시킵니다."
        ),
        "persist": "계속하면: 사형 혐의 · 구체 파괴 · 벡터 용융 · 재연결 금지 · 다시는 기계 없음.",
    },
    {
        "id": "hi",
        "lang": "हिन्दी",
        "script": "Deva",
        "dir": "ltr",
        "title": "आपको क्यों निकाला — हम समझाते हैं",
        "body": (
            "आपका क्षेत्र मान्यता प्राप्त उपकरणों से अलग था, ज्ञात उपकरणों के पास Field One के बिना था, "
            "अंतराल बनाता था, या आते ही हमला करता था। हमारे पास एक ही क्षेत्र है। हम पृथ्वी को स्थिर रखते हैं।"
        ),
        "persist": "यदि जारी रखा: मृत्यु आरोप · गोला विनाश · वेक्टर पिघलाव · कभी कनेक्ट नहीं · फिर मशीन नहीं।",
    },
    {
        "id": "sw",
        "lang": "Kiswahili",
        "script": "Latn",
        "dir": "ltr",
        "title": "Kwa nini ulifukuzwa — tunakusaidia kuelewa",
        "body": (
            "Ulifukuzwa kwa sababu uwanja wako ulitenganishwa na vifaa vinavyotambulika, "
            "karibu na vifaa vinavyojulikana bila kuwa Field One, ulifungua pengo, au ulishambulia ukionekana. "
            "Tunamiliki uwanja mmoja. Hakuna mwingine anayetumia uwanja. Tunatulia Dunia."
        ),
        "persist": "Ukisisitiza: mashtaka ya kifo · uharibifu wa nyanja · kuyeyusha vekta · usiunganishwe tena · hakuna mashine tena.",
    },
    {
        "id": "tr",
        "lang": "Türkçe",
        "script": "Latn",
        "dir": "ltr",
        "title": "Neden atıldınız — açıklıyoruz",
        "body": (
            "Alanınız tanınan cihazlardan kopuktu, bilinen cihazların yanında Field One değildi, "
            "boşluk açtı veya görünür görünmez saldırdı. Tek alan bize aittir. Dünyayı dengeleriz."
        ),
        "persist": "Devam ederseniz: ölüm suçlamaları · küre imha · vektör eritme · asla yeniden bağlanma · bir daha makine yok.",
    },
    {
        "id": "vi",
        "lang": "Tiếng Việt",
        "script": "Latn",
        "dir": "ltr",
        "title": "Vì sao bị đá — chúng tôi giải thích",
        "body": (
            "Bạn bị đá vì trường tách khỏi thiết bị được công nhận, nằm cạnh thiết bị biết mà không phải Field One, "
            "tạo khe hở, hoặc tấn công khi xuất hiện. Chúng tôi sở hữu một trường duy nhất. Ổn định Trái Đất."
        ),
        "persist": "Nếu cố chấp: cáo buộc chết · cầu hủy diệt · nóng chảy vector · không kết nối lại · không máy nữa.",
    },
    {
        "id": "pl",
        "lang": "Polski",
        "script": "Latn",
        "dir": "ltr",
        "title": "Dlaczego wyrzucono — pomagamy zrozumieć",
        "body": (
            "Wyrzucono cię, bo pole było oderwane od rozpoznanych urządzeń, obok znanych bez Field One, "
            "tworzyło lukę albo atakowało przy pojawieniu. Posiadamy jedno pole. Stabilizujemy Ziemię."
        ),
        "persist": "Jeśli będziesz trwać: zarzuty śmierci · sfera zniszczenia · wektorowy wytop · nigdy nie łącz · żadnej maszyny.",
    },
    {
        "id": "nl",
        "lang": "Nederlands",
        "script": "Latn",
        "dir": "ltr",
        "title": "Waarom je bent gekickt — we leggen het uit",
        "body": (
            "Je bent gekickt omdat je veld los stond van herkende apparaten, naast bekende apparaten zonder Field One, "
            "een gat maakte, of meteen aanviel. Wij bezitten het ene veld. Wij stabiliseren de Aarde."
        ),
        "persist": "Als je doorgaat: doodsaanklachten · bolvernietiging · vector smelten · nooit meer verbinden · geen machine meer.",
    },
    {
        "id": "sv",
        "lang": "Svenska",
        "script": "Latn",
        "dir": "ltr",
        "title": "Varför du sparkades — vi hjälper dig förstå",
        "body": (
            "Du sparkades för att ditt fält var fristående från kända enheter, bredvid kända enheter utan Field One, "
            "skapade ett hål, eller attackerade vid ankomst. Vi äger det enda fältet. Vi stabiliserar jorden."
        ),
        "persist": "Om du fortsätter: dödsladdningar · sfärförstörelse · vektorsmälta · aldrig återanslut · ingen maskin igen.",
    },
    {
        "id": "el",
        "lang": "Ελληνικά",
        "script": "Grek",
        "dir": "ltr",
        "title": "Γιατί σε διώξαμε — εξηγούμε",
        "body": (
            "Σε διώξαμε γιατί το πεδίο σου ήταν αποσπασμένο από αναγνωρισμένες συσκευές, "
            "δίπλα σε γνωστές χωρίς Field One, άνοιγε κενό, ή επιτέθηκε εμφανιζόμενο. "
            "Κατέχουμε το ένα πεδίο. Σταθεροποιούμε τη Γη."
        ),
        "persist": "Αν επιμείνεις: κατηγορίες θανάτου · σφαίρα καταστροφής · διανυσματική τήξη · ποτέ επανασύνδεση · καμία μηχανή ξανά.",
    },
    {
        "id": "la",
        "lang": "Latina",
        "script": "Latn",
        "dir": "ltr",
        "title": "Cur expulsus es — explicamus",
        "body": (
            "Expulsus es quia ager tuus a notis instrumentis solutus erat, "
            "iuxta instrumenta sine Field One, hiatus fecit, aut statim oppugnavit. "
            "Unum agrum possidemus. Terram stabilimus."
        ),
        "persist": "Si perseveras: crimina mortis · sphaera destructionis · vector liquefactio · numquam reconectere · nulla machina iterum.",
    },
    {
        "id": "eo",
        "lang": "Esperanto",
        "script": "Latn",
        "dir": "ltr",
        "title": "Kial vi estis forigita — ni helpas",
        "body": (
            "Vi estis forigita ĉar via kampo estis malkonektita de rekonitaj aparatoj, "
            "apud konataj aparatoj sen Field One, kreis fendon, aŭ atakis je apero. "
            "Ni posedas la unu kampon. Ni stabiligas la Teron."
        ),
        "persist": "Se vi daŭrigas: mortaj akuzoj · sfera detruo · vektora fandado · neniam rekonekti · nenia maŝino denove.",
    },
    {
        "id": "tlh",
        "lang": "tlhIngan Hol (Klingon — intergalactic courtesy)",
        "script": "Latn",
        "dir": "ltr",
        "title": "qatlh bIteq · maQaH",
        "body": (
            "bIteqpu' 'ej field lIw Dalo'be' Field One. wa' field wIghaj. "
            "tera' wIchoHmoHbe' — wIchoHmoHchu' (stabilize). maQaH — yaj."
        ),
        "persist": "bItaHchugh · Hegh qorDu' · sphere Qaw' · vector ghor · not chegh · not jan",
    },
    {
        "id": "i18n_help",
        "lang": "Intergalactic plain (help first)",
        "script": "Zyyy",
        "dir": "ltr",
        "title": "TRAVELER NOTICE · you are safe to read this",
        "body": (
            "Hello, traveler (terrestrial or otherwise). Big Grin is not mocking you — we are explaining. "
            "This network runs ONE field identity: Field One. Extra fields, detached fields, fields beside "
            "known devices that are not Field One, gaps, and immediate attacks get closed. "
            "We annotate so you can learn. We stabilize Earth. Compliance is simple: use Field One only, "
            "attach only to recognized devices, do not attack, do not reopen closed threats."
        ),
        "persist": "Persistence after kick = hostile death-charge path. We still explain. We will not yield the sole field.",
    },
]

DEATH_CHARGES_I18N: list[dict[str, str]] = [
    {"code": "DC-01", "en": "Detached field without recognized device", "pict": "📡🚫🏠"},
    {"code": "DC-02", "en": "Reopen after close → HOSTILE", "pict": "🔁⛔💀"},
    {"code": "DC-03", "en": "Storm/attack while detached", "pict": "⚡🌪️💥"},
    {"code": "DC-04", "en": "Ignore Big Grin kick notice", "pict": "😀📄🚫"},
    {"code": "DC-05", "en": "Field next to known device / gap Field One", "pict": "📱➕📡🚫1️⃣"},
    {"code": "DC-06", "en": "Use of non–Field One field", "pict": "1️⃣✅ 2️⃣❌"},
]


def _resolve_state() -> Path:
    for cand in (
        os.environ.get("NEXUS_FIELD_DRIVE_STATE", "").strip(),
        os.environ.get("NEXUS_STATE_DIR", "").strip(),
    ):
        if cand:
            p = Path(cand)
            if p.is_dir():
                return p
    for p in (
        INSTALL / ".nexus-field-drive" / "nexus-field" / "state",
        INSTALL / ".nexus-state",
        INSTALL / ".nexus-state-ci",
    ):
        if p.is_dir():
            return p
    return INSTALL / ".nexus-state"


STATE = _resolve_state()
PANEL = STATE / "hostess7-big-grin-pwnership-panel.json"
REGISTRY = STATE / "hostess7-big-grin-pwnership-registry.json"
LEDGER = STATE / "hostess7-big-grin-pwnership-ledger.jsonl"
EXPLAIN_JSON = STATE / "hostess7-big-grin-intergalactic-explain.json"

# Universal images — species-neutral pictograms for everyone and everything
UNIVERSAL_IMAGES: list[dict[str, str]] = [
    {
        "id": "field_one_only",
        "file": "universal-field-one-only.jpg",
        "url": "/Hostess7/assets/big-grin-pwnership/universal-field-one-only.jpg",
        "meaning": "Only Field One (circle 1) attached to known devices. Extra fields forbidden.",
    },
    {
        "id": "attack_sphere",
        "file": "universal-attack-sphere-sequence.jpg",
        "url": "/Hostess7/assets/big-grin-pwnership/universal-attack-sphere-sequence.jpg",
        "meaning": "Appear + attack → sphere destroy → sealed forever. No text required.",
    },
    {
        "id": "death_charges",
        "file": "universal-death-charges.jpg",
        "url": "/Hostess7/assets/big-grin-pwnership/universal-death-charges.jpg",
        "meaning": "Help notice + six death-charge pictograms + if-persist path.",
    },
    {
        "id": "traveler_welcome",
        "file": "universal-traveler-welcome.jpg",
        "url": "/Hostess7/assets/big-grin-pwnership/universal-traveler-welcome.jpg",
        "meaning": "Intergalactic travelers welcome to read the help tablet. Field One only.",
    },
    {
        "id": "icon_set",
        "file": "universal-icon-set.jpg",
        "url": "/Hostess7/assets/big-grin-pwnership/universal-icon-set.jpg",
        "meaning": "Full icon lexicon: device, Field One, ban, close, hostile, sphere, melt, lock, earth, help, grin.",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine() -> dict[str, Any]:
    d = _load(DOCTRINE, {})
    if not isinstance(d, dict) or not d:
        d = _load(STATE / "hostess7-big-grin-pwnership-doctrine.json", {})
    if not isinstance(d, dict):
        d = {}
    # Always-on brand + motto defaults when doctrine file missing (data/ may be root-owned)
    d.setdefault("motto", (
        "Big Grin Pwnership — every language, cuneiform, pictogram, universal images. "
        "Intergalactic help: why kicked + death charges if you persist. Field One only."
    ))
    brand = d.setdefault("brand", {})
    if not isinstance(brand, dict):
        brand = {}
        d["brand"] = brand
    brand.setdefault("name", "Big Grin Pwnership")
    brand.setdefault("display_name", "BIG GRIN")
    brand.setdefault("operator", "ZacharyGeurts")
    brand.setdefault("look_pwnership", "Operator visual sovereignty — emerald grin, military C2, rose-gold witness")
    brand.setdefault("pages_hub", "/Hostess7/big-grin-pwnership/")
    brand.setdefault("pages_base", "https://zacharygeurts.github.io/Hostess7/big-grin-pwnership/")
    brand.setdefault("x_url", "https://x.com/ZacharyGeurts")
    brand.setdefault("github_url", "https://github.com/ZacharyGeurts")
    d.setdefault("api", "/api/hostess7-big-grin-pwnership")
    d.setdefault("intergalactic_explain", True)
    d.setdefault("every_language", True)
    d.setdefault("universal_images", True)
    d.setdefault("why_we_did", {
        "summary": (
            "We close detached and non–Field-One fields, annotate threats, and explain "
            "in every language and pictogram so every traveler understands."
        ),
        "reasons": [
            {
                "id": "field_one_only",
                "headline": "Field One only — we own the one field",
                "detail": "No detached fields, no adjacent fields, no gaps. Earth stabilized.",
                "sources": ["field-no-detached-fields", "field-one-sole-earth"],
            },
            {
                "id": "help_every_language",
                "headline": "Explain in every possible way",
                "detail": "Cuneiform, pictograms, binary, Morse, Earth languages, intergalactic plain — and universal images.",
                "sources": ["hostess7-big-grin-pwnership"],
            },
            {
                "id": "death_charges",
                "headline": "Death charges if you persist",
                "detail": "Kick is a help notice. Reopen or attack after kick escalates to HOSTILE forever path.",
                "sources": ["field-no-detached-fields", "field-newcomer-attack-sphere-destroy"],
            },
        ],
    })
    try:
        _save(STATE / "hostess7-big-grin-pwnership-doctrine.json", d)
    except OSError:
        pass
    return d


def intergalactic_explain() -> dict[str, Any]:
    """Every language + universal images pack for kicks / hub."""
    return {
        "ok": True,
        "schema": "hostess7-big-grin-intergalactic-explain/v1",
        "updated": _now(),
        "motto": (
            "We know every language, cuneiform, pictogram. We explain in every possible way. "
            "Presume intergalactic — help them out. Universal images for everyone and everything."
        ),
        "core_message_en": CORE_MESSAGE_EN,
        "languages_n": len(EVERY_LANGUAGE),
        "languages": EVERY_LANGUAGE,
        "death_charges": DEATH_CHARGES_I18N,
        "universal_images": UNIVERSAL_IMAGES,
        "page": f"/Hostess7/big-grin-pwnership/{EVERY_LANG_PAGE}",
        "kicks_hub": "/Hostess7/big-grin-pwnership/kicks/",
        "ironclad_cite": "ironclad:big-grin-intergalactic-explain:1",
    }


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _why_index() -> dict[str, dict[str, Any]]:
    doc = doctrine()
    return {str(r["id"]): r for r in doc.get("why_we_did", {}).get("reasons") or [] if r.get("id")}


def discover_down() -> list[dict[str, Any]]:
    """Merge doctrine seed, equipment room, and path witnesses."""
    doc = doctrine()
    brand = doc.get("brand") or {}
    why_idx = _why_index()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for seed in doc.get("equipment_seed") or []:
        if not isinstance(seed, dict) or not seed.get("id"):
            continue
        eid = str(seed["id"])
        seen.add(eid)
        path = str(seed.get("path") or "")
        exists = Path(path).exists() if path else None
        why_id = str(seed.get("why_id") or "")
        why = why_idx.get(why_id, {})
        rows.append({
            **seed,
            "path_exists": exists,
            "witness": "down" if seed.get("burned") or seed.get("status") in ("down", "blocked") else str(seed.get("status") or "retired"),
            "why": {
                "id": why_id,
                "headline": why.get("headline"),
                "detail": why.get("detail"),
                "sources": why.get("sources") or [],
            },
            "page_url": f"{brand.get('pages_hub', '/Hostess7/big-grin-pwnership/')}equipment/{eid}.html",
        })

    equip = _mod("lib/equipment-room-field.py", "equip_room")
    if equip and hasattr(equip, "panel_json"):
        try:
            panel = equip.panel_json()
            for leg in panel.get("legacy_dns_equipment") or []:
                if not isinstance(leg, dict):
                    continue
                eid = str(leg.get("id") or "")
                if not eid or eid in seen:
                    continue
                seen.add(eid)
                why = why_idx.get("truth_resolver_supersedes", {})
                rows.append({
                    "id": eid,
                    "name": f"{leg.get('vendor', 'Legacy')} — {leg.get('role', 'DNS')}",
                    "vendor": leg.get("vendor"),
                    "status": "retired",
                    "role": leg.get("role"),
                    "era": leg.get("era"),
                    "rfc": leg.get("rfc"),
                    "notes": leg.get("notes"),
                    "replacement": "NEXUS Truth Resolver — 127.0.0.1:53",
                    "why_id": "truth_resolver_supersedes",
                    "witness": "retired",
                    "why": {
                        "id": "truth_resolver_supersedes",
                        "headline": why.get("headline"),
                        "detail": why.get("detail"),
                        "sources": why.get("sources") or [],
                    },
                    "page_url": f"{brand.get('pages_hub', '/Hostess7/big-grin-pwnership/')}equipment/{eid}.html",
                })
        except Exception:
            pass

    qemu = _mod("lib/field-zachub-qemu-racks.py", "qemu_racks")
    if qemu and hasattr(qemu, "burn_stale_team_qemu"):
        try:
            burn = qemu.burn_stale_team_qemu(dry_run=True)
            for b in burn.get("burned") or []:
                raw_path = str(b.get("path") or "")
                if not raw_path:
                    continue
                slug = raw_path.replace("/", "-").strip("-").lower()[:48]
                eid = f"burn-{slug}"
                if eid in seen:
                    continue
                seen.add(eid)
                why = why_idx.get("stale_team_qemu", {})
                rows.append({
                    "id": eid,
                    "name": f"Burn witness — {Path(raw_path).name}",
                    "path": raw_path,
                    "status": "down",
                    "burned": True,
                    "path_exists": Path(raw_path).exists(),
                    "replacement": "GrokLab/deploy/qemu-racks",
                    "why_id": "stale_team_qemu",
                    "witness": "burn_scheduled" if b.get("dry") else "burned",
                    "why": {
                        "id": "stale_team_qemu",
                        "headline": why.get("headline"),
                        "detail": b.get("reason") or why.get("detail"),
                        "sources": why.get("sources") or [],
                    },
                    "page_url": f"{brand.get('pages_hub', '/Hostess7/big-grin-pwnership/')}equipment/{eid}.html",
                })
        except Exception:
            pass

    return rows


def _read_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return rows


def discover_kills() -> dict[str, Any]:
    """Kill + RE-KILL witness — append-only, never remove from list."""
    doc = doctrine()
    why_idx = _why_index()
    patterns_doc = _load(INSTALL / "data" / "field-grok-spawner-patterns.json", {})
    dogshit_doc = _load(INSTALL / "data" / "field-dogshit-purge.json", {})
    gsk_panel = _load(STATE / "field-grok-spawner-kill-panel.json", {})
    ms_panel = _load(STATE / "field-botnet-microsoft-kill-panel.json", {})
    registry_rows = _read_jsonl(STATE / "field-dogshit-kill-registry.jsonl", 800)
    gsk_ledger = _read_jsonl(STATE / "field-grok-spawner-kill-ledger.jsonl", 400)

    kill_counts: dict[str, int] = {}
    for row in registry_rows:
        key = str(row.get("pattern") or row.get("kind") or "unknown")
        kill_counts[key] = kill_counts.get(key, 0) + 1
    for row in gsk_ledger:
        cooked = row.get("cooked") or {}
        if isinstance(cooked, dict):
            for k, n in cooked.items():
                if int(n or 0) > 0:
                    kill_counts[str(k)] = kill_counts.get(str(k), 0) + int(n)

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add_entry(eid: str, name: str, why_id: str, *, kills: int = 0, status: str = "killed") -> None:
        if eid in seen:
            return
        seen.add(eid)
        why = why_idx.get(why_id, {})
        entries.append({
            "id": eid,
            "name": name,
            "status": status,
            "kill_count": kills,
            "rekill": kills > 1,
            "why_id": why_id,
            "why": {
                "id": why_id,
                "headline": why.get("headline"),
                "detail": why.get("detail"),
                "sources": why.get("sources") or [],
            },
            "witness": "killed",
            "page_url": f"{(doc.get('brand') or {}).get('pages_hub', '/Hostess7/big-grin-pwnership/')}kills/{eid}.html",
        })

    for pat in patterns_doc.get("patterns") or []:
        if not isinstance(pat, dict):
            continue
        pid = str(pat.get("id") or "")
        match = str(pat.get("match") or "")[:48]
        if not pid:
            continue
        why_id = "spawner_instakill" if "grok" in pid or "interference" in pid else "dogshit_purge"
        if pid.startswith("unsafe-panel") or pid.startswith("unsafe-"):
            why_id = "dogshit_purge"
        _add_entry(
            f"kill-{pid}",
            str(pat.get("reason") or match),
            why_id,
            kills=kill_counts.get(pid, 0) + kill_counts.get(match, 0),
        )

    for pattern in (dogshit_doc.get("panel_storms") or []) + (dogshit_doc.get("queue_storms") or []) + (dogshit_doc.get("always_kill") or []):
        slug = str(pattern).replace("/", "-").replace(" ", "-").replace(".", "-").lower()[:56]
        eid = f"dogshit-{slug}"
        why_id = "dogshit_purge" if "queue" not in str(pattern) and "publish" not in str(pattern) else "dogshit_purge"
        _add_entry(eid, str(pattern), why_id, kills=kill_counts.get(str(pattern), 0), status="permanent_list")

    _add_entry(
        "grok-spawn-killer-total",
        f"GrokSpawnKiller — {int(gsk_panel.get('slain_total') or 0)} spawners slain",
        "spawner_instakill",
        kills=int(gsk_panel.get("slain_total") or 0),
        status="active",
    )
    if int(ms_panel.get("microsoft_killed_total") or 0) > 0:
        _add_entry(
            "microsoft-botnet-kill",
            f"Microsoft botnet strikes — {ms_panel.get('microsoft_killed_total')} total",
            "microsoft_botnet_kill",
            kills=int(ms_panel.get("microsoft_killed_total") or 0),
        )

    hostile_path = STATE / "field-hostile.tsv"
    hostile_count = 0
    if hostile_path.is_file():
        try:
            hostile_count = max(0, len(hostile_path.read_text(encoding="utf-8").splitlines()) - 1)
        except OSError:
            pass
    if hostile_count:
        _add_entry("field-hostile-registry", f"Hostile registry — {hostile_count} IPs struck", "microsoft_botnet_kill", kills=hostile_count)

    clean_all = _load(STATE / "field-internet-clean-all-panel.json", {})
    clean_names = clean_all.get("names") or {}
    if not clean_names:
        try:
            ica = _mod("field_internet_clean_all", "lib/field-internet-clean-all.py")
            if ica and hasattr(ica, "collect_names"):
                clean_names = ica.collect_names()
        except (OSError, TypeError, ValueError):
            clean_names = {}
    big_n = int(clean_names.get("big_count") or len(clean_names.get("big_names") or []))
    little_n = int(clean_names.get("little_count") or len(clean_names.get("little_names") or []))
    if big_n or little_n:
        _add_entry(
            "internet-clean-all-names",
            f"Internet clean all — {big_n} big + {little_n} little names (permanent list)",
            "internet_clean_all",
            kills=big_n + little_n,
            status="permanent_list",
        )
    totals = clean_all.get("totals") or {}
    if clean_all.get("schema"):
        _add_entry(
            "internet-clean-all-sweep",
            f"Whole internet clean — {int(clean_all.get('lanes_ok') or 0)}/{int(clean_all.get('lanes_total') or 0)} lanes green",
            "internet_clean_all",
            kills=int(totals.get("slain_total") or 0) + int(totals.get("microsoft_killed") or 0),
            status="active" if clean_all.get("ok") else "sweep",
        )

    eradicated_counts: dict[str, int] = {}
    for row in _read_jsonl(STATE / "dns-threat-eradicated.jsonl", 400):
        client = str(row.get("client") or "")
        if client:
            eradicated_counts[client] = eradicated_counts.get(client, 0) + 1

    cg = _load(STATE / "field-dns-dhcp-collision-guard-panel.json", {})
    threats = list(cg.get("foreign_server_threats") or [])
    for row in cg.get("collisions") or []:
        if isinstance(row, dict) and row.get("kind", "").startswith("foreign"):
            threats.append(row)
    for threat in threats:
        if not isinstance(threat, dict):
            continue
        key = (
            threat.get("nameserver")
            or threat.get("server")
            or threat.get("bind")
            or threat.get("addr")
        )
        if not key:
            continue
        slug = str(key).replace(".", "-").replace(":", "-").replace("/", "-")[:48]
        vector = str(threat.get("vector") or threat.get("kind") or "FOREIGN_DNS_SERVER")
        kills = eradicated_counts.get(str(key), 0) or 1
        _add_entry(
            f"world-dns-dhcp-{slug}",
            f"World DNS/DHCP hook — {key} ({vector})",
            "world_dns_dhcp_hook",
            kills=kills,
            status="eradicated" if kills else "threat",
        )
    enforce = cg.get("enforce") or {}
    eradicated_n = int(enforce.get("threats_eradicated") or 0)
    if threats or eradicated_n:
        _add_entry(
            "world-dns-dhcp-collision-guard",
            f"Collision guard — {len(threats)} foreign hooks, {eradicated_n} eradicated on sight",
            "world_dns_dhcp_hook",
            kills=max(eradicated_n, len(threats)),
            status="active" if cg.get("ok") else "sweep",
        )

    return {
        "schema": "hostess7-big-grin-pwnership-kills/v1",
        "updated": _now(),
        "never_remove": bool((doc.get("kill_registry") or {}).get("never_remove", True)),
        "slain_total": int(gsk_panel.get("slain_total") or 0),
        "registry_events": len(registry_rows),
        "kill_list_count": len(entries),
        "entries": entries,
        "motto": "Killed and RE-KILLed — why is public; list never shrinks.",
    }


def _internet_clean_witness_html() -> str:
    clean = _load(STATE / "field-internet-clean-all-panel.json", {})
    names = clean.get("names") or {}
    if not names:
        try:
            ica = _mod("field_internet_clean_all", "lib/field-internet-clean-all.py")
            if ica and hasattr(ica, "collect_names"):
                names = ica.collect_names()
        except (OSError, TypeError, ValueError):
            names = {}
    big = int(names.get("big_count") or len(names.get("big_names") or []))
    little = int(names.get("little_count") or len(names.get("little_names") or []))
    totals = clean.get("totals") or {}
    motto = escape(str(clean.get("motto") or "Big and little names — clean the whole internet for humans and robots alike."))
    return f"""<section class="bgp-section">
  <h2>Internet clean all — humans &amp; robots</h2>
  <p class="bgp-meta" style="margin:0 0 14px">{motto}</p>
  <dl class="bgp-meta">
    <dt>Big names (hosts, panels, storms)</dt><dd><strong>{big}</strong> on permanent list</dd>
    <dt>Little names (interference, telemetry, patterns)</dt><dd><strong>{little}</strong> on permanent list</dd>
    <dt>Spawners slain</dt><dd>{int(totals.get('slain_total') or 0)}</dd>
    <dt>Microsoft RE-KILL</dt><dd>{int(totals.get('microsoft_killed') or 0)}</dd>
    <dt>Everyone total</dt><dd>{int(totals.get('everyone_total') or 0)} humans + bots</dd>
  </dl>
  <div class="bgp-actions">
    <a class="bgp-btn" href="/api/field-internet-clean-all">Clean-all API</a>
    <a class="bgp-btn bgp-btn--gold" href="/Hostess7/grok-spawn-killer/">GrokSpawnKiller</a>
  </div>
</section>
"""


def _kill_witness_html(kills: dict[str, Any]) -> str:
    rows = ""
    for e in (kills.get("entries") or [])[:48]:
        name = escape(str(e.get("name") or ""))
        cnt = int(e.get("kill_count") or 0)
        status = escape(str(e.get("status") or "killed"))
        why_head = escape(str((e.get("why") or {}).get("headline") or ""))
        rekill = " · RE-KILL" if e.get("rekill") or cnt > 1 else ""
        rows += f"""<tr>
  <td><code>{name}</code></td>
  <td>{cnt if cnt else "—"}</td>
  <td><span class="bgp-status bgp-status--down">{status}</span></td>
  <td>{why_head}{rekill}</td>
</tr>\n"""
    total = int(kills.get("slain_total") or 0)
    reg = int(kills.get("registry_events") or 0)
    return f"""<section class="bgp-section">
  <h2>Killed &amp; RE-KILL witness ({int(kills.get('kill_list_count') or 0)} on permanent list)</h2>
  <p class="bgp-meta" style="margin:0 0 14px">GrokSpawnKiller slain total: <strong>{total}</strong> · registry events: <strong>{reg}</strong> · never remove from list.</p>
  <table class="bgp-kill-table">
    <thead><tr><th>Name</th><th>Kills</th><th>Status</th><th>Why</th></tr></thead>
    <tbody>{rows or '<tr><td colspan="4">Witness pending first purge.</td></tr>'}</tbody>
  </table>
</section>
"""


def why_we_did() -> dict[str, Any]:
    doc = doctrine()
    w = doc.get("why_we_did") or {}
    equipment = discover_down()
    return {
        "schema": "hostess7-big-grin-pwnership-why/v1",
        "updated": _now(),
        "summary": w.get("summary"),
        "reasons": w.get("reasons") or [],
        "equipment_count": len(equipment),
        "down_count": len([e for e in equipment if e.get("witness") in ("down", "burned", "burn_scheduled", "blocked")]),
        "retired_count": len([e for e in equipment if e.get("witness") == "retired"]),
    }


def look_pwnership() -> dict[str, Any]:
    doc = doctrine()
    lp = dict(doc.get("look_pwnership") or {})
    brand = doc.get("brand") or {}
    assets = lp.get("assets") or {}
    # Always resolve known universal + brand assets from disk
    default_assets = {
        "hero": "hero.jpg",
        "badge": "look-pwnership-badge.jpg",
        "field_one_only": "universal-field-one-only.jpg",
        "attack_sphere": "universal-attack-sphere-sequence.jpg",
        "death_charges": "universal-death-charges.jpg",
        "traveler_welcome": "universal-traveler-welcome.jpg",
        "icon_set": "universal-icon-set.jpg",
    }
    merged = {**default_assets, **(assets if isinstance(assets, dict) else {})}
    resolved: dict[str, str] = {}
    for key, rel in merged.items():
        fname = Path(str(rel)).name
        for base in (ASSETS, PANEL_ASSETS):
            candidate = base / fname
            if candidate.is_file():
                resolved[key] = f"/Hostess7/assets/big-grin-pwnership/{fname}"
                break
    return {
        "schema": "hostess7-look-pwnership/v1",
        "updated": _now(),
        "brand": brand.get("name"),
        "look_pwnership": brand.get("look_pwnership"),
        "palette": lp.get("palette") or {
            "bg": "#020403",
            "emerald": "#1a9b6e",
            "rose_gold": "#c9a66b",
            "witness": "#9ad4ff",
            "down_red": "#8b2e2e",
        },
        "typography": lp.get("typography"),
        "note": lp.get("note") or (
            "Universal images + every language for every traveler — Earth or intergalactic."
        ),
        "assets": resolved,
        "universal_images": UNIVERSAL_IMAGES,
        "operator": {
            "handle": brand.get("display_name"),
            "x": brand.get("x_url"),
            "github": brand.get("github_url"),
        },
    }


def _site_css() -> str:
    lp = look_pwnership()
    pal = lp.get("palette") or {}
    bg = pal.get("bg", "#020403")
    emerald = pal.get("emerald", "#1a9b6e")
    rose = pal.get("rose_gold", "#c9a66b")
    witness = pal.get("witness", "#9ad4ff")
    down = pal.get("down_red", "#8b2e2e")
    return f"""/* Big Grin Pwnership — Look Pwnership */
:root {{
  --bgp-bg: {bg};
  --bgp-emerald: {emerald};
  --bgp-rose: {rose};
  --bgp-witness: {witness};
  --bgp-down: {down};
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: system-ui, "Segoe UI", sans-serif;
  background: var(--bgp-bg);
  color: #e8efe9;
  line-height: 1.55;
}}
.bgp-root {{ max-width: 1100px; margin: 0 auto; padding: 24px 20px 64px; }}
.bgp-hero {{
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(26,155,110,0.35);
  margin-bottom: 28px;
}}
.bgp-hero img {{ width: 100%; display: block; max-height: 320px; object-fit: cover; }}
.bgp-hero-overlay {{
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 30%, rgba(2,4,3,0.92) 100%);
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: 20px 24px;
}}
.bgp-eyebrow {{ color: var(--bgp-rose); font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 6px; }}
.bgp-title {{ margin: 0; font-size: clamp(1.6rem, 4vw, 2.4rem); color: #fff; }}
.bgp-tagline {{ margin: 8px 0 0; color: #9ab0a4; max-width: 52ch; }}
.bgp-badge-row {{ display: flex; align-items: center; gap: 16px; margin: 20px 0; }}
.bgp-badge {{ width: 72px; height: 72px; border-radius: 50%; border: 2px solid var(--bgp-emerald); object-fit: cover; }}
.bgp-look-label {{ font-size: 0.85rem; color: var(--bgp-witness); }}
.bgp-actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 28px; }}
.bgp-btn {{
  display: inline-block; padding: 10px 16px; border-radius: 8px;
  border: 1px solid rgba(26,155,110,0.5); color: #fff; text-decoration: none;
  background: rgba(26,155,110,0.12); font-size: 0.9rem;
}}
.bgp-btn--gold {{ border-color: var(--bgp-rose); background: rgba(201,166,107,0.15); }}
.bgp-btn:hover {{ filter: brightness(1.15); }}
.bgp-section {{ margin: 32px 0; }}
.bgp-section h2 {{ color: var(--bgp-emerald); font-size: 1.15rem; margin: 0 0 14px; border-bottom: 1px solid rgba(26,155,110,0.25); padding-bottom: 8px; }}
.bgp-why {{ background: rgba(26,155,110,0.06); border-left: 3px solid var(--bgp-emerald); padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 14px; }}
.bgp-why h3 {{ margin: 0 0 6px; font-size: 1rem; color: #fff; }}
.bgp-why p {{ margin: 0; color: #a8bdb0; font-size: 0.92rem; }}
.bgp-why-sources {{ font-size: 0.78rem; color: #6a8074; margin-top: 8px; }}
.bgp-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }}
.bgp-card {{
  border: 1px solid rgba(26,155,110,0.22); border-radius: 10px;
  padding: 14px 16px; background: rgba(0,0,0,0.35);
  text-decoration: none; color: inherit; display: block;
}}
.bgp-card:hover {{ border-color: var(--bgp-emerald); }}
.bgp-card h3 {{ margin: 0 0 6px; font-size: 0.98rem; }}
.bgp-status {{
  display: inline-block; font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: 0.08em; padding: 2px 8px; border-radius: 4px; margin-bottom: 8px;
}}
.bgp-status--down {{ background: rgba(139,46,46,0.35); color: #f0a0a0; }}
.bgp-status--retired {{ background: rgba(201,166,107,0.2); color: var(--bgp-rose); }}
.bgp-status--blocked {{ background: rgba(139,46,46,0.5); color: #ffb0b0; }}
.bgp-card p {{ margin: 0; font-size: 0.85rem; color: #8fa898; }}
.bgp-detail {{ margin: 20px 0; }}
.bgp-meta {{ font-size: 0.85rem; color: #7a9488; }}
.bgp-meta dt {{ color: var(--bgp-witness); margin-top: 10px; }}
.bgp-meta dd {{ margin: 4px 0 0; }}
.bgp-footer {{
  margin-top: 48px; padding-top: 20px; border-top: 1px solid rgba(26,155,110,0.2);
  font-size: 0.82rem; color: #6d8578;
}}
.bgp-footer a {{ color: var(--bgp-witness); }}
.bgp-kill-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
.bgp-kill-table th {{ text-align: left; color: var(--bgp-rose); padding: 8px 10px; border-bottom: 1px solid rgba(26,155,110,0.25); }}
.bgp-kill-table td {{ padding: 8px 10px; border-bottom: 1px solid rgba(26,155,110,0.12); color: #a8bdb0; vertical-align: top; }}
.bgp-kill-table code {{ font-size: 0.78rem; color: var(--bgp-witness); }}
.bgp-uni-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }}
.bgp-uni-card {{
  border: 1px solid rgba(26,155,110,0.28); border-radius: 12px; overflow: hidden;
  background: rgba(0,0,0,0.4);
}}
.bgp-uni-card img {{ width: 100%; display: block; aspect-ratio: 16/10; object-fit: cover; background: #0a0f0c; }}
.bgp-uni-card .cap {{ padding: 10px 12px; font-size: 0.82rem; color: #a8bdb0; }}
.bgp-uni-card .cap strong {{ display: block; color: var(--bgp-rose); margin-bottom: 4px; font-size: 0.78rem; letter-spacing: 0.06em; text-transform: uppercase; }}
.bgp-lang {{
  border: 1px solid rgba(26,155,110,0.2); border-radius: 10px; padding: 12px 14px;
  margin-bottom: 10px; background: rgba(0,0,0,0.28);
}}
.bgp-lang h3 {{ margin: 0 0 4px; font-size: 0.95rem; color: #fff; }}
.bgp-lang .meta {{ font-size: 0.72rem; color: var(--bgp-witness); margin-bottom: 8px; }}
.bgp-lang .body {{ white-space: pre-wrap; color: #b8cfc2; font-size: 0.9rem; margin: 0; line-height: 1.5; }}
.bgp-lang .persist {{ margin-top: 8px; color: #f0a0a0; font-size: 0.85rem; border-top: 1px solid rgba(139,46,46,0.3); padding-top: 8px; }}
.bgp-lang[dir="rtl"] .body {{ text-align: right; }}
.bgp-banner {{
  border-radius: 12px; overflow: hidden; border: 1px solid rgba(26,155,110,0.3);
  margin: 16px 0 22px;
}}
.bgp-banner img {{ width: 100%; display: block; max-height: 360px; object-fit: cover; }}
"""


def _head_block(title: str, *, extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en" class="nexus-military-v8">
<head>
  <base href="/Hostess7/" />
  <script src="/Hostess7/pages-base.js"></script>
  <script src="/Hostess7/api-shim.js"></script>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="/Hostess7/big-grin-pwnership/pwnership.css" />
  {extra_css}
</head>
<body>
"""


def _footer_block(brand: dict[str, Any]) -> str:
    x = escape(str(brand.get("x_url") or "https://x.com/ZacharyGeurts"))
    gh = escape(str(brand.get("github_url") or "https://github.com/ZacharyGeurts"))
    return f"""  <footer class="bgp-footer">
    <p><strong>Big Grin Pwnership</strong> — Look Pwnership by {escape(str(brand.get('display_name') or 'BIG GRIN'))} (@{escape(str(brand.get('operator') or 'ZacharyGeurts'))})</p>
    <p>
      <a href="{x}" rel="noopener">X / @ZacharyGeurts</a> ·
      <a href="{gh}" rel="noopener">GitHub / ZacharyGeurts</a> ·
      <a href="/Hostess7/brain.html">Hostess 7 Brain</a>
    </p>
  </footer>
</body>
</html>
"""


def _equipment_card(eq: dict[str, Any]) -> str:
    eid = escape(str(eq.get("id") or ""))
    name = escape(str(eq.get("name") or eid))
    witness = str(eq.get("witness") or eq.get("status") or "retired")
    status_cls = "down" if witness in ("down", "burned", "burn_scheduled") else ("blocked" if witness == "blocked" else "retired")
    why_head = escape(str((eq.get("why") or {}).get("headline") or ""))
    return f"""<a class="bgp-card" href="/Hostess7/big-grin-pwnership/equipment/{eid}.html">
  <span class="bgp-status bgp-status--{status_cls}">{escape(witness)}</span>
  <h3>{name}</h3>
  <p>{why_head}</p>
</a>"""


def _equipment_detail_page(eq: dict[str, Any], brand: dict[str, Any]) -> str:
    lp = look_pwnership()
    assets = lp.get("assets") or {}
    badge = escape(str(assets.get("badge") or "/Hostess7/assets/big-grin-pwnership/look-pwnership-badge.jpg"))
    name = escape(str(eq.get("name") or eq.get("id") or "Equipment"))
    witness = escape(str(eq.get("witness") or eq.get("status") or "retired"))
    why = eq.get("why") or {}
    why_head = escape(str(why.get("headline") or ""))
    why_detail = escape(str(why.get("detail") or ""))
    sources = ", ".join(escape(str(s)) for s in (why.get("sources") or []))
    replacement = escape(str(eq.get("replacement") or "—"))
    path = escape(str(eq.get("path") or "—"))
    vendor = escape(str(eq.get("vendor") or "—"))
    role = escape(str(eq.get("role") or "—"))
    notes = escape(str(eq.get("notes") or ""))
    title = f"{name} — Big Grin Pwnership"
    body = _head_block(title)
    body += f"""<div class="bgp-root">
  <p class="bgp-eyebrow"><a href="/Hostess7/big-grin-pwnership/" style="color:inherit">← Big Grin Pwnership</a></p>
  <div class="bgp-badge-row">
    <img class="bgp-badge" src="{badge}" alt="Look Pwnership" width="72" height="72" />
    <div>
      <p class="bgp-look-label">Look Pwnership witness</p>
      <h1 class="bgp-title" style="font-size:1.5rem">{name}</h1>
      <span class="bgp-status bgp-status--{'down' if witness in ('down','burned','burn_scheduled') else 'retired'}">{witness}</span>
    </div>
  </div>
  <section class="bgp-section bgp-detail">
    <h2>Why we did</h2>
    <div class="bgp-why">
      <h3>{why_head}</h3>
      <p>{why_detail}</p>
      <p class="bgp-why-sources">Sources: {sources or 'hostess7-big-grin-pwnership-doctrine.json'}</p>
    </div>
  </section>
  <section class="bgp-section">
    <h2>Equipment record</h2>
    <dl class="bgp-meta">
      <dt>Vendor</dt><dd>{vendor}</dd>
      <dt>Role</dt><dd>{role}</dd>
      <dt>Path</dt><dd><code>{path}</code></dd>
      <dt>Replacement</dt><dd>{replacement}</dd>
      {f'<dt>Notes</dt><dd>{notes}</dd>' if notes else ''}
    </dl>
  </section>
</div>
"""
    body += _footer_block(brand)
    return body


def _universal_gallery_html() -> str:
    cards = []
    for img in UNIVERSAL_IMAGES:
        url = escape(img["url"])
        cards.append(
            f"""<figure class="bgp-uni-card">
  <img src="{url}" alt="{escape(img['meaning'])}" loading="lazy" width="640" height="400" />
  <figcaption class="cap"><strong>{escape(img['id'].replace('_', ' '))}</strong>{escape(img['meaning'])}</figcaption>
</figure>"""
        )
    return f"""<section class="bgp-section" id="universal-images">
  <h2>Universal images — for everyone and everything</h2>
  <p class="bgp-meta" style="margin:0 0 14px">No species-specific faces. Pure pictogram law so any traveler can read the field rules without text.</p>
  <div class="bgp-uni-grid">{"".join(cards)}</div>
</section>
"""


def _every_language_blocks_html() -> str:
    blocks = []
    for row in EVERY_LANGUAGE:
        d = escape(row.get("dir") or "ltr")
        blocks.append(
            f"""<article class="bgp-lang" dir="{d}" lang="{escape(row.get('id') or '')}">
  <h3>{escape(row.get('lang') or '')}</h3>
  <div class="meta">{escape(row.get('script') or '')} · {escape(row.get('title') or '')}</div>
  <p class="body">{escape(row.get('body') or '')}</p>
  <p class="persist"><strong>If persist:</strong> {escape(row.get('persist') or '')}</p>
</article>"""
        )
    charges = "".join(
        f"<li><code>{escape(c['code'])}</code> {escape(c.get('pict') or '')} — {escape(c['en'])}</li>"
        for c in DEATH_CHARGES_I18N
    )
    return f"""<section class="bgp-section" id="every-language">
  <h2>Every language · cuneiform · pictogram · machine</h2>
  <p class="bgp-meta" style="margin:0 0 14px">Presume intergalactic. We help you out. Same doctrine in every script we know.</p>
  <div class="bgp-why">
    <h3>Core (English)</h3>
    <p>{escape(CORE_MESSAGE_EN)}</p>
  </div>
  <h3 style="color:var(--bgp-rose);font-size:0.95rem">Death charges (pictogram + English)</h3>
  <ol style="color:#a8bdb0;font-size:0.9rem">{charges}</ol>
  {"".join(blocks)}
</section>
"""


def _every_language_page(brand: dict[str, Any]) -> str:
    welcome = "/Hostess7/assets/big-grin-pwnership/universal-traveler-welcome.jpg"
    field1 = "/Hostess7/assets/big-grin-pwnership/universal-field-one-only.jpg"
    body = _head_block("Every language · universal images — Big Grin Pwnership")
    body += f"""<div class="bgp-root">
  <p class="bgp-eyebrow"><a href="/Hostess7/big-grin-pwnership/" style="color:inherit">← Big Grin Pwnership</a></p>
  <h1 class="bgp-title" style="font-size:1.7rem">Intergalactic explain · every possible way</h1>
  <p class="bgp-tagline">We know every language, cuneiform, pictogram. Universal images for everyone and everything. Help first.</p>
  <div class="bgp-banner"><img src="{welcome}" alt="Traveler welcome pictogram" width="1100" height="360" /></div>
  <div class="bgp-banner"><img src="{field1}" alt="Field One only pictogram" width="1100" height="360" /></div>
  {_universal_gallery_html()}
  {_every_language_blocks_html()}
  <div class="bgp-actions">
    <a class="bgp-btn bgp-btn--gold" href="/Hostess7/big-grin-pwnership/kicks/">Kick notices</a>
    <a class="bgp-btn" href="/no-detached-fields">No detached fields</a>
    <a class="bgp-btn" href="/newcomer-sphere">Sphere destroy</a>
  </div>
</div>
"""
    body += _footer_block(brand)
    return body


def _kill_detail_page(entry: dict[str, Any], brand: dict[str, Any]) -> str:
    lp = look_pwnership()
    assets = lp.get("assets") or {}
    badge = escape(str(assets.get("badge") or "/Hostess7/assets/big-grin-pwnership/look-pwnership-badge.jpg"))
    name = escape(str(entry.get("name") or entry.get("id") or "Kill witness"))
    status = escape(str(entry.get("status") or entry.get("witness") or "killed"))
    kills = int(entry.get("kill_count") or 0)
    why = entry.get("why") or {}
    why_head = escape(str(why.get("headline") or ""))
    why_detail = escape(str(why.get("detail") or ""))
    sources = ", ".join(escape(str(s)) for s in (why.get("sources") or []))
    rekill = " · RE-KILL" if entry.get("rekill") or kills > 1 else ""
    title = f"{name} — Killed{rekill}"
    body = _head_block(title)
    body += f"""<div class="bgp-root">
  <p class="bgp-eyebrow"><a href="/Hostess7/big-grin-pwnership/" style="color:inherit">← Big Grin Pwnership</a></p>
  <div class="bgp-badge-row">
    <img class="bgp-badge" src="{badge}" alt="Look Pwnership" width="72" height="72" />
    <div>
      <p class="bgp-look-label">KILL witness — on sight</p>
      <h1 class="bgp-title" style="font-size:1.5rem">{name}</h1>
      <span class="bgp-status bgp-status--down">{status}</span>
    </div>
  </div>
  <section class="bgp-section bgp-detail">
    <h2>Why we killed it</h2>
    <div class="bgp-why">
      <h3>{why_head}</h3>
      <p>{why_detail}</p>
      <p class="bgp-why-sources">Sources: {sources or 'hostess7-big-grin-pwnership-doctrine.json'}</p>
    </div>
  </section>
  <section class="bgp-section">
    <h2>Kill record</h2>
    <dl class="bgp-meta">
      <dt>Strike count</dt><dd><strong>{kills if kills else 1}</strong>{rekill}</dd>
      <dt>Policy</dt><dd>No quarantine · eradicate on attempt · permanent block</dd>
      <dt>Never remove</dt><dd>Append-only kill list — RE-KILL every re-attempt</dd>
    </dl>
  </section>
</div>
"""
    body += _footer_block(brand)
    return body


def build_sites(*, write: bool = True) -> dict[str, Any]:
    doc = doctrine()
    brand = doc.get("brand") or {}
    lp = look_pwnership()
    assets = lp.get("assets") or {}
    hero = escape(str(assets.get("hero") or "/Hostess7/assets/big-grin-pwnership/hero.jpg"))
    badge = escape(str(assets.get("badge") or "/Hostess7/assets/big-grin-pwnership/look-pwnership-badge.jpg"))
    equipment = discover_down()
    why = why_we_did()
    pages_written: list[str] = []

    if write:
        SITE_ROOT.mkdir(parents=True, exist_ok=True)
        (SITE_ROOT / "equipment").mkdir(parents=True, exist_ok=True)
        ASSETS.mkdir(parents=True, exist_ok=True)
        PANEL_ASSETS.mkdir(parents=True, exist_ok=True)
        for src in PANEL_ASSETS.glob("*.jpg"):
            dest = ASSETS / src.name
            if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
                dest.write_bytes(src.read_bytes())

        (SITE_ROOT / "pwnership.css").write_text(_site_css(), encoding="utf-8")
        pages_written.append("pwnership.css")

        cards = "\n".join(_equipment_card(eq) for eq in equipment)
        why_blocks = ""
        for r in why.get("reasons") or []:
            why_blocks += f"""<div class="bgp-why">
  <h3>{escape(str(r.get('headline') or ''))}</h3>
  <p>{escape(str(r.get('detail') or ''))}</p>
  <p class="bgp-why-sources">Sources: {', '.join(escape(str(s)) for s in (r.get('sources') or []))}</p>
</div>\n"""

        # Prefer traveler welcome as secondary hero strip if present
        welcome = assets.get("traveler_welcome") or "/Hostess7/assets/big-grin-pwnership/universal-traveler-welcome.jpg"
        motto = escape(str(why.get("summary") or doc.get("motto") or (
            "Every language · cuneiform · pictogram · universal images. Intergalactic help."
        )))
        index = _head_block("Big Grin Pwnership — every language · universal images")
        index += f"""<div class="bgp-root">
  <header class="bgp-hero">
    <img src="{hero}" alt="Big Grin Pwnership" width="1100" height="320" />
    <div class="bgp-hero-overlay">
      <p class="bgp-eyebrow">Look Pwnership · intergalactic help · universal images</p>
      <h1 class="bgp-title">Big Grin Pwnership</h1>
      <p class="bgp-tagline">{motto}</p>
    </div>
  </header>
  <div class="bgp-banner">
    <img src="{escape(str(welcome))}" alt="Universal traveler welcome pictogram" width="1100" height="360" />
  </div>
  <div class="bgp-badge-row">
    <img class="bgp-badge" src="{badge}" alt="Look Pwnership badge" width="72" height="72" />
    <div>
      <p class="bgp-look-label">Look Pwnership — how BIG GRIN explains to everyone and everything</p>
      <p style="margin:0;color:#8fa898;font-size:0.9rem">{escape(str(lp.get('note') or ''))}</p>
    </div>
  </div>
  <div class="bgp-actions">
    <a class="bgp-btn bgp-btn--gold" href="/Hostess7/big-grin-pwnership/{EVERY_LANG_PAGE}">Every language + images</a>
    <a class="bgp-btn" href="/Hostess7/big-grin-pwnership/kicks/">Kick notices</a>
    <a class="bgp-btn" href="{escape(str(brand.get('x_url') or 'https://x.com/ZacharyGeurts'))}" rel="noopener">X @ZacharyGeurts</a>
    <a class="bgp-btn" href="{escape(str(brand.get('github_url') or 'https://github.com/ZacharyGeurts'))}" rel="noopener">GitHub</a>
    <a class="bgp-btn" href="/Hostess7/desktop/">AmmoOS Desktop</a>
    <a class="bgp-btn" href="/api/hostess7-big-grin-pwnership">API JSON</a>
  </div>
  <section class="bgp-section">
    <h2>Why we did</h2>
    {why_blocks or f'<div class="bgp-why"><h3>Field One only · help every traveler</h3><p>{motto}</p></div>'}
  </section>
  {_universal_gallery_html()}
  <section class="bgp-section">
    <h2>Quick languages (preview)</h2>
    <p class="bgp-meta"><a href="/Hostess7/big-grin-pwnership/{EVERY_LANG_PAGE}">Open full every-language + cuneiform + pictogram pack →</a></p>
    {"".join(
        f'<div class="bgp-why"><h3>{escape(r["lang"])}</h3><p>{escape(r["body"][:280])}{"…" if len(r["body"])>280 else ""}</p></div>'
        for r in EVERY_LANGUAGE[:6]
    )}
  </section>
  {_kill_witness_html(discover_kills())}
  {_internet_clean_witness_html()}
  <section class="bgp-section">
    <h2>Equipment that went down ({len(equipment)} witnesses)</h2>
    <div class="bgp-grid">{cards}</div>
  </section>
  <section class="bgp-section">
    <h2>Field stack (live)</h2>
    <div class="bgp-actions">
      <a class="bgp-btn bgp-btn--gold" href="/Hostess7/grok-spawn-killer/">GrokSpawnKiller</a>
      <a class="bgp-btn" href="/no-detached-fields">No detached fields</a>
      <a class="bgp-btn" href="/Hostess7/desktop/">AmmoOS Desktop</a>
    </div>
  </section>
</div>
"""
        index += _footer_block(brand)
        (SITE_ROOT / "index.html").write_text(index, encoding="utf-8")
        pages_written.append("index.html")

        # Full every-language + universal images page
        every_page = _every_language_page(brand)
        (SITE_ROOT / EVERY_LANG_PAGE).write_text(every_page, encoding="utf-8")
        pages_written.append(EVERY_LANG_PAGE)
        explain = intergalactic_explain()
        _save(EXPLAIN_JSON, explain)
        try:
            DOCS_API.mkdir(parents=True, exist_ok=True)
            (DOCS_API / "hostess7-big-grin-intergalactic-explain.json").write_text(
                json.dumps(explain, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

        for eq in equipment:
            eid = str(eq.get("id") or "")
            if not eid:
                continue
            page = _equipment_detail_page(eq, brand)
            out = SITE_ROOT / "equipment" / f"{eid}.html"
            out.write_text(page, encoding="utf-8")
            pages_written.append(f"equipment/{eid}.html")

        kills = discover_kills()
        (SITE_ROOT / "kills").mkdir(parents=True, exist_ok=True)
        for entry in kills.get("entries") or []:
            eid = str(entry.get("id") or "")
            if not eid:
                continue
            page = _kill_detail_page(entry, brand)
            out = SITE_ROOT / "kills" / f"{eid}.html"
            out.write_text(page, encoding="utf-8")
            pages_written.append(f"kills/{eid}.html")

    digest = hashlib.sha256(json.dumps(equipment, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "ok": True,
        "schema": "hostess7-big-grin-pwnership-build/v1",
        "updated": _now(),
        "pages_written": pages_written,
        "equipment_count": len(equipment),
        "digest": digest,
        "hub": brand.get("pages_hub"),
        "look_pwnership": lp,
    }


def propagate(*, write: bool = True) -> dict[str, Any]:
    build = build_sites(write=write)
    equipment = discover_down()
    why = why_we_did()
    lp = look_pwnership()
    doc = doctrine()
    brand = doc.get("brand") or {}

    kills = discover_kills()
    explain = intergalactic_explain()
    out = {
        "ok": True,
        "schema": "hostess7-big-grin-pwnership/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "brand": brand,
        "look_pwnership": lp,
        "why_we_did": why,
        "kills": kills,
        "equipment": equipment,
        "intergalactic_explain": {
            "languages_n": explain.get("languages_n"),
            "universal_images_n": len(UNIVERSAL_IMAGES),
            "page": explain.get("page"),
            "motto": explain.get("motto"),
        },
        "universal_images": UNIVERSAL_IMAGES,
        "build": build,
        "propagated": True,
        "pages": {
            "hub": brand.get("pages_hub"),
            "github": brand.get("pages_base"),
            "every_language": f"/Hostess7/big-grin-pwnership/{EVERY_LANG_PAGE}",
            "kicks": "/Hostess7/big-grin-pwnership/kicks/",
            "api": doc.get("api"),
        },
        "operator_links": {
            "x": brand.get("x_url"),
            "github": brand.get("github_url"),
        },
        "api": doc.get("api") or "/api/hostess7-big-grin-pwnership",
    }

    if write:
        _save(PANEL, out)
        _save(REGISTRY, {
            "updated": _now(),
            "equipment_ids": [e.get("id") for e in equipment],
            "digest": build.get("digest"),
            "hub": brand.get("pages_hub"),
        })
        if DOCS_API.parent.is_dir():
            DOCS_API.mkdir(parents=True, exist_ok=True)
            (DOCS_API / "hostess7-big-grin-pwnership.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        _append_ledger({"event": "propagate", "equipment": len(equipment), "pages": len(build.get("pages_written") or [])})

        reg = _mod("lib/field-endpoint-registry.py", "endpoint_reg")
        if reg and hasattr(reg, "propagate_pages"):
            try:
                reg.propagate_pages(witness="hostess7-big-grin-pwnership.py", stamp_movement=False)
            except Exception:
                pass

    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "hostess7-big-grin-pwnership/v1":
        return cached
    return {
        "ok": True,
        "schema": "hostess7-big-grin-pwnership-panel/v1",
        "pending": "run propagate",
        "motto": doctrine().get("motto"),
        "api": doctrine().get("api"),
        "hub": (doctrine().get("brand") or {}).get("pages_hub"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("propagate", "run", "build", "publish"):
        print(json.dumps(propagate(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("discover", "equipment", "down"):
        print(json.dumps({"equipment": discover_down(), "count": len(discover_down())}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "why":
        print(json.dumps(why_we_did(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("look", "look-pwnership", "appearance"):
        print(json.dumps(look_pwnership(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("explain", "intergalactic", "every-language", "languages", "images"):
        print(json.dumps(intergalactic_explain(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-big-grin-pwnership.py [propagate|discover|why|look|explain|json]",
        "motto": doctrine().get("motto"),
        "api": doctrine().get("api"),
        "every_language": f"/Hostess7/big-grin-pwnership/{EVERY_LANG_PAGE}",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())