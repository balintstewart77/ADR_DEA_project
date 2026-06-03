import re
import unicodedata

import pandas as pd


_DASH_TRANSLATION = str.maketrans({
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
})
_ZERO_WIDTH_RE = re.compile(r"[\u00ad\u200b\u200c\u200d\ufeff]")
_MULTISPACE_RE = re.compile(r"\s+")
_WRAPPED_NAME_LINE_RE = re.compile(
    r"(?m)^([A-Z][A-Za-z'`.-]+(?:[ \t]+[A-Z][A-Za-z'`.-]+){0,3})[ \t]*\n[ \t]*"
    r"([A-Z][A-Za-z'`.-]+(?:[ \t]+[A-Z][A-Za-z'`.-]+){0,3}[ \t]*,)"
)
_OPEN_INSTITUTION_TAIL_RE = re.compile(
    r"\b(?:for|of|and)$",
    re.IGNORECASE,
)
_INSTITUTION_CONTINUATION_TAIL_RE = re.compile(
    r"\b(?:Department|Education|Institute|University|Office|School|College|Centre|Center|Public Health)\b"
    r"(?:\s+(?:for|of|and))?$"
)
_NOT_INSTITUTION_RE = re.compile(
    r"^\s*$|^\d+$|^(and|the|of|for|in|at|to)\s*$",
    re.IGNORECASE,
)

_INSTITUTION_KEYWORDS = (
    "academy",
    "agency",
    "authority",
    "bank",
    "business school",
    "centre",
    "center",
    "college",
    "commission",
    "council",
    "databank",
    "department",
    "economics",
    "foundation",
    "government",
    "hospital",
    "institute",
    "laboratory",
    "ministry",
    "office",
    "public health",
    "research",
    "school",
    "service",
    "services",
    "statistics",
    "trust",
    "university",
)
_NAME_PARTICLES = {"al", "bin", "da", "de", "del", "der", "di", "dos", "du", "la", "le", "st", "van", "von"}
_NON_PERSON_WORDS = {
    "academy",
    "administrative",
    "agency",
    "authority",
    "bank",
    "belfast",
    "biosciences",
    "business",
    "cardiff",
    "centre",
    "center",
    "college",
    "commission",
    "communities",
    "council",
    "databank",
    "data",
    "department",
    "economics",
    "education",
    "energy",
    "england",
    "fiscal",
    "food",
    "foundation",
    "frontier",
    "government",
    "health",
    "housing",
    "institute",
    "international",
    "justice",
    "king's",
    "london",
    "markets",
    "media",
    "ministry",
    "national",
    "office",
    "policy",
    "public",
    "queen's",
    "research",
    "resolution",
    "royal",
    "school",
    "science",
    "service",
    "simetrica",
    "statistics",
    "strategy",
    "swansea",
    "trade",
    "uk",
    "university",
    "wales",
    "welsh",
}
_ALIASES = {
    "ons": "Office for National Statistics",
    "office for national": "Office for National Statistics",
    "office for national statistics": "Office for National Statistics",
    "dfe": "Department for Education",
    "dwp": "Department for Work and Pensions",
    "hmrc": "HM Revenue and Customs (HMRC)",
    "hm revenue and customs": "HM Revenue and Customs (HMRC)",
    "moj": "Ministry of Justice",
    "ads group limited": "ADS (Aerospace, Defence, Security, Space) Group Limited",
    "belmana ltd": "Belmana",
    "cebr": "Centre for Economic and Business Research (CEBR)",
    "centre for economic and business research": "Centre for Economic and Business Research (CEBR)",
    "centre for economic and business research ltd": "Centre for Economic and Business Research (CEBR)",
    "centre for economic and business research ltd (cber)": "Centre for Economic and Business Research (CEBR)",
    "cedar": "Centre for Healthcare Evaluation, Device Assessment, and Research (CEDAR)",
    "cristina sechel": "",
    "ecibt": "Engineering Construction Industry Training Board (ECITB)",
    "ecitb": "Engineering Construction Industry Training Board (ECITB)",
    "ehrc": "Equality and Human Rights Commission (EHRC)",
    "equality and human rights commission": "Equality and Human Rights Commission (EHRC)",
    "esri": "Environmental Systems Research Institute (ESRI)",
    "independent research": "",
    "insead": "Institut Européen d'Administration des Affaires (INSEAD)",
    "insead / institut européen d'administration des affaires": "Institut Européen d'Administration des Affaires (INSEAD)",
    "insead / institut europã©en d'administration des affaires": "Institut Européen d'Administration des Affaires (INSEAD)",
    "natcen social research": "National Centre for Social Research",
    "ucl": "University College London",
    "lse": "London School of Economics and Political Science (LSE)",
    "lshtm": "London School of Hygiene and Tropical Medicine",
    "kcl": "King's College London",
    "kings college london": "King's College London",
    "king's college london": "King's College London",
    "king's college london dimitris vallis, king's college london": "King's College London",
    "london school of economics": "London School of Economics and Political Science (LSE)",
    "london school of economics and political science": "London School of Economics and Political Science (LSE)",
    "london school of economics & political science": "London School of Economics and Political Science (LSE)",
    "the london school of economics and political science": "London School of Economics and Political Science (LSE)",
    "the london school of economics": "London School of Economics and Political Science (LSE)",
    "london school of hygiene and tropical medicine rochelle schneider dos": "London School of Hygiene and Tropical Medicine",
    "the university of manchester": "University of Manchester",
    "the university of sheffield": "University of Sheffield",
    "the university of edinburgh": "University of Edinburgh",
    "the university of warwick": "University of Warwick",
    "the university of york": "University of York",
    "the university of nottingham": "University of Nottingham",
    "the university of liverpool": "University of Liverpool",
    "the university of westminster": "University of Westminster",
    "the alan turing institute": "Alan Turing Institute",
    "agri-food biosciences institute": "Agri-Food and Biosciences Institute",
    "agri-food bioscience institute": "Agri-Food and Biosciences Institute",
    "agri-food & biosciences institute": "Agri-Food and Biosciences Institute",
    "agri-food and biosciences institute": "Agri-Food and Biosciences Institute",
    "agrifood biosciences institute": "Agri-Food and Biosciences Institute",
    "agri food biosciences institute": "Agri-Food and Biosciences Institute",
    "cardiff business school": "Cardiff University",
    "city university": "City, University of London",
    "city university london": "City, University of London",
    "city university of london": "City, University of London",
    "city university jannis stã¶ckel, london school of economics and political science": "City, University of London",
    "city, university of london": "City, University of London",
    "casa university college london": "University College London",
    "royal holloway": "Royal Holloway, University of London",
    "royal holloway, university of london": "Royal Holloway, University of London",
    "royal holloway university of london": "Royal Holloway, University of London",
    "university of london - royal holloway": "Royal Holloway, University of London",
    "university of london - kings college": "King's College London",
    "university of london kings college": "King's College London",
    "university of london - queen mary": "Queen Mary University of London",
    "university of london queen mary": "Queen Mary University of London",
    "university of london - birkbeck college": "Birkbeck, University of London",
    "university of london - university college": "University College London",
    "university of london university college": "University College London",
    "university of london / university college": "University College London",
    "university of london-university college": "University College London",
    "university of london - imperial college": "Imperial College London",
    "university of london imperial college": "Imperial College London",
    "university of london “ imperial college": "Imperial College London",
    "london school of economics and political science, university of london": "London School of Economics and Political Science (LSE)",
    "northern ireland statistics and research agency (nisra)": "Northern Ireland Statistics and Research Agency",
    "department for digital, culture, media and sport (dcms)": "Department for Digital, Culture, Media and Sport",
    "dhsc": "Department of Health and Social Care (DHSC)",
    "department of health": "Department of Health and Social Care (DHSC)",
    "department of health and social care": "Department of Health and Social Care (DHSC)",
    "department of health and social care (dhsc)": "Department of Health and Social Care (DHSC)",
    "department of health - ni": "Department of Health (Northern Ireland)",
    "beis": "Department for Business, Energy and Industrial Strategy",
    "department for business, inovation and skills - enterprise directorate": "Department for Business, Innovation and Skills",
    "administrative data research, wales": "Administrative Data Research Wales",
    "sail databank databank, swansea university": "SAIL Databank, Swansea University",
    "sail databank, swansea university": "SAIL Databank, Swansea University",
    "education policy institute niccolã2 babbini, education policy institute": "Education Policy Institute",
    "fft education limited": "FFT Education Ltd",
    "frontier economics": "Frontier Economics Ltd",
    "frontier economics ltd margheritaserena ferrara, frontier economics ltd": "Frontier Economics Ltd",
    "institute of fiscal studies": "Institute for Fiscal Studies",
    "insitute for fiscal studies": "Institute for Fiscal Studies",
    "insititute of occupational medicine": "Institute of Occupational Medicine",
    "institute of education": "UCL Institute of Education",
    "national institute of economic and social research": "National Institute for Economic and Social Research",
    "greater london authority": "Greater London Authority (GLA)",
    "health data research uk": "Health Data Research UK (HDR UK)",
    "henley business school": "Henley Business School (University of Reading)",
    "institute for social and economic research": "Institute for Social and Economic Research (University of Essex)",
    "institute for social and economic research, university of essex": "Institute for Social and Economic Research (University of Essex)",
    "johannes kepler, university": "",
    "johannes kepler university": "",
    "learning and work": "Learning and Work Institute",
    "london metropolitan, university": "London Metropolitan University",
    "m&g": "Municipal & General (M&G)",
    "national foundation for education research": "National Foundation for Education Research (NFER)",
    "national foundation for educational research": "National Foundation for Education Research (NFER)",
    "national foundation for educational research (nfer)": "National Foundation for Education Research (NFER)",
    "nfer": "National Foundation for Education Research (NFER)",
    "london economics ltd": "London Economics",
    "ipsos": "Ipsos",
    "ipsos mori": "Ipsos",
    "ipsos uk": "Ipsos",
    "pwc llp": "PwC LLP",
    "pwc": "PwC LLP",
    "pricewaterhousecoopers llp": "PwC LLP",
    "price water house coopers": "PwC LLP",
    "the university of surrey": "University of Surrey",
    "the university of kent": "University of Kent",
    "the university of aston": "University of Aston",
    "university of west anglia": "University of East Anglia",
    "queen mary university london": "Queen Mary University of London",
    "queen mary univeristy london": "Queen Mary University of London",
    "queen mary, university of london": "Queen Mary University of London",
    "heriot watt university": "Heriot-Watt University",
    "manchester metropolitan, university": "Manchester Metropolitan University",
    "nottingham trent, university": "Nottingham Trent University",
    "economic statistics, centre of excellence": "Economic Statistics Centre of Excellence",
    "european university, institute": "European University Institute",
    "netherlands interdisciplinary demographic, institute": "Netherlands Interdisciplinary Demographic Institute",
    "office for health improvement and disparities (ohid)": "Office for Health Improvement and Disparities",
    "office for national statistics </span>": "Office for National Statistics",
    "sheffield hallam univeristy": "Sheffield Hallam University",
    "stanford univeristy": "Stanford University",
    "warwick business school": "Warwick Business School",
    "cardiff metropolitan, university": "Cardiff Metropolitan University",
    "fraser of allander institute": "Fraser of Allander Institute (University of Strathclyde)",
    "fraser of allander institute (university of strathclyde)": "Fraser of Allander Institute (University of Strathclyde)",
    "fraser of allander institute james black, university of strathclyde": "Fraser of Allander Institute (University of Strathclyde)",
    "lancaster university management, school": "Lancaster University Management School",
    "st andrews, university": "University of St Andrews",
    "ucl institute of education": "UCL Institute of Education",
    "ucl institute for epidemiology and health": "UCL Institute of Epidemiology and Health",
    "university of oxford sociology": "University of Oxford - Sociology",
    "university of london - university college rui miguel vieira marques da costa, london school of economics": "University College London",
    "university of southampton cristian": "University of Southampton",
    "university of west england": "University of the West of England",
    "sqw economic and management consultants": "SQW - Economic and Management Consultants",
    "sqw-economic and management consultants": "SQW - Economic and Management Consultants",
    "whole life consultants ltd": "Whole Life Consultants",
    "arup": "ARUP",
    "cambridge university": "University of Cambridge",
    "univeristy college london": "University College London",
    "univeristy of cambridge": "University of Cambridge",
    "univeristy of bath": "University of Bath",
    "univeraity of exeter": "University of Exeter",
    "univeristy of exeter": "University of Exeter",
    "swansea univeristy": "Swansea University",
    "edniburgh napier university": "Edinburgh Napier University",
    "university college lonfon": "University College London",
    "university of northampton": "University of Northampton",
    "university of southampt on": "University of Southampton",
    "university of west of england": "University of the West of England",
    "university": "",
}
_COMPOUND_INSTITUTION_SPLITS = {
    "health foundation/ academy of medical sciences": [
        "Health Foundation",
        "Academy of Medical Sciences",
    ],
    "imperial college business, school/london school of economics": [
        "Imperial Business School",
        "London School of Economics and Political Science (LSE)",
    ],
    "london school of economics; and university college london": [
        "London School of Economics and Political Science (LSE)",
        "University College London",
    ],
    "university of warwick/london school of economics": [
        "University of Warwick",
        "London School of Economics and Political Science (LSE)",
    ],
}


def _clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASH_TRANSLATION)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = text.replace("_x000D_", " ")
    text = text.replace("\r", "\n").replace("\t", " ")
    text = text.replace("|", "\n")
    text = re.sub(
        r"(?m)^([A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,3})\s+(?=(?:Department|Institute|University|Office|School|College|Bank|Government|Agency|Databank|Centre|Center|Ministry|Hospital|Public Health)\b)",
        r"\1, ",
        text,
    )
    text = re.sub(
        r"([A-Za-z\)])\s{2,}([A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,4}\s*,)",
        r"\1\n\2",
        text,
    )
    text = re.sub(
        r"\b(Ltd|LLP)\s+([A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,4}\s*,)",
        r"\1\n\2",
        text,
    )
    text = _join_wrapped_name_lines(text)
    text = re.sub(r",\s*\n\s*", ", ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


def _join_wrapped_name_lines(text: str) -> str:
    while True:
        updated = _WRAPPED_NAME_LINE_RE.sub(
            lambda match: _join_wrapped_name_match(match, text),
            text,
        )
        if updated == text:
            return text
        text = updated


def _join_wrapped_name_match(match: re.Match, source_text: str) -> str:
    previous_line = source_text[: match.start()].rstrip("\n").split("\n")[-1]
    if previous_line.rstrip().endswith(","):
        return match.group(0)
    previous_tail = _clean_fragment(previous_line.split(",")[-1])
    if _INSTITUTION_CONTINUATION_TAIL_RE.search(previous_tail):
        return match.group(0)

    candidate = f"{match.group(1)} {match.group(2).rstrip(' ,')}"
    prefix_words = _clean_fragment(match.group(1)).split()
    suffix_words = _clean_fragment(match.group(2).rstrip(" ,")).split()
    if len(prefix_words) > 1 and len(suffix_words) > 1:
        return match.group(0)
    if _looks_like_name(candidate):
        return f"{match.group(1)} {match.group(2)}"
    return match.group(0)


def _clean_fragment(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASH_TRANSLATION)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _MULTISPACE_RE.sub(" ", text)
    return text.strip(" \t\r\n,;.")


def _build_logical_lines(text: str) -> list[str]:
    logical_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = _clean_fragment(raw_line)
        if not line:
            continue
        tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
        if logical_lines:
            previous_tail = _clean_fragment(logical_lines[-1].split(",")[-1])
            if "," in line:
                split_line = _split_leading_institution_continuation(line)
                if split_line:
                    continuation, remainder = split_line
                    if _same_fragment(continuation, previous_tail):
                        line = _clean_fragment(remainder)
                        tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
                        if not line:
                            continue
                    elif (
                        _OPEN_INSTITUTION_TAIL_RE.search(previous_tail)
                        or (
                            _INSTITUTION_CONTINUATION_TAIL_RE.search(previous_tail)
                            and not _looks_like_single_name_token(continuation)
                        )
                    ):
                        logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {continuation}")
                        line = _clean_fragment(remainder)
                        tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
                        if not line:
                            continue
            if _OPEN_INSTITUTION_TAIL_RE.search(previous_tail):
                split_line = _split_leading_institution_continuation(line)
                if split_line:
                    continuation, remainder = split_line
                    logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {continuation}")
                    line = _clean_fragment(remainder)
                    tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
                    if not line:
                        continue
                if not _starts_name(tokens, 0):
                    logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
                    continue
            if "," not in line and _INSTITUTION_CONTINUATION_TAIL_RE.search(previous_tail):
                logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
                continue
        if (
            logical_lines
            and tokens
            and not _starts_name(tokens, 0)
            and _looks_like_institution_fragment(tokens[0])
        ):
            logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
            continue
        if logical_lines and "," not in line and not _starts_name(line.split(","), 0):
            logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
            continue
        logical_lines.append(line)
    return logical_lines


def _same_fragment(left: str, right: str) -> bool:
    return _clean_fragment(left).casefold() == _clean_fragment(right).casefold()


def _split_leading_institution_continuation(line: str) -> tuple[str, str] | None:
    if "," not in line:
        return None
    head, tail = line.split(",", 1)
    words = head.split()
    for cut in range(1, len(words) - 1):
        continuation = " ".join(words[:cut])
        name = " ".join(words[cut:])
        if _looks_like_name(name):
            return continuation, _clean_fragment(f"{name}, {tail}")
    return None


def _looks_like_name_word(word: str) -> bool:
    cleaned = word.strip("()")
    if not cleaned:
        return False
    if cleaned.lower() in _NAME_PARTICLES:
        return True
    if cleaned.lower() in _NON_PERSON_WORDS:
        return False
    return bool(re.fullmatch(r"[A-Z][A-Za-z'`.-]*", cleaned))


def _looks_like_name(token: str) -> bool:
    token = _clean_fragment(token)
    words = token.split()
    if len(words) < 2 or len(words) > 5:
        return False
    if any(any(keyword in word.lower() for keyword in _INSTITUTION_KEYWORDS) for word in words):
        return False
    return all(_looks_like_name_word(word) for word in words)


def _looks_like_single_name_token(token: str) -> bool:
    token = _clean_fragment(token)
    words = token.split()
    return len(words) == 1 and _looks_like_name_word(words[0])


def _looks_like_institution_fragment(token: str) -> bool:
    token = _clean_fragment(token)
    if not token:
        return False
    lower = token.lower()
    if lower in _ALIASES:
        return True
    return any(keyword in lower for keyword in _INSTITUTION_KEYWORDS)


def _starts_name(tokens: list[str], index: int) -> int:
    token = tokens[index]
    if _looks_like_name(token):
        return 1
    if (
        _looks_like_single_name_token(token)
        and index + 1 < len(tokens)
        and _looks_like_single_name_token(tokens[index + 1])
    ):
        return 2
    return 0


def _normalise_institution(name: str) -> str:
    name = _clean_fragment(name)
    if not name:
        return ""

    lowered = name.lower()
    if lowered in _ALIASES:
        return _ALIASES[lowered]

    repeated_alias = _normalise_repeated_alias_with_researcher(name)
    if repeated_alias is not None:
        return repeated_alias

    if "," in name:
        head, tail = name.rsplit(",", 1)
        if _looks_like_institution_fragment(head) and _looks_like_name(tail):
            name = _clean_fragment(head)

    lowered = name.lower()
    if lowered in _ALIASES:
        return _ALIASES[lowered]

    institution_prefix = _normalise_known_institution_prefix(name)
    if institution_prefix is not None:
        return institution_prefix

    return name


def _normalise_repeated_alias_with_researcher(name: str) -> str | None:
    if "," not in name:
        return None

    head, tail = (_clean_fragment(part) for part in name.rsplit(",", 1))
    tail_canonical = _canonical_from_alias_or_name(tail)
    if tail_canonical is None:
        return None

    head_lower = head.lower()
    tail_lower = tail.lower()
    if not head_lower.startswith(f"{tail_lower} "):
        return None

    suffix = _clean_fragment(head[len(tail):])
    if _looks_like_name(suffix):
        return tail_canonical
    return None


def _normalise_known_institution_prefix(name: str) -> str | None:
    name_lower = name.lower()
    for alias, canonical in _known_institution_prefixes():
        if name_lower.startswith(f"{alias} "):
            suffix = _clean_fragment(name[len(alias):])
            if _looks_like_name(suffix):
                return canonical
    return None


def _known_institution_prefixes() -> list[tuple[str, str]]:
    candidates: dict[str, str] = {}
    for alias, canonical in _ALIASES.items():
        if canonical:
            candidates[alias] = canonical
            candidates.setdefault(canonical.lower(), canonical)
    return sorted(candidates.items(), key=lambda item: len(item[0]), reverse=True)


def _canonical_from_alias_or_name(name: str) -> str | None:
    lowered = name.lower()
    if lowered in _ALIASES:
        return _ALIASES[lowered] or None
    for canonical in {value for value in _ALIASES.values() if value}:
        if lowered == canonical.lower():
            return canonical
    return None


def _split_compound_institution(name: str) -> list[str]:
    lowered = name.lower()
    if lowered in _COMPOUND_INSTITUTION_SPLITS:
        return _COMPOUND_INSTITUTION_SPLITS[lowered]
    return [name]


def parse_institutions(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, proj in df.iterrows():
        raw = proj.get("Researchers", "")
        if not isinstance(raw, str) or not raw.strip():
            continue

        project_id = proj["Project ID"]
        year = proj["Year"]
        text = _clean_text(raw)
        institutions_seen = set()

        for line in _build_logical_lines(text):
            if not line or "," not in line:
                continue

            tokens = [_clean_fragment(part) for part in line.split(",")]
            tokens = [token for token in tokens if token]
            i = 0
            while i < len(tokens):
                consumed = _starts_name(tokens, i)
                if not consumed:
                    i += 1
                    continue

                i += consumed
                institution_parts = []

                while i < len(tokens):
                    next_consumed = _starts_name(tokens, i)
                    if institution_parts and next_consumed:
                        break
                    token = tokens[i]
                    if institution_parts and _looks_like_name(token) and i == len(tokens) - 1:
                        break
                    institution_parts.append(token)
                    i += 1

                institution = _normalise_institution(", ".join(institution_parts))
                for split_institution in _split_compound_institution(institution):
                    if (
                        split_institution
                        and not _NOT_INSTITUTION_RE.match(split_institution)
                        and len(split_institution) > 2
                        and split_institution not in institutions_seen
                    ):
                        institutions_seen.add(split_institution)
                        rows.append({
                            "Project ID": project_id,
                            "Year": year,
                            "institution": split_institution,
                        })

    return pd.DataFrame(rows, columns=["Project ID", "Year", "institution"])
