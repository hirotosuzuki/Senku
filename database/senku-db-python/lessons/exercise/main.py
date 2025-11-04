import argparse

# exercise用の実装に合わせてインポート
from .db.database import Database


def _print_result(result):
    if result is None:
        return
    print(result)


def main():
    parser = argparse.ArgumentParser(description="MiniDB exercise (ch01→ch10 累積)")
    parser.add_argument("-e", "--execute", action="append")
    args = parser.parse_args()

    db = Database()

    if args.execute:
        try:
            for q in args.execute:
                res = db.execute(q)
                _print_result(res)
        finally:
            # ch02以降: 実装できたら保存処理が呼ばれる想定
            if hasattr(db, "save_all"):
                db.save_all()
        return

    print("MiniDB exercise REPL: Ctrl+Dで終了")
    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            res = db.execute(line)
            _print_result(res)
    finally:
        if hasattr(db, "save_all"):
            db.save_all()


if __name__ == "__main__":
    main()

