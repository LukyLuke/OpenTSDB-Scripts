# coding=utf-8
import sys
import time
import potsdb
import json
import re
import hashlib
import requests
from datetime import date
from datetime import datetime
from datetime import timedelta

import config

if len(sys.argv) < 2:
	print('Give the start date as first argument: ' + sys.argv[0] + ' 2017-08-03')
	print('			or the number of day in past: ' + sys.argv[0] + ' 10')
	sys.exit()

now_last = datetime.now().date()
utc_date = None

if '-' in sys.argv[1]:
	utc_date = datetime(*(time.strptime(sys.argv[1], '%Y-%m-%d')[0:6])) - timedelta(days=1)
else:
	utc_date = datetime.now() - timedelta(days=int(sys.argv[1]) + 1)

jqls = [
	{"new":    config.Jira['jql_new']}, 
	{"closed": config.Jira['jql_closed']}, 
	{"team":   config.Jira['jql_team']}, 
	{"total":  config.Jira['jql_total']}
]
tag_fields = [
	config.Jira['field_team'], 
	config.Jira['field_category'], 
	config.Jira['field_customer']
]
stat_fields = [
	config.Jira['field_prio']
]

regex = re.compile('[^a-zA-Z0-9]+')

def getTagValues(fields):
	tags = { 'host': config.Jira['metrics_host'] }
	for fieldname, field in fields.items():
			if fieldname in tag_fields:
				value = 'none'
				if field != None and 'value' in field:
					value = field['value']
				elif field != None and 'name' in field:
					value = field['name']
				tags[fieldname] = regex.sub('', value)
	return tags


def getFieldValues(cache, tag, fields):
	for fn, field in fields.items():
		if fn in stat_fields:
			fieldname = ''
			if 'value' in field:
				fieldname = fieldname + '_' + field['value']
			elif 'name' in field:
				fieldname = fieldname + '_' + field['name']

			# Total for this field
			fname = name + '_' + fn
			if fname not in cache[tag]:
				cache[tag][fname] = 0
			cache[tag][fname] += 1

			# Separated by the values
			fname = name + '_' + fn + '_' + regex.sub('', fieldname).lower()
			if fname not in cache[tag]:
				cache[tag][fname] = 0
			cache[tag][fname] += 1

metrics = potsdb.Client(config.openTSDB['host'], port = config.openTSDB['port'], check_host = False)
while utc_date.date() != now_last:
	utc_date = utc_date + timedelta(days=1)
	timestamp = str((utc_date.toordinal() - date(1970, 1, 1).toordinal()) * 86400)
	print("")
	print("####################")
	print("# Date: " + utc_date.date().strftime('%Y-%m-%d'))
	print("####################")

	for entry in jqls:
		name = list(entry.keys())[0]
		jql = list(entry.values())[0]
		payload = {
			"jql": jql.replace('${DATE}', utc_date.date().strftime('%Y-%m-%d')),
			"startAt": 0,
			"maxResults": 9999,
			"fields": tag_fields + stat_fields
		}

		response = requests.post(config.Jira['host'] + '/rest/api/latest/search',
		                        data = json.dumps(payload),
		                        auth = (config.Jira['username'], config.Jira['password']),
		                        headers = {"Content-Type": "application/json"})
		if (response.ok):
			fields_cache = {}
			tags_cache = {}
			for issue in response.json()['issues']:
				tags = getTagValues(issue['fields'])
				tagid = hashlib.sha1(json.dumps(tags, sort_keys=True).encode('utf-8')).hexdigest()

				if tagid not in tags_cache:
					tags_cache[tagid] = tags
					fields_cache[tagid] = {}

				getFieldValues(fields_cache, tagid, issue['fields'])

			for tagid, field in fields_cache.items():
				tags = tags_cache[tagid];
				tags['timestamp'] = timestamp
				print('Tags: ' + str(tags))

				for fld, val in field.items():
					print('	 ' + config.Jira['metrics_base'] + fld + ' = ' + str(val))
					metrics.log(config.Jira['metrics_base'] + fld, val, **tags)
				print("---")
		else:
			print(response)
			print(response.reason)
			print(response.headers)

metrics.wait()
