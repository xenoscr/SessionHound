#!/usr/bin/env python

import argparse, csv, datetime, getpass, logging, os, sys
from neo4j import GraphDatabase
from timeit import default_timer as timer

class bhDB(object):
    def __init__(self, logging, domain):
        # Default Database Values
        self.neo4jDB = 'bolt://localhost:7687'
        self.username = 'neo4j'
        self.password = 'neo4jj'
        self.domain = domain
        self.driver = None
        self.db_validated = False
        self.logging = logging

    def showDomain(self):
        print('The current domain setting is:')
        print('Domain: {}\n'.format(self.domain))
        
    def updateDomain(self):
        print(self.domain)
        self.domain = input_default('Enter the domain name.', self.domain)
        self.domain = self.domain.upper()
        
    def showDBInfo(self):
        print('The current database settings are:')
        print('Neo4j URL: {}'.format(self.neo4jDB))
        print('Username: {}'.format(self.username))
        print('Password: {}\n'.format(self.password))
    
    def updateDBInfo(self):
        self.neo4jDB = input_default('Enter the Neo4j Bolt URL:', self.neo4jDB)
        self.username = input_default('Enter the username:', self.username)
        self.password = input_default('Enter the password:', self.password, True)
        print('\n')
    
    def connectDB(self):
        # Close the database if it is connected
        if self.driver is not None:
            self.driver.close()
        
        # Connect to the database
        while self.db_validated == False:
            self.driver = GraphDatabase.driver(self.neo4jDB, auth=(self.username, self.password))
            self.db_validated = self.validateDB()
            if not self.db_validated:
                print('\nUnable to validate provided domain and database settings. Please verify provided values:')
                self.updateDomain()
                self.updateDBInfo()

    def validateDB(self):
        print('Validating Selected Domain')
        session = self.driver.session()
        domainRegex = "[A-Z]*.{}".format(self.domain)
        try:
            result = session.run("MATCH (n) WHERE n.domain =~ $domain RETURN COUNT(n)", domain=domainRegex).value()
        except Exception as e:
            self.logging.debug('Unable to connect to the neo4j database')
            self.logging.error(e)
            
        if (int(result[0]) > 0):
            return True
        else:
            return False
    
    def closeDB(self):
        try:
            self.driver.close()
            logging.info('Successfully closed Neo4j database.')
        except Exception as e:
            logging.error('Failed to close Neo4j database.')
            logging.error(e)
    
    def runQuery(self, query, parameters=None, queryType=None):
        try:
            session = self.driver.session()
            start = timer()
            results = session.run(query, parameters=parameters)
            logging.debug('{} with userName = {} and hostName = {} ran in {}s'.format(query, parameters['userName'], parameters['hostName'], timer() - start))
        except Exception as e:
            logging.error('Query failed.')
            logging.error(e)
            raise SystemExit
        if queryType == 'int':
            for result in results:
                return result[0]
        elif queryType == 'list':
            resultList = []
            keys = results.keys()
            for result in results:
                fullRet = ''
                tKeys = len(keys)
                for key in range(0, tKeys):
                    fullRet += '{}: {}'.format(keys[key], result[key])
                    if (key + 1) < tKeys:
                        logging.debug('key: {}, tKeys: {}'.format(key, tKeys))
                        fullRet += ', '
                resultList.append(fullRet)
            return resultList
        else
            resultList = []
            keys = results.keys()
            for result in results:
                resultList.append(result[keys[0]])
            return resultList

def input_default(prompt, default, secure=False):
    if secure:
        return getpass.getpass('{} [{}]:'.format(prompt, default)) or default
    else:
        return input('{} [{}]'.format(prompt, default)) or default

def query_yes_no(question, default="no"):
    valid = {'yes': True, 'y': True, 'ye': True, 'no': False, 'n': False}

    if default == None:
        prompt = ' [y/n] '
    elif default.lower() == 'yes':
        prompt = ' [Y/n] '
    elif default.lower() == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError('Invalid default answer: {}'.format(default))

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

def getCSVData(csvPath):
    sessionList = []
    with open(csvPath, 'r') as csvFile:
        header = next(csv.reader(csvFile))
        if not header == ['username', 'hostname']:
            return None
    with open(csvPath, 'r') as csvFile:
        csvReader = csv.DictReader(csvFile)
        try:
            for row in csvReader:
                sessionList.append({'userName': row['username'].upper(), 'hostName':  row['hostname'].upper()})
        except Exception as e:
            print(row)
            print(e)
        return sessionList

def main(csvData, domain):
    # Create a BloodHound Neo4j Database Object
    bhDatabase = bhDB(logging, domain.upper())

    # Ask if the domain needs to be corrected
    bhDatabase.showDomain()
    if query_yes_no('Would you like to change the domain name?'):
        bhDatabase.updateDomain()

    # Show DB settings and prompt to change
    bhDatabase.showDBInfo()
    if query_yes_no('Would you like to change the Neo4j DB settings?'):
        bhDatabase.updateDBInfo()

    # Space it out
    print('\n')

    # Connect to the Neo4j Database
    print('[+] Connecting to Neo4j Database...')
    bhDatabase.connectDB()

    # Import the data
    print('[+] Importing data from CSV file...')

    existsQuery = """MATCH (c:Computer), (u:User), p=(c)-[r:HasSession]->(u)
        WHERE c.name = $hostName AND u.name = $userName
        RETURN COUNT(p)"""
    addQuery = """MATCH (c:Computer), (u:User)
        WHERE c.name = $hostName AND u.name = $userName
        CREATE (c)-[r:HasSession]->(u)
        RETURN type(r)"""

    for user in csvData:
        if bhDatabase.runQuery(existsQuery, user, 'int') < 1:
            if 'HasSession' in bhDatabase.runQuery(addQuery, user):
                logging.info('Successfully added session for {} to {}.'.format(user['userName'], user['hostName']))
            else:
                logging.info('Failed to add session for {} to {}.'.format(user['userName'], user['hostName']))
        else:
            logging.info('Session information already exists for userName = {} on hostName = {}, skiping.'.format(user['userName'], user['hostName']))

if __name__ == "__main__":
    # Setup logging
    logLvl = logging.INFO
    logging.basicConfig(level=logLvl, format='%(asctime)s - %(levelname)s: %(message)s')
    logging.debug('Debugging logging is on.')

    # Parse the command line arguments
    parser = argparse.ArgumentParser(description = 'Import computer session data from a CSV file into BloodHound\'s Neo4j database.\n\nThe CSV should have two colums matching the following header structure:\n\n[\'username\', \'hostname\']\n\n')
    parser.add_argument('-d', '--domain', type=str, help='The base AD Domain for your environment. i.e. EXAMPLE.COM')
    parser.add_argument('-c', '--csv', type=str, help='The path to the CSV file containing the session data to import.')
    args = parser.parse_args()

    if args.domain:
        if args.csv:
            if os.path.exists(args.csv):
                csvData = getCSVData(args.csv)
                if csvData:
                    main(csvData, args.domain)
                else:
                    print('Please check the format of your CSV file and ensure it has the expected structure.\n')
                    parser.print_help(sys.stderr)
            else:
                print('The CSV file path is invalid.\n')
                parser.print_help(sys.stderr)
        else:
            print('No CSV file was provided, you must specify the path to a valid CSV file.\n')
            parser.print_help(sys.stderr)
    else:
        print('No base AD domain name was proided, you must specify a base domain.\n')
        parser.print_help(sys.stderr)
