#!/usr/bin/env python

import argparse, csv, getpass, logging, os, sys

import neo4j.exceptions
from neo4j import GraphDatabase
from timeit import default_timer as timer


class BloodHoundDatabase(object):
    def __init__(self, connection_string="bolt://localhost:7687", username="neo4j", password="neo4j",
                 dry_run=False):
        # Default Database Values
        self.neo4jDB = connection_string
        self.username = username
        self.password = password
        self.dry_run = dry_run
        self.driver = None
        self.db_validated = False
        self.logger = logging.getLogger('SessionHound')

    def connect_database(self):
        # Close the database if it is connected
        if self.driver is not None:
            self.driver.close()

        try:
            self.driver = GraphDatabase.driver(self.neo4jDB, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            self.logger.info('[+] Successfully connected.')
            return True
        except (neo4j.exceptions.AuthError, neo4j.exceptions.ServiceUnavailable) as e:
            self.logger.info('[-] Error connecting to neo4j: ')
            self.driver.close()
            self.logger.error(e.message)
            return False

    def session_exists(self, parameters):
        query = """MATCH (c:Computer), (u:User), p=(c)-[r:HasSession]->(u)
            WHERE c.name = $hostName AND u.name = $userName
            RETURN COUNT(p)"""

        try:
            session = self.driver.session()
            start = timer()
            results = session.run(query, parameters=parameters)

            self.logger.debug(
                '[+] {} with userName = {} and hostName = {} ran in {}s'.format(query, parameters['userName'],
                                                                                parameters['hostName'],
                                                                                timer() - start))
            result = results.single()
            session.close()

            return result is None or result[0] != 0

        except Exception as e:
            session.close()
            self.logger.error('[-] Neo4j query failed to execute.')
            self.logger.error(e)
            raise SystemExit

    def add_session(self, parameters):
        query = """MATCH (c:Computer), (u:User)
            WHERE c.name = $hostName AND u.name = $userName
            CREATE (c)-[r:HasSession]->(u)
            RETURN type(r)"""

        try:
            session = self.driver.session()
            start = timer()
            results = session.run(query, parameters=parameters)
            logger.debug('[+] {} with userName = {} and hostName = {} ran in {}s'.format(query, parameters['userName'],
                                                                                         parameters['hostName'],
                                                                                         timer() - start))

            result_list = []
            keys = results.keys()
            for result in results:
                result_list.append(result[keys[0]])
            session.close()
            return result_list

        except Exception as e:
            session.close()
            self.logger.error('[-] Neo4j query failed.')
            self.logger.error(e)
            raise SystemExit


def get_csv_data(csv_path):
    session_list = []
    with open(csv_path, 'r') as csvFile:
        header = next(csv.reader(csvFile))
        if not header == ['username', 'hostname']:
            logger.error("[-] Error in CSV file. Please ensure that your "
                         "CSV uses the headers 'username' and 'hostname'.")
            return None
    with open(csv_path, 'r') as csvFile:
        csv_reader = csv.DictReader(csvFile)
        try:
            for row in csv_reader:
                session_list.append({'userName': row['username'].upper(), 'hostName': row['hostname'].upper()})
        except Exception as e:
            print(row)
            print(e)
        return session_list


def main(csv_data, connection_string="bolt://localhost:7687", username="neo4j", password="neo4j", dry_run=False):
    # Create a BloodHound Neo4j Database Object
    bh_database = BloodHoundDatabase(connection_string=connection_string, username=username, password=password,
                                     dry_run=dry_run)

    # Connect to the Neo4j Database
    logger.info('[+] Connecting to Neo4j Database...')
    if not bh_database.connect_database():
        logger.info("[-] Unable to connect to neo4j database")
        return False

    # Import the data
    logger.info('[+] Importing data from CSV file...')
    if not dry_run:
        for user in csv_data:
            logger.debug(f"[+] Importing: {user}")

            if not bh_database.session_exists(user):
                if 'HasSession' in bh_database.add_session(user):
                    logger.info(
                        '[+] Successfully added session for {} to {}.'.format(user['userName'], user['hostName']))
                else:
                    logger.info('[-] Failed to add session for {} to {}.'.format(user['userName'], user['hostName']))
            else:
                logger.info(
                    '[+] Session information already exists for userName = {} on hostName = {}, skipping.'.format(
                        user['userName'], user['hostName']))
    else:
        logger.info('[+] No further action taken, as this is a dry-run.')


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        description='Import computer session data from a CSV file into BloodHound\'s Neo4j database.\n\n'
                    'The CSV should have two colums matching the following header '
                    'structure:\n\n[\'username\', \'hostname\']\n\n')
    parser.add_argument('csv', type=str, help='The path to the CSV file containing the session data to import.')
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687',
                        help='Neo4j connection string (Default: bolt://localhost:7687 )')
    parser.add_argument('-u', '--username', default='neo4j', help='Neo4j username (Default: neo4j)')
    parser.add_argument('--password', help='Neo4j password. If not provided on the command line, '
                                           'you will be prompted to enter it.')
    parser.add_argument('--debug', action='store_true', help='Print debug information.')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Verify connectivity to neo4j and check for '
                             'CSV parsing issues, but don\'t actually import data')
    args = parser.parse_args()

    if args.password is not None:
        neo4j_password = args.password
    else:
        neo4j_password = getpass.getpass(prompt='Neo4j Connection Password: ')

    # Setup logging
    if args.debug:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(name)s - %(levelname)s: %(message)s')
    logger = logging.getLogger('SessionHound')
    logger.debug('Debugging logging is on.')

    if args.csv:
        if os.path.exists(args.csv):
            csvData = get_csv_data(args.csv)
            if csvData:
                main(csvData, username=args.username, password=neo4j_password,
                     connection_string=args.neo4j_uri, dry_run=args.dry_run)
            else:
                logger.error('[-] Please check the format of your CSV file and ensure it has the expected structure.\n')
                parser.print_help(sys.stderr)
        else:
            logger.error('[-] The CSV file path is invalid.\n')
            parser.print_help(sys.stderr)
    else:
        logger.error('[-] No CSV file was provided, you must specify the path to a valid CSV file.\n')
        parser.print_help(sys.stderr)
