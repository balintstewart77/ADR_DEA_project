import re

import pandas as pd


def _project_id_key(value) -> str:
    if pd.isna(value):
        return ""
    key = " ".join(str(value).split())
    return re.sub(r"\s+CLOSED$", "", key, flags=re.IGNORECASE)


def _title_key(value) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).split())
