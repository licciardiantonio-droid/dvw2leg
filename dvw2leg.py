#!/usr/bin/env python3
"""
dvw2leg.py  –  DataVolley 4 (.dvw) → DataVolley 2 (.leg) converter

Usage:
    python3 dvw2leg.py input.dvw              # writes input.leg
    python3 dvw2leg.py input.dvw output.leg
"""

import sys
import os
import re

# ── Skill and zone code translation DV4 → DV2 ─────────────────────────────────
# DV4 skill letters  →  DV2/Italian letters
SKILL = {
    'S': 'B',   # Serve    → Battuta
    'R': 'R',   # Reception → Ricezione
    'E': 'A',   # Set      → Alzata
    'A': 'S',   # Attack   → Spike/Schiacciata
    'B': 'M',   # Block    → Muro
    'D': 'D',   # Defense  → Difesa
    'F': 'F',   # Freeball (pass-through)
}
# DV4 zone letters  →  DV2 zone letters
ZONE = {
    'Q': 'V',   # Quick/veloce
    'H': 'A',   # High/alta
    'O': 'L',   # Off-pace/lenta
    'U': 'T',   # (another tempo) → T
    'T': 'T',
    'M': 'M',
    'V': 'V',
    'A': 'A',
    'L': 'L',
}

def xlat3(s3):
    """Translate 3-char skill code (e.g. 'SM-' → 'BM-').
    Special case: freeball 'F{zone}{qual}' → 'D{zone}{qual}F' in DV2."""
    if len(s3) < 3:
        return s3
    skill, zone, qual = s3[0], s3[1], s3[2]
    z2 = ZONE.get(zone, zone)
    if skill == 'F':
        return 'D' + z2 + qual + 'F'
    return SKILL.get(skill, skill) + z2 + qual


# ── File helpers ───────────────────────────────────────────────────────────────

def read_file(path):
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            pass
    raise RuntimeError(f"Cannot decode: {path}")


def parse_dvw(content):
    """
    Returns (sections, header):
      sections  – dict[section_header_string] → list[line]
      header    – dict[key] → value  (KEY: value lines, including those inside [3DATAVOLLEYSCOUT])
    """
    header = {}
    sections = {}
    cur_key = None
    cur_lines = []

    # Section names may contain hyphens (e.g. [3PLAYERS-H])
    SECTION_RE = re.compile(r'^\[3[\w-]+\]$')

    for raw in content.splitlines():
        line = raw.rstrip('\r')
        if SECTION_RE.match(line):
            if cur_key is not None:
                sections[cur_key] = cur_lines
            cur_key = line
            cur_lines = []
        elif cur_key is not None:
            cur_lines.append(line)

    if cur_key is not None:
        sections[cur_key] = cur_lines

    # Generator metadata lives inside [3DATAVOLLEYSCOUT] as "KEY: value" lines
    for line in sections.get('[3DATAVOLLEYSCOUT]', []):
        if ':' in line and not line.startswith('['):
            k, _, v = line.partition(':')
            header[k.strip()] = v.strip()

    return sections, header


def nonempty(lines):
    return [l for l in lines if l.strip()]


# ── Main conversion ────────────────────────────────────────────────────────────

# Regex that matches real action scout lines: team-char, 2-digit jersey, skill, zone, quality
ACTION_RE = re.compile(r'^([a*])(\d{2})([SREABDFsreabdf])(.)(.)(.*)$')


def convert(dvw_content):
    secs, hdr = parse_dvw(dvw_content)
    out = []

    gen_str = ' '.join(filter(None, [
        hdr.get('GENERATOR-IDP', 'DVW'),
        hdr.get('GENERATOR-REL', ''),
        hdr.get('GENERATOR-VER', ''),
    ])).strip()

    # ── [Match] ───────────────────────────────────────────────────────────────
    out.append('[Match]')
    ml = nonempty(secs.get('[3MATCH]', []))
    if ml:
        p1 = (ml[0].split(';') + [''] * 12)
        p2 = (ml[1].split(';') + [''] * 4) if len(ml) > 1 else [''] * 4
        # date ; time ; season ; championship ; phase ; '' ; f1 ; f2 ; 0 ; 1 ; teamid1 ; teamid2 ; generator
        row = [p1[0], p1[1], p1[2], p1[3], p1[4], p1[5],
               p1[6], p1[7], '0', '1',
               p2[0], p2[1], gen_str]
        out.append(';'.join(row))

    # ── [Team] ────────────────────────────────────────────────────────────────
    out.append('[Team]')
    for line in nonempty(secs.get('[3TEAMS]', [])):
        parts = line.split(';')
        out.append(';'.join(parts[:5]) + ';')

    # ── [Oders] ───────────────────────────────────────────────────────────────
    out.append('[Oders]')
    for line in nonempty(secs.get('[3MORE]', [])):
        parts = line.split(';')
        # "Referee1, Referee2" → "Referee1  Referee2" (comma+space → double space)
        parts[0] = re.sub(r',\s+', '  ', parts[0])
        fields = (parts + [''] * 6)[:6]
        out.append(';'.join(fields) + ';;0;0;')
        break  # only the first data line

    # ── [MatchComments] ───────────────────────────────────────────────────────
    out.append('[MatchComments]')
    cl = nonempty(secs.get('[3COMMENTS]', []))
    out.append((cl[0] if cl else 'no comments') + ';;;;;')

    # ── [Set] ─────────────────────────────────────────────────────────────────
    out.append('[Set]')
    for line in nonempty(secs.get('[3SET]', [])):
        out.append(line)

    # ── Build away-jersey remap  (jerseys > 49 → free slot ≤ 49) ─────────────
    home_lines = nonempty(secs.get('[3PLAYERS-H]', []))
    away_lines = nonempty(secs.get('[3PLAYERS-V]', []))

    def jersey_of(line):
        p = line.split(';')
        return int(p[1]) if len(p) > 1 and p[1].strip().isdigit() else 0

    home_js   = {jersey_of(l) for l in home_lines}
    away_orig = [jersey_of(l) for l in away_lines]

    # Numbers already "claimed" as LEG player codes (home uses jersey directly,
    # away uses jersey+50; we need jersey+50 ≤ 99, so away jersey must be ≤ 49)
    occupied = home_js | {j for j in away_orig if j <= 49}
    free = [n for n in range(1, 50) if n not in occupied]

    remap = {}   # original away jersey (>49) → remapped jersey (≤49)
    fi = 0
    for j in away_orig:
        if j > 49:
            if fi < len(free):
                remap[j] = free[fi]; fi += 1
            else:
                remap[j] = j  # fallback (unlikely)

    # ── Player line formatter ─────────────────────────────────────────────────
    def fmt_player(line, is_away):
        p = line.split(';')
        if len(p) < 16:
            return line
        if is_away:
            j = int(p[1]) if p[1].strip().isdigit() else 0
            if j > 49:
                p[1] = str(remap.get(j, j))

        # DVW:  [0]team [1]jersey [2]idx [3..7]rots(5) [8]code
        #       [9]lastName [10]firstName [11]fullName [12]libero
        #       [13]role [14]bool [15]dvid ...
        # LEG:  [0]team [1]jersey [2]idx [3..7]rots(5) [8]code
        #       [9]fullName [10]libero [11]dvid [12..16]empty(5) [17]role [18]trailing
        team   = p[0]
        jersey = p[1]
        idx    = p[2]
        rots   = p[3:8]
        code   = p[8]
        fname  = p[11] if len(p) > 11 else ''
        libero = p[12] if len(p) > 12 else ''
        role   = p[13] if len(p) > 13 else ''
        dvid   = p[15] if len(p) > 15 else ''

        return ';'.join([team, jersey, idx] + rots +
                        [code, fname, libero, dvid, '', '', '', '', role, ''])

    # ── [Player1] / [Player2] ─────────────────────────────────────────────────
    out.append('[Player1]')
    for l in home_lines:
        out.append(fmt_player(l, False))

    out.append('[Player2]')
    for l in away_lines:
        out.append(fmt_player(l, True))

    # ── Scout code translation helpers ────────────────────────────────────────

    def player_code(team_char, jersey_str):
        """DV4 team+jersey → DV2 2-digit player code."""
        j = int(jersey_str)
        if team_char == '*':          # home team: use jersey as-is
            return f'{j:02d}'
        else:                         # away team: (remapped jersey) + 50
            j2 = remap.get(j, j)
            return f'{(j2 + 50):02d}'

    # ── [Scout] ───────────────────────────────────────────────────────────────
    out.append('[Scout]')

    for line in secs.get('[3SCOUT]', []):
        if not line.strip():
            continue

        parts = line.split(';')

        # DV4 adds 12 player-position fields after the standard 14; strip them.
        # Pad to at least 14 so we can safely index.
        parts = (parts + [''] * 14)[:14]

        code = parts[0]

        # Strip DV4-only ">LUp" suffix (pre-match lineup marker)
        code = code.split('>')[0]

        # ── Team-error / free-ball-win: *$$&Hx  or  a$$&Hx ──────────────
        if re.match(r'^[a*]\$\$&', code):
            team_char = code[0]
            rest = code[3:]           # e.g. "&H#"  →  & + zone + qual
            player = '49' if team_char == '*' else '99'
            if len(rest) >= 3 and rest[0] == '&':
                new_zone = ZONE.get(rest[1], rest[1])
                parts[0] = player + '&' + new_zone + rest[2]
            else:
                parts[0] = player + rest

        # ── Regular action line: *NNSZq  or  aNNSZq ──────────────────────
        else:
            m = ACTION_RE.match(code)
            if m:
                team_char, jnum, skill, zone, qual, _extra = m.groups()
                parts[0] = player_code(team_char, jnum) + xlat3(skill + zone + qual)
            else:
                # Special control lines (z, p, P, T, c, sub markers) — keep as-is
                parts[0] = code

        out.append(';'.join(parts) + ';')

    return '\n'.join(out) + '\n'


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.leg'

    content = read_file(src)
    result  = convert(content)

    with open(dst, 'w', encoding='latin-1') as f:
        f.write(result)

    print(f'Converted: {os.path.basename(src)}  →  {os.path.basename(dst)}')
