def _sanitize(text: str) -> str:
    return text.replace("{", "").replace("}", "")


def _fmt_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(
    words, width, height, words_per_group, highlight_color, text_color,
    font_name="Arial", pos_x_frac=0.5, pos_y_frac=0.85, font_size=None, letter_spacing=0,
) -> str:
    font_size = font_size or max(28, int(height * 0.05))
    pos_x = int(width * pos_x_frac)
    pos_y = int(height * pos_y_frac)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,{letter_spacing},0,1,4,2,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    pos_tag = f"{{\\an5\\pos({pos_x},{pos_y})}}"

    groups = [words[i:i + words_per_group] for i in range(0, len(words), words_per_group)]
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
