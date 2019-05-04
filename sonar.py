# coding=utf-8
import sys
import time
import potsdb
import json
import re
import hashlib
import requests
from string import Template
from datetime import date
from datetime import datetime
from datetime import timedelta

import config

if len(sys.argv) < 2:
	print('Give the start date as first argument: ' + sys.argv[0] + ' 2017-08-03')
	print('         or the number of day in past: ' + sys.argv[0] + ' 10')
	sys.exit()

utc_date = None
if '-' in sys.argv[1]:
	utc_date = datetime(*(time.strptime(sys.argv[1], '%Y-%m-%d')[0:6]))
else:
	utc_date = datetime.now() - timedelta(days=int(sys.argv[1]))

use_oldsonar = config.SonarQube['use_oldsonar']
oldsonar_host = config.SonarQube['host'] + '/timemachine?resource=${PROJECT}&metrics=coverage&fromDateTime=${DATE}T00:00:00%2B0200'

portfolios = config.SonarQube['host'] + '/components/search?qualifiers=VW'
project_tree = config.SonarQube['host'] + '/components/tree?qualifier=TRK&componentId=${ID}'
coverage = config.SonarQube['host'] + '/measures/search_history?component=${PROJECT}&metrics=coverage&from=${DATE}T00:00:00%2B0200'

def getEntriesFromResponse(json):
	return json['measures'][0]['history'] if not(use_oldsonar) else json[0]['cells']

def getDateFromEntry(entry):
	s = entry['date'] if not(use_oldsonar) else entry['d']
	return datetime(*(time.strptime(s[0:19], '%Y-%m-%dT%H:%M:%S')[0:6]))

def getValueFromEntry(entry):
	return float((entry['value'] if 'value' in entry else '0') if not(use_oldsonar) else entry['v'][0])


combine_projects = config.SonarQube['combine_projects']
if not(use_oldsonar):
	print("Fetching Portfolios:")
	combine_projects = {}
	response_portfolio = requests.get(portfolios,
	                                  auth = (config.SonarQube['username'], config.SonarQube['password']),
	                                  headers = {"Content-Type": "application/json"})
	if (response_portfolio.ok):
		for portf in response_portfolio.json()['components']:
			combine_projects[portf['key']] = []
			response_projects = requests.get(Template(project_tree).substitute(ID = portf['id']),
			                                 auth = (config.SonarQube['username'], config.SonarQube['password']),
			                                 headers = {"Content-Type": "application/json"})
			if (response_projects.ok):
				for prj in response_projects.json()['components']:
					combine_projects[portf['key']].append(prj['refKey'])
			else:
				print("Error while getting projects: " + response_projects.reason)
				raise SystemExit(6)
	else:
		print("Error while getting portfolios: " + response_portfolio.reason)
		raise SystemExit(6)

metrics = potsdb.Client(config.openTSDB['host'], port = config.openTSDB['port'], check_host = False)
url = Template(coverage if not(use_oldsonar) else oldsonar_host)
for identifier, projects in combine_projects.items():
	for project in projects:
		response = requests.get(url.substitute(PROJECT = project, DATE = utc_date.date().strftime('%Y-%m-%d')),
		                        auth = (config.SonarQube['username'], config.SonarQube['password']),
		                        headers = {"Content-Type": "application/json"})
		if (response.ok):
			for entry in getEntriesFromResponse(response.json()):
				d = getDateFromEntry(entry)
				val = getValueFromEntry(entry)
				print("")
				print("####################")
				print("# Date: " + d.date().strftime('%Y-%m-%d'))
				print("####################")
				
				tags = {
					'host': config.SonarQube['metrics_host'],
					'timestamp': str((d.toordinal() - date(1970, 1, 1).toordinal()) * 86400)
				}
				tags[config.SonarQube['metrics_project_tag']] = project
				print('Tags: ' + str(tags))
				print('    ' + config.SonarQube['metrics_base'] + '.' + identifier + ' = ' + str(val))
				metrics.log(config.SonarQube['metrics_base'] + '.' + identifier, val, **tags)

metrics.wait()
