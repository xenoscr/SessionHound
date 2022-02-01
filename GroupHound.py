#!/usr/bin/env python

import argparse, csv, getpass, logging, os, sys, warnings

import neo4j.exceptions
from neo4j import GraphDatabase
from timeit import default_timer as timer


class BloodHoundDatabase(object):
    def __init__(self, connection_string="bolt://localhost:7687", username="neo4j", password="neo4j"):
        # Default Database Values
        self.neo4jDB = connection_string
        self.username = username
        self.password = password
        self.driver = None
        self.logger = logging.getLogger('GroupHound')

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
            self.logger.error(e.message)
            self.driver.close()
            return False

    def run_query(self, query, parameters=None, relation=None, query_type=None):
        try:
            session = self.driver.session()
            start = timer()
            if parameters['type']:
                query = query.format(lType=parameters['type'], relation=relation)
            results = session.run(query, parameters=parameters)
            self.logger.debug(f"[+] {query} with userName = {parameters['userName']} and "
                              f"hostName = {parameters['hostName']} "
                              f"ran in {timer() - start}s")
        except Exception as e:
            session.close()
            self.logger.error('[-] Neo4j query failed to execute.')
            self.logger.error(e)
            raise SystemExit
        if query_type == 'int':
            for result in results:
                session.close()
                return result[0]
        elif query_type == 'list':
            result_list = []
            keys = results.keys()
            for result in results:
                full_return = ''
                total_keys = len(keys)
                for key in range(0, total_keys):
                    full_return += f'{keys[key]}: {result[key]}'
                    if (key + 1) < total_keys:
                        self.logger.debug(f'[+] key: {key}, total_keys: {total_keys}')
                        full_return += ', '
                result_list.append(full_return)
            session.close()
            return result_list
        else:
            result_list = []
            keys = results.keys()
            for result in results:
                result_list.append(result[keys[0]])
            session.close()
            return result_list


def get_csv_data(csv_path):
    session_list = []
    with open(csv_path, 'r') as csvFile:
        header = next(csv.reader(csvFile))
        if not header == ['username', 'hostname', 'type']:
            return None
    with open(csv_path, 'r') as csvFile:
        csv_reader = csv.DictReader(csvFile)
        try:
            for row in csv_reader:
                session_list.append({'userName': row['username'].upper(), 'hostName': row['hostname'].upper(),
                                     'type': row['type'].capitalize()})
        except Exception as e:
            logger.error('[-] Exception while reading CSV data: ')
            logger.error(row)
            logger.error(e)
        return session_list


def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error(f"[-] The file {arg} does not exist!")
    else:
        return arg


def main(csv_data, relation_type, connection_string="bolt://localhost:7687", username="neo4j", password="neo4j",
         dry_run=False):
    # Create a BloodHound Neo4j Database Object
    bh_database = BloodHoundDatabase(connection_string=connection_string, username=username, password=password)

    # Connect to the Neo4j Database
    logger.info('[+] Connecting to Neo4j Database...')
    if not bh_database.connect_database():
        logger.info("[-] Unable to connect to neo4j database")
        return False

    # Set the relationship type
    if relation_type == 'adminto':
        relation = "AdminTo"
    elif relation_type == 'canrdp':
        relation = "CanRDP"
    elif relation_type == 'canpsremote':
        relation = "CanPSRemote"
    elif relation_type == 'executedcom':
        relation = "ExecuteDCOM"

    exists_query = """MATCH (c:Computer), (u:{lType}), p=(u)-[r:{relation}]->(c)
        WHERE c.name = $hostName AND u.name = $userName
        RETURN COUNT(p)"""
    add_query = """MATCH (c:Computer), (u:{lType})
        WHERE c.name = $hostName AND u.name = $userName
        CREATE (u)-[r:{relation}]->(c)
        RETURN type(r)"""

    exists_query_sid = """MATCH (c:Computer), (u:{lType}), p=(u)-[r:{relation}]->(c)
        WHERE c.name = $hostName AND u.objectid = $userName
        RETURN COUNT(p)"""
    add_query_sid = """MATCH (c:Computer), (u:{lType})
        WHERE c.name = $hostName AND u.objectid = $userName
        CREATE (u)-[r:{relation}]->(c)
        RETURN type(r)"""
    if not dry_run:
        # Import the data
        logger.info('[+] Importing data from CSV file...')
        for user in csv_data:
            logger.debug(user)
            if user['userName'].upper().startswith('S-1-5-'):
                user['userName'] = user['userName'].split('@')[0]
                if bh_database.run_query(exists_query_sid, user, relation, 'int') < 1:
                    if relation in bh_database.run_query(add_query_sid, user, relation):
                        logger.info(f"[-] Successfully added {relation} relation for {user['userName']} "
                                    f"to {user['hostName']}.")
                    else:
                        logger.info(f"[-] Failed to add {relation} relation for {user['userName']} to "
                                    f"{user['hostName']}. Verify that username and hostname exist and try running "
                                    f"again.")
                else:
                    # Try to see if it's a group
                    user['type'] = "Group"
                    if bh_database.run_query(exists_query_sid, user, relation, 'int') < 1:
                        if relation in bh_database.run_query(add_query_sid, user, relation):
                            logger.info(f"[+] Successfully added {relation} relation "
                                        f"for {user['userName']} to {user['hostName']}.")
                        else:
                            logger.info(f"[-] Failed to add {relation} relation for {user['userName']} "
                                        f"to {user['hostName']}. Verify that username and hostname exist and try "
                                        f"running again.")
                    else:
                        logger.info(f"[-] {relation} relation already exists for userName = {user['userName']} "
                                    f"on hostName = {user['hostName']}, skiping.")
            else:
                if bh_database.run_query(exists_query, user, relation, 'int') < 1:
                    if relation in bh_database.run_query(add_query, user, relation):
                        logger.info(f"[+] Successfully added {relation} relation for {user['userName']} "
                                    f"to {user['hostName']}.")
                    else:
                        logger.info(f"[-] Failed to add {relation} relation "
                                    f"for {user['userName']} to {user['hostName']}. Verify that username and hostname "
                                    f"exist and try running again.")
                else:
                    logger.info(f"[-] {relation} relation already exists for userName = {user['userName']} "
                                f"on hostName = {user['hostName']}, skiping.""")

    else:
        logger.info('[+] No further action taken, as this is a dry-run.')


if __name__ == "__main__":

    # Parse the command line arguments
    parser = argparse.ArgumentParser(description='Import computer local group  data from a CSV file into '
                                                 'BloodHound\'s Neo4j database.\n\nThe CSV should have three colums '
                                                 'matching the following header structure:'
                                                 '\n\n[\'username\', \'hostname\', \'type\']\n\n')

    parser.add_argument('csv', type=lambda x: is_valid_file(parser, x), help='The path to the CSV file containing'
                                                                             ' the session data to import.')
    parser.add_argument('type', type=str.lower, choices=['adminto', 'canrdp', 'canpsremote', 'executedcom'],
                        help='The access type: AdminTo, CanRDP, CanPSRemote, or ExecuteDCOM.')
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
    logger = logging.getLogger('GroupHound')
    logger.debug('Debugging logging is on.')

    # Filter out warnings from neo4j's verify_connectivity
    warnings.filterwarnings('ignore', "The configuration may change in the future.")

    csv_data = get_csv_data(args.csv)
    if csv_data:
        main(csv_data, args.type, username=args.username, password=neo4j_password,
             connection_string=args.neo4j_uri, dry_run=args.dry_run)
    else:
        logger.error('[-] Please check the format of your CSV file and ensure it has the expected structure.')
        parser.print_help(sys.stderr)
