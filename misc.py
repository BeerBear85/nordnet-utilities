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

#Get info df for stock from Stock Ticker Symbols
def get_stock_info(session, stock_ticker):
    # Set NEXT cookie and header
    url = 'https://www.nordnet.dk/markedet'
    session.get(url)
    session.headers['client-id'] = 'NEXT'
    url = 'https://www.nordnet.dk/api/2/instrument_search/query/stocklist'
    params = {'free_text_search': stock_ticker,
              'limit': 100}
    stock = session.get(url, params=params)
    stocks = stock.json()
    results = stocks['results']
    if len(results) == 0:
        print(f'Found no results for {stock_ticker}. Please check your search term.')
        exit(-1)
    # check all results for exact match
    result_list = []
    for result in results:
        if result['instrument_info']['symbol'] == stock_ticker:
            result_list.append(result)
    if len(result_list) > 1: #Don't want more than one result with the same stock ticker
        print(f'Found more than one result for {stock_ticker}. Please specify a more unique search term.')
        exit(-1)
    result = result_list[0]
    result_dict = {'symbol': result['instrument_info']['symbol'],
                   'id': result['instrument_info']['instrument_id'],
                   'name': result['instrument_info']['name'],
                   'currency': result['instrument_info']['currency'],
                   'price': result['price_info']['last']['price']}
    return result_dict

#Get account info
def get_account_info(session, account_alias):
    url = 'https://www.nordnet.dk/api/2/accounts'
    accounts = session.get(url)
    accounts = accounts.json()
    for acc in accounts:
        if acc['alias'] == account_alias:
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
    global account_dict
    account_dict = {'market_value': account_info['full_marketvalue']['value'], #stock value
                    'account_sum': account_info['account_sum']['value'], #cash
                    'total_value': account_info['own_capital']['value'], #total value
                    'currency': account_info['account_currency'], #account currency
                    'account_id': account_id
                    }
    return account_dict

# Get list of stocks in account
def get_account_stocks(session, account_alias):
    account_dict = get_account_info(session, account_alias)

    url = f'https://www.nordnet.dk/api/2/accounts/{account_dict["account_id"]}/positions'
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

    return pos_dataframe

# Method for reading the monthly pdf report from Nordnet
def read_pdf_report(file):

    # make dummy dataframe for now
    df = pd.DataFrame(columns=['Company', 'Ticker', 'Sector', 'Weight', 'Change'])
    #insert data into dummy dataframe
    df.loc[0] = ['Tomra Systems', 'TOM', 'Industrials', '6%', '-1%']
    df.loc[1] = ['Meta company', 'META', 'Tech', '5%', '1%']
    df.loc[1] = ['Alphabet', 'GOOG', 'Tech', '8%', '-2%']
    return df

# Method for generating a dataframe with the corrections to be made to the account portfolio
def generate_account_corrections(session, report_df, account_df):

    # read the report dataframe Ticker column
    report_tickers = report_df['Ticker'].tolist()

    for ticker in report_tickers:
        stock_info = get_stock_info(session, ticker)
        price_in_account_currency = convert_to_account_currency(session, stock_info['price'], stock_info['currency'])
        print(stock_info)
    

def convert_to_account_currency(session, amount, currency):

    account_currency = account_dict['currency']
    currency_convert_string = f'{currency}/{account_currency}'

    # Set NEXT cookie and header
    url = 'https://www.nordnet.dk/markedet'
    session.get(url)
    session.headers['client-id'] = 'NEXT'

    url = 'https://www.nordnet.dk/api/2/instrument_search/query/indicator'
    params = {'free_text_search': currency,
              'limit': 100}
    currency = session.get(url, params=params)
    currency = currency.json()
    for result in currency['results']:
        if result['instrument_info']['name'] == currency_convert_string:
            currency = result
            break
        #if currency is not found
        if result == currency['results'][-1]: #if last currency in list
            print(f'Currency {currency} not found. Please check your currency name.')
            exit(-1)
    conversion_rate = currency['price_info']['last']['price']
    amount_in_account_currency = amount*conversion_rate
    return amount_in_account_currency


