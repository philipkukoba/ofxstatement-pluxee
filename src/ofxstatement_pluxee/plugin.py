import csv
import re
from datetime import datetime
from decimal import Decimal
from typing import TextIO, Dict, List, Optional

from unidecode import unidecode
from ofxstatement.parser import StatementParser, LT
from ofxstatement.plugin import Plugin
from ofxstatement.statement import Statement, StatementLine


class PluxeePlugin(Plugin):
    def get_parser(self, filename: str) -> "PluxeeParser":
        f = open(filename, "r", encoding='utf-8')
        f.readline()  # disregard header line
        return PluxeeParser(f)


class PluxeeParser(StatementParser[List[str]]):
    fin: TextIO  # file input stream

    # 0-based csv column mapping to StatementLine field
    mappings: Dict[str, int] = {
        "Datum": 0,
        "Beschrijving": 1,
        "Bedrag": 2
    }

    date_format = "%d-%m-%Y"

    def __init__(self, f: TextIO):
        super().__init__()
        self.fin = f

    def parse(self) -> Statement:
        reader = csv.reader(self.fin, delimiter=';', quotechar='"')

        statement = Statement(currency="euro")

        for row in reader:
            date = datetime.strptime(row[self.mappings["Datum"]], self.date_format)
            memo = unidecode(row[self.mappings["Beschrijving"]])
            amount = Decimal(self.trim_amount(row[self.mappings["Bedrag"]], row[self.mappings["Beschrijving"]]))
            transaction_type = self.get_transactiontype(memo)

            statement_line = StatementLine(date=date, memo=memo, amount=amount)
            statement_line.trntype = transaction_type
            statement.lines.append(statement_line)

        return statement

    # unused
    def parse_record(self, line: LT) -> Optional[StatementLine]:
        return None

    # helper methods
    @staticmethod
    def trim_transaction_id(memo: str) -> str:
        return re.sub(r'\(Transactie [^)]+\)', '', memo)

    @staticmethod
    def get_transactiontype(memo: str) -> str:
        if "Uitgave" in memo:
            return "POS"
        if "Storting" in memo:
            return "DEP"
        return None

    @staticmethod
    def trim_amount(transaction_amount: str, memo: str) -> str:
        expense = "Uitgave"
        trimmed = transaction_amount.replace(' ', '').removesuffix('€')
        if expense in memo:
            return trimmed.replace('+', '-')
        else:
            return trimmed.replace('+', '')
