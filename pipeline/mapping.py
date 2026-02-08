"""
PHASE 5 & 8 — Cartes interactives (Folium).

Deux cartes :
  A) map_sites.html  : tous les sites géocodés, colorés par score
  B) map_route.html  : itinéraire optimal avec polyline + marqueurs ordonnés
"""

from pathlib import Path

import folium
import pandas as pd

from .config import OUTPUT_DIR

# ── Couleurs par statut ──────────────────────────────────────────────
STATUS_COLORS = {"OK": "#2ecc71", "WARNING": "#f39c12", "FAILED": "#e74c3c"}


def _legend_html() -> str:
    """Légende HTML injectée dans la carte."""
    return """
    <div style="
        position:fixed; bottom:30px; left:30px; z-index:1000;
        background:white; padding:10px 14px; border-radius:8px;
        box-shadow:0 2px 6px rgba(0,0,0,.3); font-size:13px;
        font-family:sans-serif; line-height:1.6;">
        <b>Score géocodage</b><br>
        <span style="color:#2ecc71;">&#9679;</span> OK (&ge; 0.7)<br>
        <span style="color:#f39c12;">&#9679;</span> WARNING (0.5 – 0.7)<br>
        <span style="color:#e74c3c;">&#9679;</span> FAILED (&lt; 0.5)
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════
#  Carte des sites
# ═══════════════════════════════════════════════════════════════════════

def create_sites_map(df_sites: pd.DataFrame) -> folium.Map:
    """
    Un CircleMarker par site, couleur selon score,
    popup avec label + score + nb orthos.
    """
    df = df_sites[df_sites["latitude"].notna()].copy()

    if df.empty:
        return folium.Map(location=[46.6, 2.3], zoom_start=6)

    center = [df["latitude"].mean(), df["longitude"].mean()]
    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

    for _, row in df.iterrows():
        color = STATUS_COLORS.get(row.get("status", ""), "#999")
        popup_html = (
            f"<b>{row.get('geocoded_label', '')}</b><br>"
            f"Score : {row.get('score', '')}<br>"
            f"Orthos : {row.get('nb_orthos', '?')}<br>"
            f"<small>{row.get('address_normalized', '')}</small>"
        )
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=6,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"Site {row.get('site_id','')} – {row.get('nb_orthos','')} orthos",
        ).add_to(m)

    m.get_root().html.add_child(folium.Element(_legend_html()))
    return m


# ═══════════════════════════════════════════════════════════════════════
#  Carte de l'itinéraire
# ═══════════════════════════════════════════════════════════════════════

def create_route_map(
    df_routable: pd.DataFrame,
    route_order: list[int],
    route_geometry: list[list[list[float]]] | None = None,
) -> folium.Map:
    """
    Trace l'itinéraire optimal sur la carte.
      - route_order : indices 0-based dans df_routable
      - route_geometry : segments [[lat,lon], …] venant d'OSRM (optionnel)
    """
    df = df_routable.copy()
    if df.empty or not route_order:
        return folium.Map(location=[46.6, 2.3], zoom_start=6)

    center = [df["latitude"].mean(), df["longitude"].mean()]
    m = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")

    # ── Polyline ─────────────────────────────────────────────────────
    if route_geometry:
        for segment in route_geometry:
            folium.PolyLine(
                locations=segment,
                weight=4,
                color="#3498db",
                opacity=0.8,
            ).add_to(m)
    else:
        coords = []
        for idx in route_order:
            row = df.iloc[idx]
            coords.append([row["latitude"], row["longitude"]])
        folium.PolyLine(
            locations=coords,
            weight=4,
            color="#3498db",
            opacity=0.8,
        ).add_to(m)

    # ── Marqueurs numérotés ──────────────────────────────────────────
    n = len(route_order)
    for order, idx in enumerate(route_order):
        row = df.iloc[idx]

        # Couleur : vert=départ, rouge=arrivée, bleu=intermédiaire
        if order == 0:
            bg = "#27ae60"
        elif order == n - 1:
            bg = "#c0392b"
        else:
            bg = "#2980b9"

        label = str(order + 1)

        # Construire la popup avec les noms des orthophonistes
        orthos_list = row.get("orthos_list", [])
        popup_html = f"<b>#{order + 1}</b> – {row.get('geocoded_label', '')}<br>"

        if orthos_list and len(orthos_list) > 0:
            popup_html += "<br><b>Orthophonistes :</b><br>"
            for ortho in orthos_list:
                name = f"{ortho.get('given_names', '')} {ortho.get('family_name', '')}".strip()
                popup_html += f"• {name}<br>"
                phone = ortho.get('phone', '')
                email = ortho.get('email', '')
                if phone and phone != '' and phone != 'nan':
                    popup_html += f"&nbsp;&nbsp;📞 {phone}<br>"
                if email and email != '' and email != 'nan':
                    popup_html += f"&nbsp;&nbsp;✉️ {email}<br>"
        else:
            popup_html += f"<br>{row.get('nb_orthos', '?')} orthophoniste(s)"

        # Tooltip au survol (noms seulement)
        if orthos_list and len(orthos_list) > 0:
            tooltip_text = f"#{order + 1} — " + ", ".join([
                f"{o.get('given_names', '')} {o.get('family_name', '')}".strip()
                for o in orthos_list[:3]  # Max 3 noms dans le tooltip
            ])
            if len(orthos_list) > 3:
                tooltip_text += f" (+{len(orthos_list) - 3})"
        else:
            tooltip_text = f"#{order + 1}"

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=tooltip_text,
            icon=folium.DivIcon(
                html=(
                    f'<div style="background:{bg};color:#fff;border-radius:50%;'
                    f'width:22px;height:22px;text-align:center;line-height:22px;'
                    f'font-size:10px;font-weight:700;border:2px solid #fff;'
                    f'box-shadow:0 1px 3px rgba(0,0,0,.4);">{label}</div>'
                ),
                icon_size=(22, 22),
                icon_anchor=(11, 11),
            ),
        ).add_to(m)

    return m


# ═══════════════════════════════════════════════════════════════════════
#  Export
# ═══════════════════════════════════════════════════════════════════════

def save_map(
    m: folium.Map,
    filename: str,
    output_dir: Path | str | None = None,
) -> Path:
    out = Path(output_dir) if output_dir else OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    m.save(str(path))
    return path
