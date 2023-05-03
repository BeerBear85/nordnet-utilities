import requests
import pandas as pd
import xlsxwriter
#import camelot
import camelot.io as camelot


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
        exit(-1)

# Logout from Nordnet
def logout(session):
    url = 'https://www.nordnet.dk/api/2/authentication/basic/login'
    logout = session.delete(url)
    logout.close()
    # # Success
    # if logout.status_code == 200:
    #     return session
    # else:
    #     print(f'Log out of Nordnet failed with status code {logout.status_code}. The response was:')
    #     print(logout.text)
    #     exit(-1)


#Get info df for stock from Stock Ticker Symbols
def get_stock_info(session, stock_ticker, stock_exchange_country = 'DK'):
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
        if result['instrument_info']['symbol'] == stock_ticker and result['exchange_info']['exchange_country'] == stock_exchange_country:
            result_list.append(result)
    if len(result_list) > 1: #Don't want more than one result with the same stock ticker
        print(f'Found more than one result for {stock_ticker}. Please specify a more unique search term.')
        print('The following ticker and name were found:')
        for result in result_list:
            print(result['instrument_info']['symbol'], result['instrument_info']['name'])
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
    if positions.status_code == 204: #handle empty account
        #create and return empty dataframe
        pos_dataframe = pd.DataFrame(columns=['symbol', 'id', 'currency', 'qty', 'stock_price', 'sum_price_local', 'Weight'])
        return pos_dataframe
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
        pos_dict['Weight'] = pos_dict['sum_price_local']/account_dict['total_value']
        pos_dict_list.append(pos_dict)
    pos_dataframe = pd.DataFrame(pos_dict_list)

    return pos_dataframe

# Method for reading the monthly pdf report from Nordnet
def read_pdf_report(file):

    # # dummy dataframe:
    # df = pd.DataFrame(columns=['Company', 'Ticker', 'Sector', 'Weight', 'Change'])
    # #insert data into dummy dataframe
    # df.loc[0] = ['TOMRA SYSTEMS', 'TOM.NO', 'Industrials', '6%', '-1%']
    # df.loc[1] = ['Meta Platforms A', 'META.US', 'Tech', '5%', '1%']
    # df.loc[2] = ['Alphabet C', 'GOOG.US', 'Tech', '8%', '-2%']

    # Read the data from the pdf file
    tables = camelot.read_pdf(file, pages='1-end', flavor='stream')

    # Extract the data from the tables
    df_list = []
    for table in tables:
        df_list.append(table.df)

    #Only keep the tables with index 0 and 3
    #We know that the tables with index 0 and 3 contains the data we want
    df_list = [df_list[0], df_list[3]]

    column_name_translation = {'Selskab og handelslink': 'Company',
                               'Ticker': 'Ticker',
                               'Sektor': 'Sector',
                               'Aktuel vægt': 'Weight',
                               'Ændring': 'Change'}
    
    new_df_list = []
    for df in df_list:
        # Remove the first 2 rows of each dataframe (don't contain any data)
        df.drop(df.index[:2], inplace=True)
        # And use the first row as the header before dropping it
        df.columns = df.iloc[0] 
        df.drop(df.index[0], inplace=True)
        #reset the index
        df.reset_index(drop=True, inplace=True) 
        # Rename the columns
        df.rename(columns=column_name_translation, inplace=True)
        #If the value of the colum 'Change' is 'Ny!', then set the value equal to same as the value in the 'Weight' column
        df.loc[df['Change'] == 'Ny!', 'Change'] = df['Weight']
        
        # Divide the ticker into ticker and exchange (using the "." as a separator)
        df[['Ticker', 'Exchange']] = df['Ticker'].str.split('.', expand=True)
        # Translate from city code to country code
        exchange_translation = {'HE': 'FI', 
                                'OL': 'NO',
                                'CO': 'DK',
                                'ST': 'SE',
                                'US': 'US',}
        df['Exchange'] = df['Exchange'].map(exchange_translation)

        # Convert the weight to decimal and the change to float
        df['Weight'] = df['Weight'].str.replace('%', '').astype(float)/100
        df['Change'] = df['Change'].str.replace('%', '').astype(float)/100

        new_df_list.append(df)
    return new_df_list[1] #return the dataframe with the nordic stock info


# Method for generating a dataframe with the corrections to be made to the account portfolio
#The correction is a list of dictornaries with the following keys:
#name, ticker, current procent, target procent, current value [DKK], 
# target value[DKK], diff value [DKK], stock price [DKK], current qty, target qty, diff qty
def generate_account_corrections(session, report_df, account_df):

    correction_dict_list = []

    #itereate through the report dataframe
    for index, row in report_df.iterrows():
        #get the stock info from the report using the ticker
        stock_info = get_stock_info(session, row['Ticker'], row['Exchange'])

        #get the stock price in the account currency
        stock_price_in_account_currency = convert_to_account_currency(session, stock_info['price'], stock_info['currency'])
        # check if the stock is already in the account, and the current procentage, price and quantity
        if row['Ticker'] in account_df['symbol'].values:
            current_procent = account_df.loc[account_df['symbol'] == row['Ticker'], 'Weight'].iloc[0]
            current_procent = round(current_procent, 1) # round to 1 decimals
            current_value = account_df.loc[account_df['symbol'] == row['Ticker'], 'sum_price_local'].iloc[0]
            current_value = round(current_value, 2) # round to 2 decimals
            current_qty = account_df.loc[account_df['symbol'] == row['Ticker'], 'qty'].iloc[0]
            current_qty = round(current_qty, 1) # round to 1 decimals

        else:
            current_procent = 0.0
            current_value = 0.0
            current_qty = 0.0
        
        #calculate the target value
        target_value = row['Weight'] * account_dict['total_value']
        target_value = round(target_value, 2)  # round to 2 decimals
        #calculate the difference between the target and current value
        diff_value = target_value - current_value
        #calculate the target quantity
        target_qty = round(target_value/stock_price_in_account_currency, 1)
        #calculate the difference between the target and current quantity
        diff_qty = target_qty - current_qty

        #check that the name in the report is the same as the name in the stock_info
        if row['Company'] != stock_info['name']:
            print(f'Warning: the name of the stock in the report ({row["Company"]}) is not the same as the name in the stock info ({stock_info["name"]}).')

        correction_dict = {'name': row['Company'],
                           'ticker': row['Ticker'],
                           'current_procent': current_procent,
                           'target_procent': row['Weight'],
                           'current_value': current_value,
                           'target_value': target_value,
                           'diff_value': diff_value,
                           'stock_price': stock_price_in_account_currency,
                           'current_qty': current_qty,
                           'target_qty': target_qty,
                           'diff_qty': diff_qty
                           }
        correction_dict_list.append(correction_dict) #add the dictionary to the list

    # Convert the list of dictionaries to a dataframe
    df = pd.DataFrame(correction_dict_list)
    print(df)
    return df
    

def convert_to_account_currency(session, amount, currency):

    account_currency = account_dict['currency']
    if currency == account_currency:
        return round(amount, 2)
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
    return round(amount_in_account_currency, 2)

# Export the correction DF to an excel file, with columns width set to the max width of the content
def export_to_excel(df):
    #Export the correction DF to an excel file, with columns width set to the max width of the content
    writer = pd.ExcelWriter('corrections.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    for idx, col in enumerate(df):  # loop through all columns
        series = df[col]
        max_len = max((
            series.astype(str).map(len).max(),  # len of largest item
            len(str(series.name))  # len of column name/header
        )) + 2  # adding a little extra space
        worksheet.set_column(idx, idx, max_len)  # set column width
    # if value of diff_value is above absolut 1000, color the cell red
    format1 = workbook.add_format({'bg_color': '#FFC7CE',
                                    'font_color': '#9C0006'})
    worksheet.conditional_format('G2:G1000', {'type': 'cell',
                                            'criteria': '>=',
                                            'value': 1000,
                                            'format': format1})
    worksheet.conditional_format('G2:G1000', {'type': 'cell',
                                            'criteria': '<=',
                                            'value': -1000,
                                            'format': format1})
    
    writer.close()