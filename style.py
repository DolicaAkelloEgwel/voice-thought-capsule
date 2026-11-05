"""
style.py - the look of the app only (colours, fonts, layout, buttons).

Nothing here changes what the app does. app.py passes THEME, CSS and HEAD to Gradio when it starts.

Style: "light streaks" - a black page, a cinematic hero with soft streaks of orange, peach and
violet light, a floating pill navigation, large light-weight headings, quiet dark cards and
white / dark pill buttons. Orange is the one accent colour.
"""

import base64
import inspect
from pathlib import Path

import gradio as gr

BG = "#050506"  # page (black)
SURFACE = "#0e0e11"  # cards
SURFACE_2 = "#16161a"  # raised parts: dark buttons, bubbles
FIELD = "#08080a"  # inputs
LINE = "rgba(255,255,255,0.08)"
LINE_STRONG = "rgba(255,255,255,0.14)"
TEXT = "#f5f5f7"
MUTED = "#8f8f99"
ORANGE = "#ff7a2f"  # the accent
PEACH = "#ffc4a0"
VIOLET = "#8b5cf6"

# Theme values, set for both light and dark mode so the app always looks the same.
_values = {
    "body_background_fill": BG,
    "body_text_color": TEXT,
    "body_text_color_subdued": MUTED,
    "background_fill_primary": SURFACE,
    "background_fill_secondary": BG,
    "block_background_fill": "transparent",
    "block_border_color": "transparent",
    "block_border_width": "0px",
    "block_label_background_fill": "transparent",
    "block_label_text_color": MUTED,
    "block_label_border_color": "transparent",
    "block_title_text_color": MUTED,
    "block_info_text_color": MUTED,
    "block_radius": "16px",
    "block_shadow": "none",
    "border_color_primary": LINE,
    "border_color_accent": ORANGE,
    "color_accent": ORANGE,
    "color_accent_soft": "rgba(255,122,47,0.14)",
    "input_background_fill": FIELD,
    "input_background_fill_focus": FIELD,
    "input_border_color": LINE,
    "input_border_color_focus": "rgba(255,122,47,0.55)",
    "input_border_width": "1px",
    "input_placeholder_color": "#5c5c66",
    "input_radius": "12px",
    "input_shadow": "none",
    "input_shadow_focus": "0 0 0 3px rgba(255,122,47,0.12)",
    # main buttons: white pill with black text ("Work with us" in the reference)
    "button_primary_background_fill": "#ffffff",
    "button_primary_background_fill_hover": "#ffe9dc",
    "button_primary_text_color": "#0a0a0b",
    "button_primary_border_color": "transparent",
    # other buttons: dark pill with white text ("Talk to Sales")
    "button_secondary_background_fill": SURFACE_2,
    "button_secondary_background_fill_hover": "#202026",
    "button_secondary_text_color": TEXT,
    "button_secondary_border_color": LINE,
    # delete buttons: dark pill with soft red text
    "button_cancel_background_fill": SURFACE_2,
    "button_cancel_background_fill_hover": "#2a1715",
    "button_cancel_text_color": "#ff9b8a",
    "button_cancel_border_color": "rgba(255,120,100,0.22)",
    "button_large_radius": "999px",
    "button_small_radius": "999px",
    "checkbox_background_color": FIELD,
    "checkbox_background_color_selected": ORANGE,
    "checkbox_border_color": "rgba(255,255,255,0.22)",
    "checkbox_border_color_selected": ORANGE,
    "checkbox_label_background_fill": SURFACE_2,
    "checkbox_label_background_fill_selected": SURFACE_2,
    "checkbox_label_border_color": LINE,
    "checkbox_label_text_color": TEXT,
    "checkbox_label_text_color_selected": TEXT,
    "slider_color": ORANGE,
    "table_even_background_fill": "transparent",
    "table_odd_background_fill": "rgba(255,255,255,0.02)",
    "table_border_color": LINE,
    "table_row_focus": "rgba(255,122,47,0.08)",
    "link_text_color": PEACH,
    "link_text_color_hover": "#ffffff",
    "code_background_fill": "rgba(255,255,255,0.06)",
    "panel_background_fill": SURFACE,
    "panel_border_color": LINE,
    "shadow_drop": "none",
    "shadow_drop_lg": "none",
    "stat_background_fill": ORANGE,
}

_base = gr.themes.Base(
    primary_hue="orange",
    neutral_hue="zinc",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
    radius_size="lg",
)
_allowed = set(inspect.signature(_base.set).parameters)
THEME = _base.set(
    **{k: v for k, v in _values.items() if k in _allowed},
    **{f"{k}_dark": v for k, v in _values.items() if f"{k}_dark" in _allowed},
)

# The hero artwork (drawn by assets/make_hero.py), built into the page so no extra file is needed.
_hero_file = Path(__file__).parent / "assets" / "hero.jpg"
HERO_IMAGE = (
    f"url(data:image/jpeg;base64,{base64.b64encode(_hero_file.read_bytes()).decode()})"
    if _hero_file.exists()
    else "none"
)

HEADING = '"Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif'

CSS = f"""
/* =========================================================================
   PAGE
   ========================================================================= */
html, body, gradio-app {{ background: {BG} !important; }}
.gradio-container, .gradio-container > .main, .contain {{ background: transparent !important; }}
.gradio-container > .main, .contain, .vtc-nav, .tabitem {{ width: 100% !important; }}
.gradio-container {{ max-width: 1240px !important; margin: 0 auto !important; padding: 0 32px 80px !important; }}
footer {{ display: none !important; }}                       /* hides "Built with Gradio" for the exhibition */
*:focus-visible {{ outline: 2px solid {ORANGE} !important; outline-offset: 2px; }}
::selection {{ background: rgba(255,122,47,0.35); }}

/* =========================================================================
   HERO - full-screen light streaks, title bottom-left, text + buttons bottom-right
   ========================================================================= */
.vtc-hero {{
    position: relative; min-height: 92vh; justify-content: flex-end !important;
    padding: 120px 0 0 !important; gap: 0 !important; margin-bottom: 40px;
    background: transparent !important; border: none !important; overflow: visible !important;
}}
.gradio-container, .gradio-container > .main, .gradio-container .wrap:has(> .vtc-hero),
.contain, .contain > .column {{ overflow: visible !important; }}
.vtc-hero::before {{
    content: ""; position: absolute; z-index: 0; pointer-events: none;
    top: 0; bottom: 0; left: 50%; width: 100vw; transform: translateX(-50%);
    background: {HERO_IMAGE} center 30% / cover no-repeat, {BG};
    animation: vtc-drift 18s ease-in-out infinite alternate;
}}
.vtc-hero::after {{                 /* soft fade into the page */
    content: ""; position: absolute; z-index: 0; pointer-events: none; bottom: 0; height: 30%;
    left: 50%; width: 100vw; transform: translateX(-50%);
    background: linear-gradient(180deg, transparent, {BG});
}}
@keyframes vtc-drift {{ from {{ background-position: center 26%; }} to {{ background-position: center 36%; }} }}
.vtc-hero > * {{ position: relative; z-index: 1; }}
.vtc-hero .block, .vtc-hero .form, .vtc-hero .html-container {{ background: transparent !important; border: none !important; padding: 0 !important; }}
.vtc-hero-row {{ align-items: flex-end !important; gap: 48px !important; padding-bottom: 40px; }}
.vtc-hero-row > .block {{ flex: 3 1 0 !important; min-width: 0 !important; }}
.vtc-hero-side {{ flex: 2 1 0 !important; gap: 22px !important; max-width: 420px; margin-left: auto; }}
.vtc-hero h1 {{
    font-family: {HEADING}; font-weight: 300; color: #ffffff; margin: 0;
    font-size: clamp(52px, 7vw, 104px); line-height: 0.95; letter-spacing: -0.045em;
}}
.vtc-hero-text {{ color: #d4d4da; font-size: 15px; line-height: 1.6; margin: 0; }}
.vtc-hero-text code {{ color: #fff; background: rgba(255,255,255,0.10); padding: 1px 6px; border-radius: 6px; }}
.vtc-hero-ctas {{ gap: 10px !important; flex-wrap: nowrap !important; }}
.vtc-hero-ctas button {{ flex: 0 0 auto !important; width: auto !important; min-width: 130px !important; }}
.vtc-flow {{
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 18px 28px;
    border-top: 1px solid {LINE}; padding: 30px 4px 6px;
}}
.vtc-flow div {{ display: flex; align-items: center; gap: 10px; color: #e7e7ea; font-size: 15px; font-weight: 500; }}
.vtc-flow svg {{ width: 22px; height: 22px; stroke: #fff; opacity: .9; }}
.vtc-flow i {{ font-style: normal; color: {ORANGE}; font-size: 11px; letter-spacing: .08em; font-family: "JetBrains Mono", monospace; }}

/* =========================================================================
   NAVIGATION - a floating pill at the top, always visible
   ========================================================================= */
.vtc-nav {{ background: transparent !important; border: none !important; padding: 0 !important; scroll-margin-top: 96px; }}
.vtc-nav > .tab-wrapper, .vtc-nav .tab-wrapper {{
    position: fixed !important; top: 16px; left: 50%; transform: translateX(-50%); z-index: 100;
    width: min(980px, calc(100vw - 32px)) !important; margin: 0 !important; height: auto !important;
    padding: 6px 6px 6px 60px !important; border-radius: 999px !important;
    background: rgba(12,12,14,0.72) !important; border: 1px solid {LINE_STRONG} !important;
    backdrop-filter: blur(18px) saturate(140%); -webkit-backdrop-filter: blur(18px) saturate(140%);
    box-shadow: 0 12px 40px rgba(0,0,0,0.45);
}}
.vtc-nav .tab-wrapper::before {{       /* logo mark: a small capsule of light */
    content: ""; position: absolute; left: 18px; top: 50%; width: 26px; height: 16px; margin-top: -8px;
    border-radius: 999px; background: linear-gradient(120deg, {PEACH}, {ORANGE} 45%, {VIOLET});
    box-shadow: 0 0 18px rgba(255,122,47,0.55);
}}
.vtc-nav .tab-container {{ border: none !important; gap: 2px; justify-content: space-between !important; width: 100%; height: auto !important; }}
.vtc-nav .tab-container::after {{ display: none !important; }}
button[role="tab"] {{
    border-radius: 999px !important; padding: 9px 16px !important; margin: 0 !important; height: auto !important;
    color: #c9c9d0 !important; border: 1px solid transparent !important; background: transparent !important;
    font-weight: 500 !important; font-size: 14px !important; transition: all 0.2s ease;
}}
button[role="tab"]:hover {{ color: #ffffff !important; }}
button[role="tab"][aria-selected="true"] {{
    color: #0a0a0b !important; background: #ffffff !important; font-weight: 600 !important;
}}
button[role="tab"]::after, button[role="tab"][aria-selected="true"]::after {{ display: none !important; }}
/* the last tab looks like the "Work with us" button in the reference */
.vtc-nav .tab-container button[role="tab"]:last-of-type:not([aria-selected="true"]) {{
    background: {SURFACE_2} !important; border-color: {LINE_STRONG} !important; color: #fff !important;
}}
.tabitem {{ background: transparent !important; border: none !important; padding: 0 !important; }}

/* =========================================================================
   SECTION HEADER - number + big light title on the left, explanation on the right
   ========================================================================= */
.vtc-section {{
    align-items: flex-end !important; gap: 40px !important;
    padding: 24px 0 28px !important; margin-bottom: 28px; border-bottom: 1px solid {LINE};
}}
.vtc-section > .block {{ padding: 0 !important; background: transparent !important; }}
.vtc-section > .block:first-child {{ flex: 1 1 0 !important; }}
.vtc-section-title span {{
    display: inline-block; font-family: "JetBrains Mono", monospace; font-size: 12px; letter-spacing: .1em;
    color: {ORANGE}; margin-bottom: 10px;
}}
.vtc-section .vtc-section-title h2 {{
    font-family: {HEADING} !important; font-weight: 300 !important; color: #fff !important; margin: 0 !important;
    font-size: clamp(40px, 5vw, 64px) !important; line-height: 1 !important; letter-spacing: -0.04em !important;
}}
.vtc-intro {{ flex: 1 1 0 !important; max-width: 520px; margin-left: auto; }}
.vtc-intro p {{ color: #b8b8c0 !important; font-size: 15px !important; line-height: 1.6; margin: 0 0 8px !important; }}
.vtc-intro em {{ color: #b8b8c0 !important; }}
.vtc-intro strong {{ color: #fff !important; }}

/* =========================================================================
   CARDS - quiet dark panels
   ========================================================================= */
.vtc-card {{
    background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0)) , {SURFACE} !important;
    border: 1px solid {LINE} !important; border-radius: 22px !important;
    padding: 24px !important; gap: 16px !important; margin-bottom: 20px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}}
.vtc-card .block, .vtc-card .form, .vtc-card > .styler {{
    background: transparent !important; border: none !important; box-shadow: none !important;
}}
.vtc-card .block, .vtc-card .form {{ padding: 0 !important; }}
.vtc-card .form {{ gap: 16px !important; }}
.vtc-card .accordion {{ margin: 4px 0; }}
.vtc-card .label-wrap {{ padding: 4px 0 !important; color: {TEXT} !important; font-weight: 500; }}
.vtc-quiet {{ background: transparent !important; }}
.vtc-grid {{ gap: 20px !important; align-items: flex-start !important; }}
.vtc-grid > .column {{ gap: 0 !important; }}
.vtc-grid > .vtc-card {{ margin-bottom: 20px; }}

/* labels: small, quiet, sentence case */
.vtc-card [data-testid="block-info"], .vtc-card [data-testid="block-label"], .vtc-toolbar [data-testid="block-info"] {{
    font-size: 13px !important; color: {MUTED} !important; font-weight: 500 !important; letter-spacing: 0 !important;
}}
.vtc-card [data-testid="block-label"] svg {{ display: none; }}
.vtc-card textarea, .vtc-card input[type="text"], .vtc-card input:not([type]) {{ font-size: 15px !important; }}

/* =========================================================================
   RECORDER - a clean white "Record" pill with a mic icon (no red dot)
   ========================================================================= */
.vtc-recorder {{ justify-content: space-between; }}
.vtc-recorder [data-testid="audio"], .vtc-recorder .audio-container {{ background: transparent !important; }}
.vtc-recorder .controls {{ align-items: center; gap: 12px; }}
.record-button, button.record {{
    background: #ffffff !important; color: #0a0a0b !important; border: none !important;
    border-radius: 999px !important; padding: 0 22px 0 18px !important; min-height: 44px !important;
    font-size: 15px !important; font-weight: 600 !important; box-shadow: 0 0 0 6px rgba(255,255,255,0.05) !important;
}}
.record-button::before, button.record::before {{       /* replaces Gradio's red dot with a mic */
    content: "" !important; display: inline-block !important; width: 16px !important; height: 16px !important;
    vertical-align: -3px; margin-right: 8px !important; border-radius: 0 !important; background: no-repeat center/contain url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230a0a0b' stroke-width='2.2' stroke-linecap='round'><rect x='9' y='3' width='6' height='11' rx='3'/><path d='M5 11a7 7 0 0 0 14 0M12 18v3'/></svg>") !important;
    animation: none !important;
}}
.record-button:hover, button.record:hover {{ background: #ffe9dc !important; }}
.stop-button, .stop-button-paused {{
    background: {ORANGE} !important; color: #0a0a0b !important; border: none !important;
    border-radius: 999px !important; padding: 0 22px !important; min-height: 44px !important;
    font-size: 15px !important; font-weight: 600 !important;
    box-shadow: 0 0 0 6px rgba(255,122,47,0.16), 0 0 30px rgba(255,122,47,0.45) !important;
}}
.stop-button::before, .stop-button-paused::before {{       /* a small square "stop" sign instead of a dot */
    content: "" !important; display: inline-block !important; width: 10px !important; height: 10px !important;
    border-radius: 2px !important; vertical-align: 0; margin: 0 8px 0 0 !important;
    background: #0a0a0b !important; animation: none !important;
}}
.vtc-recorder select, .mic-select {{
    background: {SURFACE_2} !important; border: 1px solid {LINE} !important; border-radius: 999px !important;
    color: #c9c9d0 !important; padding: 0 14px !important; height: 38px !important; line-height: 38px;
    max-width: 240px; font-size: 13px !important;
}}

/* =========================================================================
   BUTTONS - one height everywhere; white = main action, dark = everything else
   ========================================================================= */
button.primary, button.secondary, button.stop, button.cancel {{
    border-radius: 999px !important; min-height: 46px !important; height: 46px;
    padding: 0 24px !important; font-size: 15px !important; font-weight: 500 !important;
    white-space: nowrap; box-shadow: none !important;
    transition: background .2s ease, transform .15s ease, box-shadow .25s ease !important;
}}
button.primary {{ font-weight: 600 !important; }}
button.primary:hover {{ transform: translateY(-1px); box-shadow: 0 8px 30px rgba(255,122,47,0.25) !important; }}
.vtc-card button.primary, .vtc-card button.secondary, .vtc-card button.stop {{
    width: 100% !important; max-width: none !important; margin: 0 !important;
}}
.vtc-card > button, .vtc-card > .column > button {{ flex: 0 0 auto !important; }}
.vtc-card .row {{ align-items: flex-end !important; gap: 12px !important; margin-top: 4px; }}
.vtc-card .row + button, .vtc-card .row + .row {{ margin-top: 8px !important; }}
.vtc-card .form + button {{ margin-top: 8px !important; }}
.vtc-card .row > button {{ flex: 1 1 0 !important; align-self: flex-end !important; }}
.vtc-card .row > .form:has(input[type="checkbox"]) {{ flex-direction: column !important; }}
.vtc-card .row > .form:has(input[type="checkbox"]) > .block {{ width: 100% !important; flex: 1 1 auto !important; }}
/* one main action at the top of a card (Connections): left aligned, natural width */
.vtc-actions {{ justify-content: flex-start !important; }}
.vtc-card .vtc-actions > button {{ flex: 0 0 auto !important; width: auto !important; min-width: 240px; }}
/* settings row on Record: accordion left, button right */
.vtc-settings {{ align-items: center !important; }}
.vtc-settings > .column {{ justify-content: center; }}
/* toolbar on Sorted items */
.vtc-toolbar {{ align-items: center !important; gap: 16px !important; margin-bottom: 20px; }}
.vtc-toolbar > .block, .vtc-chips, .vtc-chips .wrap, .vtc-chips fieldset {{ background: transparent !important; border: none !important; padding: 0 !important; }}
.vtc-toolbar > .form, .vtc-section > .form {{ background: transparent !important; border: none !important; }}
.vtc-chips [data-testid="block-info"] {{ display: block; margin: 0 0 10px 2px; font-size: 13px !important; color: {MUTED} !important; }}
.vtc-toolbar > .column {{ justify-content: center; gap: 8px !important; align-self: center !important; }}
.vtc-toolbar button {{ width: 100% !important; }}
/* undo bar on Edit */
.vtc-undo {{ align-items: center !important; padding: 14px 14px 14px 24px !important; }}
.vtc-undo > button {{ flex: 0 0 240px !important; width: 240px !important; }}

/* =========================================================================
   CHIPS (radio buttons as pills)
   ========================================================================= */
.vtc-chips label, .vtc-card .wrap label:has(input[type="radio"]) {{
    border-radius: 999px !important; padding: 9px 18px !important;
    background: {SURFACE_2} !important; border: 1px solid {LINE} !important;
}}
.vtc-chips label:has(input:checked), .vtc-card .wrap label:has(input[type="radio"]:checked) {{
    background: #ffffff !important; border-color: #ffffff !important;
}}
.vtc-chips label:has(input:checked) span, .vtc-card .wrap label:has(input[type="radio"]:checked) span {{ color: #0a0a0b !important; }}
.vtc-chips input[type="radio"], .vtc-card .wrap input[type="radio"] {{ display: none; }}

/* =========================================================================
   ASK - question bar first, then the answer
   ========================================================================= */
.vtc-composer {{
    background: {FIELD} !important; border: 1px solid {LINE_STRONG} !important;
    border-radius: 999px !important; padding: 6px 6px 6px 14px !important; align-items: center !important;
    gap: 6px !important;
}}
.vtc-composer:focus-within {{ border-color: rgba(255,122,47,0.55) !important; }}
.vtc-composer .block, .vtc-composer .form {{ background: transparent !important; border: none !important; padding: 0 !important; }}
.vtc-composer label > span, .vtc-composer [data-testid="block-info"] {{
    position: absolute !important; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0);
}}
.vtc-composer textarea, .vtc-composer input {{
    background: transparent !important; border: none !important; box-shadow: none !important;
    font-size: 16px !important; padding: 10px 4px !important;
}}
.vtc-card .vtc-composer button.primary {{ width: auto !important; flex: 0 0 auto !important; min-width: 96px; }}
.vtc-chat .gallery button, .vtc-chat .gallery-item, .vtc-chat table.examples-table td {{
    border-radius: 999px !important; background: {SURFACE_2} !important; border: 1px solid {LINE} !important;
    color: #d4d4da !important; font-size: 13.5px !important;
}}
.vtc-bubble textarea {{
    background: {SURFACE_2} !important; border: 1px solid {LINE} !important; border-left: 2px solid {ORANGE} !important;
    border-radius: 14px !important; color: #ffffff !important; padding: 16px 18px !important;
    font-size: 16px !important; line-height: 1.6;
}}

/* =========================================================================
   TEXT
   ========================================================================= */
.prose {{ padding-left: 2px; padding-right: 2px; }}
.prose, .prose p, .prose li {{ color: #d4d4da; }}
.prose h2, .prose h3 {{
    font-family: {HEADING}; font-weight: 400; color: #ffffff; letter-spacing: -0.03em;
    font-size: 26px !important; margin: 0 0 6px !important;
}}
.prose em {{ color: {MUTED}; }}
.prose strong {{ color: #ffffff; }}
.vtc-consent {{ max-width: 760px; }}

/* =========================================================================
   TABLES
   ========================================================================= */
.vtc-table-card {{ padding: 14px !important; }}
.table-wrap, .table-wrap *, .body-cell, .body-cell *, table, table * {{
    --font-mono: "Inter", ui-sans-serif, system-ui, sans-serif;
    font-family: "Inter", ui-sans-serif, system-ui, sans-serif !important;
}}
table {{ border: none !important; }}
thead th {{ background: transparent !important; color: {MUTED} !important;
    font-weight: 500 !important; font-size: 12.5px !important; border-bottom: 1px solid {LINE} !important; }}
td {{ border-color: rgba(255,255,255,0.05) !important; }}

/* =========================================================================
   SMALL SCREENS
   ========================================================================= */
@media (max-width: 860px) {{
    .gradio-container {{ padding: 0 16px 60px !important; }}
    .vtc-hero-row, .vtc-section {{ flex-direction: column !important; align-items: flex-start !important; gap: 20px !important; }}
    .vtc-hero-side, .vtc-intro {{ margin-left: 0; max-width: none; }}
    .vtc-nav .tab-wrapper {{ border-radius: 22px !important; padding-left: 6px !important; }}
    .vtc-nav .tab-wrapper::before {{ display: none; }}
}}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.12); border-radius: 10px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
"""

HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500&display=swap" rel="stylesheet">
"""

# --- hero pieces (used in app.py) ---
HERO_TITLE = "<h1>Voice Thought<br>Capsule</h1>"

HERO_TEXT = """<p class="vtc-hero-text">Recordings and thoughts are stored on this computer in the
<code>data/</code> folder. To transcribe, sort, connect and answer, the audio and text are sent to
Google's Gemini service.</p>"""

_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">{}</svg>'
)
_FLOW = [
    (
        "01",
        "Speak",
        '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    ),
    ("02", "Transcribe", '<path d="M4 6h16M4 12h10M4 18h13"/>'),
    ("03", "Sort", '<path d="M4 7h10M4 12h7M4 17h4M17 5v14M14 16l3 3 3-3"/>'),
    (
        "04",
        "Connect",
        '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/>'
        '<circle cx="18" cy="18" r="2.5"/><path d="M8.3 11 15.7 7M8.3 13l7.4 4"/>',
    ),
    ("05", "Ask", '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/>'),
    (
        "06",
        "Listen",
        '<path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="14" width="4" height="6" rx="1.5"/>'
        '<rect x="17" y="14" width="4" height="6" rx="1.5"/>',
    ),
]
FLOW_STRIP = (
    '<div class="vtc-flow">'
    + "".join(
        f"<div>{_ICON.format(svg)}<i>{n}</i>{word}</div>" for n, word, svg in _FLOW
    )
    + "</div>"
)

# Hero buttons: after switching tab, scroll down to it smoothly.
SCROLL_TO_TABS = "() => { document.querySelector('.vtc-nav')?.scrollIntoView({behavior: 'smooth'}); }"
