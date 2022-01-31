# SessionHound & GroupHound
A pair of scripts to import session and local group information that has been collected from alternate data sources into BloodHound's Neo4j database.

## Problem
SharpHound's privileged session collection requires an account with elevated permissions to operate. When using BloodHound as a Blue tool to locate and resolve misconfigurations and identify dangerous behaviors, detailed and accurate session information is highly beneficial. An account that has local administrative rights on all endpoints is a security risk.

## Solution
Session information can be obtained from alternate sources. This information can be obtained by collecting the information from centrally logged local Windows Security Events or from other tools that can poll information about logged on users from live endpoints. It can be collected into a spreadsheet and added to the BloodHound database via Cypher queries.

## Requirments
```
neo4j
```

## SessionHound Usage
```
usage: SessionHound.py [-h] [--neo4j-uri NEO4J_URI] [-u USERNAME]
                       [--password PASSWORD] [--debug] [--dry-run]
                       csv

Import computer session data from a CSV file into BloodHound's Neo4j database.
The CSV should have two colums matching the following header structure:
['username', 'hostname']

positional arguments:
  csv                   The path to the CSV file containing the session data
                        to import.

optional arguments:
  -h, --help            show this help message and exit
  --neo4j-uri NEO4J_URI
                        Neo4j connection string (Default:
                        bolt://localhost:7687 )
  -u USERNAME, --username USERNAME
                        Neo4j username (Default: neo4j)
  --password PASSWORD   Neo4j password. If not provided on the command line,
                        you will be prompted to enter it.
  --debug               Print debug information.
  --dry-run             Verify connectivity to neo4j and check for CSV parsing
                        issues, but don't actually import data
```

## SessionHound CSV File Format
The CSV file needs to have two columns:
- username: The User Principal Name (UPN). i.e. USER01@EXAMPLE.COM
- hostname: The Host's FQDN. i.e. HOSTNAME.EXAMPLE.COM

### SessionHound CSV Example
```
username,hostname
user01@example.com,host01.example.com
user02@example.com,host01.example.com
user02@example.com,host02.example.com
```

## GroupHound Usage
```
usage: GroupHound.py [-h] [-d DOMAIN] [-c CSV] [-t TYPE]

Import computer local group data from a CSV file into BloodHound's Neo4j database. The CSV should have three colums matching the following header structure: ['username', 'hostname',
'type']

optional arguments:
  -h, --help            show this help message and exit
  -d DOMAIN, --domain DOMAIN
                        The base AD Domain for your environment. i.e. EXAMPLE.COM
  -c CSV, --csv CSV     The path to the CSV file containing the session data to import.
  -t TYPE, --type TYPE  The access type: AdminTo or CanRDP.
```

## GroupHound CSV File Format
The CSV file needs to have three columns:
- username: The User Principal Name (UPN). i.e. USER01@EXAMPLE.COM
- hostname: The Host's FQDN. i.e. HOSTNAME.EXAMPLE.COM
- type: The object type. Group or User

### Groupound CSV Example
```
username,hostname,type
user01@example.com,host01.example.com,User
user02@example.com,host01.example.com,User
group01@example.com,host02.example.com,Group
group02@example.com,host02.example.com,Group
```

**NOTE:** If using Excel to prepare your CSV, saving the CSV in Unicode/UTF-8 format will cause some errors. To avoid these issues use the **CSV (Comma delimited)** option and not **CSV UTF-8 (Comma delimited)**.
