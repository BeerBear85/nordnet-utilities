import requests

# Login to Nordnet
def login(session, user, password):
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