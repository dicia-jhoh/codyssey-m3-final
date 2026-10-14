import sys
from pathlib import Path

# backend/ 에서 pytest 를 치면 app 패키지를 찾게 한다
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
