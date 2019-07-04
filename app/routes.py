from flask import render_template, flash
from flask import request
from app import app
from app.forms import QueryForm
from app.jiraquery import get_jira_query_results
import urllib
from app.jira_graph_viz_config import Configs

@app.route('/', methods=['GET','POST'])
@app.route('/index', methods=['GET','POST'])
def index():
	form = QueryForm()
	query = request.args.get('query')

	jira_configs = Configs()
	authed_jira = jira_configs.authed_jira

	if form.validate_on_submit():
		flash('Query submitted: {}'.format(form.query.data))
		return submit_query(form.query.data, authed_jira)
	elif query:
		flash('Query submitted: {}'.format(query))
		return submit_query(query, authed_jira)
	else:
		return display_home()

@app.route('/health', methods=['GET'])
def health():
	return 'JIRA-GRAPH-VIZ Online'

def submit_query(query, authed_jira):

	dataset, links, query_list, linked_epic_query_string, query_epic_set, error = get_jira_query_results(
		query_string=query, threading=True, authed_jira=authed_jira)
	if error is not None:
		flash('Error Code: {} - {}'.format(error.status_code, error.text))
	else:
		add_linked_epics_to_dataset_links(dataset, linked_epic_query_string, authed_jira)
		add_children_of_epics_in_query_epic_set_to_dataset(dataset, query_epic_set, authed_jira)
		flash('Issues in query results: {}'.format(len(dataset)))
		url = request.url_root + "index?query=" + urllib.parse.quote(str(query))
		flash('Share this jira-graph-viz: {}'.format(url))

	form = QueryForm()
	form.query.data = query
	return render_template('index.html', form=form, dataset=dataset, links=links, query_list=query_list)

def add_children_of_epics_in_query_epic_set_to_dataset(dataset, query_epic_set, authed_jira):
	if query_epic_set:
		epic_link_hash = {}
		query_epic_tuple = tuple(query_epic_set)
		epic_link_dataset, _, _, _, _, _ = get_jira_query_results(
			query_string='"Epic Link" in {}'.format(query_epic_tuple), threading=True, authed_jira=authed_jira)
		for issue in epic_link_dataset:
			for linked_issue in issue['issuelinks']:
				if 'issuetype' in linked_issue and linked_issue['issuetype'] == 'Epic':
					epic_key = linked_issue['key']
					if epic_key in epic_link_hash:
						epic_link_hash[epic_key].append(issue)
					else:
						epic_link_hash[epic_key] = [issue]
		for issue in dataset:
			if issue['key'] in epic_link_hash:
				for epic_link_issue in epic_link_hash[issue['key']]:
					issue['issuelinks'].append(epic_link_issue)

def add_linked_epics_to_dataset_links(dataset, linked_epic_query_string, authed_jira):
	epic_hash = {}
	if linked_epic_query_string != 'issuekey in ()':
		flash('Linked Epic query submitted: {}'.format(linked_epic_query_string))
		#get data for epics that are 'linked' to tickets in initial query and add them as links
		linked_epic_dataset, _, _, _, _, _ = get_jira_query_results(query_string=linked_epic_query_string,
																	threading=True, authed_jira=authed_jira)

		for epic in linked_epic_dataset:
			if 'key' in epic:
				epic_hash[epic['key']] = epic
		for issue in dataset:
			for linked_issue in issue['issuelinks']:
				if linked_issue['key'] in epic_hash and 'issuetype' in linked_issue and linked_issue[
					'issuetype'] == 'Epic':
					if 'summary' in epic_hash[linked_issue['key']]:
						linked_issue['summary'] = epic_hash[linked_issue['key']]['summary']
					if 'priority' in epic_hash[linked_issue['key']]:
						linked_issue['priority'] = epic_hash[linked_issue['key']]['priority']
					if 'status' in epic_hash[linked_issue['key']]:
						linked_issue['status'] = epic_hash[linked_issue['key']]['status']

def display_home():
	dataset = {}
	links = {}
	query_list = []
	return render_template('index.html', form=QueryForm(), dataset=dataset, links=links, query_list=query_list)
