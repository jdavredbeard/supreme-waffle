#!/usr/bin/env python

import configparser
import jira
import os
import json
import jira
from jira.exceptions import JIRAError

def get_jira_query_results(query_string):
	SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

	Config = configparser.ConfigParser()
	Config.read(SCRIPT_DIR + '/' + 'config.ini')

	url = Config.get('Basic', 'url')
	username = Config.get('Auth', 'username')
	password = Config.get('Auth', 'password')

	try:
		authed_jira = jira.JIRA(url, basic_auth=(username, password))
		issues = authed_jira.search_issues(query_string, fields='assignee,summary,status,issuetype,priority,project,issuelinks,subtasks,customfield_10007,customfield_10006')

		tickets = []
		querySet = set()
		allLinks = []
		linksInTickets = []
		epic_set = set()


		for issue in issues:
			links = issue.fields.issuelinks
			subtasks = issue.fields.subtasks
			link_data = []

			for link in links:
				if link is not None:

					data = {
						'type': link.type.name,
						'inwardtype': link.type.inward,
						'outwardtype': link.type.outward,
					}
					if 'inwardIssue' in vars(link).keys():
						data['direction'] = 'inward'
						data['key'] = link.inwardIssue.key
						data['summary'] = link.inwardIssue.fields.summary
						data['status'] = link.inwardIssue.fields.status.name
						data['issuetype'] = link.inwardIssue.fields.issuetype.name
						data['priority'] = link.inwardIssue.fields.priority.name

						#d3 links array
						allLinks.append({
						'source': issue.key,
						'target': link.inwardIssue.key,
						'type': link.type.name,
						'direction': 'inward'
						})
					elif 'outwardIssue' in vars(link).keys():
						data['direction'] = 'outward'
						data['key'] = link.outwardIssue.key
						data['summary'] = link.outwardIssue.fields.summary
						data['status'] = link.outwardIssue.fields.status.name
						data['issuetype'] = link.outwardIssue.fields.issuetype.name
						data['priority'] = link.outwardIssue.fields.priority.name

						allLinks.append({
						'source': issue.key,
						'target': link.outwardIssue.key,
						'type': link.type.name,
						'direction': 'outward'
						})
					#add data to array to be held within issue data	
					link_data.append(data)
					
			for subtask in subtasks:
				if subtask is not None:
					data = {
						'type': 'subtask',
						'key': subtask.key,
						'summary': subtask.fields.summary,
						'status': subtask.fields.status.name,
						'priority': subtask.fields.priority.name
					}
					link_data.append(data)



			data = {
				'key': issue.key,
				'summary': issue.fields.summary,
				'status': issue.fields.status.name,
				'issuetype': issue.fields.issuetype.name,
				'priority': issue.fields.priority.name,
				'project': issue.fields.project.name,
				'issuelinks': link_data
			}
			if issue.fields.assignee is not None:
				data['assignee'] = issue.fields.assignee.name
			#customfield_10006 = sprint
			if 'customfield_10006' in vars(issue.fields).keys():
				if len(issue.fields.customfield_10006) > 0:			
					for chunk in issue.fields.customfield_10006[0].split(','):
						bite = chunk.split('=')
						if  bite[0] == 'name':
							data['sprint'] = bite[1]
							break 
			#customfield_10007 = epic key			
			if issue.fields.customfield_10007 is not None:
				epic_set.add(issue.fields.customfield_10007)	

			tickets.append(data)
			querySet.add(issue.key)

		for link in allLinks:
			if link['source'] in querySet and link['target'] in querySet:
				link['addedBy'] = 'query'

		query_list = list(querySet)
		epic_list = list(epic_set)
		epic_query_string = 'issuekey in (' + ','.join(epic_list) + ')' 



		
		return tickets, linksInTickets, query_list, epic_query_string, None
	

	except JIRAError as e:
		return [], [], [], "", e

