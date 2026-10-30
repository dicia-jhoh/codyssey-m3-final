import os
import sqlite3

from app.schema import Decoded
from app.share import create_share


def test_expires_at_has_an_index():
    create_share(Decoded(doc_type="고지서", title="t", plain=[], marks=[], todos=[], basis=[]))
    db = sqlite3.connect(os.environ["SHARE_DB"])
    names = [row[1] for row in db.execute("PRAGMA index_list(shares)")]
    assert "shares_expires_at" in names
