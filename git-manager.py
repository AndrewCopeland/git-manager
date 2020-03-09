import yaml
import sys
from os import path
import tempfile
from subprocess import check_output
from os import listdir
from os.path import isfile, join
from shutil import copyfile
import json
import logging


global LOGGER

MANDATORY_GENERAL_PARAMETERS = [
	'pr-name',
	'branch-name',
	'commit-message',
	'git-add',
	'playbook-dir'
]


def create_logger():
	# create logger with 'spam_application'
	logger = logging.getLogger('git-manager')
	logger.setLevel(logging.DEBUG)
	# create file handler which logs even debug messages
	fh = logging.FileHandler('git-manager.logs')
	fh.setLevel(logging.DEBUG)
	# create console handler with a higher log level
	ch = logging.StreamHandler()
	ch.setLevel(logging.ERROR)
	# create formatter and add it to the handlers
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	fh.setFormatter(formatter)
	ch.setFormatter(formatter)
	# add the handlers to the logger
	logger.addHandler(fh)
	logger.addHandler(ch)
	logger.info("------------------ STARTING ------------------")
	logger.info("Logger initialized")
	return logger

def error_message(message):
	LOGGER.error(message)
	LOGGER.info("------------------ ENDING ------------------")
	# print("ERROR: {}".format(message))
	exit(1)

def validate_config(config):
	LOGGER.debug("Starting to validate config")
	if 'orgs' not in config:
		error_message("'orgs' was not provided in the config file")

	if 'general' not in config:
		error_message("'general' was not provided in the config file")

	general = config['general']
	for mandatory_parameter in MANDATORY_GENERAL_PARAMETERS:
		if mandatory_parameter not in general:
			error_message("'{}' was not provided in the config file".format(mandatory_parameter))
	LOGGER.debug("Successfully validated config")

def get_repo_dir(tmp_folder, org, repo):
	return "{}/{}/{}".format(tmp_folder, org, repo)

def get_config_file_path():
	LOGGER.debug("Starting to get config file path")
	# default config file path
	config_file_path = "git-manager-config.yml"
	# it can be provided as an argument
	if len(sys.argv) == 2:
		config_file_path = sys.argv[1]
	# validate the config file path actuall exists
	if not path.exists(config_file_path):
		error_message("'{}' does not exists or is not readable".format(config_file_path))
	LOGGER.debug("Using config file: '{}'".format(config_file_path))
	LOGGER.debug("Successfully retrieved config file")
	return config_file_path

def subprocess_command(command, working_dir):
	LOGGER.info("executing: {}".format(" ".join(command)))
	LOGGER.info(check_output(command, cwd=working_dir).decode('utf-8'))

def git_command(working_dir, command, org, repo):
	git_url = "https://github.com/{}/{}.git".format(org, repo)
	repo_dir = get_repo_dir(working_dir, org, repo)
	command = ['git', command, git_url, repo_dir]
	subprocess_command(command, None)

def git_clone(working_dir, org, repo):
	git_command(working_dir, "clone", org, repo)

def git_branch(working_dir, org, repo, branch_name):
	command = ['git', 'branch', branch_name]
	repo_dir = get_repo_dir(working_dir, org, repo)
	subprocess_command(command, repo_dir)

def git_checkout(working_dir, org, repo, branch_name):
	command = ['git', 'checkout', branch_name]
	repo_dir = get_repo_dir(working_dir, org, repo)
	subprocess_command(command, repo_dir)

def run_playbook(working_dir, org, repo, extra_vars):
	command = ['ansible-playbook', 'run.yml']
	if extra_vars is not None:
		command.append('--extra-vars')
		command.append(json.dumps(extra_vars))
	repo_dir = get_repo_dir(working_dir, org, repo)
	subprocess_command(command, repo_dir)

def get_config():
	config_file_path = get_config_file_path()
	# read the config content
	config_content = open(config_file_path, 'r').read()
	# create the python dictionary of the config, this will throw yaml 
	# exception if the config does not meet yaml standards
	config = yaml.load(config_content)

	# validate mandatory config fields
	validate_config(config)
	return config

def create_working_dir():
	dir_path = tempfile.mkdtemp()
	LOGGER.info("Created a tmp directory for cloning repos: " + dir_path)
	return dir_path

def clone_and_setup_repos(config, working_dir):
	for org, value in config['orgs'].items():
		repos = value['repos']
		for repo in repos:
			LOGGER.info("Cloning repo '{}/{}' and copying over files located in playbook directory".format(org, repo))
			git_clone(working_dir, org, repo)
			branch_name = config['general']['branch-name']
			# if we are creating branch then lets do it
			if config['general'].get('create-branch') is True:
				git_branch(working_dir, org, repo, branch_name)
			# now checkout branch
			git_checkout(working_dir, org, repo, branch_name)

			playbook_dir = config['general']['playbook-dir']
			# now copy over the playbook
			playbook_files = [f for f in listdir(playbook_dir) if isfile(join(playbook_dir, f))]
			for playbook_file in playbook_files:
				repo_dir = get_repo_dir(working_dir, org, repo)
				copyfile(playbook_dir + "/" + playbook_file, repo_dir + "/" + playbook_file)
			LOGGER.info("Finished cloning repo '{}/{}'".format(org, repo))

def update_repos(config, working_dir):
	extra_vars = {}
	if 'extra-vars' in config['general']:
		extra_vars = config['general']['extra-vars']

	for org, value in config['orgs'].items():
		repos = value['repos']
		for repo in repos:
			LOGGER.info("Running 'run.yml' in '{}/{}'".format(org, repo))
			extra_vars['org'] = org
			extra_vars['repo'] = repo
			run_playbook(working_dir, org, repo, extra_vars)
			LOGGER.info("Finished running 'run.yml' in '{}/{}'".format(org, repo))

def git_add(config, working_dir, org, repo):
	# this should be a list
	add_files = config['general']['git-add']
	command = ['git', 'add']
	command.extend(add_files)
	repo_dir = get_repo_dir(working_dir, org, repo)
	subprocess_command(command, repo_dir)

def git_commit(config, working_dir, org, repo):
	commit_message = config['general']['commit-message']
	command = ['git', 'commit', '-m', commit_message]
	repo_dir = get_repo_dir(working_dir, org, repo)
	subprocess_command(command, repo_dir)

def git_push(config, working_dir, org, repo):
	command = ['git', 'push']
	repo_dir = get_repo_dir(working_dir, org, repo)
	subprocess_command(command, repo_dir)

def git_add_commit_push_repos(config, working_dir):
	for org, value in config['orgs'].items():
		repos = value['repos']
		for repo in repos:
			git_add(config, working_dir, org, repo)
			git_commit(config, working_dir, org, repo)
			git_push(config, working_dir, org, repo)

# at this point we should have cloned, created a branch
# checked out this branch and copied over all of the files 
# in the playbook dir into the repo directories

def main():
	config=get_config()
	working_dir=create_working_dir()
	clone_and_setup_repos(config, working_dir)
	update_repos(config, working_dir)
	git_add_commit_push_repos(config, working_dir)

if __name__ == "__main__":
	LOGGER = create_logger()
	main()
	LOGGER.info("------------------ ENDING ------------------")

# shutil.rmtree(dir_path)




