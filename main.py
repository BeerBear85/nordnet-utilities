import argparse
import requests
import misc
import keyring
from getpass import getpass


#use argparse to parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument("--user", default="bear85", help="user name for Nordnet")
parser.add_argument("--account", default="AI depot", help="Nordnet konto name to use")
parser.add_argument("--report_path", default="report.pdf", help="Path for Nordnet monthly AI report")
args = parser.parse_args()

# Get password from windows credential manager or promt user for password
password =  keyring.get_password("nordnet",args.user)
if password is None:
    password = getpass("Password for " + args.user + ": ") # prompt user for password (do not show password)

session = misc.login(args.user, password) #login to Nordnet

account_df = misc.get_account_stocks(session, args.account) #get list of stocks in account
report_df = misc.read_pdf_report(args.report_path) #read the monthly pdf report from Nordnet
correction_df = misc.generate_account_corrections(session, report_df, account_df) #generate a dataframe with the corrections to be made to the account portfolio
misc.export_to_excel(correction_df) #export the correction dataframe to an excel file

#Logout from Nordnet
misc.logout(session)
