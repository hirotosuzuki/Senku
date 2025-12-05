"""
字句解析器（Lexer）

SQL文をトークンに分割する字句解析器です。
コンパイラ理論における「字句解析（Lexical Analysis）」の段階を担当します。

字句解析の役割:
- 文字列を意味のある最小単位（トークン）に分割
- キーワード、識別子、リテラル、演算子などを識別
- 空白やコメントの除去

歴史的背景:
- 字句解析は1950年代からコンパイラの基本構成要素として存在
- 正規表現や有限状態機械（FSM）を使用して実装されることが多い
- 現代のパーサジェネレータ（yacc, ANTLR等）でも字句解析が最初の段階
"""

from typing import List


class Lexer:
    """SQL字句解析器
    
    SQL文をトークンに分割します。
    将来的には正規表現や状態機械を使用したより堅牢な実装に置き換えることができます。
    """
    
    def tokenize(self, line: str) -> List[str]:
        """SQL文を行単位でトークンに分割する
        
        簡易的な実装ですが、基本的なクォート処理と括弧の扱いに対応しています。
        将来的には本格的な字句解析器（正規表現、状態機械）に置き換えることができます。
        
        Args:
            line: 入力SQL文
            
        Returns:
            トークンのリスト
            
        Examples:
            >>> lexer = Lexer()
            >>> lexer.tokenize("CREATE TABLE users(id INT, name TEXT)")
            ['CREATE', 'TABLE', 'users', '(', 'id', 'INT', ',', 'name', 'TEXT', ')']
            >>> lexer.tokenize("INSERT INTO users VALUES (1, 'alice')")
            ['INSERT', 'INTO', 'users', 'VALUES', '(', '1', ',', "'alice'", ')']
        """
        line = line.strip().rstrip(";")
        
        # クォートされた文字列を保護しながら分割
        tokens = []
        current = ""
        in_quotes = False
        quote_char = None
        
        i = 0
        while i < len(line):
            char = line[i]
            
            # クォート文字の処理
            if char in ("'", '"') and (i == 0 or line[i-1] != '\\'):
                if not in_quotes:
                    # クォート開始
                    in_quotes = True
                    quote_char = char
                    if current.strip():
                        tokens.extend(current.strip().split())
                        current = ""
                    current += char
                elif char == quote_char:
                    # クォート終了
                    in_quotes = False
                    current += char
                    tokens.append(current)
                    current = ""
                    quote_char = None
                else:
                    # 異なるクォート文字（文字列内のクォート）
                    current += char
            elif in_quotes:
                # クォート内の文字
                current += char
            elif char in ('(', ')', ','):
                # 括弧やカンマは独立したトークンとして扱う
                if current.strip():
                    tokens.extend(current.strip().split())
                    current = ""
                if char != ' ':  # 空白はトークンにしない
                    tokens.append(char)
            else:
                # 通常の文字
                current += char
            i += 1
        
        # 残りの文字列を処理
        if current.strip():
            tokens.extend(current.strip().split())
        
        return tokens

