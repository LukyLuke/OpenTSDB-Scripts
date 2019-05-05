# coding=utf-8
import os
import sys
import time
import potsdb
import json
import re
import requests
from string import Template
from datetime import date
from datetime import datetime
from datetime import timedelta

import config

num_env = os.getenv('FETCH_NUM_DAYS', '') if len(sys.argv) < 2 else sys.argv[1]

if len(num_env) == 0:
	print('Give the start date as first argument: ' + sys.argv[0] + ' 2017-08-03')
	print('         or the number of day in past: ' + sys.argv[0] + ' 10')
	sys.exit()

config.openTSDB['host'] = config.openTSDB['host'] if os.getenv('OPENTSDB_HOST', 'None') == 'None' else os.getenv('OPENTSDB_HOST', '127.0.0.1')
config.openTSDB['port'] = config.openTSDB['port'] if os.getenv('OPENTSDB_PORT', 'None') == 'None' else int(os.getenv('OPENTSDB_PORT', '4242'))

config.GlobalAuthData['username'] = config.GlobalAuthData['username'] if os.getenv('AUTH_USERNAME', 'None') == 'None' else os.getenv('AUTH_USERNAME', '')
config.GlobalAuthData['password'] = config.GlobalAuthData['password'] if os.getenv('AUTH_PASSWORD', 'None') == 'None' else os.getenv('AUTH_PASSWORD', '')

metrics = potsdb.Client(config.openTSDB['host'], port = config.openTSDB['port'], check_host = True)

utc_date = None
if '-' in num_env:
	utc_date = datetime(*(time.strptime(num_env, '%Y-%m-%d')[0:6]))
else:
	utc_date = datetime.now() - timedelta(days=int(num_env))

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
				print('Portfolio: ' + portf['key'])
				for prj in response_projects.json()['components']:
					print('	' + prj['refKey'])
					combine_projects[portf['key']].append(prj['refKey'])
				print('')
			else:
				print("Error while getting projects: " + response_projects.reason)
				raise SystemExit(6)
	else:
		print("Error while getting portfolios: " + response_portfolio.reason)
		raise SystemExit(6)

regex = re.compile('[^a-zA-Z0-9]+')

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
				tags = {
					'host': config.SonarQube['metrics_host'],
					'timestamp': str((d.toordinal() - date(1970, 1, 1).toordinal()) * 86400)
				}
				tags[config.SonarQube['metrics_project_tag']] = regex.sub('_', project)
				print(str(tags))
				print('    ' + config.SonarQube['metrics_base'] + '.' + identifier + ' = ' + str(val))
				metrics.log(config.SonarQube['metrics_base'] + '.' + identifier, val, **tags)

metrics.wait()
