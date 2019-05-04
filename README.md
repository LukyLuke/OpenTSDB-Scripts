# Jira and SonarQube in OpenTSDB

Two simple Python3 scripts for fill in Jira and Sonar (Coverage) statistics into an OpenTSDB.

# Configuration

Rename `config.py.example` to `config.py` and replace all needed values for your need. The configuration is multiple simple python dicts.

See sections below for more details.

You can use the gloabal Username and Password if you have the same on SonarQube and Jira:
```python
GlobalAuthData = {
	'username': 'USERNAME',
	'password': 'PASSWORD'
}
```

# OpenTSDB

There is currently only two configuration values needed:

```python
openTSDB = {
	'host': 'HOST',
	'port': 4242
}
```

# Jira

Jira does not have a time-machine so each day has to be requested with each query.

The Jira-Specific things are:
```python
Jira = {
	'username': GlobalAuthData['username'],
	'password': GlobalAuthData['password'],

	'host': 'https://jira.example.com',

	'metrics_base': 'bugs.jira.',
	'metrics_host': 'jira.example.com',

	'jql_team': 'issuetype = Bug AND status was in ("Ready to Develope", Development, Testing) on ${DATE}',
	'jql_new': 'issuetype = Bug AND status changed to "Ready to Develope" on ${DATE}',
	'jql_closed': 'issuetype = Bug AND status changed to (Closed, Resolved) on ${DATE} AND status was Testing on ${DATE}',
	'jql_total': 'issuetype = Bug AND category in ("Customers", "Development") AND status was not in (Resolved, Closed) on ${DATE}',

	'field_prio': 'priority',
	'field_team': 'customfield_10510',
	'field_customer': 'customfield_12910',
	'field_category': 'customfield_11310'
}
```

## Queries:

Test these queries first carefully in Jira before you start to fetch the data.

* **jql_team**: JQL to fetch all tickets for a given team on a day - ${DATE} is replaced by the date
* **jql_new**: JQL to fetch all tickets which are new on a date - ${DATE} is replaced by the date
* **jql_closed**: JQL to fetch all tickets which where closed on a day - ${DATE} is replaced by the date
* **jql_total**: JQL to fetch the total amount of tickets on a day - ${DATE} is replaced by the date

## Fields:

* **field_prio**: Field where the Ticket-Priority is
* **field_team**: Field where the Dev-Team is mentioned in - Custom Field
* **field_customer**: Field where the Customer is mentioned in - Custom Field
* **field_category**: Field where you have a potential category, like the domain - Custom Field

## Run it

Fill in OpenTSDB with the last 10 days:
```bash
$ python jira.py 10
```

Fill in OpenTSDB for all days since 2017-01-01:
```bash
$ python jira.py 2017-01-01
```

# SonarQube

SonarQube has a Time-Machine so there is only one call needed to fetch a lot of data.

The Sonar-Specific things are:

```python
SonarQube = {
	'username': GlobalAuthData['username'],
	'password': GlobalAuthData['password'],
	
	'host': 'https://codeanalysis.example.com/api',
	
	'metrics_base': 'coverage',
	'metrics_host': 'codeanalysis.example.com',
	'metrics_project_tag': 'project',
	
	'use_oldsonar': False,
	'combine_projects': {
		'ProjectOne': [ 'project:name-one-impl:release', 'project:name-one-api:release', 'project:name-one-domain:release' ],
		'ProjectTwo': [ 'project:name-two-impl:release', 'project:name-two-api:release', 'project:name-two-domain:release' ]
	}
}
```
If you use a SonarQube-Version older than 6.0 or so, you have to use the *use_oldsonar* and also define the projects and summarisation by yourself in *combine_projects*.
If you use a newer Sonar, the Portfolios are read out and the Projects are grouped automatically.

