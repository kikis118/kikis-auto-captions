def _sanitize(text: str) -> str:
    return text.replace("{", "").replace("}", "")


def _hex_to_bgr(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"{b}{g}{r}".upper()


def hex_to_tag_color(hex_color: str) -> str:
    """#RRGGBB -> ASS override-tag color, e.g. \\c&HBBGGRR&"""
    return f"&H{_hex_to_bgr(hex_color)}&"


def hex_to_style_color(hex_color: str) -> str:
    """#RRGGBB -> ASS Style-line color field (opaque), e.g. &H00BBGGRR"""
    return f"&H00{_hex_to_bgr(hex_color)}"


def _fmt_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _group_words(words, words_per_group, max_gap):
    """Groups words for display, breaking early on a speech pause so words
    don't appear on screen before they're actually said."""
    groups = []
    current = []
    for w in words:
        if current and (len(current) >= words_per_group or w["start"] - current[-1]["end"] > max_gap):
            groups.append(current)
            current = []
        current.append(w)
    if current:
        groups.append(current)
    return groups


def build_ass(
    words, width, height, words_per_group, highlight_color, text_color,
    font_name="Arial", pos_x_frac=0.5, pos_y_frac=0.85, font_size=None, letter_spacing=0, max_group_gap=0.5,
    outline_color="&H00000000", outline_width=4, bold=True,
) -> str:
    font_size = font_size or max(28, int(height * 0.05))
    pos_x = int(width * pos_x_frac)
    pos_y = int(height * pos_y_frac)
    bold_val = -1 if bold else 0

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,{outline_color},&H00000000,{bold_val},0,0,0,100,100,{letter_spacing},0,1,{outline_width},2,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    pos_tag = f"{{\\an5\\pos({pos_x},{pos_y})}}"

    groups = _group_words(words, words_per_group, max_group_gap)
    lines = []
    for gi, group in enumerate(groups):
        # cap the last word's display end at the next group's start so two
        # groups never render on screen at once during the handoff
        next_group_start = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else None

        for i, w in enumerate(group):
            start = w["start"]
            if i + 1 < len(group):
                end = group[i + 1]["start"]
            else:
                end = w["end"] + 0.2
                if next_group_start is not None:
                    end = min(end, next_group_start)

            parts = []
            for j, gw in enumerate(group):
                text = _sanitize(gw["word"])
                if j == i:
                    parts.append(f"{{\\c{highlight_color}}}{text}{{\\c{text_color}}}")
                else:
                    parts.append(text)
            text_line = pos_tag + " ".join(parts)

            lines.append(f"Dialogue: 0,{_fmt_ass_time(start)},{_fmt_ass_time(end)},Default,,0,0,0,,{text_line}")

    return header + "\n".join(lines) + "\n"
