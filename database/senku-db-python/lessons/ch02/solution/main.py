import argparse
from db.database import Database


def _print_result(result):
    if result is None:
        return
    print(result)


def main():
    parser = argparse.ArgumentParser(description="MiniDB ch02 solution")
    parser.add_argument("-e", "--execute", action="append")
    args = parser.parse_args()

    db = Database()

    if args.execute:
        try:
            for q in args.execute:
                try:
                    res = db.execute(q)
                    _print_result(res)
                except Exception as e:
                    print(f"エラー: {str(e)}")
        finally:
            db.save_all()
        return

    print("MiniDB ch02 solution REPL: Ctrl+Dで終了")
    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            try:
                res = db.execute(line)
                _print_result(res)
            except Exception as e:
                print(f"エラー: {str(e)}")
    finally:
        db.save_all()


if __name__ == "__main__":
    main()

