import argparse
import requests
import misc

#use argparse to parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument("--user", default="bear85", required=True, help="user name")
parser.add_argument("--password", help="password", required=True)
args = parser.parse_args()

session = requests.Session()
session = misc.login(session, args.user, args.password)

stock_ticker_list = ['TSLA', 'TRYG']

for stock_ticker in stock_ticker_list:
    number = misc.get_stock_id(session, stock_ticker)
    print(': '.join([stock_ticker, str(number)]))