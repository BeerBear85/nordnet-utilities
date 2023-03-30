import argparse
import requests
import misc
import keyring
from getpass import getpass

#use argparse to parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument("--user", default="bear85", help="user name for Nordnet")
parser.add_argument("--account", default="AI debot", help="Nordnet konto name to use")
args = parser.parse_args()

# Get password from windows credential manager or promt user for password
password =  keyring.get_password("nordnet",args.user)
if password is None:
    password = getpass("Password for " + args.user + ": ") # prompt user for password (do not show password)

session = misc.login(args.user, password) #login to Nordnet
misc.get_account_stocks(session, args.account) #get list of stocks in account

stock_ticker_list = ['TSLA', 'TRYG']

for stock_ticker in stock_ticker_list:
    number = misc.get_stock_id(session, stock_ticker)
    print(': '.join([stock_ticker, str(number)]))