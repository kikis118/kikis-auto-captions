def _sanitize(text: str) -> str:
    return text.replace("{", "").replace("}", "")


def _fmt_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(words, width, height, words_per_group, highlight_color, text_color) -> str:
    font_size = max(28, int(height * 0.05))
    margin_v = int(height * 0.12)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    groups = [words[i:i + words_per_group] for i in range(0, len(words), words_per_group)]
    lines = []
    for group in groups:
        for i, w in enumerate(group):
            start = w["start"]
            end = group[i + 1]["start"] if i + 1 < len(group) else w["end"] + 0.2

            parts = []
            for j, gw in enumerate(group):
                text = _sanitize(gw["word"])
                if j == i:
                    parts.append(f"{{\\c{highlight_color}}}{text}{{\\c{text_color}}}")
                else:
                    parts.append(text)
            text_line = " ".join(parts)

            lines.append(f"Dialogue: 0,{_fmt_ass_time(start)},{_fmt_ass_time(end)},Default,,0,0,0,,{text_line}")

    return header + "\n".join(lines) + "\n"
