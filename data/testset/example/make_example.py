"""합성 예시 고지서 1장 생성 — 진짜 30장 테스트셋이 아니다.

score_testset.py가 실제 이미지 파일로 끝까지 도는지(라벨 읽기→추출→채점) 확인하는
스모크 테스트용. images/ 는 개인정보라 통째로 gitignore 대상이라, 진짜 데이터가
모이기 전엔 아무도 score_testset.py를 실제 이미지로 돌려본 적이 없었다.

사용(재생성할 때만, 이미 example.jpg는 커밋돼 있어서 평소엔 안 돌려도 됨):
    pip install pillow
    python data/testset/example/make_example.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "example.jpg"
FONT_CANDIDATES = [
    "/Library/Fonts/NanumGothic.ttf",  # macOS
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
]

WIDTH, HEIGHT = 1000, 1400


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(40)
    body_font = _font(28)

    draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], outline="black", width=2)
    draw.text((60, 60), "2026년 자동차세 납부고지서(예시)", fill="black", font=title_font)
    draw.text((60, 160), "납부금액: 금 48,200원", fill="black", font=body_font)
    draw.text((60, 240), "납부기한: 2026.10.31까지", fill="black", font=body_font)
    draw.text((100, 980), "구비서류: 신분증, 차량등록증 사본", fill="black", font=body_font)
    draw.text((60, 1300), "(합성 예시 — 실제 고지서 아님)", fill="black", font=body_font)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, quality=90)
    print(f"[✓] {OUT}")


if __name__ == "__main__":
    main()
