from pathlib import Path
from threading import Thread

import pandas as pd
import requests

THIS_FOLDER = Path(__file__).parent.resolve()
file_tokens = THIS_FOLDER / "data" / "tokens.txt"

class PrivatBank:
    def __init__(self, name, id_number, token, acc, date_from, date_to):
        self.name = name
        self.id_number = id_number
        self.token = token
        self.acc = acc
        self.date_from = date_from
        self.date_to = date_to
        self.json_data = None
        self.balance_in = None
        self.balance_out = None
        self.balances = None
        self.turnover_credit = None
        self.turnover_debt = None
        self.status = None
        self.message = None

    def send_to_privat_bank(self):
        url = 'https://acp.privatbank.ua/api/statements/balance'
        payload = {
            'acc': self.acc,
            'startDate': self.date_from,
            'endDate': self.date_to
        }
        headers = {
            'id': self.id_number,
            'token': self.token,
            'Content-Type': 'application/json;charset=cp1251'
        }
        response = requests.get(url, headers=headers, params=payload)
        self.json_data = response.json()

    def read_json_period(self):
        self.status = self.json_data['status']
        if self.status == 'ERROR':
            self.message = self.json_data['message']
            return
        try:
            self.balances = pd.DataFrame(self.json_data['balances'])
            self.balances[['balanceIn', 'balanceOut', 'turnoverCred', 'turnoverDebt']] = self.balances[
                ['balanceIn', 'balanceOut', 'turnoverCred', 'turnoverDebt']].apply(pd.to_numeric)
            self.balance_in = self.balances['balanceIn'].iloc[-1]
            self.balance_out = self.balances['balanceOut'].iloc[0]
            self.turnover_credit = self.balances['turnoverCred'].sum().round(2)
            self.turnover_debt = self.balances['turnoverDebt'].sum().round(2)
            self.acc = self.balances['acc'][0]
        except (IndexError, KeyError):
            print("Попытка получить данные за несуществующий период")

    def read_json(self):
        self.status = self.json_data['status']
        if self.status == 'ERROR':
            self.message = self.json_data['message']
            return
        try:
            self.balance_in = self.json_data['balances'][-1]['balanceIn']
            self.balance_out = self.json_data['balances'][-1]['balanceOut']
            self.turnover_credit = self.json_data['balances'][-1]['turnoverCred']
            self.turnover_debt = self.json_data['balances'][-1]['turnoverDebt']
            self.acc = self.json_data['balances'][-1]['acc']
        except (IndexError, KeyError):
            print("Попытка получить данные за несуществующий период")

    def append_to_table(self, table):
        table.append({
            "Organization": f"{self.name}",
            "ACC": f"Code: {self.json_data.get('code', '')} {self.message}"
            if self.status == 'ERROR' else f"{self.acc}",
            "Balance IN": f"{self.balance_in}",
            "Credit": f"{self.turnover_credit}",
            "Debit": f"{self.turnover_debt}",
            "Balance OUT": f"{self.balance_out}"})

    def print_result(self):
        print(
            f"{self.name}\nНачальный остаток: {self.balance_in} UAH\nПоступление: {self.turnover_credit} UAH\n"
            f"Выбытие: {self.turnover_debt}\nКонечный остаток: {self.balance_out} UAH")

    def print_error(self):
        print(f"{self.name}\n{self.message}")


def get_data_from_privatbank(date_start, date_end=None):
    def process_line(data):
        try:
            name, acc, id_number, token = data.strip().split(';')
        except ValueError:
            print(f"Invalid data: {data}")
            return []
        balance_fop = PrivatBank(name, id_number, token, acc, date_start, date_end)
        balance_fop.send_to_privat_bank()
        if date_end:
            balance_fop.read_json_period()
        else:
            balance_fop.read_json()

        if balance_fop.status == 'ERROR':
            balance_fop.print_error()
        balance_fop.append_to_table(table_result)

    table_result = []
    with open(file_tokens, 'r', encoding="utf-8") as f:
        threads = []
        for line in f:
            th = Thread(target=process_line, args=(line,))
            threads.append(th)
            th.start()
        for th in threads:
            th.join()

    return table_result
