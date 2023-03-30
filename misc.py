import requests
import pandas as pd

# Login to Nordnet
def login(user, password):
    session = requests.Session() # create a session object

    # Setting cookies prior to login by visiting login page
    url = 'https://www.nordnet.dk/logind'
    session.get(url)

    # Update headers for login
    session.headers['client-id'] = 'NEXT'
    session.headers['sub-client-id'] = 'NEXT'

    # Actual login
    url = 'https://www.nordnet.dk/api/2/authentication/basic/login'
    login = session.post(url, data = {'username': user, 'password': password})
    # Success
    if login.status_code == 200:
        return session
    else:
        print(f'Login to Nordnet failed with status code {login.status_code}. The response was:')
        print(login.text)
        print('Please check that you have correctly set up nordnet_configuration.py and enabled username/password logins on Nordnet')
        exit(-1)

#Get identifer number for stock from Stock Ticker Symbols
def get_stock_id(session, stock_ticker):
    # Set NEXT cookie and header
    url = 'https://www.nordnet.dk/markedet'
    session.get(url)
    session.headers['client-id'] = 'NEXT'
    url = 'https://www.nordnet.dk/api/2/instrument_search/query/stocklist'
    params = {'free_text_search': stock_ticker}
    stock = session.get(url, params=params)
    stocks = stock.json()
    results = stocks['results']
    if len(results) == 0:
        print(f'Found no results for {stock_ticker}. Please check your search term.')
        exit(-1)
    if len(results) > 1:
        print(f'Found more than one result for {stock_ticker}. Please specify a more unique search term.')
        exit(-1)
    number = results[0]['instrument_info']['instrument_id']
    return number

# Get list of stocks in account
def get_account_stocks(session, account):
    url = 'https://www.nordnet.dk/api/2/accounts'
    accounts = session.get(url)
    accounts = accounts.json()
    for acc in accounts:
        if acc['alias'] == account:
            account_id = acc['accno']
            break
        #if account is not found
        if acc == accounts[-1]: #if last account in list
            print(f'Account {account} not found. Please check your account name.')
            exit(-1)
    #Extract info of available cash in account
    url = f'https://www.nordnet.dk/api/2/accounts/{account_id}/info'
    account_info_list = session.get(url)
    account_info_list = account_info_list.json()
    account_info = account_info_list[0]
    account_dict = {'market_value': account_info['full_marketvalue']['value'], #stock value
                    'account_sum': account_info['account_sum']['value'], #cash
                    'total_value': account_info['own_capital']['value'] #total value
                    }
    account_dataframe = pd.DataFrame(account_dict, index=[0])
    print(account_dataframe)

    url = f'https://www.nordnet.dk/api/2/accounts/{account_id}/positions'
    positions = session.get(url)
    positions = positions.json()
    pos_dict_list = []
    for pos in positions:
        pos_dict = {'symbol': pos['instrument']['symbol'], 
                    'id': pos['instrument']['instrument_id'],
                    'currency': pos['instrument']['currency'],
                    'qty': pos['qty'], 
                    'stock_price': pos['main_market_price']['value'], #in instrument currency
                    'sum_price_local': pos['market_value_acc']['value'], #in DKK (account currency)
                    }
        #calculate the procentage of the total value of the account
        pos_dict['percent'] = pos_dict['sum_price_local']/account_dict['total_value']*100
        pos_dict_list.append(pos_dict)
    pos_dataframe = pd.DataFrame(pos_dict_list)
    print(pos_dataframe)

    return pos_dataframe


