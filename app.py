import csv
import inspect
import io
import math
import textwrap
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# SAYFA AYARLARI
# ==========================================
st.set_page_config(
    page_title="Perakendeci Stok Bilgi Sistemi",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Kurumsal renk paleti
LACIVERT = "#0B2545"
MAVI = "#1F4E79"
ACIK_MAVI = "#8DA9C4"
KIRMIZI = "#B23A48"
GRI = "#5B6776"

# Ek operasyonel maliyet seçenekleri
SECENEK_SIP = "Sipariş maliyetine ek maliyet (D/Q üzerinden hesaplanır)"
SECENEK_DEPO = "Depolama maliyetine ek maliyet (stok seviyesi üzerinden hesaplanır)"
BAZ_ORT = "Ortalama stok üzerinden (Ī)"
BAZ_MAKS = "Maksimum stok üzerinden (I_max)"


def genis(fonk):
    """Streamlit sürümüne göre tam genişlik parametresini döndürür."""
    try:
        if "width" in inspect.signature(fonk).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


# ==========================================
# OPTİMİZASYON FONKSİYONLARI
# a : toplam sipariş maliyeti (A + A_ek), g : ek depolama maliyeti [TL/adet-yıl]
# ==========================================
def model4_coz(D, a, h, g, baz):
    """Model 4 (Klasik EOQ). Ortalama stok tabanında h_etkin = h + g,
    maksimum stok tabanında (I_max = Q) h_etkin = h + 2g."""
    h_etkin = h + g if baz == BAZ_ORT else h + 2 * g
    return math.sqrt((2 * D * a) / h_etkin)


def model3_coz(D, a, h, g, baz, pi_hat, pi):
    """Model 3 (Sonradan karşılamalı). (Q, b, hata_kodu) döndürür."""
    if baz == BAZ_MAKS and g > 0:
        # Ek depolama maliyeti maksimum stok (Q - b) üzerinden
        pay = 2 * a * D * (h + pi_hat) - (pi * D) ** 2
        payda = pi_hat * (h + 2 * g) - g ** 2
        if pay <= 0 or payda <= 0:
            return None, None, "ekonomik_degil"
        Q = math.sqrt(pay / payda)
        b = ((h + g) * Q - pi * D) / (h + pi_hat)
        if b >= Q:
            return None, None, "stok_yok"
    else:
        # Ek depolama maliyeti ortalama stok üzerinden: h yerine (h + g)
        h_e = h + g
        kok_ici = ((2 * a * D) / h_e) - (((pi * D) ** 2) / (h_e * (h_e + pi_hat)))
        if kok_ici <= 0:
            return None, None, "ekonomik_degil"
        Q = math.sqrt(kok_ici) * math.sqrt((h_e + pi_hat) / pi_hat)
        b = (h_e * Q - pi * D) / (h_e + pi_hat)
    return Q, b, None

# ==========================================
# KURUMSAL TEMA (CSS)
# ==========================================
st.markdown(
    f"""
    <style>
    #MainMenu, footer {{ visibility: hidden; }}

    .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }}

    /* Üst başlık bandı */
    .hero {{
        background: linear-gradient(120deg, {LACIVERT} 0%, {MAVI} 100%);
        color: #FFFFFF;
        padding: 1.6rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.4rem;
    }}
    .hero h1 {{
        color: #FFFFFF;
        font-size: 1.7rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
        padding: 0;
        letter-spacing: 0.2px;
    }}
    .hero p {{
        color: #D6E2F0;
        font-size: 0.97rem;
        margin: 0;
    }}

    /* Seçili model rozeti */
    .rozet {{
        display: inline-block;
        background: #E3ECF6;
        color: {MAVI};
        border: 1px solid #C5D5E8;
        padding: 0.25rem 0.8rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }}

    /* Bölüm başlıkları */
    h2, h3 {{
        color: {LACIVERT};
        font-weight: 650;
    }}
    .bolum {{
        color: {LACIVERT};
        font-size: 1.05rem;
        font-weight: 650;
        border-bottom: 2px solid #D5DEE9;
        padding-bottom: 0.35rem;
        margin: 1.4rem 0 0.9rem 0;
    }}

    /* Metrik kartları */
    div[data-testid="stMetric"] {{
        background: #FFFFFF;
        border: 1px solid #DDE3EA;
        border-left: 4px solid {MAVI};
        border-radius: 8px;
        padding: 0.9rem 1rem;
        box-shadow: 0 1px 3px rgba(11, 37, 69, 0.06);
    }}
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"] p {{
        color: {GRI};
        font-size: 0.82rem;
        font-weight: 600;
    }}
    div[data-testid="stMetricValue"] {{
        color: {LACIVERT};
        font-weight: 700;
    }}

    /* Yan menü */
    section[data-testid="stSidebar"] {{
        border-right: 1px solid #D5DEE9;
    }}
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        font-size: 1.0rem;
        color: {LACIVERT};
    }}

    /* Butonlar */
    div.stButton > button[kind="primary"] {{
        background: {MAVI};
        border: 1px solid {MAVI};
        color: #FFFFFF;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.55rem 1rem;
    }}
    div.stButton > button[kind="primary"]:hover {{
        background: {LACIVERT};
        border-color: {LACIVERT};
    }}

    /* Sekmeler */
    button[data-baseweb="tab"] {{
        font-weight: 600;
    }}

    /* Boş durum kartı */
    .bos-durum {{
        background: #FFFFFF;
        border: 1px dashed #B9C7D9;
        border-radius: 10px;
        padding: 2.2rem 1.5rem;
        text-align: center;
        color: {GRI};
    }}
    .bos-durum b {{ color: {LACIVERT}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# BAŞLIK
# ==========================================
st.markdown(
    """
    <div class="hero">
        <h1>Perakendeci Stok Modelleri Bilgi Sistemi</h1>
        <p>Probleminize uygun modeli belirleyin, parametreleri girin ve optimum sipariş politikasını tek adımda elde edin.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# YAN MENÜ: MODEL SEÇİMİ VE PARAMETRELER
# ==========================================
with st.sidebar:
    st.markdown("### 1. Adım: Stok ve Yoksatma Politikası")

    sonradan_karsilama = st.radio(
        "Stok tükenmesi durumunda işletme politikası nedir?",
        (
            "Sonradan karşılama yapılmaz (Model 4 - Klasik EOQ)",
            "Sonradan karşılama (yoksatma) yapılır (Model 3 - Perakendeci Modeli)",
        ),
    )

    pi_var_mi = False
    if "Model 3" in sonradan_karsilama:
        pi_durumu = st.radio(
            "Sonradan karşılama (yoksatma) maliyet yapısı nasıl işliyor?",
            (
                "Yalnızca zamana bağlı maliyet uygulanır (π̂)",
                "Zamana bağlı (π̂) ve zamandan bağımsız (π) maliyet birlikte uygulanır",
            ),
        )
        if "birlikte" in pi_durumu:
            pi_var_mi = True

    st.divider()
    st.markdown("### 2. Adım: İşletme ve Maliyet Parametreleri")

    D = st.number_input("Yıllık Talep (D) [adet/yıl]", min_value=0.01, value=1000.0, step=50.0)
    A = st.number_input("Sipariş Verme Maliyeti (A) [TL/sipariş]", min_value=0.01, value=100.0, step=10.0)

    h_durumu = st.radio(
        "Depolama maliyeti (h) hangi esasa göre belirlensin?",
        (
            "Birim depolama maliyeti doğrudan girilecek (h)",
            "Elde tutma oranı ile hesaplanacak (h = i × C)",
        ),
    )

    if "doğrudan" in h_durumu:
        h = st.number_input("Stokta Bulundurma Maliyeti (h) [TL/adet-yıl]", min_value=0.01, value=5.0, step=0.5)
        C = st.number_input(
            "Birim Satın Alma Maliyeti (C) [TL/adet] (Opsiyonel)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Problemde satın alma maliyeti verilmemişse veya toplama dahil edilmeyecekse 0 bırakın.",
        )
    else:
        C = st.number_input("Birim Satın Alma Maliyeti (C) [TL/adet]", min_value=0.01, value=25.0, step=1.0)
        i_yuzde = st.number_input(
            "Stokta Bulundurma Maliyet Oranı (i) [%]",
            min_value=0.01,
            max_value=1000.0,
            value=20.0,
            step=1.0,
            help="Örneğin %20 için 20 yazın.",
        )
        i_oran = i_yuzde / 100.0
        h = i_oran * C
        st.info(f"Hesaplanan h = i × C = {i_oran:.2f} × {C:.2f} = **{h:.4f} TL/adet-yıl**")

    if "Model 3" in sonradan_karsilama:
        pi_hat = st.number_input(
            "Zamana Bağlı Sonradan Karşılama Maliyeti (π̂) [TL/adet-yıl]", min_value=0.01, value=15.0, step=1.0
        )
        if pi_var_mi:
            pi_sabit = st.number_input(
                "Zamandan Bağımsız Sonradan Karşılama Maliyeti (π) [TL/adet]", min_value=0.0, value=2.0, step=0.5
            )
        else:
            pi_sabit = 0.0

    st.divider()
    st.markdown("### 3. Adım: Ek Operasyonel Maliyetler (Nakliye, Ek Depo vb.)")

    ek_secimler = st.multiselect(
        "Hangi maliyet kalemlerine ek operasyonel maliyet uygulanıyor?",
        [SECENEK_SIP, SECENEK_DEPO],
        default=[],
        placeholder="Ek maliyet yoksa boş bırakınız",
        help="Her iki kalem de aynı anda seçilebilir. Seçim yapılmazsa ek maliyet hesaba katılmaz.",
    )
    siparis_ek_var = SECENEK_SIP in ek_secimler
    depo_ek_var = SECENEK_DEPO in ek_secimler

    A_ek = 0.0
    g_ek = 0.0
    ek_baz = BAZ_ORT

    if siparis_ek_var:
        A_ek = st.number_input(
            "Ek Sipariş Maliyeti (A_ek) [TL/sipariş]",
            min_value=0.0,
            value=50.0,
            step=10.0,
            help="Nakliye, gümrükleme gibi her siparişte oluşan ek maliyet. Yıllık tutar (D/Q)·A_ek olarak hesaplanır.",
        )
    if depo_ek_var:
        g_ek = st.number_input(
            "Ek Depolama Maliyeti (g) [TL/adet-yıl]",
            min_value=0.0,
            value=1.0,
            step=0.5,
            help="Ek depo kiralama, sigorta gibi stok miktarına bağlı ek maliyet.",
        )
        ek_baz = st.radio(
            "Ek depolama maliyeti hangi stok seviyesi baz alınarak hesaplansın?",
            (BAZ_ORT, BAZ_MAKS),
            help="Ortalama stok: g·Ī  |  Maksimum stok: g·I_max (ek depo kapasitesi en yüksek stok düzeyine göre kiralanıyorsa).",
        )

    st.divider()
    if st.button("Stok Planını Oluştur", type="primary", **genis(st.button)):
        st.session_state["hesaplandi"] = True


# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================
def stok_grafigi_ciz(Q_opt, b_opt, T, t1, t2, model_adi):
    fig, ax = plt.subplots(figsize=(8, 3.8))

    I_max = Q_opt - b_opt
    if b_opt == 0:
        x = [0, 0, T, T, 2 * T]
        y = [0, Q_opt, 0, Q_opt, 0]
    else:
        x = [0, 0, t1, T, T, T + t1, 2 * T]
        y = [0, I_max, 0, -b_opt, I_max, 0, -b_opt]

    ax.plot(x, y, color=MAVI, linewidth=2.2, label="Stok Seviyesi")
    ax.axhline(0, color=LACIVERT, linewidth=1)
    ax.fill_between(x, y, 0, where=[val >= 0 for val in y], color=MAVI, alpha=0.15, label="Elde Bulunan Stok")
    if b_opt > 0:
        ax.fill_between(x, y, 0, where=[val <= 0 for val in y], color=KIRMIZI, alpha=0.22, label="Sonradan Karşılama (b)")

    ax.set_title(f"{model_adi} - Stok Seviyesi Grafiği (2 Çevrim)", color=LACIVERT, fontweight="bold", loc="left")
    ax.set_xlabel("Zaman (Yıl)", color=GRI)
    ax.set_ylabel("Stok Miktarı (Adet)", color=GRI)
    ax.grid(True, linestyle="--", alpha=0.35)
    for yon in ("top", "right"):
        ax.spines[yon].set_visible(False)
    for yon in ("left", "bottom"):
        ax.spines[yon].set_color("#B9C7D9")
    ax.tick_params(colors=GRI)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    return fig


def maliyet_dagilimi_ciz(satirlar):
    """satirlar: [(ad, tutar), ...] - toplam satırı hariç."""
    adlar = [s[0] for s in satirlar]
    tutarlar = [s[1] for s in satirlar]
    fig, ax = plt.subplots(figsize=(6, 3.0 + 0.2 * len(satirlar)))
    renkler = [MAVI, ACIK_MAVI, KIRMIZI, "#E0A458", "#6C8EAD", "#4A7C59", "#7A5C99"][: len(satirlar)]
    cubuklar = ax.barh(adlar[::-1], tutarlar[::-1], color=renkler[::-1])
    ax.bar_label(cubuklar, labels=[f"{t:,.2f}" for t in tutarlar[::-1]], padding=4, color=LACIVERT, fontsize=9)
    ax.set_xlabel("TL / Yıl", color=GRI)
    ax.set_title("Yıllık Maliyet Dağılımı", color=LACIVERT, fontweight="bold", loc="left")
    for yon in ("top", "right"):
        ax.spines[yon].set_visible(False)
    for yon in ("left", "bottom"):
        ax.spines[yon].set_color("#B9C7D9")
    ax.tick_params(colors=GRI)
    ax.set_xlim(0, max(tutarlar) * 1.25 if max(tutarlar) > 0 else 1)
    fig.tight_layout()
    return fig


def maliyet_tablosu(kalemler, toplam_adi, toplam):
    """kalemler: [(ad, tutar), ...]. Tutar ve yüzde sütunlarıyla tablo döndürür."""
    satirlar = []
    for ad, tutar in kalemler:
        oran = (tutar / toplam * 100) if toplam > 0 else 0.0
        satirlar.append([ad, f"{tutar:,.2f}", f"%{oran:.1f}"])
    satirlar.append([toplam_adi, f"{toplam:,.2f}", "%100.0"])
    return pd.DataFrame(satirlar, columns=["Maliyet Kalemi", "Tutar (TL/Yıl)", "Pay"])


def bolum(baslik):
    st.markdown(f'<div class="bolum">{baslik}</div>', unsafe_allow_html=True)


# ==========================================
# RAPORLAMA FONKSİYONLARI
# ==========================================
def tr_say(x, nd=2, binlik=True):
    """Sayıyı Türkçe biçimde yazar (1.234,56). binlik=False ise Excel için binlik ayracı kullanılmaz."""
    s = f"{x:,.{nd}f}" if binlik else f"{x:.{nd}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def rapor_zamani():
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Europe/Istanbul"))
    except Exception:
        return datetime.now()


def _deger(v, binlik=True):
    return v if isinstance(v, str) else tr_say(v, binlik=binlik)


def rapor_girdileri():
    """Rapora yazılacak model bilgileri ve girdi parametreleri."""
    metinler = [("Seçilen Model", model_etiketi)]
    ek = []
    if siparis_ek_var:
        ek.append("Sipariş maliyetine ek maliyet (nakliye vb.)")
    if depo_ek_var:
        ek.append(
            "Depolama maliyetine ek maliyet ("
            + ("ortalama stok" if ek_baz == BAZ_ORT else "maksimum stok")
            + " esaslı)"
        )
    metinler.append(("Ek Operasyonel Maliyetler", "; ".join(ek) if ek else "Uygulanmamıştır"))

    sayilar = [
        ("Yıllık Talep (D)", D, "adet/yıl"),
        ("Sipariş Verme Maliyeti (A)", A, "TL/sipariş"),
    ]
    if "doğrudan" in h_durumu:
        sayilar.append(("Stokta Bulundurma Maliyeti (h)", h, "TL/adet-yıl"))
        if C > 0:
            sayilar.append(("Birim Satın Alma Maliyeti (C)", C, "TL/adet"))
    else:
        sayilar.append(("Birim Satın Alma Maliyeti (C)", C, "TL/adet"))
        sayilar.append(("Stokta Bulundurma Maliyet Oranı (i)", i_yuzde, "%"))
        sayilar.append(("Stokta Bulundurma Maliyeti (h = i × C)", h, "TL/adet-yıl"))
    if "Model 3" in sonradan_karsilama:
        sayilar.append(("Zamana Bağlı Sonradan Karşılama Maliyeti (π̂)", pi_hat, "TL/adet-yıl"))
        if pi_var_mi:
            sayilar.append(("Zamandan Bağımsız Sonradan Karşılama Maliyeti (π)", pi_sabit, "TL/adet"))
    if siparis_ek_var:
        sayilar.append(("Ek Sipariş Maliyeti (A_ek)", A_ek, "TL/sipariş"))
    if depo_ek_var:
        sayilar.append(("Ek Depolama Maliyeti (g)", g_ek, "TL/adet-yıl"))
    return metinler, sayilar


def rapor_notlari():
    notlar = [
        "Hesaplamalar yıl 365 gün esas alınarak yapılmıştır. Talebin sabit ve önceden bilindiği, "
        "siparişlerin verildiği anda teslim alındığı varsayılmıştır.",
        "Sunulan değerler, girilen parametreler altında toplam yıllık maliyeti en küçükleyen (optimum) "
        "stok politikasını göstermektedir.",
    ]
    if "Model 3" in sonradan_karsilama:
        notlar.append(
            "Sonradan karşılama (yoksatma) politikası uygulanmıştır; stok tükendiğinde gelen talep "
            "bekletilmekte ve bir sonraki teslimatta karşılanmaktadır."
        )
    if siparis_ek_var:
        notlar.append(
            "Ek sipariş maliyeti (A_ek), her sipariş için oluştuğundan yıllık maliyete (D/Q)·A_ek olarak yansıtılmıştır."
        )
    if depo_ek_var:
        if ek_baz == BAZ_ORT:
            notlar.append("Ek depolama maliyeti (g), ortalama stok düzeyi (Ī) üzerinden hesaplanmıştır.")
        else:
            notlar.append(
                "Ek depolama maliyeti (g), maksimum stok düzeyi (I_max) üzerinden hesaplanmıştır; "
                "optimum sipariş miktarı bu esasa göre yeniden türetilmiştir."
            )
    notlar.append(
        "Bu rapor karar destek amacıyla otomatik olarak üretilmiştir. Uygulamaya geçmeden önce "
        "girdi parametrelerinin güncelliği ve doğruluğu teyit edilmelidir."
    )
    return notlar


def _paylar(kalemler, toplam):
    return [(ad, tutar, (tutar / toplam * 100) if toplam > 0 else 0.0) for ad, tutar in kalemler]


def rapor_metni(sonuclar, ozet, kalemler, toplam_adi, toplam, tarih, rapor_no):
    G = 80
    kalin, ince = "=" * G, "-" * G
    metinler, sayilar = rapor_girdileri()

    def satir(ad, deger, birim=""):
        return f" {ad:<52}{(_deger(deger) + ' ' + birim).strip():>26}"

    L = [
        kalin,
        "PERAKENDECİ STOK MODELLERİ BİLGİ SİSTEMİ".center(G),
        "STOK POLİTİKASI VE MALİYET ANALİZİ RAPORU".center(G),
        kalin,
        f" Rapor No            : {rapor_no}",
        f" Düzenlenme Tarihi   : {tarih:%d.%m.%Y %H:%M}",
        " Düzenleyen          : Perakendeci Stok Modelleri Bilgi Sistemi",
        "",
        "1. MODEL VE GİRDİ PARAMETRELERİ",
        ince,
    ]
    for ad, v in metinler:
        L.append(
            textwrap.fill(
                f"{ad:<26}: {v}", width=G - 1, initial_indent=" ", subsequent_indent=" " + " " * 28
            )
        )
    L.append("")
    L += [satir(ad, v, b) for ad, v, b in sayilar]
    L += ["", "2. OPTİMUM SONUÇLAR", ince]
    L += [satir(ad, v, b) for ad, v, b in sonuclar]
    L += ["", "3. KARAR ÖZETİ", ince]
    L.append(textwrap.fill(ozet, width=G - 2, initial_indent=" ", subsequent_indent=" "))
    L += ["", "4. YILLIK MALİYET ANALİZİ", ince]
    L.append(f" {'Maliyet Kalemi':<56}{'Tutar (TL/Yıl)':>14}{'Pay':>8}")
    L.append(" " + "-" * (G - 2))
    for ad, tutar, pay in _paylar(kalemler, toplam):
        L.append(f" {ad:<56}{tr_say(tutar):>14}{('%' + tr_say(pay, 1)):>8}")
    L.append(" " + "-" * (G - 2))
    L.append(f" {toplam_adi:<56}{tr_say(toplam):>14}{'%100,0':>8}")
    L += ["", "5. DEĞERLENDİRME VE NOTLAR", ince]
    for i, n in enumerate(rapor_notlari(), 1):
        L.append(textwrap.fill(n, width=G - 2, initial_indent=f" {i}. ", subsequent_indent="    "))
    L += [
        "",
        kalin,
        "Bu rapor Perakendeci Stok Modelleri Bilgi Sistemi tarafından otomatik olarak".center(G),
        "üretilmiştir.".center(G),
        kalin,
    ]
    return "\n".join(L).replace("\n", "\r\n") + "\r\n"


def rapor_csv(sonuclar, ozet, kalemler, toplam_adi, toplam, tarih, rapor_no):
    """Excel (Türkçe) uyumlu: ';' ayraçlı, ondalık virgüllü. UTF-8 BOM ile kodlanmalıdır."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    metinler, sayilar = rapor_girdileri()

    w.writerow(["PERAKENDECİ STOK MODELLERİ BİLGİ SİSTEMİ"])
    w.writerow(["Stok Politikası ve Maliyet Analizi Raporu"])
    w.writerow(["Rapor No", rapor_no])
    w.writerow(["Düzenlenme Tarihi", f"{tarih:%d.%m.%Y %H:%M}"])
    w.writerow([])
    w.writerow(["1. MODEL VE GİRDİ PARAMETRELERİ"])
    w.writerow(["Parametre", "Değer", "Birim"])
    for ad, v in metinler:
        w.writerow([ad, v, ""])
    for ad, v, b in sayilar:
        w.writerow([ad, _deger(v, binlik=False), b])
    w.writerow([])
    w.writerow(["2. OPTİMUM SONUÇLAR"])
    w.writerow(["Gösterge", "Değer", "Birim"])
    for ad, v, b in sonuclar:
        w.writerow([ad, _deger(v, binlik=False), b])
    w.writerow([])
    w.writerow(["3. KARAR ÖZETİ"])
    w.writerow([ozet])
    w.writerow([])
    w.writerow(["4. YILLIK MALİYET ANALİZİ"])
    w.writerow(["Maliyet Kalemi", "Tutar (TL/Yıl)", "Pay (%)"])
    for ad, tutar, pay in _paylar(kalemler, toplam):
        w.writerow([ad, tr_say(tutar, binlik=False), tr_say(pay, 1, binlik=False)])
    w.writerow([toplam_adi, tr_say(toplam, binlik=False), "100,0"])
    w.writerow([])
    w.writerow(["5. DEĞERLENDİRME VE NOTLAR"])
    for i, n in enumerate(rapor_notlari(), 1):
        w.writerow([f"{i}. {n}"])
    return buf.getvalue()


# ==========================================
# ANA ALAN: SEKMELER
# ==========================================
model_etiketi = (
    "Model 4 · Klasik EOQ (Yoksatmasız)"
    if "Model 4" in sonradan_karsilama
    else ("Model 3 · Perakendeci Modeli (π > 0)" if pi_var_mi else "Model 3 · Perakendeci Modeli (π = 0)")
)
ek_ozet = []
if siparis_ek_var:
    ek_ozet.append("Sipariş")
if depo_ek_var:
    ek_ozet.append("Depolama (" + ("ortalama stok" if ek_baz == BAZ_ORT else "maksimum stok") + ")")
rozet_metni = f"Seçili model: {model_etiketi}"
if ek_ozet:
    rozet_metni += " · Ek maliyet: " + ", ".join(ek_ozet)
st.markdown(f'<span class="rozet">{rozet_metni}</span>', unsafe_allow_html=True)


def formuller_uret():
    """Seçili modele ve ek maliyet tercihlerine göre LaTeX formüllerini üretir."""
    A_s = r"(A + A_{ek})" if siparis_ek_var else "A"
    maks = depo_ek_var and ek_baz == BAZ_MAKS

    if "Model 4" in sonradan_karsilama:
        baslik = "**Model 4 - Klasik EOQ (sonradan karşılama yok)**"
        H = "h" if not depo_ek_var else ("(h+2g)" if maks else "(h+g)")
        q = r"Q^* = \sqrt{\dfrac{2@A@D}{@H@}}".replace("@A@", A_s).replace("@H@", H)
        k = r"K(Q) = \dfrac{D}{Q}@A@ + \dfrac{Q}{2}h".replace("@A@", A_s)
        if depo_ek_var:
            k += r" + Q\,g" if maks else r" + \dfrac{Q}{2}g"
        k += " + DC"
        return baslik, [q, k]

    baslik = "**Model 3 - Perakendeci Modeli (π > 0)**" if pi_var_mi else "**Model 3 - Perakendeci Modeli (π = 0)**"
    if not maks:
        H = "(h+g)" if depo_ek_var else "h"
        if pi_var_mi:
            q = r"Q^* = \sqrt{\left(\dfrac{2@A@D}{@H@} - \dfrac{(\pi D)^2}{@H@(@H@+\hat{\pi})}\right)\dfrac{@H@+\hat{\pi}}{\hat{\pi}}}"
            b = r"b^* = \dfrac{@H@Q^* - \pi D}{@H@+\hat{\pi}}"
        else:
            q = r"Q^* = \sqrt{\dfrac{2@A@D}{@H@}\cdot\dfrac{@H@+\hat{\pi}}{\hat{\pi}}}"
            b = r"b^* = Q^*\,\dfrac{@H@}{@H@+\hat{\pi}}"
    else:
        if pi_var_mi:
            q = r"Q^* = \sqrt{\dfrac{2@A@D(h+\hat{\pi}) - (\pi D)^2}{\hat{\pi}(h+2g) - g^2}}"
            b = r"b^* = \dfrac{(h+g)Q^* - \pi D}{h+\hat{\pi}}"
        else:
            q = r"Q^* = \sqrt{\dfrac{2@A@D(h+\hat{\pi})}{\hat{\pi}(h+2g) - g^2}}"
            b = r"b^* = \dfrac{(h+g)Q^*}{h+\hat{\pi}}"
    q = q.replace("@A@", A_s).replace("@H@", H if not maks else "h")
    b = b.replace("@H@", H if not maks else "h")

    k = r"K(Q,b) = \dfrac{D}{Q}@A@ + \dfrac{(Q-b)^2}{2Q}h + \dfrac{b^2}{2Q}\hat{\pi}".replace("@A@", A_s)
    if pi_var_mi:
        k += r" + \dfrac{D}{Q}\pi b"
    if depo_ek_var:
        k += r" + (Q-b)\,g" if maks else r" + \dfrac{(Q-b)^2}{2Q}g"
    k += " + DC"
    return baslik, [q, b, k]


sekme_sonuc, sekme_formul = st.tabs(["Sonuçlar", "Model Formülleri"])

# ------------------------------------------
# SEKME: MODEL FORMÜLLERİ
# ------------------------------------------
with sekme_formul:
    formul_baslik, formul_listesi = formuller_uret()
    st.markdown(formul_baslik)
    for formul in formul_listesi:
        st.latex(formul)

    st.caption(
        "Simgeler: D yıllık talep, A sipariş maliyeti, A_ek ek sipariş maliyeti, h stokta bulundurma maliyeti, "
        "g ek depolama maliyeti, C birim satın alma maliyeti, π̂ zamana bağlı sonradan karşılama maliyeti, "
        "π zamandan bağımsız sonradan karşılama maliyeti, Ī ortalama stok, I_max maksimum stok."
    )
    if depo_ek_var and ek_baz == BAZ_MAKS:
        st.caption(
            "Ek depolama maliyeti maksimum stok düzeyi üzerinden hesaplandığında, maliyet fonksiyonunun Q ve b'ye göre "
            "türevleri sıfıra eşitlenerek yukarıdaki Q* ve b* ifadeleri elde edilir."
        )

# ------------------------------------------
# SEKME: SONUÇLAR
# ------------------------------------------
with sekme_sonuc:
    if not st.session_state.get("hesaplandi", False):
        st.markdown(
            """
            <div class="bos-durum">
                <b>Henüz hesaplama yapılmadı.</b><br>
                Sol menüden modeli seçip parametreleri girin, ardından
                <b>Stok Planını Oluştur</b> düğmesine basın.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    a_toplam = A + A_ek  # Toplam sipariş başına maliyet
    ek_depo_adi = "Ek Depolama Maliyeti (Ī·g)" if ek_baz == BAZ_ORT else "Ek Depolama Maliyeti (I_max·g)"

    # --- MODEL 4 (KLASİK EOQ) ---
    if "Model 4" in sonradan_karsilama:
        Q_opt = model4_coz(D, a_toplam, h, g_ek, ek_baz)
        I_max = Q_opt
        I_ort = Q_opt / 2
        T = Q_opt / D
        T_gun = T * 365
        N = D / Q_opt

        siparis_mlyt = (D / Q_opt) * A
        ek_siparis_mlyt = (D / Q_opt) * A_ek
        stok_mlyt = I_ort * h
        ek_depo_mlyt = g_ek * (I_ort if ek_baz == BAZ_ORT else I_max)
        satinalma_mlyt = D * C
        K_Q = siparis_mlyt + ek_siparis_mlyt + stok_mlyt + ek_depo_mlyt + satinalma_mlyt

        bolum("Temel Sonuçlar")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Optimum Sipariş (Q*)", f"{Q_opt:.2f} adet")
        c2.metric("Ortalama Stok (Ī)", f"{I_ort:.2f} adet")
        c3.metric("Çevrim Süresi (T)", f"{T_gun:.1f} gün")
        c4.metric("Toplam Maliyet K(Q)", f"{K_Q:,.2f} TL")

        st.write("")
        ozet_md = (
            f"**Karar Özeti:** En ekonomik çözüm için her **{T_gun:.1f} günde bir** (yılda {N:.1f} kez) "
            f"yaklaşık **{Q_opt:.0f} adet** sipariş vermelisiniz. Toplam yıllık maliyetiniz **{K_Q:,.2f} TL** olacaktır."
        )
        st.success(ozet_md)

        sonuc_listesi = [
            ("Optimum Sipariş Miktarı (Q*)", Q_opt, "adet"),
            ("Ortalama Stok Düzeyi (Ī)", I_ort, "adet"),
            ("Çevrim Süresi (T)", T_gun, "gün"),
            ("Yıllık Sipariş Sayısı (N)", N, "adet/yıl"),
            ("Toplam Yıllık Maliyet K(Q)", K_Q, "TL/yıl"),
        ]
        toplam_adi, toplam_tutar = "TOPLAM MALİYET K(Q)", K_Q
        ozet_duz = (
            f"En ekonomik çözüm için her {tr_say(T_gun, 1)} günde bir (yılda {tr_say(N, 1)} kez) "
            f"yaklaşık {tr_say(Q_opt, 0)} adet sipariş verilmelidir. "
            f"Toplam yıllık maliyet {tr_say(K_Q)} TL olarak gerçekleşecektir."
        )

        kalemler = [("Sipariş Verme Maliyeti ((D/Q)·A)", siparis_mlyt)]
        if siparis_ek_var:
            kalemler.append(("Ek Sipariş Maliyeti ((D/Q)·A_ek)", ek_siparis_mlyt))
        kalemler.append(("Stokta Bulundurma Maliyeti ((Q/2)·h)", stok_mlyt))
        if depo_ek_var:
            kalemler.append((ek_depo_adi, ek_depo_mlyt))
        if C > 0:
            kalemler.append(("Satın Alma Maliyeti (D·C)", satinalma_mlyt))

        bolum("Maliyet Analizi")
        sol, sag = st.columns([1.1, 1])
        with sol:
            st.dataframe(
                maliyet_tablosu(kalemler, "TOPLAM MALİYET K(Q)", K_Q), hide_index=True, **genis(st.dataframe)
            )
        with sag:
            st.pyplot(maliyet_dagilimi_ciz(kalemler))

        bolum("Stok Seviyesi Grafiği")
        st.pyplot(stok_grafigi_ciz(Q_opt, 0, T, T, 0, "Model 4 (EOQ)"))

    # --- MODEL 3 (SONRADAN KARŞILAMALI PERAKENDECİ MODELİ) ---
    else:
        Q_opt, b_opt, hata = model3_coz(D, a_toplam, h, g_ek, ek_baz, pi_hat, pi_sabit)

        if hata == "ekonomik_degil":
            st.error(
                "**Uyarı:** Girilen zamandan bağımsız sonradan karşılama maliyeti (π) ve/veya ek maliyetler nedeniyle "
                "sonradan karşılama yapmak ekonomik değildir (kök içi negatif/sıfır). "
                "Bu problemde **Model 4 (Yoksatmasız EOQ)** kullanmalısınız."
            )
            st.stop()
        if hata == "stok_yok":
            st.error(
                "**Uyarı:** Ek depolama maliyeti (g), zamana bağlı sonradan karşılama maliyetine (π̂) göre çok yüksek "
                "olduğundan optimum çözümde elde stok bulundurulmamaktadır (b* ≥ Q*). "
                "Lütfen g ve π̂ değerlerini kontrol ediniz."
            )
            st.stop()
        if b_opt <= 0:
            st.warning(
                "**Uyarı:** Hesaplanan b* ≤ 0 çıktı. Bu π değeriyle müşteriyi bekletmek (sonradan karşılama) "
                "ekonomik değildir; sistem otomatik olarak yoksatmasız çözüme (Model 4) yakınsar."
            )
            st.stop()
        model_baslik = "Model 3 (π > 0)" if pi_var_mi else "Model 3 (π = 0)"

        I_max = Q_opt - b_opt
        I_ort = ((Q_opt - b_opt) ** 2) / (2 * Q_opt)
        B_ort = (b_opt ** 2) / (2 * Q_opt)

        t1 = (Q_opt - b_opt) / D
        t2 = b_opt / D
        T = t1 + t2
        N = D / Q_opt

        siparis_mlyt = (D / Q_opt) * A
        ek_siparis_mlyt = (D / Q_opt) * A_ek
        stok_mlyt = I_ort * h
        ek_depo_mlyt = g_ek * (I_ort if ek_baz == BAZ_ORT else I_max)
        zamana_bagli_mlyt = B_ort * pi_hat
        zamandan_bagimsiz_mlyt = (D / Q_opt) * pi_sabit * b_opt
        satinalma_mlyt = D * C
        K_Qb = (
            siparis_mlyt
            + ek_siparis_mlyt
            + stok_mlyt
            + ek_depo_mlyt
            + zamana_bagli_mlyt
            + zamandan_bagimsiz_mlyt
            + satinalma_mlyt
        )

        bolum("Temel Sonuçlar")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Optimum Sipariş (Q*)", f"{Q_opt:.2f} adet")
        c2.metric("Maks. Yoksatma (b*)", f"{b_opt:.2f} adet")
        c3.metric("Maks. Stok (Q*-b*)", f"{I_max:.2f} adet")
        c4.metric("Toplam Maliyet K(Q,b)", f"{K_Qb:,.2f} TL")

        st.write("")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Ortalama Stok (Ī)", f"{I_ort:.2f} adet")
        c6.metric("Ort. Yoksatma (B̄)", f"{B_ort:.2f} adet")
        c7.metric("Stoklu Süre (t1)", f"{t1 * 365:.1f} gün")
        c8.metric("Yoksatma Süresi (t2)", f"{t2 * 365:.1f} gün")

        st.write("")
        ozet_md = (
            f"**Karar Özeti:** Her **{T * 365:.1f} günde bir** (yılda {N:.1f} kez) **{Q_opt:.0f} adet** sipariş vermelisiniz. "
            f"Stoklarınız **{t1 * 365:.1f} gün** boyunca talebi karşılayacak, kalan **{t2 * 365:.1f} günde** ise en fazla "
            f"**{b_opt:.0f} adet** talep sonradan karşılanmak üzere bekletilecektir. Toplam yıllık maliyet: **{K_Qb:,.2f} TL**."
        )
        st.success(ozet_md)

        sonuc_listesi = [
            ("Optimum Sipariş Miktarı (Q*)", Q_opt, "adet"),
            ("Maksimum Yoksatma Miktarı (b*)", b_opt, "adet"),
            ("Maksimum Stok Düzeyi (Q* - b*)", I_max, "adet"),
            ("Ortalama Stok Düzeyi (Ī)", I_ort, "adet"),
            ("Ortalama Yoksatma Düzeyi (B̄)", B_ort, "adet"),
            ("Stoklu Süre (t1)", t1 * 365, "gün"),
            ("Yoksatma Süresi (t2)", t2 * 365, "gün"),
            ("Çevrim Süresi (T)", T * 365, "gün"),
            ("Yıllık Sipariş Sayısı (N)", N, "adet/yıl"),
            ("Toplam Yıllık Maliyet K(Q,b)", K_Qb, "TL/yıl"),
        ]
        toplam_adi, toplam_tutar = "TOPLAM MALİYET K(Q,b)", K_Qb
        ozet_duz = (
            f"Her {tr_say(T * 365, 1)} günde bir (yılda {tr_say(N, 1)} kez) {tr_say(Q_opt, 0)} adet sipariş "
            f"verilmelidir. Stoklar {tr_say(t1 * 365, 1)} gün boyunca talebi karşılayacak; kalan "
            f"{tr_say(t2 * 365, 1)} günde ise en fazla {tr_say(b_opt, 0)} adet talep sonradan karşılanmak "
            f"üzere bekletilecektir. Toplam yıllık maliyet {tr_say(K_Qb)} TL olarak gerçekleşecektir."
        )

        kalemler = [("Sipariş Verme Maliyeti ((D/Q)·A)", siparis_mlyt)]
        if siparis_ek_var:
            kalemler.append(("Ek Sipariş Maliyeti ((D/Q)·A_ek)", ek_siparis_mlyt))
        kalemler.append(("Stokta Bulundurma Maliyeti (Ī·h)", stok_mlyt))
        if depo_ek_var:
            kalemler.append((ek_depo_adi, ek_depo_mlyt))
        kalemler.append(("Zamana Bağlı Sonradan Karş. Maliyeti (B̄·π̂)", zamana_bagli_mlyt))
        if pi_var_mi:
            kalemler.append(("Zamandan Bağımsız Sonradan Karş. Maliyeti ((D/Q)·π·b)", zamandan_bagimsiz_mlyt))
        if C > 0:
            kalemler.append(("Satın Alma Maliyeti (D·C)", satinalma_mlyt))

        bolum("Maliyet Analizi")
        sol, sag = st.columns([1.1, 1])
        with sol:
            st.dataframe(
                maliyet_tablosu(kalemler, "TOPLAM MALİYET K(Q,b)", K_Qb), hide_index=True, **genis(st.dataframe)
            )
        with sag:
            st.pyplot(maliyet_dagilimi_ciz(kalemler))

        bolum("Stok Seviyesi Grafiği")
        st.pyplot(stok_grafigi_ciz(Q_opt, b_opt, T, t1, t2, model_baslik))

    # --- RAPORLAMA (her iki model için ortak) ---
    bolum("Raporlama")
    st.caption(
        "Hesaplama sonuçlarını resmi rapor olarak indirebilirsiniz. CSV dosyası Excel'de doğrudan açılır "
        "(noktalı virgül ayraçlı, Türkçe sayı biçimli)."
    )
    simdi = rapor_zamani()
    rapor_no = f"STK-{simdi:%Y%m%d-%H%M%S}"
    txt_icerik = rapor_metni(sonuc_listesi, ozet_duz, kalemler, toplam_adi, toplam_tutar, simdi, rapor_no)
    csv_icerik = rapor_csv(sonuc_listesi, ozet_duz, kalemler, toplam_adi, toplam_tutar, simdi, rapor_no)
    dosya_tabani = f"stok_raporu_{simdi:%Y%m%d_%H%M}"

    r1, r2 = st.columns(2)
    with r1:
        st.download_button(
            "Resmi Raporu İndir (.txt)",
            data=txt_icerik.encode("utf-8"),
            file_name=f"{dosya_tabani}.txt",
            mime="text/plain",
            **genis(st.download_button),
        )
    with r2:
        st.download_button(
            "Maliyet Tablosunu İndir (.csv · Excel)",
            data=csv_icerik.encode("utf-8-sig"),
            file_name=f"{dosya_tabani}.csv",
            mime="text/csv",
            **genis(st.download_button),
        )
