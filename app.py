import math

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
    if st.button("Stok Planını Oluştur", type="primary", use_container_width=True):
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
    renkler = [MAVI, ACIK_MAVI, KIRMIZI, "#E0A458", "#6C8EAD"][: len(satirlar)]
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
# ANA ALAN: SEKMELER
# ==========================================
model_etiketi = (
    "Model 4 · Klasik EOQ (Yoksatmasız)"
    if "Model 4" in sonradan_karsilama
    else ("Model 3 · Perakendeci Modeli (π > 0)" if pi_var_mi else "Model 3 · Perakendeci Modeli (π = 0)")
)
st.markdown(f'<span class="rozet">Seçili model: {model_etiketi}</span>', unsafe_allow_html=True)

sekme_sonuc, sekme_formul = st.tabs(["Sonuçlar", "Model Formülleri"])

# ------------------------------------------
# SEKME: MODEL FORMÜLLERİ
# ------------------------------------------
with sekme_formul:
    if "Model 4" in sonradan_karsilama:
        st.markdown("**Model 4 - Klasik EOQ (sonradan karşılama yok)**")
        st.latex(r"Q^* = \sqrt{\dfrac{2AD}{h}}")
        st.latex(r"K(Q) = \dfrac{D}{Q}A + \dfrac{Q}{2}h + DC")
    elif not pi_var_mi:
        st.markdown("**Model 3 - Perakendeci Modeli (π = 0)**")
        st.latex(r"Q^* = \sqrt{\dfrac{2AD}{h}\cdot\dfrac{h+\hat{\pi}}{\hat{\pi}}}")
        st.latex(r"b^* = Q^*\,\dfrac{h}{h+\hat{\pi}}")
        st.latex(r"K(Q,b) = \dfrac{D}{Q}A + \dfrac{(Q-b)^2}{2Q}h + \dfrac{b^2}{2Q}\hat{\pi} + DC")
    else:
        st.markdown("**Model 3 - Perakendeci Modeli (π > 0)**")
        st.latex(
            r"Q^* = \sqrt{\left(\dfrac{2AD}{h} - \dfrac{(\pi D)^2}{h(h+\hat{\pi})}\right)\dfrac{h+\hat{\pi}}{\hat{\pi}}}"
        )
        st.latex(r"b^* = \dfrac{hQ^* - \pi D}{h+\hat{\pi}}")
        st.latex(
            r"K(Q,b) = \dfrac{D}{Q}A + \dfrac{(Q-b)^2}{2Q}h + \dfrac{b^2}{2Q}\hat{\pi} + \dfrac{D}{Q}\pi b + DC"
        )

    st.caption(
        "Simgeler: D yıllık talep, A sipariş maliyeti, h stokta bulundurma maliyeti, C birim satın alma maliyeti, "
        "π̂ zamana bağlı sonradan karşılama maliyeti, π zamandan bağımsız sonradan karşılama maliyeti."
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

    # --- MODEL 4 (KLASİK EOQ) ---
    if "Model 4" in sonradan_karsilama:
        Q_opt = math.sqrt((2 * D * A) / h)
        I_ort = Q_opt / 2
        T = Q_opt / D
        T_gun = T * 365
        N = D / Q_opt

        siparis_mlyt = (D / Q_opt) * A
        stok_mlyt = I_ort * h
        satinalma_mlyt = D * C
        K_Q = siparis_mlyt + stok_mlyt + satinalma_mlyt

        bolum("Temel Sonuçlar")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Optimum Sipariş (Q*)", f"{Q_opt:.2f} adet")
        c2.metric("Ortalama Stok (Ī)", f"{I_ort:.2f} adet")
        c3.metric("Çevrim Süresi (T)", f"{T_gun:.1f} gün")
        c4.metric("Toplam Maliyet K(Q)", f"{K_Q:,.2f} TL")

        st.write("")
        st.success(
            f"**Karar Özeti:** En ekonomik çözüm için her **{T_gun:.1f} günde bir** (yılda {N:.1f} kez) "
            f"yaklaşık **{Q_opt:.0f} adet** sipariş vermelisiniz. Toplam yıllık maliyetiniz **{K_Q:,.2f} TL** olacaktır."
        )

        kalemler = [
            ("Sipariş Verme Maliyeti ((D/Q)·A)", siparis_mlyt),
            ("Stokta Bulundurma Maliyeti ((Q/2)·h)", stok_mlyt),
        ]
        if C > 0:
            kalemler.append(("Satın Alma Maliyeti (D·C)", satinalma_mlyt))

        bolum("Maliyet Analizi")
        sol, sag = st.columns([1.1, 1])
        with sol:
            st.dataframe(maliyet_tablosu(kalemler, "TOPLAM MALİYET K(Q)", K_Q), hide_index=True, use_container_width=True)
        with sag:
            st.pyplot(maliyet_dagilimi_ciz(kalemler))

        bolum("Stok Seviyesi Grafiği")
        st.pyplot(stok_grafigi_ciz(Q_opt, 0, T, T, 0, "Model 4 (EOQ)"))

    # --- MODEL 3 (SONRADAN KARŞILAMALI PERAKENDECİ MODELİ) ---
    else:
        if not pi_var_mi:
            Q_opt = math.sqrt(((2 * A * D) / h) * ((h + pi_hat) / pi_hat))
            b_opt = Q_opt * (h / (h + pi_hat))
            model_baslik = "Model 3 (π = 0)"
        else:
            kok_ici = ((2 * A * D) / h) - (((pi_sabit * D) ** 2) / (h * (h + pi_hat)))
            if kok_ici <= 0:
                st.error(
                    "**Uyarı:** Girilen zamandan bağımsız sonradan karşılama maliyeti (π) çok yüksek olduğu için "
                    "sonradan karşılama yapmak ekonomik değildir (kök içi negatif/sıfır). "
                    "Bu problemde **Model 4 (Yoksatmasız EOQ)** kullanmalısınız."
                )
                st.stop()

            Q_opt = math.sqrt(kok_ici) * math.sqrt((h + pi_hat) / pi_hat)
            b_opt = (h * Q_opt - pi_sabit * D) / (h + pi_hat)

            if b_opt <= 0:
                st.warning(
                    "**Uyarı:** Hesaplanan b* ≤ 0 çıktı. Bu π değeriyle müşteriyi bekletmek (sonradan karşılama) "
                    "ekonomik değildir; sistem otomatik olarak yoksatmasız çözüme (Model 4) yakınsar."
                )
                st.stop()
            model_baslik = "Model 3 (π > 0)"

        I_max = Q_opt - b_opt
        I_ort = ((Q_opt - b_opt) ** 2) / (2 * Q_opt)
        B_ort = (b_opt ** 2) / (2 * Q_opt)

        t1 = (Q_opt - b_opt) / D
        t2 = b_opt / D
        T = t1 + t2
        N = D / Q_opt

        siparis_mlyt = (D / Q_opt) * A
        stok_mlyt = I_ort * h
        zamana_bagli_mlyt = B_ort * pi_hat
        zamandan_bagimsiz_mlyt = (D / Q_opt) * pi_sabit * b_opt
        satinalma_mlyt = D * C
        K_Qb = siparis_mlyt + stok_mlyt + zamana_bagli_mlyt + zamandan_bagimsiz_mlyt + satinalma_mlyt

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
        st.success(
            f"**Karar Özeti:** Her **{T * 365:.1f} günde bir** (yılda {N:.1f} kez) **{Q_opt:.0f} adet** sipariş vermelisiniz. "
            f"Stoklarınız **{t1 * 365:.1f} gün** boyunca talebi karşılayacak, kalan **{t2 * 365:.1f} günde** ise en fazla "
            f"**{b_opt:.0f} adet** talep sonradan karşılanmak üzere bekletilecektir. Toplam yıllık maliyet: **{K_Qb:,.2f} TL**."
        )

        kalemler = [
            ("Sipariş Verme Maliyeti ((D/Q)·A)", siparis_mlyt),
            ("Stokta Bulundurma Maliyeti (Ī·h)", stok_mlyt),
            ("Zamana Bağlı Sonradan Karş. Maliyeti (B̄·π̂)", zamana_bagli_mlyt),
        ]
        if pi_var_mi:
            kalemler.append(("Zamandan Bağımsız Sonradan Karş. Maliyeti ((D/Q)·π·b)", zamandan_bagimsiz_mlyt))
        if C > 0:
            kalemler.append(("Satın Alma Maliyeti (D·C)", satinalma_mlyt))

        bolum("Maliyet Analizi")
        sol, sag = st.columns([1.1, 1])
        with sol:
            st.dataframe(maliyet_tablosu(kalemler, "TOPLAM MALİYET K(Q,b)", K_Qb), hide_index=True, use_container_width=True)
        with sag:
            st.pyplot(maliyet_dagilimi_ciz(kalemler))

        bolum("Stok Seviyesi Grafiği")
        st.pyplot(stok_grafigi_ciz(Q_opt, b_opt, T, t1, t2, model_baslik))


        bolum("Stok Seviyesi Grafiği")
        st.pyplot(stok_grafigi_ciz(Q_opt, b_opt, T, t1, t2, model_baslik))
